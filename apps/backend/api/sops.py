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
import logging

import ujson as json
from blueapps.utils.esbclient import get_client_by_user
from django.conf import settings

from common.api.modules.ee_sops_client import CustomSopsClient

from .errors import EmptyResponseError, FalseResultError

logger = logging.getLogger("app")


class SopsClient(object):
    """
    SOPS客户端封装类
    """

    def __init__(
        self,
        bk_biz_id,
        username,
        bk_app_code=None,
        bk_app_secret=None,
        sops_api_host=None,
        default=True,
        **kwargs,
    ):
        self.bk_biz_id = bk_biz_id
        self.username = username
        if default:
            self.client = get_client_by_user(settings.BACKEND_SOPS_OPERATOR)
        else:
            self.client = CustomSopsClient(
                common_args={"bk_username": self.username},
                bk_app_code=bk_app_code,
                bk_app_secret=bk_app_secret,
                sops_api_host=sops_api_host,
            )

    def _response_exception_filter(self, api_name, params, response):
        """
        响应异常过滤器
        :param api_name: example: client.gse.register_proc_info
        :param params: api参数
        :param response: 响应
        :return: response['result']
        """
        if not response:
            logger.error(
                "user->[{}] called SOPS api->[{}] with params->[{}] but got no response.".format(
                    self.username, api_name, json.dumps(params)
                )
            )
            raise EmptyResponseError({"api_name": api_name})
        if not response["result"]:
            logger.error(
                logger.error(
                    "user->[{}] called SOPS api->[{}] with params->[{}] but an error->[FalseResultError] occurred."
                    "Full response->[{}].".format(self.username, params, api_name, json.dumps(response))
                )
            )
            raise FalseResultError({"api_name": api_name, "error_message": response["message"]})
        return response["data"]

    def create_task(self, name, template_id, ip_list):
        """
        创建标准运维任务
        :param name: 任务名称
        :param template_id: 模块ID
        :return: task_id
        """
        params = {
            "name": name,
            "template_id": template_id,
            "bk_biz_id": self.bk_biz_id,
            "bk_username": self.username,
            "constants": {"${iplist}": ip_list},
        }
        response = self.client.sops.create_task(params)
        result = self._response_exception_filter("client.job.create_task", params, response)
        return result["task_id"]

    def start_task(self, task_id):
        """
        开始任务
        :param task_id: 任务id
        :return:
        """
        params = {
            "task_id": task_id,
            "bk_biz_id": self.bk_biz_id,
            "bk_username": self.username,
        }
        response = self.client.sops.start_task(params)
        self._response_exception_filter("client.sops.create_task", params, response)
        return True

    def get_task_status(self, task_id):
        """
        查询任务状态
        :param task_id: 任务id
        :return:
        """
        params = {
            "task_id": task_id,
            "bk_biz_id": self.bk_biz_id,
            "bk_username": self.username,
        }
        response = self.client.sops.get_task_status(params)
        data = self._response_exception_filter("client.sops.get_task_status", params, response)
        return data["state"]


class DummySopsClient(SopsClient):
    """
    dummy sops client
    """

    pass
