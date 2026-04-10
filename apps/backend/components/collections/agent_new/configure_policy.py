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

from django.utils.translation import gettext_lazy as _

from apps.backend.constants import SecurityGroupType
from apps.backend.api.constants import POLLING_INTERVAL
from apps.backend.components.collections.agent_new.base import AgentBaseService
from apps.node_man import constants, models
from apps.node_man.handlers.security_group import get_security_group_factory
from pipeline.core.flow import StaticIntervalGenerator


class ConfigurePolicyService(AgentBaseService):
    """
    配置网络策略
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def _execute(self, data, parent_data, common_data):
        host_id_obj_map = common_data.host_id_obj_map

        # 获取主机对应的管控区域
        cloud_name_map = {
            cloud["bk_cloud_id"]: cloud["bk_cloud_name"]
            for cloud in models.Cloud.objects.filter(
                bk_cloud_id__in=[host.bk_cloud_id for host in host_id_obj_map.values()]
            ).values("bk_cloud_id", "bk_cloud_name")
        }
        security_group_type = models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.SECURITY_GROUP_TYPE.value)
        if not security_group_type:
            return True
        security_group_factory = get_security_group_factory(security_group_type)
        ip_list = []
        for host in host_id_obj_map.values():
            _ip_list = []
            bk_host_multi_outerip = host.extra_data.get("bk_host_multi_outerip", "")
            if bk_host_multi_outerip and host.node_type == constants.NodeType.PROXY:
                outer_ip_list = bk_host_multi_outerip.split(",")
                _ip_list.extend(outer_ip_list)
                _ip_list.append(host.login_ip)
            else:
                _ip_list.extend([host.outer_ip, host.login_ip])
            
            if security_group_type == SecurityGroupType.SOPS_RICH.value: 
                # 补全ip信息
                _ip_list = [
                    f"{ip} {host.bk_biz_id}-{host.bk_cloud_id}:{cloud_name_map.get(host.bk_cloud_id, '')}" for ip in set(_ip_list)
                ]

            ip_list.extend(_ip_list)
        # 不同的安全组工厂添加策略后得到的输出可能是不同的，输出到outputs中，在schedule中由工厂对应的check_result方法来校验结果
        creator: str = common_data.subscription.creator
        data.outputs.add_ip_output = security_group_factory.add_ips_to_security_group(ip_list, creator=creator)
        data.outputs.polling_time = 0
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        common_data = self.get_common_data(data)
        subscription_instance_ids = common_data.subscription_instance_ids
        security_group_type = models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.SECURITY_GROUP_TYPE.value)
        if not security_group_type:
            self.finish_schedule()
            return True
        security_group_factory = get_security_group_factory(security_group_type)
        polling_time = data.get_one_of_outputs("polling_time")
        add_ip_output = data.get_one_of_outputs("add_ip_output")
        if security_group_factory.check_result(add_ip_output):
            self.log_info(sub_inst_ids=subscription_instance_ids, log_content=_("到Gse和Nginx的策略配置成功"))
            self.finish_schedule()
            return True

        elif polling_time + POLLING_INTERVAL > self.service_polling_timeout / 2:
            self.move_insts_to_failed(subscription_instance_ids, _("配置到Gse和Nginx的策略失败请联系节点管理维护人员"))
            self.finish_schedule()
            return False

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True
