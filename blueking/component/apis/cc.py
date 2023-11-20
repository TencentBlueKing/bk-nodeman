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
from ..base import ComponentAPI


class CollectionsCC(object):
    """Collections of CC APIS"""

    def __init__(self, client):
        self.client = client

        self.add_host_lock = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/add_host_lock/", description="新加主机锁"
        )
        self.add_host_to_resource = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/add_host_to_resource/",
            description="新增主机到资源池",
        )
        self.add_instance_association = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/add_instance_association/",
            description="新建模型实例之间的关联关系",
        )
        self.batch_delete_inst = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/batch_delete_inst/",
            description="批量删除实例",
        )
        self.batch_delete_set = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/batch_delete_set/",
            description="批量删除集群",
        )
        self.batch_update_inst = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/batch_update_inst/",
            description="批量更新对象实例",
        )
        self.bind_process_module = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/bind_process_module/",
            description="绑定进程到模块",
        )
        self.bind_role_privilege = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/bind_role_privilege/",
            description="绑定角色权限",
        )
        self.create_business = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/create_business/", description="新建业务"
        )
        self.create_classification = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/create_classification/",
            description="添加模型分类",
        )
        self.create_custom_query = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/create_custom_query/",
            description="添加自定义API",
        )
        self.create_inst = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/create_inst/", description="创建实例"
        )
        self.create_module = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/create_module/", description="创建模块"
        )
        self.create_object = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/create_object/", description="创建模型"
        )
        self.create_object_attribute = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/create_object_attribute/",
            description="创建模型属性",
        )
        self.create_set = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/create_set/", description="创建集群"
        )
        self.create_user_group = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/create_user_group/",
            description="新建用户分组",
        )
        self.delete_business = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/delete_business/", description="删除业务"
        )
        self.delete_classification = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/delete_classification/",
            description="删除模型分类",
        )
        self.delete_custom_query = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/delete_custom_query/",
            description="删除自定义API",
        )
        self.delete_host = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/delete_host/", description="删除主机"
        )
        self.delete_host_lock = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/delete_host_lock/",
            description="删除主机锁",
        )
        self.delete_inst = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/delete_inst/", description="删除实例"
        )
        self.delete_instance_association = ComponentAPI(
            client=self.client,
            method="DELETE",
            path="/api/c/compapi{bk_api_ver}/cc/delete_instance_association/",
            description="删除模型实例之间的关联关系",
        )
        self.delete_module = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/delete_module/", description="删除模块"
        )
        self.delete_object = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/delete_object/", description="删除模型"
        )
        self.delete_object_attribute = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/delete_object_attribute/",
            description="删除对象模型属性",
        )
        self.delete_process_module_bind = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/delete_process_module_bind/",
            description="解绑进程模块",
        )
        self.delete_set = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/delete_set/", description="删除集群"
        )
        self.delete_user_group = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/delete_user_group/",
            description="删除用户分组",
        )
        self.find_host_by_module = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/find_host_by_module/",
            description="根据模块查询主机",
        )
        self.find_instance_association = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/find_instance_association/",
            description="查询模型实例之间的关联关系",
        )
        self.find_object_association = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/find_object_association/",
            description="查询模型之间的关联关系",
        )
        self.get_biz_internal_module = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_biz_internal_module/",
            description="查询业务的空闲机和故障机模块",
        )
        self.get_custom_query_data = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_custom_query_data/",
            description="根据自定义api获取数据",
        )
        self.get_custom_query_detail = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_custom_query_detail/",
            description="获取自定义API详情",
        )
        self.get_host_base_info = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_host_base_info/",
            description="获取主机详情",
        )
        self.get_mainline_object_topo = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_mainline_object_topo/",
            description="查询主线模型的业务拓扑",
        )
        self.get_operation_log = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/get_operation_log/",
            description="获取操作日志",
        )
        self.get_process_bind_module = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_process_bind_module/",
            description="查询进程绑定模块",
        )
        self.get_role_privilege = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_role_privilege/",
            description="获取角色绑定权限",
        )
        self.get_user_privilege = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/get_user_privilege/",
            description="查询用户权限",
        )
        self.search_biz_inst_topo = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/search_biz_inst_topo/",
            description="查询业务实例拓扑",
        )
        self.search_business = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/search_business/", description="查询业务"
        )
        self.search_classifications = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_classifications/",
            description="查询模型分类",
        )
        self.search_custom_query = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_custom_query/",
            description="查询自定义API",
        )
        self.search_group_privilege = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_group_privilege/",
            description="查询分组权限",
        )
        self.list_hosts_without_biz = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/list_hosts_without_biz/",
            description="没有业务信息的主机查询",
        )
        self.search_host = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/search_host/", description="根据条件查询主机"
        )
        self.search_host_lock = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_host_lock/",
            description="查询主机锁",
        )
        self.search_inst = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/search_inst/", description="查询实例"
        )
        self.search_inst_association_topo = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_inst_association_topo/",
            description="查询实例关联拓扑",
        )
        self.search_inst_by_object = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_inst_by_object/",
            description="查询实例详情",
        )
        self.search_module = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/search_module/", description="查询模块"
        )
        self.search_object_attribute = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_object_attribute/",
            description="查询对象模型属性",
        )
        self.search_object_topo = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_object_topo/",
            description="查询普通模型拓扑",
        )
        self.search_object_topo_graphics = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_object_topo_graphics/",
            description="查询拓扑图",
        )
        self.search_objects = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/search_objects/", description="查询模型"
        )
        self.search_set = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/search_set/", description="查询集群"
        )
        self.search_subscription = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_subscription/",
            description="查询订阅",
        )
        self.search_user_group = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_user_group/",
            description="查询用户分组",
        )
        self.subscribe_event = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/subscribe_event/", description="订阅事件"
        )
        self.testing_connection = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/testing_connection/",
            description="测试推送（只测试连通性）",
        )
        self.transfer_host_module = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/transfer_host_module/",
            description="业务内主机转移模块",
        )
        self.transfer_host_to_faultmodule = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/transfer_host_to_faultmodule/",
            description="上交主机到业务的故障机模块",
        )
        self.transfer_host_to_idlemodule = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/transfer_host_to_idlemodule/",
            description="上交主机到业务的空闲机模块",
        )
        self.transfer_host_to_resourcemodule = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/transfer_host_to_resourcemodule/",
            description="上交主机至资源池",
        )
        self.transfer_resourcehost_to_idlemodule = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/transfer_resourcehost_to_idlemodule/",
            description="资源池主机分配至业务的空闲机模块",
        )
        self.transfer_sethost_to_idle_module = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/transfer_sethost_to_idle_module/",
            description="清空业务下集群/模块中主机",
        )
        self.unsubcribe_event = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/unsubcribe_event/",
            description="退订事件",
        )
        self.update_business = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/update_business/", description="修改业务"
        )
        self.update_business_enable_status = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_business_enable_status/",
            description="修改业务启用状态",
        )
        self.update_classification = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_classification/",
            description="更新模型分类",
        )
        self.update_custom_query = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_custom_query/",
            description="更新自定义API",
        )
        self.update_event_subscribe = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_event_subscribe/",
            description="修改订阅",
        )
        self.update_host = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/update_host/", description="更新主机属性"
        )
        self.update_inst = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/update_inst/", description="更新对象实例"
        )
        self.update_module = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/update_module/", description="更新模块"
        )
        self.update_object = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/update_object/", description="更新定义"
        )
        self.update_object_attribute = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_object_attribute/",
            description="更新对象模型属性",
        )
        self.update_object_topo_graphics = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_object_topo_graphics/",
            description="更新拓扑图",
        )
        self.update_set = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/update_set/", description="更新集群"
        )
        self.update_user_group = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_user_group/",
            description="更新用户分组",
        )
        self.clone_host_property = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/clone_host_property/",
            description="克隆主机属性",
        )
        self.add_app = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/add_app/", description="新建业务"
        )
        self.add_module = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/add_module/", description="新建模块"
        )
        self.add_plat_id = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/add_plat_id/", description="新增子网ID"
        )
        self.add_set = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/add_set/", description="新建集群"
        )
        self.del_app = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/del_app/", description="删除业务"
        )
        self.del_host_in_app = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/del_host_in_app/",
            description="从业务空闲机集群中删除主机",
        )
        self.del_module = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/del_module/", description="删除模块"
        )
        self.del_plat = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/del_plat/", description="删除子网"
        )
        self.del_set = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/del_set/", description="删除集群"
        )
        self.del_set_host = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/del_set_host/",
            description="清空集群下所有主机",
        )
        self.edit_app = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/edit_app/", description="编辑业务"
        )
        self.enter_ip = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/cc/enter_ip/", description="导入主机到业务"
        )
        self.get_app_agent_status = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_app_agent_status/",
            description="查询业务下Agent状态",
        )
        self.get_app_by_id = ComponentAPI(
            client=self.client, method="GET", path="/api/c/compapi{bk_api_ver}/cc/get_app_by_id/", description="查询业务信息"
        )
        self.get_app_by_user = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_app_by_user/",
            description="查询用户有权限的业务",
        )
        self.get_app_by_user_role = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_app_by_user_role/",
            description="根据用户角色查询用户业务",
        )
        self.get_app_host_list = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_app_host_list/",
            description="查询业务主机列表",
        )
        self.get_app_list = ComponentAPI(
            client=self.client, method="GET", path="/api/c/compapi{bk_api_ver}/cc/get_app_list/", description="查询业务列表"
        )
        self.get_host_by_company_id = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_host_by_company_id/",
            description="根据开发商ID、子网ID、主机IP获取主机信息",
        )
        self.get_host_company_id = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_host_company_id/",
            description="获取主机开发商",
        )
        self.get_host_list_by_field = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_host_list_by_field/",
            description="根据主机属性的值group主机列表",
        )
        self.get_host_list_by_ip = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_host_list_by_ip/",
            description="根据IP查询主机信息",
        )
        self.get_hosts_by_property = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_hosts_by_property/",
            description="根据 set 属性查询主机",
        )
        self.get_ip_and_proxy_by_company = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_ip_and_proxy_by_company/",
            description="查询业务下IP及ProxyIP",
        )
        self.get_module_host_list = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_module_host_list/",
            description="查询模块主机列表",
        )
        self.get_modules = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_modules/",
            description="查询业务下的所有模块",
        )
        self.get_modules_by_property = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_modules_by_property/",
            description="根据 set 属性查询模块",
        )
        self.list_biz_hosts_topo = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/list_biz_hosts_topo/",
            description="查询业务下的主机和拓扑信息",
        )
        self.get_plat_id = ComponentAPI(
            client=self.client, method="GET", path="/api/c/compapi{bk_api_ver}/cc/get_plat_id/", description="查询子网列表"
        )
        self.get_proc_config_instance_status = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_proc_config_instance_status/",
            description="获取刷新进程实例状态",
        )
        self.get_process_port_by_app_id = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_process_port_by_app_id/",
            description="查询进程端口",
        )
        self.get_property_list = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_property_list/",
            description="查询属性列表",
        )
        self.get_set_host_list = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_set_host_list/",
            description="查询Set主机列表",
        )
        self.get_set_property = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_set_property/",
            description="获取所有 set 属性",
        )
        self.get_sets_by_property = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/cc/get_sets_by_property/",
            description="根据 set 属性获取 set",
        )
        self.update_custom_property = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_custom_property/",
            description="修改主机自定义属性",
        )
        self.update_gse_proxy_status = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_gse_proxy_status/",
            description="更新主机gse agent proxy 状态",
        )
        self.update_host_by_app_id = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_host_by_app_id/",
            description="更新主机的gse agent状态",
        )
        self.update_host_info = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_host_info/",
            description="更新主机属性",
        )
        self.batch_update_host = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/batch_update_host/",
            description="批量更新主机属性（不能用于更新主机属性中的管控区域字段）",
        )
        self.update_host_cloud_area_field = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_host_cloud_area_field/",
            description="更新主机的管控区域字段",
        )
        self.update_host_module = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_host_module/",
            description="修改主机模块",
        )
        self.update_host_plat = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_host_plat/",
            description="更新主机云子网",
        )
        self.update_module_property = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_module_property/",
            description="修改模块属性",
        )
        self.update_proc_config_instance = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_proc_config_instance/",
            description="刷新进程配置实例",
        )
        self.update_set_property = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_set_property/",
            description="更新集群属性",
        )
        self.update_set_service_status = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_set_service_status/",
            description="修改集群服务状态",
        )
        self.list_service_instance_detail = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/list_service_instance_detail/",
            description="查询服务实例详情",
        )
        self.search_cloud_area = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/search_cloud_area/",
            description="查询管控区域",
        )
        self.create_cloud_area = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/create_cloud_area/",
            description="创建管控区域",
        )
        self.update_cloud_area = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/update_cloud_area/",
            description="更新管控区域",
        )
        self.delete_cloud_area = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/delete_cloud_area/",
            description="删除管控区域",
        )
        self.list_biz_hosts = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/list_biz_hosts/",
            description="业务主机查询",
        )
        self.list_resource_pool_hosts = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/list_resource_pool_hosts/",
            description="资源池主机查询",
        )
        self.get_biz_location = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/get_biz_location/",
            description="查询业务所在环境是在cc1.0还是在cc3.0",
        )
        self.resource_watch = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/resource_watch/",
            description="监听系统资源变化产生的事件",
        )
        self.find_host_biz_relations = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/find_host_biz_relations/",
            description="查询主机关系",
        )
        self.find_host_by_topo = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/find_host_by_topo/",
            description="查询自定义topo主要机",
        )
        self.find_host_by_service_template = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/find_host_by_service_template/",
            description="根据服务模板查主机",
        )
        self.find_host_by_set_template = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/find_host_by_set_template/",
            description="根据集群模板查主机",
        )
        self.find_host_service_template = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/find_host_service_template/",
            description="查询主机服务模板",
        )
        self.list_service_template = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/list_service_template/",
            description="查询业务服务模板列表",
        )
        self.list_business_in_business_set = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/list_business_in_business_set/",
            description="查询业务集中的业务列表",
        )
        self.list_business_set = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/cc/list_business_set/",
            description="查询业务集",
        )
