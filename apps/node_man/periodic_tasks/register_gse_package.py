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
import logging

from apps.backend.celery import app
from apps.node_man.tools.gse_package import GsePackageTools

logger = logging.getLogger("app")


@app.task(queue="default")
def register_gse_package_task(file_name, tags):
    upload_package_obj = GsePackageTools.get_latest_upload_record(file_name=file_name)

    extract_dir, agent_name = GsePackageTools.extract_gse_package(
        source_file_path=upload_package_obj.file_path,
    )

    _, artifact_builder_class = GsePackageTools.distinguish_gse_package(extract_dir=extract_dir, agent_name=agent_name)

    with artifact_builder_class(
        initial_artifact_path=upload_package_obj.file_path, tags=tags, extract_dir=extract_dir
    ) as builder:
        builder.applied_tmp_dirs.add(extract_dir)
        builder.make()
