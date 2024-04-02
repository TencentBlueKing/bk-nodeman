# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import base64
from typing import Any, Dict, List, Optional, Union

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.core.concurrent import controller
from apps.node_man import constants, models
from apps.node_man.handlers.password import TjjPasswordHandler
from apps.utils import concurrent
from pipeline.core.flow import Service

from .. import core
from .base import AgentBaseService, AgentCommonData


class QueryPasswordService(AgentBaseService):
    """
    查询主机密码，可根据实际场景自行定义密码库查询处理器
    """

    def inputs_format(self):
        return super().inputs_format() + [
            Service.InputItem(name="creator", key="creator", type="str", required=True),
        ]

    @controller.ConcurrentController(
        data_list_name="cloud_ip_list",
        batch_call_func=concurrent.batch_call,
        extend_result=False,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.QUERY_PASSWORD.value},
    )
    def query_password(
        self,
        cloud_ip_list: List[str],
        cloud_ip_map: Dict[str, Dict[str, Union[models.Host, int]]],
        creator: str,
        oa_ticket: str,
    ):
        is_ok, success_ips, failed_ips, err_msg = TjjPasswordHandler().get_password(
            creator, cloud_ip_list, ticket=oa_ticket
        )
        if not is_ok:
            sub_inst_ids = [cloud_ip_map[cloud_ip]["sub_inst_id"] for cloud_ip in cloud_ip_list]
            self.log_error(sub_inst_ids=sub_inst_ids, log_content=err_msg)
            self.move_insts_to_failed(
                sub_inst_ids=sub_inst_ids, log_content=_("若 OA TICKET 过期，请重新登录 OA 后再重试您的操作。请注意不要直接使用此任务中的重试功能~")
            )

        return {"is_ok": is_ok, "success_ips": success_ips, "failed_ips": failed_ips, "err_msg": err_msg}

    def check_and_update_identity_data(
        self, sub_insts: List[models.SubscriptionInstanceRecord]
    ) -> List[models.SubscriptionInstanceRecord]:

        bk_host_ids: List[int] = [sub_inst.instance_info["host"]["bk_host_id"] for sub_inst in sub_insts]
        exist_identity_data_objs: List[models.IdentityData] = models.IdentityData.objects.filter(
            bk_host_id__in=bk_host_ids
        )
        host_id__identity_data_obj_map: Dict[int, models.IdentityData] = {
            identity_data_obj.bk_host_id: identity_data_obj for identity_data_obj in exist_identity_data_objs
        }

        def _is_auth_info_empty(_sub_inst: models.SubscriptionInstanceRecord, _host_info: Dict[str, Any]) -> bool:
            # 「第三方拉取密码」或者「手动安装」场景下无需校验是否存在认证信息
            if not (_host_info.get("auth_type") == constants.AuthType.TJJ_PASSWORD or is_manual):
                # 记录不存在认证信息的订阅实例ID，跳过记录
                if not (_host_info.get("password") or _host_info.get("key")):
                    return True
            return False

        empty_auth_info_sub_inst_ids: List[int] = []
        identity_data_objs_to_be_created: List[models.IdentityData] = []
        identity_data_objs_to_be_updated: List[models.IdentityData] = []
        sub_insts_with_auth_info: List[models.SubscriptionInstanceRecord] = []
        for sub_inst in sub_insts:
            host_info: Dict[str, Any] = sub_inst.instance_info["host"]
            bk_host_id: int = host_info["bk_host_id"]
            is_manual: bool = host_info.get("is_manual", False)
            sub_insts_with_auth_info.append(sub_inst)

            # 先校验再更新，防止存量历史任务重试（认证信息已失效）的情况下，重置最新的认证信息快照
            identity_data_obj: Optional[models.IdentityData] = host_id__identity_data_obj_map.get(bk_host_id)

            if not identity_data_obj:
                if _is_auth_info_empty(sub_inst, host_info):
                    empty_auth_info_sub_inst_ids.append(sub_inst.id)
                    continue

                # 新建认证信息对象
                identity_data_obj: models.IdentityData = models.IdentityData(
                    bk_host_id=bk_host_id,
                    auth_type=host_info.get("auth_type"),
                    account=host_info.get("account"),
                    password=base64.b64decode(host_info.get("password", "")).decode(),
                    port=host_info.get("port"),
                    key=base64.b64decode(host_info.get("key", "")).decode(),
                    retention=host_info.get("retention", 1),
                    extra_data=host_info.get("extra_data", {}),
                    updated_at=timezone.now(),
                )
                identity_data_objs_to_be_created.append(identity_data_obj)
                continue

            # 更新策略：优先使用传入数据，否则使用历史快照
            identity_data_obj.port = host_info.get("port") or identity_data_obj.port
            identity_data_obj.account = host_info.get("account") or identity_data_obj.account
            identity_data_obj.auth_type = host_info.get("auth_type") or identity_data_obj.auth_type
            identity_data_obj.password = (
                base64.b64decode(host_info.get("password", "")).decode() or identity_data_obj.password
            )
            identity_data_obj.key = base64.b64decode(host_info.get("key", "")).decode() or identity_data_obj.key
            identity_data_obj.retention = host_info.get("retention", 1) or identity_data_obj.retention
            identity_data_obj.extra_data = host_info.get("extra_data", {}) or identity_data_obj.extra_data
            identity_data_obj.updated_at = timezone.now()

            identity_data_objs_to_be_updated.append(identity_data_obj)

        models.IdentityData.objects.bulk_create(identity_data_objs_to_be_created, batch_size=self.batch_size)
        models.IdentityData.objects.bulk_update(
            identity_data_objs_to_be_updated,
            fields=["auth_type", "account", "password", "port", "key", "retention", "extra_data", "updated_at"],
            batch_size=self.batch_size,
        )

        # 移除不存在认证信息的实例
        self.move_insts_to_failed(
            sub_inst_ids=empty_auth_info_sub_inst_ids, log_content=_("登录认证信息已被清空\n" "- 若为重试操作，请新建任务重新发起")
        )

        return sub_insts_with_auth_info

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        creator = data.get_one_of_inputs("creator")
        host_id_obj_map = common_data.host_id_obj_map

        subscription_instances: List[models.SubscriptionInstanceRecord] = self.check_and_update_identity_data(
            common_data.subscription_instances
        )

        no_need_query_inst_ids = []
        direct_connection_only_inst_ids = []

        # 这里暂不支持多
        cloud_ip_map = {}
        oa_ticket = ""
        for sub_inst in subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host = host_id_obj_map[bk_host_id]

            if host.identity.auth_type != constants.AuthType.TJJ_PASSWORD:
                no_need_query_inst_ids.append(sub_inst.id)
            elif host.bk_cloud_id != constants.DEFAULT_CLOUD:
                direct_connection_only_inst_ids.append(sub_inst.id)
            else:
                cloud_ip_map[f"{host.bk_cloud_id}-{host.inner_ip}"] = {"host": host, "sub_inst_id": sub_inst.id}
                # 兼容 extra 为 None 的情况
                if host.identity.extra_data:
                    oa_ticket = host.identity.extra_data.get("oa_ticket")

        self.log_info(sub_inst_ids=no_need_query_inst_ids, log_content=_("当前主机验证类型无需查询密码"))
        self.move_insts_to_failed(sub_inst_ids=direct_connection_only_inst_ids, log_content=_("密码查询逻辑仅支持直连"))
        need_query_inst_ids = [item["sub_inst_id"] for item in cloud_ip_map.values()]
        if not need_query_inst_ids:
            return True

        # self.query_password 通过并发控制器执行，结果叠加返回列表
        query_password_results: List[Dict[str, Any]] = self.query_password(
            cloud_ip_list=list(cloud_ip_map.keys()), cloud_ip_map=cloud_ip_map, creator=creator, oa_ticket=oa_ticket
        )

        success_ips: Dict[str, str] = {}
        failed_ips: Dict[str, Dict[str, Any]] = {}
        for query_password_result in query_password_results:
            # 查询失败的情况已处理
            if not query_password_result["is_ok"]:
                continue
            success_ips.update(query_password_result["success_ips"])
            failed_ips.update(query_password_result["failed_ips"])

        for cloud_ip, failed_data in failed_ips.items():
            inst_id = cloud_ip_map[cloud_ip]["sub_inst_id"]
            self.move_insts_to_failed(sub_inst_ids=[inst_id], log_content=failed_data["Message"])

        identity_objs = []
        for cloud_ip, password in success_ips.items():
            host = cloud_ip_map[cloud_ip]["host"]
            identity_objs.append(models.IdentityData(bk_host_id=host.bk_host_id, retention=1, password=password))
        models.IdentityData.objects.bulk_update(identity_objs, fields=["retention", "password"])
        return True
