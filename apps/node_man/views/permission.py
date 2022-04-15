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
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet
from apps.node_man.constants import IAM_ACTION_DICT, IamActionType
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.serializers.iam import ApplyPermissionSerializer
from apps.utils.local import get_request_username


class PermissionViewSet(APIViewSet):
    @action(detail=False, methods=["POST"], serializer_class=ApplyPermissionSerializer)
    def fetch(self, request, *args, **kwargs):
        """
        @api {POST} /permission/fetch/ 根据条件返回用户权限
        @apiName fetch_permission
        @apiGroup Permission
        @apiParam {Object[]} apply_info 申请权限信息
        @apiParam {String="cloud_edit", "cloud_delete", "cloud_view",
        "cloud_create", "ap_create", "ap_delete", "ap_edit"} apply_info.action 操作类型
        @apiParam {Int} apply_info.instance_id 实例ID
        @apiParam {String} apply_info.instance_name 实例名
        @apiSuccessExample {Json} 成功返回:
        [{
            "system": "节点管理",
            "action": "编辑云区域",
            "instance_id": 11,
            "instance_name": cloud_one,
            "apply_url": "https://xxx.com/.../"
        }]
        """

        redirect_url = IamHandler().fetch_redirect_url(self.validated_data["apply_info"], get_request_username())

        return Response(
            {
                "apply_info": [
                    {
                        "system": _("节点管理"),
                        "action": IAM_ACTION_DICT[param["action"]],
                        "instance_id": param.get("instance_id", -1),
                        "instance_name": param.get("instance_name", ""),
                    }
                    for param in self.validated_data["apply_info"]
                ],
                "url": redirect_url,
            }
        )

    @action(detail=False, methods=["GET"])
    def cloud(self, request, *args, **kwargs):
        """
        @api {GET} /permission/cloud/ 返回用户云区域的权限
        @apiName list_cloud_permission
        @apiGroup Permission
        @apiSuccessExample {Json} 成功返回:
        {
            "edit_action": [bk_cloud_ids],
            "delete_action": [bk_cloud_ids],
            "create_action": True or False,
        }
        """
        perms = IamHandler().fetch_policy(
            get_request_username(),
            [
                IamActionType.cloud_view,
                IamActionType.cloud_edit,
                IamActionType.cloud_delete,
                IamActionType.cloud_create,
            ],
        )
        return Response(
            {
                "view_action": perms[IamActionType.cloud_view],
                "edit_action": perms[IamActionType.cloud_edit],
                "delete_action": perms[IamActionType.cloud_delete],
                "create_action": perms[IamActionType.cloud_create],
            }
        )

    @action(detail=False, methods=["GET"])
    def ap(self, request, *args, **kwargs):
        """
        @api {GET} /permission/ap/ 返回用户接入点权限
        @apiName list_ap_permission
        @apiGroup Permission
        @apiSuccessExample {Json} 成功返回:
        {
            "edit_action": [ap_ids],
            "delete_action": [ap_ids],
            "create_action": True or False
        }
        """
        perms = IamHandler().fetch_policy(
            get_request_username(), [IamActionType.ap_edit, IamActionType.ap_delete, IamActionType.ap_create]
        )

        return Response(
            {
                "edit_action": perms[IamActionType.ap_edit],
                "delete_action": perms[IamActionType.ap_delete],
                "create_action": perms[IamActionType.ap_create],
            }
        )

    @action(detail=False, methods=["GET"])
    def startegy(self, request, *args, **kwargs):
        """
        @api {GET} /permission/startegy/ 返回用户部署策略权限
        @apiName list_startegy_permission
        @apiGroup Permission
        @apiSuccessExample {Json} 成功返回:
        {
            "create_action": [biz_ids],
            "view_action": [biz_ids],
            "operate_action":[startegy_ids],
            "range_select_action": [startegy_ids],
            "delete_action": [startegy_ids],
        }
        """
        perms = IamHandler().fetch_policy(
            get_request_username(),
            [IamActionType.startegy_create, IamActionType.startegy_view, IamActionType.startegy_operate],
        )

        return Response(
            {
                "create_action": perms[IamActionType.startegy_create],
                "view_action": perms[IamActionType.startegy_view],
                "operate_action": perms[IamActionType.startegy_operate],
            }
        )

    @action(detail=False, methods=["GET"])
    def package(self, request, *args, **kwargs):
        """
        @api {GET} /permission/package/ 返回用户插件包权限
        @apiName list_package_permission
        @apiGroup Permission
        @apiSuccessExample {Json} 成功返回:
        {
            "import_action": True or False,
            "operate_action": [package_ids],
        }
        """
        perms = IamHandler().fetch_policy(
            get_request_username(), [IamActionType.plugin_pkg_import, IamActionType.plugin_pkg_operate]
        )

        return Response(
            {
                "import_action": perms[IamActionType.plugin_pkg_import],
                "operate_action": perms[IamActionType.plugin_pkg_operate],
            }
        )

    @action(detail=False, methods=["GET"])
    def plugin(self, request, *args, **kwargs):
        """
        @api {GET} /permission/plugin/ 返回用户插件实例权限
        @apiName list_plugin_instance_permission
        @apiGroup Permission
        @apiSuccessExample {Json} 成功返回:
        {
            "view_action": [biz_ids],
            "operate_action": [biz_ids],
        }
        """
        perms = IamHandler().fetch_policy(
            get_request_username(), [IamActionType.plugin_view, IamActionType.plugin_operate]
        )

        return Response(
            {"view_action": perms[IamActionType.plugin_view], "operate_action": perms[IamActionType.plugin_operate]}
        )
