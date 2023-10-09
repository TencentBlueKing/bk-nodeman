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
import json
import os
from typing import Any, Dict

import requests
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

from apps.core.files import core_files_constants
from apps.core.files.storage import get_storage
from apps.node_man import exceptions
from apps.utils.files import md5sum
from apps.utils.local import get_request_username
from common.api import NodeApi


class PackageTools:
    @staticmethod
    def upload(package_file: InMemoryUploadedFile, module: str) -> Dict[str, Any]:
        """
        将文件上传至
        :param package_file: InMemoryUploadedFile
        :param module: 所属模块
        :return:
        {
            "result": True,
            "message": "",
            "code": "00",
            "data": {
                "id": record.id,  # 上传文件记录ID
                "name": record.file_name,  # 包名
                "pkg_size": record.file_size,  # 大小，
            }
        }
        """
        with package_file.open("rb") as tf:

            # 计算上传文件的md5
            md5 = md5sum(file_obj=tf, closed=False)

            base_params = {"module": module, "md5": md5}

            # 如果采用对象存储，文件直接上传至仓库，并将返回的目标路径传到后台，由后台进行校验并创建上传记录
            # TODO 后续应该由前端上传文件并提供md5
            if settings.STORAGE_TYPE in core_files_constants.StorageType.list_cos_member_values():
                storage = get_storage()

                try:
                    storage_path = storage.save(name=os.path.join(settings.UPLOAD_PATH, tf.name), content=tf)
                except Exception as e:
                    raise exceptions.PluginUploadError(agent_name=tf.name, error=e)

                return NodeApi.upload(
                    {
                        **base_params,
                        # 最初文件上传的名称，后台会使用该文件名保存并覆盖同名文件
                        "file_name": tf.name,
                        "file_path": storage_path,
                        "download_url": storage.url(storage_path),
                    }
                )

            else:

                response = requests.post(
                    url=settings.DEFAULT_FILE_UPLOAD_API,
                    data={
                        **base_params,
                        "bk_app_code": settings.APP_CODE,
                        "bk_username": get_request_username(),
                    },
                    # 本地文件系统仍通过上传文件到Nginx并回调后台
                    files={"package_file": tf},
                )

                return json.loads(response.content)
