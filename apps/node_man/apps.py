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

from bk_notice_sdk.views import api_call
from blueapps.utils.esbclient import get_client_by_user
from django.apps import AppConfig
from django.conf import settings
from django.core.management import call_command
from django.db import ProgrammingError, connection

from common.log import logger
from env import constants as env_constants


class ApiConfig(AppConfig):
    name = "apps.node_man"
    verbose_name = "NODE_MAN"

    def ready(self):
        """
        初始化部分配置，主要目的是为了SaaS和后台共用部分配置
        """

        try:
            self.fetch_component_api_public_key()
            self.init_settings()
        except ProgrammingError as e:
            logger.info(f"init settings failed, err_msg -> {e}.")
        return True

    @classmethod
    def fetch_component_api_public_key(cls):
        """
        获取JWT公钥并存储到全局配置中
        """

        # 以下几种情况任一成立则不同步
        # 1.PaaSV3 情况下通过 manage.py 执行同步
        # 2.后台情况下，交由 SaaS 执行同步
        if any(
            [
                settings.BKPAAS_MAJOR_VERSION == env_constants.BkPaaSVersion.V3.value,
                settings.BK_BACKEND_CONFIG,
            ]
        ):
            logger.info("[JWT] skip fetch component api public key")
            return

        from apigw_manager.apigw.models import Context

        # 当依赖表暂未创建时，视为 migrate 尚未执行的阶段, 暂不同步
        # 后置这个检查，减少 DB IO
        if Context._meta.db_table not in connection.introspection.table_names():
            logger.info("[JWT] skip fetch component api public key")
            return

        client = get_client_by_user(user_or_username=settings.SYSTEM_USE_API_ACCOUNT)
        esb_result = client.esb.get_api_public_key()
        if not esb_result["result"]:
            logger.error(f'[JWT][ESB] get esb api public key error:{esb_result["message"]}')
            return

        from apigw_manager.apigw.helper import PublicKeyManager

        api_public_key = esb_result["data"]["public_key"]
        # V2 环境没有 APIGW，手动注入
        PublicKeyManager().set("bk-esb", api_public_key)
        PublicKeyManager().set("apigw", api_public_key)
        logger.info("[JWT][ESB] get api public key and save to bk-esb & apigw")

    @classmethod
    def init_settings(cls):
        """
        初始化配置，读取DB后写入settings内存中，避免多次查表
        """
        from apps.node_man.models import GlobalSettings

        obj, created = GlobalSettings.objects.get_or_create(
            key=GlobalSettings.KeyEnum.USE_TJJ.value, defaults=dict(v_json=False)
        )
        settings.USE_TJJ = obj.v_json

        obj, created = GlobalSettings.objects.get_or_create(
            key=GlobalSettings.KeyEnum.CONFIG_POLICY_BY_SOPS.value, defaults=dict(v_json=False)
        )
        settings.CONFIG_POLICY_BY_SOPS = obj.v_json

        obj, created = GlobalSettings.objects.get_or_create(
            key=GlobalSettings.KeyEnum.CONFIG_POLICY_BY_TENCENT_VPC.value, defaults=dict(v_json=False)
        )
        settings.CONFIG_POLICY_BY_TENCENT_VPC = obj.v_json

        obj, created = GlobalSettings.objects.get_or_create(
            key=GlobalSettings.KeyEnum.HEAD_PLUGINS.value,
            defaults=dict(v_json=["basereport", "exceptionbeat", "processbeat", "bkunifylogbeat", "bkmonitorbeat"]),
        )
        settings.HEAD_PLUGINS = obj.v_json

        obj, created = GlobalSettings.objects.get_or_create(
            key=GlobalSettings.KeyEnum.REGISTER_WIN_SERVICE_WITH_PASS.value, defaults=dict(v_json=False)
        )
        settings.REGISTER_WIN_SERVICE_WITH_PASS = obj.v_json

        # 注册消息中心app(适配各个环境只注册一次)
        if settings.BK_NOTICE_ENABLED:
            try:
                api_call(
                    api_method="register_application",
                    success_message="注册平台成功",
                    error_message="注册平台异常",
                    success_code=201,
                )
            except Exception as e:
                logger.error(e)

        plugin_common_constants = GlobalSettings.get_config(
            key=GlobalSettings.KeyEnum.PLUGIN_COMMON_CONSTANTS.value,
            default={},
        )
        settings.PLUGIN_COMMON_CONSTANTS = plugin_common_constants

        # 执行项目启动命令时才会自动同步，避免执行其他指令也自动同步
        if len(sys.argv) > 1 and (sys.argv[1] == "runserver" or sys.argv[0] == "gunicorn"):
            # 根据开关来决定是否执行 sync_apigw，上云环境不开启
            if settings.SYNC_APIGATEWAY_ENABLED:
                try:
                    call_command("sync_apigw")
                    logger.info("Successfully executed sync_apigw")
                except Exception as e:
                    logger.error(f"Error executing sync_apigw: {e}")
