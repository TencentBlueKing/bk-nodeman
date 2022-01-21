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
import base64
import hashlib
import hmac
import os
import re
import time
from typing import Any, Dict, Tuple

import requests
import ujson as json
from Crypto.Cipher import AES

from apps.node_man import constants
from apps.utils import env


class BasePasswordHandler(object):
    def get_password(self, username: str, cloud_ip_list: list, **options) -> Tuple[bool, Dict, Dict, str]:
        """
        查询主机密码
        :param username: 用户名
        :param cloud_ip_list: 云区域-IP列表，如"0-127.0.0.1"
        :return: is_ok, success_ips, failed_ips, message
        (True, {"0-127.0.0.1": "passwordSuccessExample"}, {"0-255.255.255.255": "用户没有权限"}, "success")
        (False, {}, {}, "{'10': 'ticket is expired'}")
        """
        raise NotImplementedError()


class DefaultPasswordHandler(BasePasswordHandler):
    """
    默认密码处理器
    """

    TJJ_PASSWORD = os.environ.get("TJJ_PASSWORD", "")
    TJJ_HOST = os.environ.get("TJJ_HOST", "")
    TJJ_ACTION = os.environ.get("TJJ_ACTION", "")
    TJJ_APP_CODE = os.environ.get("TJJ_APP_CODE", "")
    TJJ_SECRET_ID = os.environ.get("TJJ_SECRET_ID", "")
    TJJ_SECRET_KEY = os.environ.get("TJJ_SECRET_KEY", "")
    TJJ_SECRET_KEY = TJJ_SECRET_KEY.encode("utf8") if not isinstance(TJJ_SECRET_KEY, bytes) else TJJ_SECRET_KEY
    TJJ_KEY = os.environ.get("TJJ_KEY", "")

    def generate_signature(self, method, path, date_str):
        """获得签名 ."""
        signable_list = []
        message = "{}: {} {}".format("(request-target)", method.lower(), path)
        signable_list.append(message)
        message = "{}: {}".format("host", self.TJJ_HOST)
        signable_list.append(message)
        message = "{}: {}".format("date", date_str)
        signable_list.append(message)
        signable_str = "\n".join(signable_list).encode("ascii")
        # 将字符串转换为utf8/bytes编码
        msg = signable_str.encode("utf8") if not isinstance(signable_str, bytes) else signable_str
        # hash签名
        signed = hmac.new(self.TJJ_SECRET_KEY, msg=msg, digestmod=hashlib.sha256).digest()
        signature = base64.b64encode(signed).decode("ascii")
        return signature

    def generate_authorization_header(self, signature):
        """获得认证头部 ."""
        sig_str = 'Signature headers="(request-target) host date",keyId="%s",algorithm="hmac-sha256",signature="%s"'
        return sig_str % (self.TJJ_SECRET_ID, signature)

    def post(self, action, kwargs):
        uri = f"/component/compapi/{action.lstrip('/')}"
        date_str = str(int(time.time()))
        signature = self.generate_signature("post", uri, date_str)
        authorization = self.generate_authorization_header(signature)
        headers = {"Date": date_str, "Authorization": authorization}
        kwargs["app_code"] = self.TJJ_APP_CODE
        kwargs["app_secret"] = self.TJJ_SECRET_ID

        req = requests.post(f"http://{self.TJJ_HOST}{uri}", data=json.dumps(kwargs), headers=headers)
        return req.json()

    def get_key_and_iv(self, salt, klen=32, ilen=16):
        """
        :param salt: The salt.
        :param klen: The key length.
        :param ilen: The initialization vector length.
        :return: The message digest algorithm to use.
        """
        mdf = getattr(__import__("hashlib", fromlist=["md5"]), "md5")

        try:
            password = self.TJJ_PASSWORD.encode("ascii", "ignore")
            maxlen = klen + ilen
            keyiv = mdf(password + salt).digest()
            tmp = [keyiv]
            while len(tmp) < maxlen:
                tmp.append(mdf(tmp[-1] + password + salt).digest())
                keyiv += tmp[-1]  # append the last byte
            key = keyiv[:klen]
            iv = keyiv[klen : klen + ilen]
            return key, iv
        except UnicodeDecodeError:
            return None, None

    def decrypt(self, ciphertext):
        """
        解密
        """
        if isinstance(ciphertext, str):
            filtered = ""
            nl = "\n"
            re1 = r"^\s*$"
            re2 = r"^\s*#"
        else:
            filtered = b""
            nl = b"\n"
            re1 = b"^\\s*$"
            re2 = b"^\\s*#"

        for line in ciphertext.split(nl):
            line = line.strip()
            if re.search(re1, line) or re.search(re2, line):
                continue
            filtered += line + nl

        # Base64 decode
        raw = base64.b64decode(filtered)
        assert raw[:8] == b"Salted__"
        salt = raw[8:16]  # get the salt

        # Now create the key and iv.
        key, iv = self.get_key_and_iv(salt)
        if key is None:
            return None

        # The original ciphertext
        ciphertext = raw[16:]

        # Decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_plaintext = cipher.decrypt(ciphertext)
        if isinstance(padded_plaintext, str):
            padding_len = ord(padded_plaintext[-1])
        else:
            padding_len = padded_plaintext[-1]
        plaintext = padded_plaintext[:-padding_len]
        return plaintext.rstrip(b"\n")

    def fetch_pwd(self, username, hosts, **options):
        """
        查询主机密码
        """
        cloud_ip_list = [f"{constants.DEFAULT_CLOUD}-{ip}" for ip in hosts]
        is_success, success_ips, failed_ips, message = self.get_password(
            username, cloud_ip_list, ticket=options.get("ticket")
        )
        success_ips = [cloud_ip.split("-")[1] for cloud_ip in success_ips.keys()]
        return {
            "code": 0 if is_success else -1,
            "message": message,
            "data": {"success_ips": success_ips, "failed_ips": failed_ips},
            "result": is_success,
        }

    def parse_response_items(self, response_items: Dict) -> Dict[str, Any]:
        success_ips = {}
        failed_ips = {}
        for ip, value in response_items["IpList"].items():
            # 目前仅支持直连区域的密码查询，填充默认云区域ID
            if value["Code"] == 0:
                success_ips.update(
                    {f"{constants.DEFAULT_CLOUD}-{ip}": str(self.decrypt(value["Password"]), encoding="utf8")}
                )
            else:
                failed_ips.update({f"{constants.DEFAULT_CLOUD}-{ip}": value})
        return {"success_ips": success_ips, "failed_ips": failed_ips}

    def get_password(self, username: str, cloud_ip_list: list, **options) -> Tuple[bool, Dict, Dict, str]:
        ip_list = [cloud_ip.split("-")[1] for cloud_ip in cloud_ip_list]
        kwargs = {
            "operator": username,
            "data": {"Key": self.TJJ_KEY, "IpList": ip_list, "Ticket": options.get("ticket")},
        }

        try:
            result = self.post(self.TJJ_ACTION, kwargs)
        except Exception as e:
            return False, {}, {}, str(e)

        if not result["result"]:
            return False, {}, {}, result["message"]

        if result["data"]["HasError"]:
            return False, {}, {}, str(result["data"]["ResponseItems"])

        parse_response_items_result = self.parse_response_items(result["data"]["ResponseItems"])
        return True, parse_response_items_result["success_ips"], parse_response_items_result["failed_ips"], "success"


class TjjPasswordHandler(DefaultPasswordHandler):

    # 访问地址
    TJJ_IED_HOST = env.get_type_env(key="TJJ_IED_HOST", _type=str)
    # 请求资源
    TJJ_IED_ACTION = env.get_type_env(key="TJJ_IED_ACTION", _type=str)
    # 解密密钥
    TJJ_IED_PASSWORD = env.get_type_env(key="TJJ_IED_PASSWORD", default="", _type=str)
    # 认证唯一标识
    TJJ_IED_KEY = env.get_type_env(key="TJJ_IED_KEY", _type=str)

    def __init__(self):
        self.TJJ_PASSWORD = self.TJJ_IED_PASSWORD

    def get_password(self, username: str, cloud_ip_list: list, **options) -> Tuple[bool, Dict, Dict, str]:
        ip_list = [cloud_ip.split("-")[1] for cloud_ip in cloud_ip_list]
        try:
            response = requests.post(
                url=f"{self.TJJ_IED_HOST}{self.TJJ_IED_ACTION}",
                data=json.dumps({"Key": self.TJJ_IED_KEY, "Username": username, "IpList": ip_list}),
            )
            result = response.json()["Result"]
        except Exception as e:
            return False, {}, {}, str(e)

        if result["HasError"]:
            return False, {}, {}, str(result["ResponseItems"])

        parse_response_items_result = self.parse_response_items(result["ResponseItems"])
        return True, parse_response_items_result["success_ips"], parse_response_items_result["failed_ips"], "success"
