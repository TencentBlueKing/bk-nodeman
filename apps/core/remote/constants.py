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

# ENCRYPTION_ALGS & KEX_ALGS 适配不同机型，由于有别于默认值，所以作为常量固化
# 使用过程中若抛出 KeyExchangeError 异常，可以根据异常提示进行补充
# 在SSH握手期间所使用的加密算法的列表
ENCRYPTION_ALGS = [
    "3des-cbc",
    "aes128-cbc",
    "aes128-ctr",
    "aes128-gcm@openssh.com",
    "aes192-cbc",
    "aes192-ctr",
    "aes256-cbc",
    "aes256-ctr",
    "aes256-gcm@openssh.com",
    "arcfour",
    "blowfish-cbc",
    "cast128-cbc",
    "chacha20-poly1305@openssh.com",
]

# 在SSH握手期间允许的密钥交换算法列表
KEX_ALGS = [
    "curve25519-sha256",
    "curve25519-sha256@libssh.org",
    "curve448-sha512",
    "diffie-hellman-group-exchange-sha1",
    "diffie-hellman-group-exchange-sha256",
    "diffie-hellman-group1-sha1",
    "diffie-hellman-group14-sha1",
    "diffie-hellman-group14-sha256",
    "diffie-hellman-group14-sha256@ssh.com",
    "diffie-hellman-group15-sha512",
    "diffie-hellman-group16-sha512",
    "diffie-hellman-group17-sha512",
    "diffie-hellman-group18-sha512",
    "ecdh-sha2-1.3.132.0.10",
    "ecdh-sha2-nistp256",
    "ecdh-sha2-nistp384",
    "ecdh-sha2-nistp521",
    "rsa2048-sha256",
]

# 默认的连接最长等待时间
DEFAULT_CONNECT_TIMEOUT = 30

# 默认的命令执行最长等待时间
DEFAULT_CMD_RUN_TIMEOUT = 30
