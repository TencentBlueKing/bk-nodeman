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
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import permissions

from apps.node_man.constants import IamActionType
from apps.node_man.handlers.iam import IamHandler
from apps.utils.local import get_request_username

from . import constants, models


class TagPermission(permissions.BasePermission):
    message = _("您没有该操作的权限")

    def has_permission(self, request, view):

        if view.action in ["list", "retrieve"]:
            return True

        if IamHandler().is_superuser(get_request_username()):
            return True

        if not settings.USE_IAM:
            return True

        perms = IamHandler().fetch_policy(
            get_request_username(), [IamActionType.plugin_pkg_operate, IamActionType.plugin_pkg_import]
        )

        # TODO 这里需要区分 Agent / 插件

        if view.action in ["partial_update", "delete"]:
            tag: models.Tag = view.get_object()
            if tag.target_type == constants.TargetType.PLUGIN.value:
                return tag.target_id in perms[IamActionType.plugin_pkg_operate]
        elif view.action in ["create"]:
            return perms[IamActionType.plugin_pkg_import]

        return False
