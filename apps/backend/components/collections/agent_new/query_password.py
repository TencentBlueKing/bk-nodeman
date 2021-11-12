# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants, models
from apps.node_man.handlers.password import DefaultPasswordHandler

from .base import AgentBaseService, AgentCommonData


class QueryPasswordService(AgentBaseService):
    """
    查询主机密码，可根据实际场景自行定义密码库查询处理器
    """

    name = _("查询主机密码")

    def __init__(self):
        super().__init__(name=self.name)

    def _execute(self, data, parent_data, common_data: AgentCommonData):
        creator = data.get_one_of_inputs("creator")
        host_id_obj_map = common_data.host_id_obj_map

        no_need_query_inst_ids = []
        # 这里暂不支持多
        cloud_ip_map = {}
        oa_ticket = ""
        for sub_inst in common_data.subscription_instances:
            bk_host_id = sub_inst.instance_info["host"]["bk_host_id"]
            host = host_id_obj_map[bk_host_id]

            if host.identity.auth_type != constants.AuthType.TJJ_PASSWORD:
                no_need_query_inst_ids.append(sub_inst.id)
            else:
                cloud_ip_map[f"{host.bk_cloud_id}-{host.inner_ip}"] = {"host": host, "sub_inst_id": sub_inst.id}
                oa_ticket = host.identity.extra_data.get("oa_ticket")

        self.log_info(sub_inst_ids=no_need_query_inst_ids, log_content=_("当前主机验证类型无需查询密码"))
        need_query_inst_ids = [item["sub_inst_id"] for item in cloud_ip_map.values()]
        if not need_query_inst_ids:
            return True

        is_ok, success_ips, failed_ips, err_msg = DefaultPasswordHandler().get_password(
            creator, list(cloud_ip_map.keys()), oa_ticket
        )

        if not is_ok:
            self.log_error(sub_inst_ids=need_query_inst_ids, log_content=err_msg)
            self.move_insts_to_failed(
                sub_inst_ids=need_query_inst_ids, log_content=_("若 OA TICKET 过期，请重新登录 OA 后再重试您的操作。请注意不要直接使用此任务中的重试功能~")
            )

        for cloud_ip, failed_data in failed_ips.items():
            inst_id = cloud_ip_map[cloud_ip]["sub_inst_id"]
            self.move_insts_to_failed(sub_inst_ids=[inst_id], log_content=failed_data["Message"])

        identity_objs = []
        for cloud_ip, password in success_ips.items():
            host = cloud_ip_map[cloud_ip]["host"]
            identity_objs.append(models.IdentityData(bk_host_id=host.bk_host_id, retention=1, password=password))
        models.IdentityData.objects.bulk_update(identity_objs, fields=["retention", "password"])
        return True
