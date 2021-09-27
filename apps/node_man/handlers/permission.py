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
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import permissions

from apps.node_man.constants import IamActionType
from apps.node_man.exceptions import CloudNotExistError
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.models import Cloud, GsePluginDesc, Packages, Subscription
from apps.utils.local import get_request_username


class GlobalSettingPermission(permissions.BasePermission):
    """
    全局配置权限控制
    """

    message = _("您没有权限执行操作")

    def has_permission(self, request, view):
        # 接入点编辑、删除、创建权限

        if view.action in ["list", "ap_is_using"]:
            # 不需要鉴权的action
            return True

        # 若没有使用权限中心
        if not settings.USE_IAM:
            if IamHandler.is_superuser(get_request_username()):
                return True
            else:
                self.message = _("您没有该接入点的权限")
                return False

        # 使用权限中心
        perms = IamHandler().fetch_policy(
            get_request_username(),
            [IamActionType.ap_edit, IamActionType.ap_delete, IamActionType.ap_create, IamActionType.ap_view],
        )

        if view.action in ["create", "test"] and perms[IamActionType.ap_create]:
            return True

        if view.action == "update" and int(view.kwargs.get("pk", 0)) in perms[IamActionType.ap_edit]:
            return True

        if view.action == "destroy" and int(view.kwargs.get("pk", 0)) in perms[IamActionType.ap_delete]:
            return True

        if view.action == "retrieve" and int(view.kwargs.get("pk", 0)) in perms[IamActionType.ap_view]:
            return True

        message_dict = {
            "create": _("您没有创建接入点的权限"),
            "update": _("您没有编辑该接入点的权限"),
            "destroy": _("您没有删除该接入点的权限"),
            "view": _("您没有查看该接入点详情的权限"),
        }

        self.message = message_dict.get(view.action, "您没有相应操作的权限")
        return False


class CloudPermission(permissions.BasePermission):
    """
    云区域权限控制
    """

    message = _("您没有权限执行操作")

    def has_permission(self, request, view):
        # 云区域查看、编辑、删除、创建权限

        if view.action == "list":
            # List接口不需要鉴权
            return True

        # **若没有使用权限中心**
        if not settings.USE_IAM:

            # 任何人都有创建云区域权限
            if view.action == "create":
                return True

            # 只有创建者和超管才有云区域详情、编辑、删除权限
            try:
                cloud = Cloud.objects.get(pk=int(view.kwargs.get("pk", -1)))
            except Cloud.DoesNotExist:
                raise CloudNotExistError(_("不存在ID为: {bk_cloud_id} 的云区域").format(bk_cloud_id=int(view.kwargs.get("pk"))))

            if get_request_username() in cloud.creator or IamHandler.is_superuser(get_request_username()):
                return True
            else:
                return False

        # **使用了权限中心**
        perms = IamHandler().fetch_policy(
            get_request_username(),
            [
                IamActionType.cloud_view,
                IamActionType.cloud_edit,
                IamActionType.cloud_delete,
                IamActionType.cloud_create,
            ],
        )

        if perms[IamActionType.cloud_create] and view.action == "create":
            return True

        if int(view.kwargs.get("pk", 0)) in perms[IamActionType.cloud_view] and view.action == "retrieve":
            return True

        if int(view.kwargs.get("pk", 0)) in perms[IamActionType.cloud_edit] and view.action == "update":
            return True

        if int(view.kwargs.get("pk", 0)) in perms[IamActionType.cloud_delete] and view.action == "destroy":
            return True

        message_dict = {
            "create": _("您没有创建云区域的权限"),
            "update": _("您没有编辑该云区域的权限"),
            "destroy": _("您没有删除该云区域的权限"),
            "retrieve": _("您没有查看该云区域详情的权限"),
        }

        self.message = message_dict.get(view.action, "您没有相应操作的权限")
        return False


class InstallChannelPermission(permissions.BasePermission):
    """
    安装通道权限控制，复用云区域的编辑权限
    """

    message = _("您没有权限执行操作，请申请云区域编辑权限")

    def has_permission(self, request, view):
        perms = IamHandler().fetch_policy(
            get_request_username(),
            [
                IamActionType.cloud_edit,
            ],
        )
        if view.action == "list":
            # List接口不需要鉴权
            return True
        if request.method == "GET":
            bk_cloud_id = request.query_params.get("bk_cloud_id")
        else:
            bk_cloud_id = request.data.get("bk_cloud_id")
        if bk_cloud_id in perms[IamActionType.cloud_edit]:
            return True
        return False


class DebugPermission(permissions.BasePermission):
    """
    Debug接口权限控制
    """

    message = _("您没有查询Debug接口的权限")

    def has_permission(self, request, view):
        # Debug接口权限控制，超管用户才有权限

        if IamHandler.is_superuser(get_request_username()):
            return True
        else:
            return False


class PackagePermission(permissions.BasePermission):
    """
    插件包权限控制
    """

    message = _("您没有该操作的权限")

    def has_permission(self, request, view):
        if view.action in ["list", "retrieve", "operate", "fetch_package_deploy_info"]:
            # 不需要鉴权的action
            return True

        if IamHandler().is_superuser(get_request_username()):
            return True

        if not settings.USE_IAM:
            return True

        # **使用了权限中心**
        if settings.USE_IAM:
            perms = IamHandler().fetch_policy(
                get_request_username(), [IamActionType.plugin_pkg_operate, IamActionType.plugin_pkg_import]
            )

            if view.action in ["update", "history"]:
                return int(view.kwargs.get("pk", 0)) in perms[IamActionType.plugin_pkg_operate]

            if view.action in ["plugin_status_operation"]:
                return not set(request.data.get("id", [])) - set(perms[IamActionType.plugin_pkg_operate])

            if view.action in ["package_status_operation"]:
                plugin_package_ids = request.data.get("id", [])
                plugin_names = list(
                    Packages.objects.filter(id__in=plugin_package_ids).values_list("project", flat=True)
                )
                plugin_ids = list(GsePluginDesc.objects.filter(name__in=plugin_names).values_list("id", flat=True))
                return not set(plugin_ids) - set(perms[IamActionType.plugin_pkg_operate])

            if view.action in ["upload", "parse", "create_register_task", "query_register_task"]:
                return perms[IamActionType.plugin_pkg_import]

            if view.action in ["create_export_task", "query_export_task", "fetch_config_variables", "list_plugin_host"]:
                return True

        return False


class PolicyPermission(permissions.BasePermission):
    """
    策略权限控制
    """

    message = _("您没有该操作的权限")

    def has_permission(self, request, view):

        if view.action in ["search"]:
            return True

        if IamHandler().is_superuser(get_request_username()):
            return True

        if not settings.USE_IAM:
            return True

        # **使用了权限中心**
        if view.action in [
            "update",
            "retrieve",
            "update_policy",
            "run_policy",
            "upgrade_preview",
            "operate",
            "rollback_preview",
        ]:
            perms = IamHandler().fetch_policy(get_request_username(), [IamActionType.strategy_operate])
            operate_perms = perms[IamActionType.strategy_operate]

            pk = int(view.kwargs.get("pk", 0))
            if view.action in ["operate", "rollback_preview"]:
                pk = int(request.data.get("policy_id", 0))

            try:
                policy = Subscription.objects.get(id=pk)
            except Subscription.DoesNotExist:
                return False

            return policy.pid in operate_perms if policy.pid != -1 else policy.id in operate_perms

        if view.action in [
            "fetch_common_variable",
            "fetch_policy_topo",
            "selected_preview",
            "plugin_preselection",
            "fetch_policy_abnormal_info",
            "migrate_preview",
        ]:
            # 不需要鉴权的action
            return True

        bk_biz_scope = list(set([node["bk_biz_id"] for node in request.data["scope"]["nodes"]]))

        if view.action in ["host_policy"]:
            return CmdbHandler().check_biz_permission(bk_biz_scope, IamActionType.strategy_view)

        if view.action in ["create_policy"]:
            return CmdbHandler().check_biz_permission(bk_biz_scope, IamActionType.strategy_create)

        return False
