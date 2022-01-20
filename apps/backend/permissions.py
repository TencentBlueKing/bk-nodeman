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
from rest_framework.permissions import BasePermission

from apps.exceptions import (
    BkJwtClientException,
    BkJwtVerifyException,
    BkJwtVerifyFailException,
)
from common.log import logger

bk_jwt_backend = True
try:
    from blueapps.account.components.bk_jwt.backends import BkJwtBackend
except ImportError:
    bk_jwt_backend = False


class BackendBasePermission(BasePermission):
    """
    后台权限
    """

    @classmethod
    def get_auth_info(cls, request):
        if not bk_jwt_backend:
            raise BkJwtClientException()

        try:
            verify_data = BkJwtBackend.verify_bk_jwt_request(request)
        except Exception as e:
            logger.exception(u"[BK_JWT]校验异常: %s" % e)
            raise BkJwtVerifyException()

        if not verify_data["result"] or not verify_data["data"]:
            logger.error(u"BK_JWT 验证失败： %s" % (verify_data))
            raise BkJwtVerifyFailException()

        return {
            "bk_app_code": verify_data["data"]["app"]["bk_app_code"],
            "bk_username": verify_data["data"]["user"]["bk_username"],
        }

    def has_permission(self, request, view):
        self.get_auth_info(request)
        return True
