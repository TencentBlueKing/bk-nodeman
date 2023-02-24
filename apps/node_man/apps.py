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

        # 判断 APIGW 的表是否存在，不存在先跳过
        from apigw_manager.apigw.models import Context

        if Context._meta.db_table not in connection.introspection.table_names():
            # 初次部署表不存在时跳过 DB 写入操作
            logger.info(f"[ESB][JWT] {Context._meta.db_table} not exists, skip fetch_esb_api_key before migrate.")
        else:
            logger.info(f"[ESB][JWT] {Context._meta.db_table} exist, start to fetch_esb_api_key.")
            self.fetch_esb_api_key()

        try:
            self.init_settings()
        except ProgrammingError as e:
            logger.info(f"init settings failed, err_msg -> {e}.")
        return True

    def fetch_esb_api_key(self):
        """
        获取JWT公钥并存储到全局配置中
        """

        # 当环境整体使用 APIGW 时，尝试通过 apigw-manager 获取 esb & apigw 公钥
        if settings.BKPAAS_MAJOR_VERSION == env_constants.BkPaaSVersion.V3.value:
            try:
                call_command("fetch_apigw_public_key")
            except Exception:
                logger.info("[ESB][JWT] fetch apigw public key error")
            else:
                logger.info("[ESB][JWT] fetch apigw public key success")

            try:
                call_command("fetch_esb_public_key")
            except Exception:
                logger.info("[ESB][JWT] fetch esb public key error")
            else:
                logger.info("[ESB][JWT] fetch esb public key success")

        client = get_client_by_user(user_or_username=settings.SYSTEM_USE_API_ACCOUNT)
        esb_result = client.esb.get_api_public_key()
        if not esb_result["result"]:
            logger.error(f'[ESB][JWT] get esb api public key error:{esb_result["message"]}')
            return

        from apigw_manager.apigw.helper import PublicKeyManager

        api_public_key = esb_result["data"]["public_key"]
        # esb-ieod-clouds / bk-esb / apigw 为各个环境的约定值，由 ESB 调用时解析 jwt header 的 kid 属性获取
        # Refer：site-packages/apigw_manager/apigw/providers.py
        if settings.RUN_VER == "ieod":
            # ieod 环境需要额外注入 esb 公钥，从而支持 ESB & APIGW
            PublicKeyManager().set("esb-ieod-clouds", api_public_key)
            logger.info("[ESB][JWT] get esb api public key and save to esb-ieod-clouds")
        elif settings.BKPAAS_MAJOR_VERSION != env_constants.BkPaaSVersion.V3.value:
            # V2 环境没有 APIGW，手动注入
            PublicKeyManager().set("bk-esb", api_public_key)
            PublicKeyManager().set("apigw", api_public_key)
            logger.info("[ESB][JWT] get esb api public key and save to bk-esb & apigw")

    def init_settings(self):
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
            defaults=dict(
                v_json=["basereport", "exceptionbeat", "processbeat", "bkunifylogbeat", "bkmonitorbeat", "gsecmdline"]
            ),
        )
        settings.HEAD_PLUGINS = obj.v_json

        obj, created = GlobalSettings.objects.get_or_create(
            key=GlobalSettings.KeyEnum.REGISTER_WIN_SERVICE_WITH_PASS.value, defaults=dict(v_json=False)
        )
        settings.REGISTER_WIN_SERVICE_WITH_PASS = obj.v_json
