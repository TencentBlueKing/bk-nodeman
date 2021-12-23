# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import abc
import json
from typing import List, Set, Union

from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _lazy
from iam import Resource

from apps.iam.exceptions import ResourceNotExistError
from apps.node_man import models


class ResourceMeta(metaclass=abc.ABCMeta):
    """
    资源定义
    """

    system_id = settings.BK_IAM_SYSTEM_ID
    id: str = ""
    lookup_field: str = None
    name: str = ""
    selection_mode: str = ""
    related_instance_selections: List = ""

    @classmethod
    def to_json(cls):
        return {
            "system_id": cls.system_id,
            "id": cls.id,
            "lookup_field": cls.lookup_field,
            "selection_mode": cls.selection_mode,
            "related_instance_selections": cls.related_instance_selections,
        }

    @classmethod
    def create_simple_instance(cls, instance_id: str, attribute=None) -> Resource:
        """
        创建简单资源实例
        :param instance_id: 实例ID
        :param attribute: 属性kv对
        """
        attribute = attribute or {}
        if "bk_biz_id" in attribute:
            # 补充路径信息
            attribute.update({"_bk_iam_path_": "/{},{}/".format(Business.id, attribute["bk_biz_id"])})
        return Resource(cls.system_id, cls.id, str(instance_id), attribute)

    @classmethod
    def create_instance(cls, instance_id: str, attribute=None) -> Resource:
        """
        创建资源实例（带实例名称）可由子类重载
        :param instance_id: 实例ID
        :param attribute: 属性kv对
        """
        return cls.create_simple_instance(instance_id, attribute)

    @classmethod
    def create_instances(cls, instance_ids: Union[List[str], Set[str]], attribute=None) -> List[Resource]:
        return [cls.create_instance(instance_id, attribute) for instance_id in instance_ids]


class Business(ResourceMeta):
    """
    CMDB业务
    """

    system_id = "bk_cmdb"
    id = "biz"
    lookup_field = "bk_biz_id"
    name = _lazy("业务")
    selection_mode = "instance"
    related_instance_selections = [{"system_id": system_id, "id": "business", "ignore_iam_path": True}]

    @classmethod
    def create_instance(cls, instance_id: str, attribute=None) -> Resource:
        resource = cls.create_simple_instance(instance_id, attribute)

        bk_biz_name = str(instance_id)

        resource.attribute = {"id": str(instance_id), "name": bk_biz_name}
        return resource


class Cloud(ResourceMeta):
    """
    云区域
    """

    id = "cloud"
    name = _lazy("云区域")

    @classmethod
    def create_instance(cls, instance_id: str, attribute=None) -> Resource:
        resource = cls.create_simple_instance(instance_id, attribute)
        bk_cloud_name = str(instance_id)
        resource.attribute = {"id": str(instance_id), "name": bk_cloud_name}
        return resource

    @classmethod
    def create_instances(cls, instance_ids: Union[List[str], Set[str]], attribute=None) -> List[Resource]:
        cloud_id_name_map = models.Cloud.cloud_id_name_map()
        return [
            cls.create_instance(instance_id, {"name": cloud_id_name_map.get(int(instance_id))})
            for instance_id in instance_ids
        ]


class AccessPoint(ResourceMeta):
    """
    接入点
    """

    id = "ap"
    name = _lazy("接入点")


class Package(ResourceMeta):
    """
    插件包
    """

    id = "package"
    name = _lazy("插件包")


class Strategy(ResourceMeta):
    """
    策略
    """

    id = "strategy"
    name = _lazy("策略")


class GlobalSettings(ResourceMeta):
    """
    全局配置
    """

    id = "global_settings"
    name = _lazy("全局配置")


class ResourceEnum:
    """
    资源类型枚举
    """

    BUSINESS = Business
    CLOUD = Cloud
    ACCESS_POINT = AccessPoint
    PACKAGE = Package
    STRATEGY = Strategy
    GLOBAL_SETTINGS = GlobalSettings


_all_resources = {resource.id: resource for resource in ResourceEnum.__dict__.values() if hasattr(resource, "id")}


def get_resource_by_id(resource_id: str) -> ResourceMeta:
    """
    根据资源ID获取资源
    """
    if resource_id not in _all_resources:
        raise ResourceNotExistError(_("资源ID不存在：{resource_id}").format(resource_id=resource_id))

    return _all_resources[resource_id]


def generate_all_resources_json() -> List:
    """
    生成migrations的json配置
    """
    results = []
    for value in _all_resources.values():
        results.append({"operation": "upsert_action", "data": value.to_json()})
    print(json.dumps(results, ensure_ascii=False, indent=4))
    return results
