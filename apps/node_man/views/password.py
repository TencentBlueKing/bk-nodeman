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
from blueapps.account.conf import ConfFixture
from blueapps.account.handlers.response import ResponseHandler
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import action

from apps.generic import APIViewSet
from apps.node_man.handlers import password


class PasswordViews(APIViewSet):
    @action(methods=["post"], detail=False)
    def fetch_pwd(self, request, *args, **kwargs):
        """
        @api {POST} /tjj/fetch_pwd/  查询支持查询密码的主机
        @apiName fetch pwd
        @apiGroup Tjj
        @apiParam {String[]} hosts 主机IP
        @apiParamExample {Json} 请求参数
        {
            "hosts": [
                "x.x.x.x",
                "x.x.x.x"
            ]
        }
        @apiSuccessExample {json} 成功返回:
        {
            "result": True,
            "code": 0,
            "data": {
                "success_ips": ["x.x.x.x", "x.x.x.x"],
                "failed_ips": {
                    "x.x.x.x": {
                        "Code": 6,
                        "Message": "x.x.x.x不存在",
                        "Password": ""
                    }
                }
            },
            "message": "success"
        }
        """

        result = password.TjjPasswordHandler().fetch_pwd(
            request.user.username, request.data.get("hosts", []), ticket=request.COOKIES.get("TCOA_TICKET")
        )

        # ticket过期返回401
        if not result["result"] and ("ticket is expired" in result["message"] or "OATicket" in result["message"]):
            handler = ResponseHandler(ConfFixture, settings)
            return handler.build_401_response(request)

        return JsonResponse(result)
