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
import json
from typing import Any, Dict

from rest_framework import status
from rest_framework.test import APIClient

# DEFAULT_CONTENT_TYPE & DEFAULT_FORMAT 不能同时设置
DEFAULT_CONTENT_TYPE = None  # or "application/json"

DEFAULT_FORMAT = "json"


class CustomAPIClient(APIClient):
    @staticmethod
    def assert_response(response) -> Dict[str, Any]:
        assert response.status_code == status.HTTP_200_OK
        return json.loads(response.content)

    def get(self, path, data=None, follow=False, **extra):
        response = super().get(path=path, data=data, follow=float, **extra)
        return self.assert_response(response)

    def post(self, path, data=None, format=DEFAULT_FORMAT, content_type=DEFAULT_CONTENT_TYPE, follow=False, **extra):
        response = super().post(
            path=path, data=data, format=format, content_type=DEFAULT_CONTENT_TYPE, follow=follow, **extra
        )
        return self.assert_response(response)

    def put(self, path, data=None, format=DEFAULT_FORMAT, content_type=DEFAULT_CONTENT_TYPE, follow=False, **extra):
        response = super().put(
            path=path, data=data, format=format, content_type=DEFAULT_CONTENT_TYPE, follow=follow, **extra
        )
        return self.assert_response(response)

    def delete(self, path, data=None, format=DEFAULT_FORMAT, content_type=DEFAULT_CONTENT_TYPE, follow=False, **extra):
        response = super().delete(
            path=path, data=data, format=format, content_type=content_type, follow=follow, **extra
        )
        return self.assert_response(response)
