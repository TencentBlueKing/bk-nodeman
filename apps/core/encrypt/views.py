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
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet

from . import handlers, serializers

RSA_VIEW_TAGS = ["rsa"]


class RSAViewSet(APIViewSet):
    URL_BASE_NAME = "encrypt_rsa"

    @swagger_auto_schema(
        operation_id="fetch_public_keys",
        operation_summary="获取公钥列表",
        tags=RSA_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.AsymmetricFetchKeysSerializer)
    def fetch_public_keys(self, request):
        """
        @api {POST} /encrypt_rsa/fetch_public_keys/  获取公钥列表
        @apiName fetch_public_keys
        @apiGroup rsa
        @apiParam {String[]} names 公钥名称列表
        @apiParamExample {Json} 请求参数
        {
            "names": ["DEFAULT"]
        }
        @apiSuccessExample {json} 公钥信息列表:
        [
            {
                "name": "DEFAULT",
                "description": "默认RSA密钥",
                "content": "-----BEGIN PUBLIC KEY-----\n xxx\n-----END PUBLIC KEY-----"
            }
        ]
        """
        return Response(handlers.AsymmetricHandler.fetch_public_keys(names=self.validated_data["names"]))


class AsymmetricViewSet(APIViewSet):
    URL_BASE_NAME = "encrypt_asymmetric"

    @swagger_auto_schema(
        operation_summary="获取公钥列表",
        tags=["asymmetric"],
    )
    @action(detail=False, methods=["POST"], serializer_class=serializers.AsymmetricFetchKeysSerializer)
    def fetch_public_keys(self, request):
        """
        @api {POST} /encrypt_asymmetric/fetch_public_keys/  获取公钥列表
        @apiName fetch_public_keys
        @apiGroup asymmetric
        @apiParam {String[]} names 公钥名称列表
        """
        return Response(handlers.AsymmetricHandler.fetch_public_keys(names=self.validated_data["names"]))
