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
import hashlib
import hmac
import random
import time
import typing

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from ..base import DataAPI
from ..domains import BKAPP_YUNTI_API_ROOT


def yunti_api_before_request(params) -> typing.Dict[str, typing.Any]:
    api_ts: int = int(time.time())
    api_key_name: str = settings.BKAPP_REQUEST_YUNTI_APP_KEY
    api_key_secret: str = settings.BKAPP_REQUEST_YUNTI_SECRET
    api_sign: str = hmac.new(
        api_key_secret.encode("utf8"),
        (str(api_ts) + api_key_name).encode("utf8"),
        hashlib.sha1,
    ).hexdigest()

    params["api_key"] = api_key_name
    params["api_ts"] = api_ts
    params["api_sigin"] = api_sign
    params["jsonrpc"] = "2.0"
    params["id"] = f"{str(api_ts)}{random.randint(100000, 999999)}"
    return params


def yunti_api_after_request(result):
    data = result.pop("result")
    result["data"] = data
    result["result"] = True
    return result


class _YunTiApi(object):
    MODULE = _("云梯")

    def __init__(self):

        self.get_security_group_details = DataAPI(
            method="POST",
            url=BKAPP_YUNTI_API_ROOT + "/account/manage?api_key={api_key}&api_sign={api_sigin}&api_ts={api_ts}",
            module=self.MODULE,
            description="查询安全组详情",
            before_request=yunti_api_before_request,
            after_request=yunti_api_after_request,
        )

        self.operate_security_group = DataAPI(
            method="POST",
            url=BKAPP_YUNTI_API_ROOT + "/apply/api/sg?api_key={api_key}&api_sign={api_sigin}&api_ts={api_ts}",
            module=self.MODULE,
            description="修改安全组",
            before_request=yunti_api_before_request,
            after_request=yunti_api_after_request,
        )
