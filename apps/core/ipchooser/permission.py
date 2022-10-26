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
import typing

from django.http import QueryDict
from django.utils.translation import ugettext_lazy as _

from apps.iam import Permission
from apps.iam.exceptions import PermissionDeniedError
from apps.iam.handlers.resources import Business
from apps.node_man.handlers import cmdb

from . import constants, types


class IpChooserBasePermission:
    @staticmethod
    def handle_scope_permission_denied(bk_biz_scope: typing.List[int], action: str):
        resources = Business.create_instances(set(bk_biz_scope))
        apply_data, apply_url = Permission().get_apply_data([action], resources)
        raise PermissionDeniedError(action_name=action, apply_url=apply_url, permission=apply_data)

    def has_scope_list_permission(
        self, request, validated_data: typing.Dict[str, typing.Any], user_biz_ids: typing.Set[int]
    ) -> bool:
        if not validated_data["all_scope"]:
            scope_list: types.ScopeList = [
                scope for scope in validated_data["scope_list"] if scope["bk_biz_id"] in user_biz_ids
            ]
            if scope_list:
                request.data["scope_list"] = scope_list
            else:
                # 传入的范围列表均没有权限，提示用户申请相应的访问权限
                self.handle_scope_permission_denied(
                    [scope["bk_biz_id"] for scope in validated_data["scope_list"]], validated_data["action"]
                )
        else:
            # 默认返回用户所拥有的业务权限
            scope_list: types.ScopeList = []
            for biz_id in user_biz_ids:
                scope_list.append(
                    {"scope_id": str(biz_id), "scope_type": constants.ScopeType.BIZ.value, "bk_biz_id": biz_id}
                )
            request.data["scope_list"] = scope_list
        return True


class IpChooserTopoPermission(IpChooserBasePermission):
    message = _("您没有该操作的权限")

    def has_permission(self, request, view):

        validated_data: typing.Dict[str, typing.Any] = view.validated_data
        user_biz_ids: typing.Set[int] = set(cmdb.CmdbHandler().biz_id_name({"action": validated_data["action"]}).keys())

        # request.data 修改，ref：https://stackoverflow.com/questions/33861545/
        if isinstance(request.data, QueryDict):
            request.data._mutable = True
        # 鉴权过程会调整 scope 范围，需要清理序列化器缓存
        if hasattr(view, "_validated_data"):
            delattr(view, "_validated_data")

        if view.action in ["trees"]:
            return self.has_scope_list_permission(request, validated_data, user_biz_ids)

        elif view.action in ["query_path", "query_hosts", "query_host_id_infos", "agent_statistics"]:
            # 原先传递的参数就是空，允许访问，不属于鉴权失败
            if not validated_data["node_list"]:
                return True
            node_list: typing.List[types.ReadableTreeNode] = [
                node for node in validated_data["node_list"] if node["meta"]["bk_biz_id"] in user_biz_ids
            ]
            if node_list:
                request.data["node_list"] = node_list
            else:
                # 传入的范围列表均没有权限，提示用户申请相应的访问权限
                self.handle_scope_permission_denied(
                    [node["meta"]["bk_biz_id"] for node in validated_data["node_list"]], validated_data["action"]
                )
            return True
        return False


class IpChooserHostPermission(IpChooserBasePermission):
    message = _("您没有该操作的权限")

    def has_permission(self, request, view):

        validated_data: typing.Dict[str, typing.Any] = view.validated_data
        user_biz_ids: typing.Set[int] = set(cmdb.CmdbHandler().biz_id_name({"action": validated_data["action"]}).keys())
        # request.data 修改，ref：https://stackoverflow.com/questions/33861545/
        if isinstance(request.data, QueryDict):
            request.data._mutable = True
        # 鉴权过程会调整 scope 范围，需要清理序列化器缓存
        if hasattr(view, "_validated_data"):
            delattr(view, "_validated_data")

        if view.action in ["check", "details"]:
            return self.has_scope_list_permission(request, validated_data, user_biz_ids)

        return False
