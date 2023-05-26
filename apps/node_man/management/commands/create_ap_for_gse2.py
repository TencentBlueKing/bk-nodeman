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
import json
from copy import deepcopy
from typing import Dict

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from apps.core.gray.handlers import GrayHandler
from apps.exceptions import ValidationError
from apps.node_man.constants import GSE_V2_PORT_DEFAULT_VALUE
from apps.node_man.models import AccessPoint, GlobalSettings
from env.constants import GseVersion


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-r", "--reference_ap_id", type=int, required=True, help="AP_ID create from V1 AP_ID")
        parser.add_argument(
            "-c", "--clean_old_map_id", action="store_true", default=False, help="Clean up the original mapping ID"
        )

    def format_gse2_agent_config(self, agent_config):
        for key, value in agent_config.items():
            if isinstance(value, dict):
                self.format_gse2_agent_config(value)
            elif isinstance(value, str) and "hostid" not in value:
                # 接入点ID路径不变
                agent_config[key] = value.replace("gse", "gse2")

    def handle(self, **kwargs):
        gse_v1_ap: AccessPoint = AccessPoint.objects.filter(
            id=kwargs["reference_ap_id"],
            gse_version=GseVersion.V1.value,
        ).first()
        if not gse_v1_ap:
            raise ValidationError("The AP ID you entered does not exist. Please confirm and try again.")

        with atomic():
            # 生成GSEV2接入点信息
            gse_v2_ap: AccessPoint = deepcopy(gse_v1_ap)
            gse_v2_ap.pk: int = None

            gse_v2_ap.name: str = f"GSE2_{gse_v1_ap.name}"
            gse_v2_ap.description: str = f"GSE2_{gse_v1_ap.description}"
            gse_v2_ap.gse_version: str = GseVersion.V2.value

            # 更新port_config
            gse_v2_ap.port_config: Dict[str, int] = GSE_V2_PORT_DEFAULT_VALUE
            print(f"\nGSE2 port_config:\n{json.dumps(GSE_V2_PORT_DEFAULT_VALUE, indent=4)}")

            # 更新agent_config
            gse_v2_agent_config: Dict[str, Dict[str, str]] = gse_v1_ap.agent_config
            self.format_gse2_agent_config(gse_v2_agent_config)
            print(f"\nGSE2 agent_config:\n{json.dumps(gse_v2_agent_config, indent=4)}")

            gse_v2_ap.agent_config: Dict[str, Dict[str, str]] = gse_v2_agent_config
            gse_v2_ap.save()

            # 全局配置写入接入点映射
            try:
                gray_ap_map: Dict[int, int] = GrayHandler.get_gray_ap_map()
            except Exception:
                gray_ap_map: Dict[int, int] = {}

            if kwargs["clean_old_map_id"]:
                # 清理掉原有映射的AP
                AccessPoint.objects.filter(id=gray_ap_map[gse_v1_ap.id]).delete()

            # 暂不支持一对多，强制更新为最后一次执行的映射
            gray_ap_map[gse_v1_ap.id] = gse_v2_ap.id
            GlobalSettings.objects.update_or_create(
                key=GlobalSettings.KeyEnum.GSE2_GRAY_AP_MAP.value, defaults={"v_json": gray_ap_map}
            )

            print(
                "\nThe GSE V2 access point creation is complete. "
                "Please go to the NODEMAN global configuration to confirm the details."
            )
