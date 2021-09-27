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
import os

from blueapps.utils.esbclient import get_client_by_user
from django.apps import AppConfig
from django.conf import settings
from django.db import ProgrammingError, connection

from common.log import logger


class ApiConfig(AppConfig):
    name = "apps.node_man"
    verbose_name = "NODE_MAN"

    def ready(self):
        """
        初始化部分配置，主要目的是为了SaaS和后台共用部分配置
        """
        from apps.node_man.models import GlobalSettings

        if GlobalSettings._meta.db_table not in connection.introspection.table_names():
            # 初次部署表不存在时跳过DB写入操作
            logger.info(f"{GlobalSettings._meta.db_table} not exists, skip fetch_esb_api_key before migrate.")
        else:
            self.fetch_esb_api_key()

        try:
            self.init_settings()
        except ProgrammingError as e:
            logger.info(f"init settings failed, err_msg -> {e}.")
        return True

    def fetch_esb_api_key(self):
        """
        企业版获取JWT公钥并存储到全局配置中
        """
        if hasattr(settings, "APIGW_PUBLIC_KEY") or os.environ.get("BKAPP_APIGW_CLOSE"):
            return
        from apps.node_man.models import GlobalSettings

        try:
            config = GlobalSettings.objects.filter(key=GlobalSettings.KeyEnum.APIGW_PUBLIC_KEY.value).first()
        except ProgrammingError:
            config = None

        if config:
            # 从数据库取公钥，若存在，直接使用
            settings.APIGW_PUBLIC_KEY = config.v_json
            message = "[ESB][JWT]get esb api public key success (from db cache)"
            # flush=True 实时刷新输出
            logger.info(message)
        else:
            if settings.RUN_MODE == "DEVELOP":
                return

            client = get_client_by_user(user_or_username=settings.SYSTEM_USE_API_ACCOUNT)
            esb_result = client.esb.get_api_public_key()
            if esb_result["result"]:
                api_public_key = esb_result["data"]["public_key"]
                settings.APIGW_PUBLIC_KEY = api_public_key
                # 获取到公钥之后回写数据库
                GlobalSettings.objects.update_or_create(
                    key=GlobalSettings.KeyEnum.APIGW_PUBLIC_KEY,
                    defaults={"v_json": api_public_key},
                )
                logger.info("[ESB][JWT]get esb api public key success (from realtime api)")
            else:
                logger.error(f'[ESB][JWT]get esb api public key error:{esb_result["message"]}')

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
