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
import os
import shutil
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.utils.translation import ugettext as _

from apps.backend import exceptions
from apps.core.files.storage import get_storage
from apps.core.tag import targets
from apps.core.tag.models import Tag
from apps.exceptions import ValidationError
from apps.node_man import constants, models
from apps.node_man import tools as node_man_tools
from apps.utils import files

logger = logging.getLogger("app")


class PluginHandler:
    @classmethod
    def fetch_package_infos(
        cls, project: str, pkg_version: Optional[str], os_type: Optional[str], cpu_arch: Optional[str]
    ) -> List[Dict[str, Any]]:
        package_infos: List[Dict[str, Any]] = node_man_tools.PluginV2Tools.fetch_package_infos(
            project=project, pkg_version=pkg_version, os_type=os_type, cpu_arch=cpu_arch
        )
        for package_info in package_infos:
            # 历史字段兼容
            package_info["name"] = package_info["project"]
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

    @classmethod
    def retrieve(cls, plugin_id: int):
        gse_plugin_desc = (
            models.GsePluginDesc.objects.filter(id=plugin_id)
            .values(
                "id",
                "description",
                "name",
                "category",
                "source_app_code",
                "scenario",
                "deploy_type",
                "node_manage_control",
                "is_ready",
            )
            .first()
        )
        if gse_plugin_desc is None:
            raise exceptions.PluginNotExistError(_("不存在ID为: {id} 的插件").format(id=plugin_id))
        # 字段翻译
        gse_plugin_desc.update(
            {
                "category": constants.CATEGORY_DICT[gse_plugin_desc["category"]],
                "deploy_type": constants.DEPLOY_TYPE_DICT[gse_plugin_desc["deploy_type"]]
                if gse_plugin_desc["deploy_type"]
                else gse_plugin_desc["deploy_type"],
            }
        )
        # 筛选可用包，规则：启用，版本降序
        packages = models.Packages.objects.filter(project=gse_plugin_desc["name"]).values(
            *["id", "pkg_name", "module", "project", "version", "os", "cpu_arch"]
            + ["pkg_mtime", "creator", "is_ready", "is_release_version"]
        )
        plugin_packages = []
        # 按支持的cpu, os对包进行分类
        packages_group_by_os_cpu = defaultdict(list)
        for package in packages:
            os_cpu = "{os}_{cpu}".format(os=package["os"], cpu=package["cpu_arch"])
            packages_group_by_os_cpu[os_cpu].append(package)

        top_tag: Tag = targets.PluginTargetHelper.get_top_tag_or_none(plugin_id)
        top_versions: List[str] = []
        if top_tag is not None:
            top_versions = [top_tag.name]
        # 取每个支持系统的最新版本插件包
        for os_cpu, package_group in packages_group_by_os_cpu.items():
            # 取启用版本的最新插件包，如无启用，取未启用的最新版本插件包
            package_group = node_man_tools.PluginV2Tools.get_sorted_package_infos(
                package_group, top_versions=top_versions
            )
            release_package = package_group[0]
            release_package["support_os_cpu"] = os_cpu
            plugin_packages.append(release_package)

        targets.PluginTargetHelper.fill_latest_config_tmpls_to_packages(packages)
        gse_plugin_desc["plugin_packages"] = plugin_packages
        return gse_plugin_desc

    @classmethod
    def history(
        cls, plugin_id: int, pkg_ids: Optional[List[int]] = None, os_type: str = None, cpu_arch: str = None
    ) -> List[Dict[str, Any]]:

        gse_plugin_desc_obj = models.GsePluginDesc.objects.filter(id=plugin_id).first()
        if gse_plugin_desc_obj is None:
            raise exceptions.PluginNotExistError(_("不存在ID为: {id} 的插件").format(id=plugin_id))
        plugin_name = gse_plugin_desc_obj.name

        package_infos: List[Dict[str, Any]] = node_man_tools.PluginV2Tools.fetch_package_infos(
            project=plugin_name, pkg_ids=pkg_ids, os_type=os_type, cpu_arch=cpu_arch
        )

        # 查找置顶版本
        top_tag: Tag = targets.PluginTargetHelper.get_top_tag_or_none(plugin_id)
        top_versions: List[str] = []
        if top_tag is not None:
            top_versions = [top_tag.name]

        # 获取排序后的插件包列表
        package_infos = node_man_tools.PluginV2Tools.get_sorted_package_infos(package_infos, top_versions=top_versions)

        # 标记最新版本包
        if package_infos:
            package_infos[0]["is_newest"] = True

        # 填充配置模板信息
        targets.PluginTargetHelper.fill_latest_config_tmpls_to_packages(package_infos)

        return package_infos
