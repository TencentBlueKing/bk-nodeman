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

from django.utils.translation import ugettext_lazy as _

from ..base import BaseApi, DataAPI
from ..domains import CC_APIGATEWAY_ROOT_V2
from .utils import add_esb_info_before_request


class _CCApi(BaseApi):
    MODULE = _("配置平台")

    def __init__(self):
        self.search_business = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "search_business/",
            module=self.MODULE,
            description="查询业务列表",
            before_request=add_esb_info_before_request,
        )
        self.search_cloud_area = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "search_cloud_area/",
            module=self.MODULE,
            description="查询管控区域",
            before_request=add_esb_info_before_request,
        )
        self.search_biz_inst_topo = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "search_biz_inst_topo/",
            module=self.MODULE,
            description="查询业务实例拓扑",
            before_request=add_esb_info_before_request,
        )
        self.get_biz_internal_module = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "get_biz_internal_module/",
            module=self.MODULE,
            description="根据业务ID获取业务空闲机, 故障机和待回收模块",
            before_request=add_esb_info_before_request,
        )
        self.find_topo_node_paths = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find_topo_node_paths/",
            module=self.MODULE,
            description="查询业务拓扑节点的拓扑路径",
            before_request=add_esb_info_before_request,
        )
        self.find_module_batch = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find_module_batch/",
            module=self.MODULE,
            description="批量获取模块详情",
            before_request=add_esb_info_before_request,
        )
        self.list_hosts_without_biz = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "list_hosts_without_biz/",
            module=self.MODULE,
            description="没有业务ID的主机查询",
            before_request=add_esb_info_before_request,
        )
        self.list_biz_hosts = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "list_biz_hosts/",
            module=self.MODULE,
            description="带业务的主机查询",
            before_request=add_esb_info_before_request,
        )
        self.list_service_template = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "list_service_template/",
            module=self.MODULE,
            description="查询服务模板列表",
            before_request=add_esb_info_before_request,
        )
        self.list_service_instance = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "list_service_instance/",
            module=self.MODULE,
            description="查询服务实例列表",
            before_request=add_esb_info_before_request,
        )
        self.list_process_instance = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "list_process_instance/",
            module=self.MODULE,
            description="查询进程实例列表",
            before_request=add_esb_info_before_request,
        )
        self.list_proc_template = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "list_proc_template/",
            module=self.MODULE,
            description="查询进程模板信息",
            before_request=add_esb_info_before_request,
        )
        self.find_set_batch = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find_set_batch/",
            module=self.MODULE,
            description="批量获取指定业务下集群",
            before_request=add_esb_info_before_request,
        )
        self.search_set = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "search_set/",
            module=self.MODULE,
            description="查询集群",
            before_request=add_esb_info_before_request,
        )
        self.search_module = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "search_module/",
            module=self.MODULE,
            description="查询模块",
            before_request=add_esb_info_before_request,
        )
        self.search_object_attribute = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "search_object_attribute/",
            module=self.MODULE,
            description="查询对象模型属性",
            before_request=add_esb_info_before_request,
        )
        self.find_host_topo_relation = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find_host_topo_relation/",
            module=self.MODULE,
            description="获取主机与拓扑的关系",
            before_request=add_esb_info_before_request,
        )
        self.find_host_biz_relations = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find_host_biz_relations/",
            module=self.MODULE,
            description="查询主机业务关系信息",
            before_request=add_esb_info_before_request,
        )
        self.batch_update_host = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "batch_update_host/",
            module=self.MODULE,
            description="批量更新主机属性",
            before_request=add_esb_info_before_request,
        )
        self.resource_watch = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "resource_watch/",
            module=self.MODULE,
            description="监听资源变化事件",
            before_request=add_esb_info_before_request,
        )
        #
        self.bind_host_agent = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "bind_host_agent/",
            module=self.MODULE,
            description="将agent绑定到主机上",
            before_request=add_esb_info_before_request,
        )
        self.unbind_host_agent = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "unbind_host_agent/",
            module=self.MODULE,
            description="将agent和主机解绑",
            before_request=add_esb_info_before_request,
        )
        self.add_host_to_business_idle = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "add_host_to_business_idle/",
            module=self.MODULE,
            description="添加主机到业务空闲机",
            before_request=add_esb_info_before_request,
        )
        self.push_host_identifier = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "push_host_identifier/",
            module=self.MODULE,
            description="推送主机身份到机器上",
            before_request=add_esb_info_before_request,
        )
        self.find_host_identifier_push_result = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find_host_identifier_push_result/",
            module=self.MODULE,
            description="获取推送主机身份到机器结果",
            before_request=add_esb_info_before_request,
        )
        self.list_service_instance_detail = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "list_service_instance_detail/",
            module=self.MODULE,
            description="查询服务实例详情",
            before_request=add_esb_info_before_request,
        )
