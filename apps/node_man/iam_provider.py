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
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.core.paginator import Paginator
from iam import IAM
from iam.resource.provider import ListResult, ResourceProvider

from apps.component.esbclient import client_v2
from apps.node_man.constants import IamActionType
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.models import AccessPoint, Cloud, GsePluginDesc, Subscription

SYSTEM_ID = settings.BK_IAM_SYSTEM_ID


def resources_filter(filter, resource_data):
    """
    资源值过滤器
    :param filter: 过滤参数
    :param resource_data: 资源数据
    :return: 过滤结果
    """
    results = set()
    for resource in resource_data:
        # 过滤id与模糊搜索
        if resource["id"] in filter.get("ids") or filter.get("keyword") in resource["display_name"]:
            results.add(resource)
    return results


class BusinessResourceProvider(ResourceProvider):
    """
    业务资源Provider
    """

    def fetch_cmdb_bizs(self):
        """
        获得cmdb所有业务
        :return:
        [{
            'id': biz_id ,
            'display_name': bk_biz_name
        }]
        """
        all_business = [
            {"bk_biz_id": business["bk_biz_id"], "bk_biz_name": business["bk_biz_name"]}
            for business in client_v2.cc.search_business({"fields": ["bk_biz_id", "bk_biz_name"]}).get("info") or []
        ]
        all_business.insert(0, {"bk_biz_id": settings.BK_CMDB_RESOURCE_POOL_BIZ_ID, "bk_biz_name": "资源池"})
        for business in all_business:
            business.update({"id": business.pop("bk_biz_id")})
            business.update({"display_name": business.pop("bk_biz_name")})
        return all_business

    def list_attr(self, **options):
        """
        业务资源属性
        """
        results = [{"id": "biz", "display_name": "业务"}]
        return ListResult(results, len(results))

    def list_attr_value(self, filter, page, **options):
        """
        业务资源属性值
        """
        if filter.get("search") == "biz" and (filter.get("keyword") or filter.get("ids")):
            results = resources_filter(filter, self.fetch_cmdb_bizs())
        elif filter.get("attr") == "biz":
            results = self.fetch_cmdb_bizs()
        else:
            return ListResult(results=[], count=0)

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def list_instance(self, filter, page, **options):
        """
        业务属性值过滤
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_cmdb_bizs()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("biz"):
                    results.append(resource)
        else:
            results = self.fetch_cmdb_bizs()

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def fetch_instance_info(self, filter, **options):
        """
        批量获取资源实例详情
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_cmdb_bizs()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("biz"):
                    results.append(resource)
        else:
            results = self.fetch_cmdb_bizs()

        return ListResult(results, len(results))

    def list_instance_by_policy(self, filter, page, **options):
        """
        不需要动态查询资源实例进行预览
        """
        return ListResult(results=[], count=0)


class CloudResourceProvider(ResourceProvider):
    """
    云区域资源Provider
    """

    def fetch_clouds(self, condition=None):
        """
        获得所有云区域列表
        :return:
        [{
            'id': bk_cloud_id ,
            'display_name': bk_cloud_name
        }]
        """
        if not condition:
            condition = {}
        result = [
            {"id": cloud["bk_cloud_id"], "display_name": cloud["bk_cloud_name"]}
            for cloud in list(Cloud.objects.filter(**condition).values("bk_cloud_id", "bk_cloud_name"))
        ]
        # result.insert(0, {"id": DEFAULT_CLOUD, "display_name": _("直连区域")})
        return result

    def list_attr(self, **options):
        """
        云区域资源属性
        """
        results = [{"id": "cloud", "display_name": "云区域"}]
        return ListResult(results, len(results))

    def list_attr_value(self, filter, page, **options):
        """
        云区域资源属性值
        """
        if filter.get("attr") == "cloud" and (filter.get("keyword") or filter.get("ids")):
            results = resources_filter(filter, self.fetch_clouds())
        elif filter.get("attr") == "cloud":
            results = self.fetch_clouds()
        else:
            return ListResult(results=[], count=0)

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def list_instance(self, filter, page, **options):
        """
        云区域属性值过滤
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_clouds()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("cloud"):
                    results.append(resource)
        else:
            results = self.fetch_clouds()

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def search_instance(self, filter, page, **options):
        """
        云区域搜索
        """
        condition = {"bk_cloud_name__icontains": filter.get("keyword", "")}
        results = self.fetch_clouds(condition)

        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def fetch_instance_info(self, filter, **options):
        """
        批量获取资源实例详情
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_clouds()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("cloud"):
                    results.append(resource)
        else:
            results = self.fetch_clouds()

        return ListResult(results, len(results))

    def list_instance_by_policy(self, filter, page, **options):
        """
        不需要动态查询资源实例进行预览
        """
        return ListResult(results=[], count=0)


class ApResourceProvider(ResourceProvider):
    """
    接入点资源Provider
    """

    def fetch_aps(self):
        """
        获得所有接入点列表
        :return:
        [{
            'id': ap_id ,
            'display_name': ap_name
        }]
        """
        return [
            {"id": ap["id"], "display_name": ap["name"]} for ap in list(AccessPoint.objects.all().values("id", "name"))
        ]

    def list_attr(self, **options):
        """
        接入点资源属性
        """
        results = [{"id": "ap", "display_name": "接入点"}]
        return ListResult(results, len(results))

    def list_attr_value(self, filter, page, **options):
        """
        接入点资源属性值
        """
        if filter.get("attr") == "ap" and (filter.get("keyword") or filter.get("ids")):
            results = resources_filter(filter, self.fetch_aps())
        elif filter.get("attr") == "ap":
            results = self.fetch_aps()
        else:
            return ListResult(results=[], count=0)

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def list_instance(self, filter, page, **options):
        """
        接入点属性值过滤
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_aps()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("ap"):
                    results.append(resource)
        else:
            results = self.fetch_aps()

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def fetch_instance_info(self, filter, **options):
        """
        批量获取资源实例详情
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_aps()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("ap"):
                    results.append(resource)
        else:
            results = self.fetch_aps()

        return ListResult(results, len(results))

    def list_instance_by_policy(self, filter, page, **options):
        """
        不需要动态查询资源实例进行预览
        """
        return ListResult(results=[], count=0)


class PackageResourceProvider(ResourceProvider):
    """
    插件包资源Provider
    """

    def fetch_packages(self, condition=None):
        """
        获得所有插件包列表
        :return:
        [{
            'id': ap_id ,
            'display_name': ap_name
        }]
        """
        if not condition:
            condition = {}
        return [
            {"id": plugin["id"], "display_name": plugin["description"]}
            for plugin in list(GsePluginDesc.objects.filter(**condition).values("id", "description"))
        ]

    def list_attr(self, **options):
        """
        接入点资源属性
        """
        results = [{"id": "package", "display_name": "插件包"}]
        return ListResult(results, len(results))

    def list_attr_value(self, filter, page, **options):
        """
        接入点资源属性值
        """
        if filter.get("attr") == "package" and (filter.get("keyword") or filter.get("ids")):
            results = resources_filter(filter, self.fetch_packages())
        elif filter.get("attr") == "package":
            results = self.fetch_packages()
        else:
            return ListResult(results=[], count=0)

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def list_instance(self, filter, page, **options):
        """
        接入点属性值过滤
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_packages()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("package"):
                    results.append(resource)
        else:
            results = self.fetch_packages()

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def fetch_instance_info(self, filter, **options):
        """
        批量获取资源实例详情
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_packages()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("package"):
                    results.append(resource)
        else:
            results = self.fetch_packages()

        return ListResult(results, len(results))

    def search_instance(self, filter, page, **options):
        """
        云区域搜索
        """
        condition = {"description__icontains": filter.get("keyword", "")}
        results = self.fetch_packages(condition)

        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def list_instance_by_policy(self, filter, page, **options):
        """
        不需要动态查询资源实例进行预览
        """
        return ListResult(results=[], count=0)


class StrategyResourceProvider(ResourceProvider):
    """
    策略资源Provider
    """

    def fetch_strategy(self, condition=None):
        """
        获得所有策略列表
        :return:
        [{
            'id': id ,
            'display_name': name
        }]
        """
        init_condition = {
            "category": "policy",
            "is_deleted": False,
        }
        if not condition:
            condition = init_condition
        else:
            condition.update(init_condition)

        result = [
            {"id": strategy["id"], "display_name": strategy["name"]}
            for strategy in list(Subscription.objects.filter(**condition).values("id", "name"))
        ]
        # result.insert(0, {"id": DEFAULT_CLOUD, "display_name": _("直连区域")})
        return result

    def list_attr(self, **options):
        """
        资源属性
        """
        results = [{"id": "strategy", "display_name": "策略"}]
        return ListResult(results, len(results))

    def list_attr_value(self, filter, page, **options):
        """
        资源属性值
        """
        if filter.get("attr") == "strategy" and (filter.get("keyword") or filter.get("ids")):
            results = resources_filter(filter, self.fetch_strategy())
        elif filter.get("attr") == "strategy":
            results = self.fetch_strategy()
        else:
            return ListResult(results=[], count=0)

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def list_instance(self, filter, page, **options):
        """
        策略属性值过滤
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_strategy()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("stratety"):
                    results.append(resource)
        else:
            results = self.fetch_strategy()

        # 分页
        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def search_instance(self, filter, page, **options):
        """
        策略搜索
        """
        condition = {"name__icontains": filter.get("keyword", "")}
        results = self.fetch_strategy(condition)

        paginator = Paginator(list(results), page.limit)
        page = int(page.offset / page.limit) + 1
        ret_list = ListResult(paginator.page(page).object_list, len(results))
        return ret_list

    def fetch_instance_info(self, filter, **options):
        """
        批量获取资源实例详情
        """
        if filter.get("search", {}):
            results = []
            resource_data = self.fetch_strategy()
            for resource in resource_data:
                if resource["display_name"] in filter["search"].get("stratety"):
                    results.append(resource)
        else:
            results = self.fetch_strategy()

        return ListResult(results, len(results))

    def list_instance_by_policy(self, filter, page, **options):
        """
        不需要动态查询资源实例进行预览
        """
        return ListResult(results=[], count=0)


# ***********************
# 权限中心迁移数据相关代码
# ***********************


def sync_cloud_area_creator_to_iam():
    """
    同步CMDB云区域权限给权限中心, 仅需手动运行一次
    """
    clouds = Cloud.objects.all()
    for cloud in clouds:
        for username in cloud.creator:
            if username == "system":
                username = "admin"
            ok, message = IamHandler.sync_cloud_instance(cloud.bk_cloud_id, cloud.bk_cloud_name, username)
            if not ok:
                print(f"failed! id: {cloud.bk_cloud_id}, for: {username}, {message}")
            else:
                print(f"succeeded! id: {cloud.bk_cloud_id}, for: {username}")


# ***********************
# 权限中心注册相关代码
# ***********************


class IamRegister(object):

    cmdb_related_biz_resource_type = [
        {
            "id": "biz",
            "system_id": settings.BK_IAM_CMDB_SYSTEM_ID,
            "selection_mode": "instance",
            "related_instance_selections": [{"system_id": settings.BK_IAM_CMDB_SYSTEM_ID, "id": "business"}],
        }
    ]

    nodeman_related_cloud_resource_type = [
        {
            "system_id": "bk_nodeman",
            "id": "cloud",
            "name_alias": "",
            "name_alias_en": "",
            "selection_mode": "instance",
            "related_instance_selections": [{"system_id": "bk_nodeman", "id": "cloud_instance_selection"}],
        }
    ]

    nodeman_related_ap_resource_type = [
        {
            "system_id": "bk_nodeman",
            "id": "ap",
            "name_alias": "",
            "name_alias_en": "",
            "selection_mode": "instance",
            "related_instance_selections": [{"system_id": "bk_nodeman", "id": "ap_instance_selection"}],
        }
    ]

    def __init__(self):
        self._iam = IAM(
            settings.APP_CODE, settings.SECRET_KEY, settings.BK_IAM_INNER_HOST, settings.BK_COMPONENT_API_URL
        )

    def register_system(self):
        # ***需要将placeholder改为内网访问地址***
        system_data = {
            "id": "bk_nodeman",
            "name": "节点管理",
            "name_en": "nodeman",
            "description": "",
            "description_en": "",
            "clients": "bk_nodeman,bk_bknodeman",
            "provider_config": {"host": "nodeman.bknodeman.service.consul:10300", "auth": "basic"},
        }
        # 修改
        self._iam._client.update_system("bk_nodeman", system_data)

        # 创建
        # self._iam._client.add_system(system_data)

    def register_resource_types(self):
        data = [
            {
                "id": "ap",
                "name": "接入点",
                "name_en": "Access Point",
                "description": "",
                "description_en": "",
                "provider_config": {"path": "/api/iam/v1/ap"},
                "version": 1,
            },
            {
                "id": "global_settings",
                "name": "全局配置",
                "name_en": "Global Settings",
                "description": "",
                "description_en": "",
                "provider_config": {"path": "/api/iam/v1/gs"},
                "version": 1,
            },
        ]
        for resource in data:
            # 更新
            ok, message = self._iam._client.update_resource_type(
                system_id=SYSTEM_ID, resource_type_id=resource["id"], data=resource
            )
            print(ok, message)
        # 创建
        # self._iam._client.batch_add_resource_types(system_id=SYSTEM_ID, data=data)

    def register_action(self):
        data = [
            {
                "id": IamActionType.cloud_view,
                "name": "云区域查看",
                "name_en": "Cloud View",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": self.nodeman_related_cloud_resource_type,
            },
            {
                "id": IamActionType.cloud_edit,
                "name": "云区域编辑",
                "name_en": "Cloud Edit",
                "description": "",
                "description_en": "",
                "type": "edit",
                "version": 1,
                "related_actions": [IamActionType.cloud_view],
                "related_resource_types": self.nodeman_related_cloud_resource_type,
            },
            {
                "id": IamActionType.cloud_delete,
                "name": "云区域删除",
                "name_en": "Cloud Delete",
                "description": "",
                "description_en": "",
                "type": "delete",
                "version": 1,
                "related_actions": [IamActionType.cloud_view],
                "related_resource_types": self.nodeman_related_cloud_resource_type,
            },
            {
                "id": IamActionType.cloud_create,
                "name": "云区域创建",
                "name_en": "Cloud Create",
                "description": "",
                "description_en": "",
                "type": "create",
                "version": 1,
            },
            {
                "id": IamActionType.ap_view,
                "name": "接入点查看",
                "name_en": "Ap View",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": self.nodeman_related_ap_resource_type,
            },
            {
                "id": IamActionType.ap_edit,
                "name": "接入点编辑",
                "name_en": "Ap Edit",
                "description": "",
                "description_en": "",
                "type": "edit",
                "version": 1,
                "related_actions": [IamActionType.ap_view],
                "related_resource_types": self.nodeman_related_ap_resource_type,
            },
            {
                "id": IamActionType.ap_delete,
                "name": "接入点删除",
                "name_en": "Ap Delete",
                "description": "",
                "description_en": "",
                "type": "delete",
                "version": 1,
                "related_actions": [IamActionType.ap_view],
                "related_resource_types": self.nodeman_related_ap_resource_type,
            },
            {
                "id": IamActionType.ap_create,
                "name": "接入点创建",
                "name_en": "Ap Create",
                "description": "",
                "description_en": "",
                "type": "create",
                "version": 1,
            },
            {
                "id": IamActionType.globe_task_config,
                "name": "任务配置",
                "name_en": "Globe Task Config",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
            },
            {
                "id": IamActionType.agent_view,
                "name": "Agent查询",
                "name_en": "Agent View",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": self.cmdb_related_biz_resource_type,
            },
            {
                "id": IamActionType.agent_operate,
                "name": "Agent操作",
                "name_en": "Agent Operate",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": self.cmdb_related_biz_resource_type,
            },
            {
                "id": IamActionType.proxy_operate,
                "name": "Proxy操作",
                "name_en": "Proxy Operate",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": self.cmdb_related_biz_resource_type,
            },
            {
                "id": IamActionType.plugin_view,
                "name": "插件查看",
                "name_en": "Plugin View",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": self.cmdb_related_biz_resource_type,
            },
            {
                "id": IamActionType.plugin_operate,
                "name": "插件操作",
                "name_en": "Plugin Operate",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": self.cmdb_related_biz_resource_type,
            },
            {
                "id": IamActionType.task_history_view,
                "name": "任务历史查看",
                "name_en": "Task History view",
                "description": "",
                "description_en": "",
                "type": "view",
                "version": 1,
                "related_resource_types": self.cmdb_related_biz_resource_type,
            },
        ]
        # self._iam._client.batch_add_actions(system_id=SYSTEM_ID, data=data)

        # 更新Action
        for action in data:
            ok, message = self._iam._client.update_action(system_id=SYSTEM_ID, data=action, action_id=action["id"])
            print(ok, message)

    def add_instance_selection(self):
        data = [
            {
                "id": "ap_instance_selection",
                "name": "接入点",
                "name_en": "Access Point",
                "resource_type_chain": [{"system_id": SYSTEM_ID, "id": "ap"}],
            },
        ]
        self._iam._client.api_batch_add_instance_selections(system_id=SYSTEM_ID, data=data)

    def add_action_topologies(self):
        data = [
            {
                "id": IamActionType.cloud_create,
                "related_actions": [IamActionType.cloud_edit, IamActionType.cloud_view, IamActionType.cloud_delete],
            },
            {
                "id": IamActionType.ap_create,
                "related_actions": [IamActionType.ap_edit, IamActionType.ap_view, IamActionType.ap_delete],
            },
        ]
        self._iam._client.add_action_topology(system_id=SYSTEM_ID, action_type="create", data=data)

    def delete_action(self):
        data = [{"id": IamActionType.global_settings_edit}, {"id": IamActionType.biz_view}]
        self._iam._client.batch_delete_actions(system_id=SYSTEM_ID, data=data)

    def reg_action_groups(self):
        # 操作分组
        data = [
            {
                "name": "常规功能",
                "name_en": "Normal",
                "sub_groups": [
                    {"name": "Agent管理", "name_en": "Agent", "actions": [{"id": "agent_view"}, {"id": "agent_operate"}]},
                    {
                        "name": "云区域管理",
                        "name_en": "Cloud Area",
                        "actions": [
                            {"id": "cloud_create"},
                            {"id": "cloud_edit"},
                            {"id": "cloud_delete"},
                            {"id": "cloud_view"},
                            {"id": "proxy_operate"},
                        ],
                    },
                    {"name": "插件管理", "name_en": "Plugin", "actions": [{"id": "plugin_view"}, {"id": "plugin_operate"}]},
                    {"name": "任务历史", "name_en": "Task History", "actions": [{"id": "task_history_view"}]},
                ],
            },
            {
                "name": "全局配置",
                "name_en": "Globle Configuration",
                "sub_groups": [
                    {
                        "name": "接入点管理",
                        "name_en": "Access Point",
                        "actions": [{"id": "ap_create"}, {"id": "ap_delete"}, {"id": "ap_edit"}, {"id": "ap_view"}],
                    },
                    {"name": "任务配置", "name_en": "Task Configuration", "actions": [{"id": "globe_task_config"}]},
                ],
            },
        ]
        ok, message, data = self._iam._client.api_add_action_groups(system_id=SYSTEM_ID, data=data)
        print(ok, message, data)

    def resource_creator_actions(self):
        # 新建关联权限
        data = {
            "config": [
                {
                    "id": "ap",
                    "actions": [
                        {"id": "ap_edit", "required": False},
                        {"id": "ap_view", "required": False},
                        {"id": "ap_delete", "required": False},
                    ],
                },
                {
                    "id": "cloud",
                    "actions": [
                        {"id": "cloud_edit", "required": False},
                        {"id": "cloud_view", "required": False},
                        {"id": "cloud_delete", "required": False},
                    ],
                },
            ],
        }
        ok, message = self._iam._client.add_resource_creator_actions(system_id=SYSTEM_ID, data=data)
        print(ok, message)
