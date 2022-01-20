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
from script_tools.wmiexec import WMIEXEC


def put_file(src_file, des_path, des_ip, username, password, domain="", share="ADMIN$"):
    """upload file"""
    cmd_str = "put " + str(src_file) + " " + str(des_path)
    executor = WMIEXEC(cmd_str, username, password, domain, share=share)
    executor.run(des_ip)
    return {
        "result": True,
        "data": "upload {} success to {}:{}".format(src_file, des_ip, des_path),
    }


def execute_cmd(cmd_str, ipaddr, username, password, domain="", share="ADMIN$", no_output=False):
    """execute command"""
    executor = WMIEXEC(cmd_str, username, password, domain, share=share, noOutput=no_output)
    result_data = executor.run(ipaddr)
    return {"result": True, "data": result_data}
