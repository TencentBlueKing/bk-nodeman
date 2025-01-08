# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from apigw_manager.apigw.helper import PublicKeyManager
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from common.api import GatewayApi
from common.log import logger
from env import constants as env_constants


class Command(BaseCommand):
    """
    拉取 ESB / APIGW 公钥
    这块不放在 apps init 中，减少进程启动数据，防止容器化部署情况下，Probe 探针在 app 未就绪情况下探活失败引起容器反复重启
    依赖 migrate 后执行
    """

    def handle(self, **kwargs):

        # 当环境整体使用 APIGW 时，尝试通过 apigw-manager 获取 esb & apigw 公钥
        if settings.BKPAAS_MAJOR_VERSION == env_constants.BkPaaSVersion.V3.value:

            for component_name in ["apigw"]:
                try:
                    call_command(f"fetch_{component_name}_public_key")
                except Exception as e:
                    logger.exception(f"[JWT][{component_name.upper()}] fetch apigw public key error: {str(e)}")
                else:
                    logger.info(f"[JWT][{component_name.upper()}] fetch {component_name} public key success")

        query_args = {"api_name": "bk-nodeman"}
        apigw_result = GatewayApi.get_apigw_public_key(query_args)
        if not apigw_result["public_key"]:
            logger.error(f'[JWT][APIGW] get esb api public key error:{apigw_result["message"]}')
            return

        api_public_key = apigw_result["public_key"]
        # esb-ieod-clouds / bk-esb / apigw 为各个环境的约定值，由 ESB 调用时解析 jwt header 的 kid 属性获取
        # Refer：site-packages/apigw_manager/apigw/providers.py
        if settings.RUN_VER == "ieod":
            # ieod 环境需要额外注入 esb 公钥，从而支持 ESB & APIGW
            PublicKeyManager().set("esb-ieod-clouds", api_public_key)
            logger.info("[JWT] get esb public key and save to esb-ieod-clouds")

        logger.info("[JWT] fetch component api public key success.")
