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

import abc
import logging
import os
import shutil
import tarfile
import typing

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend import exceptions
from apps.backend.agent.config_parser import GseConfigParser
from apps.core.files import core_files_constants
from apps.core.files.storage import get_storage
from apps.core.tag.constants import TargetType
from apps.core.tag.handlers import TagHandler
from apps.core.tag.targets import AgentTargetHelper
from apps.node_man import constants, models
from apps.utils import cache, files

logger = logging.getLogger("app")


class BaseArtifactBuilder(abc.ABC):

    # 最终的制品名称
    NAME: str = None
    # 安装包的打包根路径
    PKG_DIR: str = None
    # 安装包打包前的归档路径模版
    PKG_PATH_DIR_TEMPL: str = "agent_{os}_{cpu_arch}"
    # 原始制品的打包根路径
    BASE_PKG_DIR: str = "gse"
    # 证书文件名列表
    CERT_FILENAMES: typing.List[str] = None

    # 制品存储的根路径
    BASE_STORAGE_DIR: str = "agent"

    VERSION_FILE_NAME: str = "VERSION"

    SUPPORT_FILES_DIR: str = "support-files"
    ENV_FILES_DIR: str = os.path.join(SUPPORT_FILES_DIR, "env")
    TEMPLATE_FILES_DIR: str = os.path.join(SUPPORT_FILES_DIR, "templates")
    TEMPLATE_PATTERN: str = None

    ENV_FILES: typing.List[str] = []
    TEMPLATE_FILES: typing.List[str] = []

    def __init__(
        self,
        initial_artifact_path: str,
        cert_path: typing.Optional[str] = None,
        download_path: typing.Optional[str] = None,
        overwrite_version: typing.Optional[str] = None,
        tags: typing.Optional[typing.List[str]] = None,
        enable_agent_pkg_manage: bool = False,
        username: str = "",
    ):
        """
        :param initial_artifact_path: 原始制品所在路径
        :param cert_path: 证书目录
        :param download_path: 归档路径
        :param overwrite_version: 覆盖版本号，用于覆盖原始制品内的版本信息
        :param tags：标签列表，用于批量创建标签
        """
        self.initial_artifact_path = initial_artifact_path
        self.cert_path = cert_path or settings.GSE_CERT_PATH
        self.download_path = download_path or settings.DOWNLOAD_PATH
        self.overwrite_version = overwrite_version
        self.tags = tags or []
        # 原始制品名称
        self.initial_artifact_filename = os.path.basename(initial_artifact_path)
        # 已申请的临时目录
        self.applied_tmp_dirs = set()
        # 文件源
        self.storage = get_storage(file_overwrite=True)
        self.username = username

    @staticmethod
    def download_file(file_path: str, target_path: str):
        """
        下载文件
        :param file_path: 文件路径
        :param target_path: 目标路径
        :return:
        """

        storage = get_storage()
        if not storage.exists(name=file_path):
            raise exceptions.FileNotExistError(_("文件不存在：file_path -> {file_path}").format(file_path=file_path))

        logger.info(f"start to download file -> {file_path} to {target_path}")

        if storage.storage_type in core_files_constants.StorageType.list_cos_member_values():
            # 如果是 COS 类型的存储，通过流式下载的方式保存文件，节约内存
            files.download_file(url=storage.url(file_path), name=target_path)
        else:
            # 文件系统本身就是流式读取并且可能没有对应的下载服务
            with storage.open(name=file_path, mode="rb") as fs:
                with files.FileOpen(name=target_path, mode="wb") as local_fs:
                    for chunk in iter(lambda: fs.read(4096), b""):
                        if not chunk:
                            continue
                        local_fs.write(chunk)

        logger.info(f"download file -> {file_path} to {target_path} success.")

    @abc.abstractmethod
    def extract_initial_artifact(self, initial_artifact_local_path: str, extract_dir: str) -> str:
        """
        解压原始制品到指定目录下，大致流程：
        1. 解压并转为标准格式：${node_type}_${os}_${cpu_arch}
        2. 注入证书
        待定：是否把 meta 信息都丢到 meta 目录

        得到的标准结构示例（Agent 2.0）：
        gse
        ├── CHANGELOG.md
        ├── VERSION
        ├── agent_linux_x86_64
        │   ├── bin
        │   │   ├── gse_agent
        │   │   └── gsectl
        │   └── cert
        │       ├── gse_agent.crt
        │       ├── gse_agent.key
        │       ├── gse_api_client.crt
        │       ├── gse_api_client.key
        │       ├── gse_server.crt
        │       ├── gse_server.key
        │       └── gseca.crt
        ├── agent_windows_x86
        │   ├── bin
        │   │   ├── gse_agent.exe
        │   │   ├── gse_agent_daemon.exe
        │   │   └── gsectl.bat
        │   └── cert
        │       ├── gse_agent.crt
        │       ├── gse_agent.key
        │       ├── gse_api_client.crt
        │       ├── gse_api_client.key
        │       ├── gse_server.crt
        │       ├── gse_server.key
        │       └── gseca.crt
        └── support-files
            ├── env
            └── templates
                └── gse_agent_conf.template
        :param initial_artifact_local_path: 原始制品库本地存放路径
        :param extract_dir: 解压目录
        :return:
        """
        raise NotImplementedError

    def _get_support_files_info(self, extract_dir: str) -> typing.Dict[str, typing.Any]:
        """
        获取部署依赖文件合集：配置 / 环境变量等
        :param extract_dir: 解压目录
        :return:
        """
        env_file_infos: typing.List[typing.Dict] = []
        template_file_infos: typing.List[typing.Dict] = []
        # 获取env信息
        for env_file in os.listdir(os.path.join(extract_dir, self.ENV_FILES_DIR)):
            if env_file not in self.ENV_FILES:
                continue
            env_file_infos.append(
                {
                    "file_name": env_file,
                    "file_absolute_path": os.path.join(extract_dir, self.ENV_FILES_DIR, env_file),
                }
            )

        # 获取配置文件信息
        for template in os.listdir(os.path.join(extract_dir, self.TEMPLATE_FILES_DIR)):
            template_match: str = self.TEMPLATE_PATTERN.search(template)

            if template_match:
                template_file_infos.append(
                    {
                        "file_name": template_match.group(),
                        "file_absolute_path": os.path.join(extract_dir, self.TEMPLATE_FILES_DIR, template),
                    }
                )

        return {"env": env_file_infos, "templates": template_file_infos}

    def _inject_dependencies(self, extract_dir: str):
        """
        注入依赖文件，大致流程：
        1. 注入证书
        2. 注入 gsectl
        3. 赋予部分文件可执行权限
        :param extract_dir: 解压目录
        :return:
        """
        for pkg_dir_name in os.listdir(extract_dir):
            # 通过正则提取出插件（plugin）目录名中的插件信息
            re_match = constants.AGENT_PATH_RE.match(pkg_dir_name)
            if re_match is None:
                logger.info("pkg_dir_name -> {pkg_dir_name} is not match, jump it.".format(pkg_dir_name=pkg_dir_name))
                continue

            # 证书目标路径
            cert_dst: str = os.path.join(extract_dir, pkg_dir_name, "cert")

            if os.path.exists(cert_dst):
                # 存在即移除，确保证书目标路径是干净的
                shutil.rmtree(cert_dst)
                logger.warning(f"cert_dst -> {cert_dst} not clean, removed it.")
            # 创建一个干净的证书目录
            os.makedirs(cert_dst, exist_ok=True)

            # 注入证书
            injected_cert_filenames: typing.List[str] = []
            for cert_filename in self.CERT_FILENAMES:
                cert_filepath: str = os.path.join(self.cert_path, cert_filename)
                if not os.path.exists(cert_filepath):
                    # 在部分场景下可能本身就不需要证书（比如社区版无需证书密码），此处暂不抛异常
                    logger.warning(f"cert file -> {cert_filepath} not exist, jump it.")
                    continue
                injected_cert_filenames.append(cert_filename)
                shutil.copyfile(cert_filepath, os.path.join(cert_dst, cert_filename))

            logger.info(f"copy ({','.join(injected_cert_filenames)}) from {self.cert_path} to {cert_dst} success.")

            # 注入 gsectl
            package_base_info: typing.Dict[str, str] = re_match.groupdict()
            gsectl_filename: str = ("gsectl", "gsectl.bat")[package_base_info["os"] == constants.PluginOsType.windows]
            gsectl_file_path: str = os.path.join(
                settings.DOWNLOAD_PATH, "gsectl", self.PKG_DIR, package_base_info["os"], gsectl_filename
            )
            if not self.storage.exists(gsectl_file_path):
                raise exceptions.FileNotExistError(
                    _("gsectl 文件不存在：file_path -> {file_path}").format(file_path=gsectl_file_path)
                )

            # 将 gsectl 放置到 bin 目录下
            pkg_bin_dir: str = os.path.join(extract_dir, pkg_dir_name, "bin")
            gsectl_target_file_path: str = os.path.join(pkg_bin_dir, gsectl_filename)
            # 从文件源拿 gsectl 可以保证打包的依赖与项目的版本解耦，在依赖出现问题后仅需更新文件源文件，无需出包
            with self.storage.open(gsectl_file_path, mode="rb") as fs:
                # mode 指定 w，覆盖现有文件
                with open(gsectl_target_file_path, mode="wb") as local_fs:
                    gsectl_file_content: str = fs.read().decode()
                    # TODO 后续如果 1.0 Agent 包也纳入管理，此处需要区分
                    #  1.0 Agent / Proxy 的 gsectl 采用固定的 rclocal 模式
                    if gsectl_filename == "gsectl" and "{{ AUTO_TYPE }}" in gsectl_file_content:
                        auto_type_strategy: typing.Union[str, typing.Dict[str, str]] = models.GlobalSettings.get_config(
                            models.GlobalSettings.KeyEnum.GSE2_LINUX_AUTO_TYPE.value,
                            constants.GseLinuxAutoType.RCLOCAL.value,
                        )
                        logger.info(f"get auto_type_strategy -> {auto_type_strategy} from global settings")

                        if isinstance(auto_type_strategy, dict):
                            try:
                                auto_type = auto_type_strategy[self.NAME]
                            except KeyError:
                                auto_type = constants.GseLinuxAutoType.RCLOCAL.value
                        else:
                            if auto_type_strategy not in constants.GseLinuxAutoType.list_member_values():
                                auto_type = constants.GseLinuxAutoType.RCLOCAL.value
                            else:
                                auto_type = auto_type_strategy

                        logger.info(f"apply auto_type -> {auto_type} to gsectl")
                        gsectl_file_content = gsectl_file_content.replace("{{ AUTO_TYPE }}", auto_type)
                    if "{{ AUTO_TYPE }}" in gsectl_file_content:
                        raise exceptions.PkgMetaInfoValidationError(
                            _("渲染 AUTO_TYPE -> {auto_type} 到 gsectl 失败").format(auto_type=auto_type)
                        )
                    local_fs.write(gsectl_file_content.encode(encoding="utf-8"))
            logger.info(f"copy gsectl -> {gsectl_file_path} to {gsectl_target_file_path} success.")

            # 为二进制文件授予可执行权限
            for file_path in files.fetch_file_paths_from_dir(dir_path=pkg_bin_dir):
                files.make_executable(file_path)
                logger.info(f"make file -> {file_path} executable.")

    def _list_package_dir_infos(self, extract_dir: str) -> typing.List[typing.Dict]:
        """
        解析并获取安装包目录信息
        :param extract_dir: 解压目录
        :return:
        """
        package_dir_infos: typing.List[typing.Dict] = []

        for pkg_dir_name in os.listdir(extract_dir):

            # 通过正则提取出插件（plugin）目录名中的插件信息
            re_match = constants.AGENT_PATH_RE.match(pkg_dir_name)
            if re_match is None:
                logger.info(
                    "pkg_dir_name -> {pkg_dir_name} is not match re, jump it.".format(pkg_dir_name=pkg_dir_name)
                )
                continue

            package_base_info: typing.Dict[str, str] = re_match.groupdict()
            package_dir_infos.append(
                {
                    "extract_dir": extract_dir,
                    "os": package_base_info["os"],
                    "cpu_arch": package_base_info["cpu_arch"],
                    "pkg_relative_path": pkg_dir_name,
                    "pkg_absolute_path": os.path.join(extract_dir, pkg_dir_name),
                }
            )

        return package_dir_infos

    def make_and_upload_package(
        self, package_dir_info: typing.Dict[str, typing.Any], artifact_meta_info: typing.Dict[str, typing.Any]
    ) -> typing.Dict[str, typing.Any]:
        """
        制作并上传安装包

        上传到文件源的标准结构示例：
        agent
        ├── linux
        │   └── x86_64
        │       └── gse_agent-1.0.1.tgz
        └── windows
            └── x86
                └── gse_agent-1.0.1.tgz

        TODO 关于同版本分为「企业版」「内部版」的管理设想
        - 明确原则：首先必须当成同一个版本去维护管理
        - 怎么管理：接入点「服务器目录」+「Agent 版本」可以唯一确定一个包
        - pkg - path（md5），pkg - path1（md5）
        - 证书区分：证书路径放到接入点维护

        :param package_dir_info: 安装包信息
        :param artifact_meta_info: 基础信息
        :return:
        """
        name: str = artifact_meta_info["name"]
        os_str: str = package_dir_info["os"]
        cpu_arch: str = package_dir_info["cpu_arch"]
        version_str: str = artifact_meta_info["version"]
        pkg_name: str = f"{name}-{version_str}.tgz"

        package_tmp_path = os.path.join(self.apply_tmp_dir(), self.BASE_STORAGE_DIR, os_str, cpu_arch, pkg_name)
        os.makedirs(os.path.dirname(package_tmp_path), exist_ok=True)

        with tarfile.open(package_tmp_path, "w:gz") as tf:
            tf.add(package_dir_info["pkg_absolute_path"], arcname=f"{self.PKG_DIR}/")
            logger.info(
                "project -> {project} version -> {version} "
                "now is pack to package_tmp_path -> {package_tmp_path}".format(
                    project=name, version=version_str, package_tmp_path=package_tmp_path
                )
            )

        # 将 Agent 包上传到存储系统
        package_target_path = os.path.join(self.download_path, self.BASE_STORAGE_DIR, os_str, cpu_arch, pkg_name)
        with open(package_tmp_path, mode="rb") as tf:
            # 采用同名覆盖策略，保证同版本 Agent 包仅保存一份
            storage_path = self.storage.save(package_target_path, tf)
            # 如果采用覆盖版本（标签），并且真实版本号和覆盖版本号不一样，保存一份副本
            if self.overwrite_version and version_str != self.overwrite_version:
                package_overwrite_target_path = os.path.join(
                    self.download_path, self.BASE_STORAGE_DIR, os_str, cpu_arch, f"{name}-{self.overwrite_version}.tgz"
                )
                self.storage.save(package_overwrite_target_path, tf)
                logger.info(
                    "[overwrite] package -> {pkg_name} upload to package_target_path"
                    " -> {package_target_path} success".format(
                        pkg_name=pkg_name, package_target_path=package_overwrite_target_path
                    )
                )

            if storage_path != package_target_path:
                raise exceptions.CreatePackageRecordError(
                    _("Agent 包保存错误，期望保存到 -> {package_target_path}, 实际保存到 -> {storage_path}").format(
                        package_target_path=package_target_path, storage_path=storage_path
                    )
                )

        logger.info(
            "package -> {pkg_name} upload to package_target_path -> {package_target_path} success".format(
                pkg_name=pkg_name, package_target_path=package_target_path
            )
        )

        return {
            "pkg_name": pkg_name,
            "md5": files.md5sum(name=package_tmp_path),
            "pkg_size": os.path.getsize(package_tmp_path),
            "pkg_path": os.path.dirname(package_target_path),
        }

    def apply_tmp_dir(self) -> str:
        """
        创建临时目录并返回路径
        :return:
        """
        tmp_dir: str = files.mk_and_return_tmpdir()
        self.applied_tmp_dirs.add(tmp_dir)
        return tmp_dir

    @cache.class_member_cache()
    def _get_version(self, extract_dir: str) -> str:
        """
        获取版本号
        :param extract_dir: 解压目录
        :return:
        """
        version_file_path: str = os.path.join(extract_dir, "VERSION")
        if not os.path.exists(version_file_path):
            raise exceptions.FileNotExistError(_("版本文件不存在"))
        with open(version_file_path, "r", encoding="utf-8") as version_fs:
            untreated_version_str: str = version_fs.read()
        version_match: typing.Optional[typing.Match] = constants.SEMANTIC_VERSION_PATTERN.search(
            untreated_version_str or ""
        )
        if version_match:
            return version_match.group()
        else:
            raise exceptions.NotSemanticVersionError({"version": version_match})

    @cache.class_member_cache()
    def _get_changelog(self, extract_dir: str) -> str:
        """
        获取版本日志
        :param extract_dir: 解压目录
        :return:
        """
        changelog_file_path: str = os.path.join(extract_dir, "CHANGELOG.md")
        if not os.path.exists(changelog_file_path):
            raise exceptions.FileNotExistError(_("版本日志文件不存在"))
        with open(changelog_file_path, "r", encoding="utf-8") as changelog_fs:
            changelog: str = changelog_fs.read()
        return changelog

    def generate_location_path(self, upload_path: str, pkg_name: str) -> str:
        if settings.STORAGE_TYPE == core_files_constants.StorageType.BLUEKING_ARTIFACTORY.value:
            location_path: str = f"{settings.BKREPO_ENDPOINT_URL}/generic/blueking/bknodeman/{upload_path}/{pkg_name}"
        else:
            location_path: str = f"http://{settings.BKAPP_LAN_IP}/{upload_path}/{pkg_name}"

        return location_path

    def update_or_create_package_records(self, package_infos: typing.List[typing.Dict[str, typing.Any]]):
        """
        创建或更新制品记录
        :param package_infos:
        :return:
        """
        for package_info in package_infos:
            models.GsePackages.objects.update_or_create(
                defaults={
                    "pkg_size": package_info["package_upload_info"]["pkg_size"],
                    "pkg_path": package_info["package_upload_info"]["pkg_path"],
                    "md5": package_info["package_upload_info"]["md5"],
                    "location": self.generate_location_path(
                        package_info["package_upload_info"]["pkg_path"],
                        package_info["package_upload_info"]["pkg_name"],
                    ),
                    "version_log": package_info["artifact_meta_info"]["changelog"],
                },
                pkg_name=package_info["package_upload_info"]["pkg_name"],
                version=package_info["artifact_meta_info"]["version"],
                project=package_info["artifact_meta_info"]["name"],
                os=package_info["package_dir_info"]["os"],
                cpu_arch=package_info["package_dir_info"]["cpu_arch"],
            )
            logger.info(
                f"[update_or_create_package_record] "
                f"package name -> {package_info['package_upload_info']['pkg_name']} success"
            )

        if package_infos:
            models.GsePackageDesc.objects.update_or_create(
                defaults={
                    "description": package_infos[0]["artifact_meta_info"]["changelog"],
                },
                project=package_infos[0]["artifact_meta_info"]["name"],
                category=constants.CategoryType.official,
            )

            logger.info(
                f"[update_or_create_package_record] "
                f"package desc -> {package_info['package_upload_info']['pkg_name']}, "
                f"project -> {package_infos[0]['artifact_meta_info']['name']} success"
            )

    def update_or_create_tag(self, artifact_meta_info: typing.Dict[str, typing.Any]):
        """
        创建或更新标签记录，待 Agent 包管理完善
        :param artifact_meta_info:
        :return:
        """
        agent_name_target_id_map: typing.Dict[str, int] = AgentTargetHelper.get_agent_name_target_id_map()
        for tag in self.tags:
            TagHandler.publish_tag_version(
                name=tag,
                target_type=TargetType.AGENT.value,
                target_id=agent_name_target_id_map[self.NAME],
                target_version=artifact_meta_info["version"],
            )
            logger.info(
                f"[publish_tag_version] tag -> {tag}, target_version -> {artifact_meta_info['version']} success"
            )

    @classmethod
    def parse_env(cls, content) -> typing.Dict[str, typing.Any]:
        config_env = GseConfigParser()
        config_env.read_string(f"[Default]\n{content}")
        return dict(config_env.items("Default"))

    def update_or_create_support_files(self, package_infos: typing.List[typing.Dict]):
        """
        创建或更新support_files记录
        :param package_infos:
        :return:
        """
        for package_info in package_infos:
            support_files = package_info["artifact_meta_info"]["support_files_info"]
            version = package_info["artifact_meta_info"]["version"]
            package = package_info["package_dir_info"]

            for env_file in support_files["env"]:
                with open(env_file["file_absolute_path"], "r") as f:
                    env_str = f.read()

                logger.info(
                    f"update_or_create_support_files: env_file->{env_file} version->{version} raw_env->{env_str}"
                )
                env_value: typing.Dict[str, typing.Any] = self.parse_env(env_str)
                logger.info(
                    f"update_or_create_support_files: env_file->{env_file} version->{version} env_value->{env_value}"
                )
                models.GseConfigEnv.objects.update_or_create(
                    defaults={"env_value": env_value},
                    version=version,
                    os=package["os"],
                    cpu_arch=package["cpu_arch"],
                    agent_name=self.NAME,
                )

            for template in support_files["templates"]:
                with open(template["file_absolute_path"], "r") as f:
                    content = f.read()
                logger.info(
                    f"update_or_create_support_files: template->{template} version->{version} content->{content}"
                )
                models.GseConfigTemplate.objects.update_or_create(
                    defaults={"content": content},
                    name=template["file_name"],
                    version=version,
                    os=package["os"],
                    cpu_arch=package["cpu_arch"],
                    agent_name=self.NAME,
                )

    def get_artifact_meta_info(self, extract_dir: str) -> typing.Dict[str, typing.Any]:
        """
        获取制品的基础信息、配置文件信息
        :param extract_dir: 解压目录
        :return:
        """
        # 版本
        version_str: str = self._get_version(extract_dir)
        # 配置文件
        support_files_info = self._get_support_files_info(extract_dir)
        # changelog
        changelog: str = self._get_changelog(extract_dir)

        return {
            "name": self.NAME,
            "version": version_str,
            "changelog": changelog,
            "support_files_info": support_files_info,
        }

    def list_package_dir_infos(self) -> typing.Tuple[str, typing.List[typing.Dict]]:
        # 下载原始制品
        initial_artifact_local_path: str = os.path.join(
            self.apply_tmp_dir(), os.path.basename(self.initial_artifact_path)
        )
        self.download_file(self.initial_artifact_path, initial_artifact_local_path)
        # 进行解压
        extract_dir: str = self.extract_initial_artifact(initial_artifact_local_path, self.apply_tmp_dir())
        return extract_dir, self._list_package_dir_infos(extract_dir=extract_dir)

    def make(
        self,
        operator: typing.Optional[str] = None,
        select_pkg_relative_paths: typing.Optional[typing.List[str]] = None,
    ):
        """
        制作适配于指定机型的安装包
        :param operator: 操作人
        :param select_pkg_relative_paths: 已选择的需要导入的安装包
        :return:
        """
        package_infos: typing.List[typing.Dict] = []
        extract_dir, package_dir_infos = self.list_package_dir_infos()
        artifact_meta_info: typing.Dict[str, typing.Any] = self.get_artifact_meta_info(extract_dir)

        for package_dir_info in package_dir_infos:
            if not (
                select_pkg_relative_paths is None or package_dir_info["pkg_relative_path"] in select_pkg_relative_paths
            ):
                logger.info("path -> {path} not selected, jump it".format(path=package_dir_info["pkg_relative_path"]))
                continue

            package_upload_info: typing.Dict[str, typing.Any] = self.make_and_upload_package(
                package_dir_info, artifact_meta_info
            )
            package_infos.append(
                {
                    "artifact_meta_info": artifact_meta_info,
                    "package_dir_info": package_dir_info,
                    "package_upload_info": package_upload_info,
                }
            )

        artifact_meta_info["operator"] = operator
        # Agent 包先导入文件源 -> 写配置文件 -> 创建包记录 -> 创建 Tag
        self.update_or_create_support_files(package_infos)
        self.update_or_create_package_records(package_infos)
        self.update_or_create_tag(artifact_meta_info)

    def __enter__(self) -> "BaseArtifactBuilder":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 退出前清理临时目录，避免打包导致存储膨胀
        for to_be_removed_tmp_dir in self.applied_tmp_dirs:
            if os.path.exists(to_be_removed_tmp_dir):
                shutil.rmtree(to_be_removed_tmp_dir)
        self.applied_tmp_dirs.clear()
