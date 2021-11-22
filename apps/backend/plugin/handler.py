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
import logging
import os
import shutil
from typing import Any, Dict, List

from django.conf import settings
from django.utils.translation import ugettext as _

from apps.core.files.storage import get_storage
from apps.exceptions import ValidationError
from apps.node_man import models
from apps.utils import basic, files

logger = logging.getLogger("app")


class PluginHandler:
    @classmethod
    def package_infos(cls, name: str, version: str = None, os_type: str = None, cpu_arch: str = None):
        """
        获取插件包信息
        :param name: 插件名称
        :param version: 版本
        :param os_type: 操作系统
        :param cpu_arch: cpu 架构
        :return:
        """
        # 构造DB查询参数，filter_values -> 过滤 None值
        filter_params = basic.filter_values({"project": name, "os": os_type, "version": version, "cpu_arch": cpu_arch})
        packages: List[models.Packages] = models.Packages.objects.filter(**filter_params)

        package_infos: List[Dict] = []
        for package in packages:
            package_infos.append(
                {
                    "id": package.id,
                    "name": package.project,
                    "os": package.os,
                    "cpu_arch": package.cpu_arch,
                    "version": package.version,
                    "is_release_version": package.is_release_version,
                    "is_ready": package.is_ready,
                    "pkg_size": package.pkg_size,
                    "md5": package.md5,
                    "location": package.location,
                }
            )
        return package_infos

    @classmethod
    def upload(
        cls,
        md5: str,
        origin_file_name: str,
        module: str,
        operator: str,
        app_code: str,
        file_path: str = None,
        download_url: str = None,
    ) -> Dict[str, Any]:
        """
        上传文件
        :param md5: 上传端计算的文件md5
        :param origin_file_name: 上传端提供的文件名
        :param module: 模块名称
        :param operator: 操作人
        :param app_code: 所属应用
        :param file_path: 文件保存路径，download_url & file_path 其中一个必填
        :param download_url: 文件下载url，download_url & file_path 其中一个必填
        :return:
        """
        storage = get_storage()
        # file_path 不为空表示文件已在项目管理的对象存储上，此时仅需校验md5，减少文件IO
        if file_path:
            if not storage.exists(name=file_path):
                raise ValidationError(_("文件不存在：file_path -> {file_path}").format(file_path=file_path))
            if files.md5sum(file_obj=storage.open(name=file_path)) != md5:
                raise ValidationError(_("上传文件MD5校验失败，请确认重试"))
        else:
            # 创建临时存放下载插件的目录
            tmp_dir = files.mk_and_return_tmpdir()
            with open(file=os.path.join(tmp_dir, origin_file_name), mode="wb+") as fs:
                # 下载文件并写入fs
                files.download_file(url=download_url, file_obj=fs, closed=False)
                # 计算下载文件的md5
                local_md5 = files.md5sum(file_obj=fs, closed=False)
                if local_md5 != md5:
                    logger.error(
                        "failed to valid file md5 local->[{}] user->[{}] maybe network error".format(local_md5, md5)
                    )
                    raise ValidationError(_("上传文件MD5校验失败，请确认重试"))

                # 使用上传端提供的期望保存文件名，保存文件到项目所管控的存储
                file_path = storage.save(name=os.path.join(settings.UPLOAD_PATH, origin_file_name), content=fs)

            # 移除临时目录
            shutil.rmtree(tmp_dir)

        record = models.UploadPackage.create_record(
            module=module,
            file_path=file_path,
            md5=md5,
            operator=operator,
            source_app_code=app_code,
            # 此处使用落地到文件系统的文件名，对象存储情况下文件已经写到仓库，使用接口传入的file_name会在后续判断中再转移一次文件
            file_name=os.path.basename(file_path),
        )
        logger.info(
            f"user -> {record.creator} from app-> {record.source_app_code} upload file -> {record.file_path} success."
        )

        return {"id": record.id, "name": record.file_name, "pkg_size": record.file_size}
