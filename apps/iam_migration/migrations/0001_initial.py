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
import re

from django.conf import settings
from django.db import migrations
from iam.contrib.iam_migration.migrator import IAMMigrator


def forward_func(apps, schema_editor):
    file_path = getattr(settings, "BK_IAM_MIGRATION_JSON_PATH", "support-files/iam/")
    tpl_path = os.path.join(settings.BASE_DIR, file_path, Migration.migration_tpl)
    json_path = os.path.join(settings.BASE_DIR, file_path, Migration.migration_json)

    with open(tpl_path, "r", encoding="utf-8") as f:
        with open(json_path, "w+", encoding="utf-8") as e:
            result = re.sub(
                "http://__BK_NODEMAN_API_ADDR__",
                os.environ.get("BKAPP_NODEMAN_BACKEND_ADDR", settings.BK_IAM_URL),
                f.read(),
            )
            e.write(result)

    migrator = IAMMigrator(Migration.migration_json)
    migrator.migrate()


class Migration(migrations.Migration):
    migration_tpl = "0003_bk_nodeman_20200811-1145_iam.tpl"
    migration_json = "0003_bk_nodeman_20200811-1145_iam.json"

    dependencies = []

    operations = [migrations.RunPython(forward_func)]
