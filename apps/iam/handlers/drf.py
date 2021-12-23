# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸 (Blueking) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
from functools import wraps
from typing import Callable, List

from iam import Resource
from rest_framework import permissions

from . import Permission
from .actions import ActionEnum, ActionMeta
from .resources import ResourceEnum, ResourceMeta


class IAMPermission(permissions.BasePermission):
    def __init__(self, actions: List[ActionMeta], resources: List[Resource] = None):
        self.actions = actions
        self.resources = resources or []

    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        # 超级管理员，直接返回
        if request.user.is_superuser:
            return True

        if not self.actions:
            return True

        client = Permission()
        for action in self.actions:
            client.is_allowed(
                action=action,
                resources=self.resources,
                raise_exception=True,
            )
        return True

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return self.has_permission(request, view)


class BusinessActionPermission(IAMPermission):
    """
    关联业务的动作权限检查
    """

    def __init__(self, actions: List[ActionMeta]):
        super(BusinessActionPermission, self).__init__(actions)

    @classmethod
    def fetch_biz_id_by_request(cls, request, view):
        bk_biz_id = view.kwargs.get("bk_biz_id")
        if bk_biz_id is None:
            bk_biz_id = request.data.get("bk_biz_id", 0) or request.query_params.get("bk_biz_id", 0)
        return bk_biz_id

    def has_permission(self, request, view):
        bk_biz_id = self.fetch_biz_id_by_request(request, view)
        if not bk_biz_id:
            return True
        self.resources = [ResourceEnum.BUSINESS.create_instance(bk_biz_id)]
        return super(BusinessActionPermission, self).has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        # 先查询对象中有没有业务ID相关属性
        bk_biz_id = None
        if hasattr(obj, "bk_biz_id"):
            bk_biz_id = obj.bk_biz_id
        if bk_biz_id:
            self.resources = [ResourceEnum.BUSINESS.create_instance(bk_biz_id)]
            return super(BusinessActionPermission, self).has_object_permission(request, view, obj)
        # 没有就尝试取请求的业务ID
        return self.has_permission(request, view)


class ViewBusinessPermission(BusinessActionPermission):
    """
    业务访问权限检查
    """

    def __init__(self):
        super(ViewBusinessPermission, self).__init__([ActionEnum.VIEW_BUSINESS])


class InstanceActionPermission(IAMPermission):
    """
    关联其他资源的权限检查
    """

    def __init__(self, actions: List[ActionMeta], resource_meta: ResourceMeta, instance_ids_getter: Callable = None):
        self.resource_meta = resource_meta
        self.instance_ids_getter = instance_ids_getter
        super(InstanceActionPermission, self).__init__(actions)

    def has_permission(self, request, view):
        if self.instance_ids_getter is None:
            # Perform the lookup filtering.
            lookup_url_kwarg = self.resource_meta.lookup_field or view.lookup_url_kwarg or view.lookup_field

            assert lookup_url_kwarg in view.kwargs, (
                "Expected view %s to be called with a URL keyword argument "
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                "attribute on the view correctly." % (self.__class__.__name__, lookup_url_kwarg)
            )

            instance_ids = [view.kwargs[lookup_url_kwarg]]
        else:
            instance_ids = self.instance_ids_getter(request)

        self.resources = [self.resource_meta.create_simple_instance(instance_id) for instance_id in instance_ids]
        return super(InstanceActionPermission, self).has_permission(request, view)


def insert_permission_field(
    actions: List[ActionMeta],
    resource_meta: ResourceMeta,
    id_field: Callable = lambda item: item["id"],
    data_field: Callable = lambda data_list: data_list,
    always_allowed: Callable = lambda item: False,
    many: bool = True,
):
    """
    数据返回后，插入权限相关字段
    :param actions: 动作列表
    :param resource_meta: 资源类型
    :param id_field: 从结果集获取ID字段的方式
    :param data_field: 从response.data中获取结果集的方式
    :param always_allowed: 满足一定条件进行权限豁免
    :param many: 是否为列表数据
    """

    def wrapper(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            response = view_func(*args, **kwargs)

            result_list = data_field(response.data)
            if not many:
                result_list = [result_list]

            resources = [
                [
                    resource_meta.create_simple_instance(
                        instance_id=id_field(item),
                        attribute={"bk_biz_id": item["bk_biz_id"]} if "bk_biz_id" in item else None,
                    )
                ]
                for item in result_list
                if id_field(item)
            ]

            if not resources:
                return response

            permission_result = Permission().batch_is_allowed(actions, resources)

            for item in result_list:
                origin_instance_id = id_field(item)
                if not origin_instance_id:
                    # 如果拿不到实例ID，则不处理
                    continue
                instance_id = str(origin_instance_id)
                item.setdefault("permission", {})
                item["permission"].update(permission_result[instance_id])

                if always_allowed(item):
                    # 权限豁免
                    for action_id in item["permission"]:
                        item["permission"][action_id] = True

            return response

        return wrapped_view

    return wrapper


def grant_creator_action(
    resource_meta: ResourceMeta,
    id_field: Callable = lambda item: item["id"],
    name_field: Callable = lambda item: item["name"],
):
    """
    创建资源后，新建实例关联权限授权
    :param resource_meta: 资源类型
    :param id_field: 从结果集获取取资源实例ID字段的方式
    :param name_field: 从结果集获取资源实例名称字段的方式
    """

    def wrapper(view_func):
        @wraps(view_func)
        def wrapped_view(view, request, *args, **kwargs):
            response = view_func(view, request, *args, **kwargs)

            inst_id = id_field(response.data)
            inst_name = name_field(response.data)
            attribute = {
                "id": str(inst_id),
                "name": inst_name,
            }
            bk_biz_id = kwargs.get("bk_biz_id")
            if bk_biz_id is not None:
                attribute["bk_biz_id"] = bk_biz_id
            resource = resource_meta.create_instance(inst_id, attribute)
            # 新建授权
            Permission().grant_creator_action(
                resource=resource,
                creator=request.user.username,
            )
            return response

        return wrapped_view

    return wrapper
