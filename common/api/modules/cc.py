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

from ..base import BaseApi, DataAPI
from ..domains import CC_APIGATEWAY_ROOT_V2, CC_APIGATEWAY_ROOT_V3
from .utils import add_esb_info_before_request


class _CCApi(BaseApi):
    MODULE = _("配置平台")
    SIMPLE_MODULE = "CC"

    def __init__(self):
        self.search_business = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "biz/search/0/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询业务列表",
            api_name="search_business",
        )
        self.search_cloud_area = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/cloudarea/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询管控区域",
            before_request=add_esb_info_before_request,
            api_name="search_cloud_area",
        )
        self.search_biz_inst_topo = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find/topoinst/biz/{bk_biz_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询业务实例拓扑",
            api_name="search_biz_inst_topo",
        )
        self.get_biz_internal_module = DataAPI(
            method="GET",
            url=CC_APIGATEWAY_ROOT_V2 + "topo/internal/0/{bk_biz_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="根据业务ID获取业务空闲机, 故障机和待回收模块",
            api_name="get_biz_internal_module",
        )
        self.find_topo_node_paths = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "cache/find/cache/topo/node_path/biz/{bk_biz_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询业务拓扑节点的拓扑路径",
            before_request=add_esb_info_before_request,
            api_name="find_topo_node_paths",
        )
        self.find_module_batch = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/module/bk_biz_id/{bk_biz_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="批量获取模块详情",
            before_request=add_esb_info_before_request,
            api_name="find_module_batch",
        )
        self.list_hosts_without_biz = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "hosts/list_hosts_without_app/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="没有业务ID的主机查询",
            api_name="list_hosts_without_biz",
        )
        self.list_biz_hosts = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "hosts/app/{bk_biz_id}/list_hosts/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="带业务的主机查询",
            api_name="list_biz_hosts",
        )
        self.list_service_template = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/proc/service_template/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询服务模板列表",
            before_request=add_esb_info_before_request,
            api_name="list_service_template",
        )
        self.list_service_instance = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/proc/service_instance/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询服务实例列表",
            before_request=add_esb_info_before_request,
            api_name="list_service_instance",
        )
        self.list_process_instance = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/proc/process_instance/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询进程实例列表",
            before_request=add_esb_info_before_request,
            api_name="list_process_instance",
        )
        self.list_proc_template = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/proc/proc_template/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询进程模板信息",
            before_request=add_esb_info_before_request,
            api_name="list_proc_template",
        )
        self.find_set_batch = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/set/bk_biz_id/{bk_biz_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="批量获取指定业务下集群",
            before_request=add_esb_info_before_request,
            api_name="find_set_batch",
        )
        self.search_set = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "set/search/0/{bk_biz_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询集群",
            before_request=add_esb_info_before_request,
            api_name="search_set",
        )
        self.search_module = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "module/search/0/{bk_biz_id}/0/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询模块",
            before_request=add_esb_info_before_request,
            api_name="search_module",
        )
        self.search_object_attribute = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find/objectattr/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询对象模型属性",
            before_request=add_esb_info_before_request,
            api_name="search_object_attribute",
        )
        self.find_host_topo_relation = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "host/topo/relation/read/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="获取主机与拓扑的关系",
            before_request=add_esb_info_before_request,
            api_name="find_host_topo_relation",
        )
        self.find_host_biz_relations = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "hosts/modules/read/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询主机业务关系信息",
            api_name="find_host_biz_relations",
        )
        self.batch_update_host = DataAPI(
            method="PUT",
            url=CC_APIGATEWAY_ROOT_V2 + "hosts/property/batch/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="批量更新主机属性",
            before_request=add_esb_info_before_request,
            api_name="batch_update_host",
        )
        self.resource_watch = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "event/watch/resource/{bk_resource}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="监听资源变化事件",
            before_request=add_esb_info_before_request,
            api_name="resource_watch",
        )
        self.bind_host_agent = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "host/bind/agent/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="将agent绑定到主机上",
            before_request=add_esb_info_before_request,
            api_name="bind_host_agent",
        )
        self.unbind_host_agent = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "host/unbind/agent/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="将agent和主机解绑",
            before_request=add_esb_info_before_request,
            api_name="unbind_host_agent",
        )
        self.add_host_to_business_idle = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "hosts/add/business_idle/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="添加主机到业务空闲机",
            before_request=add_esb_info_before_request,
            api_name="add_host_to_business_idle",
        )
        self.push_host_identifier = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "event/push/host_identifier/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="推送主机身份到机器上",
            before_request=add_esb_info_before_request,
            api_name="push_host_identifier",
        )
        self.find_host_identifier_push_result = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "event/find/host_identifier_push_result/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="获取推送主机身份到机器结果",
            before_request=add_esb_info_before_request,
            api_name="find_host_identifier_push_result",
        )
        self.list_service_instance_detail = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/proc/service_instance/details/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询服务实例详情",
            before_request=add_esb_info_before_request,
            api_name="list_service_instance_detail",
        )
        self.execute_dynamic_group = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "execute_dynamic_group/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="执行动态分组",
            before_request=add_esb_info_before_request,
            api_name="search_set_v2",
        )
        self.find_module_batch = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find_module_batch/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="批量查询某业务的模块详情",
            # before_request=add_esb_info_before_request,
            api_name="find_module_batch",
        )
        self.find_set_batch = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find_set_batch/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="批量查询某业务的集群详情",
            # before_request=add_esb_info_before_request,
            api_name="find_set_batch",
        )
        self.get_biz_brief_cache_topo = DataAPI(
            method="GET",
            url=CC_APIGATEWAY_ROOT_V3 + "api/v3/cache/find/cache/topo/brief/biz/{bk_biz_id}",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询业务实例拓扑(缓存)",
            # before_request=add_esb_info_before_request,
            api_name="get_biz_brief_cache_topo",
        )
        self.add_host_to_resource = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "hosts/add/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="新增主机到资源池",
            before_request=add_esb_info_before_request,
            api_name="add_host_to_resource",
        )
        self.get_mainline_object_topo = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find/topomodelmainline/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询主线模型的业务拓扑",
            before_request=add_esb_info_before_request,
            api_name="get_mainline_object_topo",
        )
        self.find_host_by_service_template = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/hosts/by_service_templates/biz/{bk_biz_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询服务模板下的主机",
            before_request=add_esb_info_before_request,
            api_name="find_host_by_service_template",
        )
        self.find_host_by_set_template = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/hosts/by_set_templates/biz/{bk_biz_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询集群模板下的主机",
            before_request=add_esb_info_before_request,
            api_name="find_host_by_set_template",
        )
        self.list_biz_hosts_topo = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "hosts/app/{bk_biz_id}/list_hosts_topo/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询业务下的主机和拓扑信息",
            before_request=add_esb_info_before_request,
            api_name="list_biz_hosts_topo",
        )
        self.update_host_cloud_area_field = DataAPI(
            method="PUT",
            url=CC_APIGATEWAY_ROOT_V2 + "updatemany/hosts/cloudarea_field/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="更新主机的管控区域字段",
            before_request=add_esb_info_before_request,
            api_name="update_host_cloud_area_field",
        )
        self.search_inst = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "find/instassociation/object/{bk_obj_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="根据关联关系实例查询模型实例",
            before_request=add_esb_info_before_request,
            api_name="search_inst",
        )
        self.list_resource_pool_hosts = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "hosts/list_resource_pool_hosts/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询资源池中的主机",
            before_request=add_esb_info_before_request,
            api_name="list_resource_pool_hosts",
        )
        self.create_cloud_area = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "create/cloudarea/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="创建管控区域",
            before_request=add_esb_info_before_request,
            api_name="create_cloud_area",
        )
        self.delete_cloud_area = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "delete/cloudarea/{bk_cloud_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="删除管控区域",
            before_request=add_esb_info_before_request,
            api_name="delete_cloud_area",
        )
        self.update_cloud_area = DataAPI(
            method="PUT",
            url=CC_APIGATEWAY_ROOT_V2 + "update/cloudarea/{bk_cloud_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="更新管控区域",
            before_request=add_esb_info_before_request,
            api_name="update_cloud_area",
        )
        self.update_inst = DataAPI(
            method="PUT",
            url=CC_APIGATEWAY_ROOT_V2 + "update/instance/object/{bk_obj_id}/inst/{bk_inst_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="更新对象实例",
            before_request=add_esb_info_before_request,
            api_name="update_inst",
        )
        self.find_host_by_topo = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/hosts/by_topo/biz/{bk_biz_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询拓扑节点下的主机",
            api_name="find_host_by_topo",
        )
        self.find_host_service_template = DataAPI(
            method="POST",
            url=CC_APIGATEWAY_ROOT_V2 + "findmany/hosts/service_template/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询主机服务模板",
            before_request=add_esb_info_before_request,
            api_name="find_host_service_template",
        )
