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
import time
from uuid import uuid4

import requests
from django.conf import settings


class TaiHuApis(object):
    def __init__(self):
        self.passid = settings.APP_CODE
        self.sender = settings.TAIHU_MAIL_SENDER
        self.token = settings.TAIHU_TOKEN
        self.url_root = settings.TAIHU_API_ROOT
        self.session = requests.Session()

    @property
    def random_timestamp(self) -> str:
        return str(int(time.time()))

    @property
    def request_headers(self) -> dict:
        """请求头"""
        timestamp = self.random_timestamp
        nonce = self.random_nonce
        hash_obj = hashlib.sha256()
        # 签名算法：x-rio-signature= sha256(x-rio-timestamp+Token+x-rio-nonce+x-rio-timestamp).upper()
        string = timestamp + self.token + nonce + timestamp
        hash_obj.update(string.encode())
        signature = hash_obj.hexdigest().upper()
        headers = {
            "x-rio-paasid": self.passid,
            "x-rio-nonce": nonce,
            "x-rio-timestamp": timestamp,
            "x-rio-signature": signature,
        }
        return headers

    @property
    def random_nonce(self) -> str:
        return str(uuid4())

    def send_mail(self, to: str, title: str, content: str):
        """发送邮件"""
        data = {
            "From": self.sender,
            "To": to,
            "Title": title,
            "Content": content,
        }
        headers = self.request_headers
        self.session.post(url=self.url_root + "/ebus/tof4_msg/api/v1/Message/SendMailInfo", headers=headers, json=data)


# 注：新增太湖API时，请确保环境变量中token和API root已配置
if all(getattr(settings, attr, False) for attr in ["TAIHU_MAIL_SENDER", "TAIHU_TOKEN", "TAIHU_API_ROOT"]):
    taihu_client = TaiHuApis()
else:
    taihu_client = object
