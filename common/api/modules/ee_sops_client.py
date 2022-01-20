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
import importlib
import logging

from django.conf import settings

try:
    from blueking.component import client, exceptions
except Exception:
    client = importlib.import_module("blueking.component.%s.client" % settings.RUN_VER)
    exceptions = importlib.import_module("blueking.component.%s.exceptions" % settings.RUN_VER)

logger = logging.getLogger("component")


class CustomSopsClient(object):
    def __init__(
        self,
        app_code=None,
        app_secret=None,
        common_args=None,
        use_test_env=False,
        language=None,
        bk_app_code=None,
        bk_app_secret=None,
        sops_api_host=None,
    ):
        self.sops = Sops(
            app_code, app_secret, common_args, use_test_env, language, bk_app_code, bk_app_secret, sops_api_host
        )


class Sops(client.BaseComponentClient):

    HTTP_STATUS_OK = 200

    def __init__(
        self,
        app_code=None,
        app_secret=None,
        common_args=None,
        use_test_env=False,
        language=None,
        bk_app_code=None,
        bk_app_secret=None,
        sops_api_host=None,
    ):
        """
        :param str app_code: App code to use
        :param str app_secret: App secret to use
        :param dict common_args: Args that will apply to every request
        :param bool use_test_env: whether use test version of components
        """
        super(Sops, self).__init__(
            app_code=app_code,
            app_secret=app_secret,
            common_args=common_args,
            use_test_env=use_test_env,
            language=language,
            bk_app_code=bk_app_code,
            bk_app_secret=bk_app_secret,
        )
        self.sops_host = sops_api_host

    def _request(self, method, url, params, data):
        try:
            resp = self.request(method, url, params, data)
        except Exception as e:
            logger.exception("Error occurred when requesting method=%s url=%s", method, url)
            raise exceptions.ComponentAPIException(self, "Request component error, Exception: %s" % str(e))

        # Parse result
        if resp.status_code != self.HTTP_STATUS_OK:
            message = "Request component error, status_code: %s" % resp.status_code
            raise exceptions.ComponentAPIException(self, message, resp=resp)
        try:
            # Parse response
            json_resp = resp.json()
            if not json_resp["result"]:
                # 组件返回错误时，记录相应的 request_id
                log_message = (
                    "Component return error message: %(message)s, request_id=%(request_id)s, "
                    "url=%(url)s, params=%(params)s, data=%(data)s, response=%(response)s"
                ) % {
                    "request_id": json_resp.get("request_id"),
                    "message": json_resp["message"],
                    "url": url,
                    "params": params,
                    "data": data,
                    "response": resp.text,
                }
                logger.error(log_message)
            return json_resp
        except Exception:
            raise exceptions.ComponentAPIException(
                self, "Return data format is incorrect, which shall be unified as json", resp=resp
            )

    def create_task(self, params):
        url = self.sops_host + "/api/c/compapi/v2/sops/create_task/"
        return self._request("POST", url, {}, data=params)

    def start_task(self, params):
        url = self.sops_host + "/api/c/compapi/v2/sops/start_task/"
        return self._request("POST", url, {}, data=params)

    def get_task_status(self, params):
        url = self.sops_host + "/api/c/compapi/v2/sops/get_task_status/"
        return self._request("POST", url, {}, data=params)
