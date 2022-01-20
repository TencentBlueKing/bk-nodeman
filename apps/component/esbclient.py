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
import sys

from blueapps.utils.request_provider import get_request
from django.conf import settings

from apps.exceptions import ComponentCallError

# 这里配置sdk包名和setting.RUN_VER的对应关系,需要维护
plat_package_map = {
    # 内部版
    "ieod": "ieod",
    # 腾讯云
    "qcloud": "qcloud",
    # 混合云
    "clouds": "clouds",
    # 企业版\社区版
    "open": "",
}


class SDKClient(object):
    sdk_package = None
    sdk_plat_module = dict()

    @property
    def __version__(self):
        return self.__class__.sdk_package.__version__

    def __new__(cls, bk_api_ver="", backend=False):
        if cls.sdk_package is None:
            try:
                cls.sdk_package = __import__(sdk_module_name(), fromlist=["shortcuts"])
            except ImportError as e:
                raise ImportError("sdk for platform({}) is not installed: {}".format(sdk_plat(), e))
        return super(SDKClient, cls).__new__(cls)

    def __init__(self, bk_api_ver="v2", backend=False):
        self.mod_name = ""
        self.sdk_mod = None
        self.bk_api_ver = bk_api_ver
        self.backend = backend or settings.BK_BACKEND_CONFIG
        self.username = "admin"
        self.bk_supplier_account = settings.DEFAULT_SUPPLIER_ACCOUNT

    def __getattr__(self, item):
        if not self.mod_name:
            # The key point here is the difference of self.mod_name and ret.mod_name
            # When called:
            #    client.xx will always comes to this block (since no code will set self.mod_name)
            #    client.xx.yyy will always come to the "else" block (in "ret" which is a new SDKClient instance)
            ret = SDKClient(self.bk_api_ver, self.backend)
            ret.mod_name = item
            ret.set_bk_supplier_account(self.bk_supplier_account)
            ret.setup_modules()
            if callable(ret.sdk_mod):
                return ret.sdk_mod
            return ret
        else:
            ret = _wrap_data_handler(getattr(self.sdk_mod, item))
        if callable(ret):
            # print self.mod_name, "->", item
            pass
        else:
            ret = self
        return ret

    def set_bk_supplier_account(self, bk_supplier_account):
        self.bk_supplier_account = bk_supplier_account

    def setup_modules(self):
        self.sdk_mod = getattr(self.sdk_client, self.mod_name, None)
        if self.sdk_mod is None:
            raise ImportError("sdk for platform({}) has no module :{}".format(sdk_plat(), self.mod_name))

    # 正常 WEB 请求所使用的函数
    def _get_client(self):
        request = get_request()
        _client = self.sdk_package.shortcuts.get_client_by_request(request)
        if self.bk_api_ver:
            _client.set_bk_api_ver(self.bk_api_ver)
        return _client

    @property
    def sdk_client(self):
        try:
            # 后台任务 & 测试任务调用 ESB 接口不需要用户权限控制
            if self.backend is True or "celery" in sys.argv or "test" in sys.argv or "shell" in sys.argv:
                _client = self.sdk_package.client.ComponentClient(
                    app_code=settings.APP_ID, app_secret=settings.APP_TOKEN, common_args={"bk_username": self.username}
                )
                _client.common_args["bk_supplier_account"] = self.bk_supplier_account
            else:
                _client = self._get_client()
                _client.common_args["bk_supplier_account"] = self.bk_supplier_account

            if self.bk_api_ver:
                _client.set_bk_api_ver(self.bk_api_ver)

            return _client
        except Exception as e:
            raise TypeError(f"sdk can only be invoked through a Web request, error:{e}")


def _wrap_data_handler(sdk_method):
    def _wrap(*args, **kwargs):
        ignore_error = args[0].get("ignore_error", False) if args else False
        if ignore_error:
            args[0].pop("ignore_error")
        response = sdk_method(*args, **kwargs)

        # When ignore_error is False, only the first part "not response['result']" works.
        # When ignore_error is True, and response["data"] exists, the error will be ignored
        # (skip the if block via short circuit of response["result"])
        # The key point here is ComponentCallError(response) will ignore the response["data"] info
        if not response["result"] and (not ignore_error or response["data"] is None):
            raise ComponentCallError(response, (args, kwargs))
        return response["data"]

    return _wrap


def sdk_module_name():
    plat_package = (
        ".{}".format(plat_package_map.get(settings.RUN_VER)) if plat_package_map.get(settings.RUN_VER, "") else ""
    )
    return "blueking.component%s" % plat_package


def sdk_plat():
    return plat_package_map.get(settings.RUN_VER, settings.RUN_VER)


client_v2 = SDKClient(backend=True)
