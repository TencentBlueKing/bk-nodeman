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
from celery.task import periodic_task

from apps.node_man import constants
from apps.node_man.constants import NodeType
from apps.node_man.exceptions import ConfigurationPolicyError
from apps.node_man.models import Host
from apps.node_man.policy.tencent_vpc_client import VpcClient
from common.log import logger


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=constants.CONFIGURATION_POLICY_INTERVAL,
)
def configuration_policy():
    """
    通过腾讯云VPC client 开通策略任务此任务与ConfigurationPolicy原子强绑定
    """
    task_id = configuration_policy.request.id
    logger.info(f"{task_id} | Start configuring policy.")

    client = VpcClient()
    is_ok, message = client.init()
    if not is_ok:
        logger.error(f"configuration_policy error: {message}")
        raise ConfigurationPolicyError()

    # 兼容nat网络，外网IP和登录IP都添加到策略中
    hosts = Host.objects.filter(node_type=NodeType.PROXY).values("login_ip", "outer_ip")
    need_add_ip_list = []
    for host in hosts:
        if host["login_ip"]:
            need_add_ip_list.append(host["login_ip"])
        if host["outer_ip"]:
            need_add_ip_list.append(host["outer_ip"])

    for template in client.ip_templates:
        using_ip_list = client.describe_address_templates(template)
        need_add_ip_list = list(set(need_add_ip_list) - set(using_ip_list))
        if need_add_ip_list:
            new_ip_list = need_add_ip_list + using_ip_list
            is_ok, message = client.add_ip_to_template(template, new_ip_list, need_query=False)
            if not is_ok:
                logger.error(f"configuration_policy error: {message}")
                raise ConfigurationPolicyError()

    logger.info(f"{task_id} | Configuration policy complete.")
