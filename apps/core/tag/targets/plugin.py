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
import typing
from collections import defaultdict

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from packaging import version

from apps.node_man import models as node_man_models

from .. import constants, exceptions
from . import base

logger = logging.getLogger("app")


class PluginTargetHelper(base.BaseTargetHelper):

    MODEL = node_man_models.GsePluginDesc
    TARGET_TYPE = constants.TargetType.PLUGIN.value

    @classmethod
    def fetch_latest_config_templates(
        cls, config_templates: typing.List[typing.Dict[str, typing.Any]], plugin_version: str
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        过滤最新的配置模板
        优先取和插件版本一致的配置模板，否则取最新版本的配置模板
        :param config_templates: 配置模板列表
        :param plugin_version: 指定插件版本号
        """
        config_tmpls_gby_name: typing.Dict[str, typing.List] = defaultdict(list)

        for config_tmpl in config_templates:
            config_tmpls_gby_name[config_tmpl["name"]].append(config_tmpl)

        latest_config_templates: typing.List[typing.Dict[str, typing.Any]] = []
        for config_tmpl_name, config_tmpls_with_the_same_name in config_tmpls_gby_name.items():
            same_name_tmpl_map: typing.Dict[str, typing.Dict[str, str]] = {}
            for tmpl in config_tmpls_with_the_same_name:
                same_name_tmpl_map[tmpl["version"]] = tmpl

            #  选取对应平台模板名中的指定版本号或者是最大版本号
            same_name_tmp_versions: typing.KeysView[str] = same_name_tmpl_map.keys()
            if same_name_tmp_versions:
                if plugin_version in same_name_tmp_versions:
                    # 优先取和插件版本一致的配置模板
                    latest_config_template = same_name_tmpl_map[plugin_version]
                else:
                    # 否则，取最新版本的配置模板
                    latest_config_template = same_name_tmpl_map[
                        sorted(same_name_tmp_versions, key=lambda v: version.parse(v))[-1]
                    ]

                latest_config_templates.append(latest_config_template)

        return latest_config_templates

    @classmethod
    def fill_latest_config_tmpls_to_packages(cls, packages: typing.List[typing.Dict[str, typing.Any]]) -> None:
        """
        填充最新配置文件到插件包信息列表
        :param packages: 插件包列表
        :return:
        """
        plugin_names: typing.Set[str] = set()
        os_types: typing.Set[str] = set()
        cpu_arches: typing.Set[str] = set()

        for package in packages:
            plugin_names.add(package["project"])
            os_types.add(package["os"])
            cpu_arches.add(package["cpu_arch"])

        # 获取插件包关联的配置模板
        config_tmpls = list(
            node_man_models.PluginConfigTemplate.objects.filter(
                plugin_name__in=plugin_names, os__in=os_types, cpu_arch__in=cpu_arches
            ).values("id", "name", "version", "is_main", "plugin_version", "cpu_arch", "os", "plugin_name")
        )

        # 以 plugin_name & os & cpu_arch & plugin_version 作为唯一标识，聚合配置模板
        config_tmpls_gby_pkg_key: typing.Dict[str, typing.List[typing.Dict[str, typing.Any]]] = defaultdict(list)
        for config_tmpl in config_tmpls:
            pkg_key = "_".join(
                [config_tmpl["plugin_name"], config_tmpl["os"], config_tmpl["cpu_arch"], config_tmpl["plugin_version"]]
            )
            config_tmpls_gby_pkg_key[pkg_key].append(
                {
                    "id": config_tmpl["id"],
                    "version": config_tmpl["version"],
                    "os": config_tmpl["os"],
                    "cpu_arch": config_tmpl["cpu_arch"],
                    "name": config_tmpl["name"],
                    "is_main": config_tmpl["is_main"],
                }
            )

        for package in packages:
            # 配置模板 = 通用版本配置模板 + 该版本的配置模板
            pkg_key_prefix = f"{package['project']}_{package['os']}_{package['cpu_arch']}_"
            config_templates = (
                config_tmpls_gby_pkg_key[f"{pkg_key_prefix}{package['version']}"]
                + config_tmpls_gby_pkg_key[f"{pkg_key_prefix}*"]
            )
            # 筛选最新配置
            package["config_templates"] = cls.fetch_latest_config_templates(
                config_templates=config_templates, plugin_version=package["version"]
            )

    def publish_tag_version_to_pkg(
        self, pkg_obj: node_man_models.Packages, config_tmpls: typing.List[typing.Dict[str, typing.Any]]
    ) -> node_man_models.Packages:
        """
        按插件包发布标签版本
        :param pkg_obj: 插件包对象
        :param config_tmpls: 对应的配置模版列表
        :return:
        """
        config_tmpl_ids: typing.List[int] = [config_tmpl["id"] for config_tmpl in config_tmpls]
        config_tmpl_objs: typing.List[
            node_man_models.PluginConfigTemplate
        ] = node_man_models.PluginConfigTemplate.objects.filter(id__in=config_tmpl_ids)
        # 发布前标签版本对应的配置模板
        before_publish_config_tmpl_ids: typing.Set[int] = set(
            node_man_models.PluginConfigTemplate.objects.filter(
                os=pkg_obj.os,
                cpu_arch=pkg_obj.cpu_arch,
                plugin_name=pkg_obj.project,
                plugin_version=self.tag_name,
            ).values_list("id", flat=True)
        )
        tag_pkg_obj, __ = node_man_models.Packages.objects.update_or_create(
            project=pkg_obj.project,
            version=self.tag_name,
            os=pkg_obj.os,
            cpu_arch=pkg_obj.cpu_arch,
            defaults=dict(
                md5=pkg_obj.md5,
                creator=pkg_obj.creator,
                module=pkg_obj.module,
                pkg_name=pkg_obj.pkg_name,
                pkg_size=pkg_obj.pkg_size,
                pkg_path=pkg_obj.pkg_path,
                pkg_mtime=str(timezone.now()),
                pkg_ctime=pkg_obj.pkg_ctime,
                location=pkg_obj.location,
                version_log=pkg_obj.version,
                version_log_en=pkg_obj.version_log_en,
                # 通过该渠道发布的版本默认启用并正式对外
                is_ready=True,
                is_release_version=True,
            ),
        )
        published_config_tmpl_ids: typing.Set[int] = set()
        for config_tmpl_obj in config_tmpl_objs:
            tag_config_tmpl_obj, __ = node_man_models.PluginConfigTemplate.objects.update_or_create(
                name=config_tmpl_obj.name,
                version=self.tag_name,
                is_main=config_tmpl_obj.is_main,
                plugin_name=tag_pkg_obj.project,
                plugin_version=self.tag_name,
                os=tag_pkg_obj.os,
                cpu_arch=tag_pkg_obj.cpu_arch,
                defaults=dict(
                    format=config_tmpl_obj.format,
                    file_path=config_tmpl_obj.file_path,
                    content=config_tmpl_obj.content,
                    is_release_version=True,
                    creator=config_tmpl_obj.creator,
                    create_time=config_tmpl_obj.create_time,
                    source_app_code=config_tmpl_obj.source_app_code,
                ),
            )
            published_config_tmpl_ids.add(tag_config_tmpl_obj.id)

        # 删除进程控制信息
        node_man_models.ProcControl.objects.filter(plugin_package_id=tag_pkg_obj.id).delete()
        # 清理多余的配置模板
        # 差集表示更新版本后减少的配置模板，属于脏数据
        node_man_models.PluginConfigTemplate.objects.filter(
            id__in=(before_publish_config_tmpl_ids - published_config_tmpl_ids)
        )
        # 清理配置实例缓存，避免同名配置更新后仍使用缓存
        node_man_models.PluginConfigInstance.objects.filter(
            plugin_config_template__in=before_publish_config_tmpl_ids
        ).delete()

        # 基于目标版本创建进程控制信息
        proc_control_obj: node_man_models.ProcControl = node_man_models.ProcControl.objects.get(
            plugin_package_id=pkg_obj.id
        )
        proc_control_obj.id = None
        proc_control_obj.plugin_package_id = tag_pkg_obj.id
        proc_control_obj.save()

        return tag_pkg_obj

    def _publish_tag_version(self):
        target: node_man_models.GsePluginDesc = self.target
        # 查找相应版本的包
        pkg_objs: typing.List[node_man_models.Packages] = node_man_models.Packages.objects.filter(
            project=target.name, version=self.target_version
        )
        if not pkg_objs:
            # 版本包不存在的情况下，不允许发布
            logger.error(f"not any packages: helper_info -> {self}")
            raise exceptions.PublishTagVersionError({"err_msg": _("未找到版本包（{helper_info}）".format(helper_info=self))})

        id__pkg_obj_map: typing.Dict[int, node_man_models.Packages] = {pkg_obj.id: pkg_obj for pkg_obj in pkg_objs}
        # 查找包对应的配置模板
        pkg_infos: typing.List[typing.Dict[str, typing.Any]] = [
            {
                "id": pkg_obj.id,
                "project": pkg_obj.project,
                "version": pkg_obj.version,
                "os": pkg_obj.os,
                "cpu_arch": pkg_obj.cpu_arch,
            }
            for pkg_obj in pkg_objs
        ]
        self.fill_latest_config_tmpls_to_packages(packages=pkg_infos)

        # 获取发布前的插件包 ID 列表
        before_publish_tag_pkg_ids: typing.Set[int] = set(
            node_man_models.Packages.objects.filter(project=target.name, version=self.tag_name).values_list(
                "id", flat=True
            )
        )

        published_tag_pkg_ids: typing.Set[int] = set()
        for pkg_info in pkg_infos:
            # 逐个发布版本包
            tag_pkg_obj: node_man_models.Packages = self.publish_tag_version_to_pkg(
                pkg_obj=id__pkg_obj_map[pkg_info["id"]], config_tmpls=pkg_info["config_templates"]
            )
            published_tag_pkg_ids.add(tag_pkg_obj.id)

        # 删除多余插件包
        # 发布采取的是 存在即更新 的策略，发布前后差集表示不再支持的插件包，例如新版本移除了对 x86 的支持，需要删除
        node_man_models.Packages.objects.filter(id__in=before_publish_tag_pkg_ids - published_tag_pkg_ids).delete()

    def _delete_tag_version(self):
        target: node_man_models.GsePluginDesc = self.target
        pkg_ids: typing.List[int] = list(
            node_man_models.Packages.objects.filter(project=target.name, version=self.tag_name).values_list(
                "id", flat=True
            )
        )
        config_tmpl_ids: typing.List[int] = list(
            node_man_models.PluginConfigTemplate.objects.filter(
                plugin_name=target.name, plugin_version=self.tag_name
            ).values_list("id", flat=True)
        )

        pkg_deleted_count, __ = node_man_models.Packages.objects.filter(id__in=pkg_ids).delete()
        config_tmpl_deleted_count, __ = node_man_models.PluginConfigTemplate.objects.filter(
            id__in=config_tmpl_ids
        ).delete()
        config_inst_deleted_count, __ = node_man_models.PluginConfigInstance.objects.filter(
            plugin_config_template__in=config_tmpl_ids
        ).delete()
        proc_control_deleted_count, __ = node_man_models.ProcControl.objects.filter(
            plugin_package_id__in=pkg_ids
        ).delete()

        logger.info(
            f"[delete_tag_version] finished: pkg_deleted_count -> {pkg_deleted_count}, "
            f"config_tmpl_deleted_count -> {config_tmpl_deleted_count}, "
            f"config_inst_deleted_count -> {config_inst_deleted_count}, "
            f"proc_control_deleted_count -> {proc_control_deleted_count}"
        )
