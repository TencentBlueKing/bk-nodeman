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
import json
import os
import random
from collections import ChainMap, defaultdict
from typing import Any, Dict, List

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import ugettext_lazy as _

from apps.core.files import core_files_constants
from apps.core.files.storage import get_storage
from apps.node_man import constants, exceptions, models, tools
from apps.node_man.constants import DEFAULT_CLOUD_NAME, IamActionType
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.host import HostHandler
from apps.node_man.handlers.iam import IamHandler
from apps.utils.basic import distinct_dict_list, list_slice
from apps.utils.concurrent import batch_call
from apps.utils.files import md5sum
from apps.utils.local import get_request_username
from common.api import NodeApi


class PluginV2Handler:
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

            # 构造通用参数
            upload_params = {
                "url": settings.DEFAULT_FILE_UPLOAD_API,
                "data": {
                    "bk_app_code": settings.APP_CODE,
                    "bk_username": get_request_username(),
                    "module": module,
                    "md5": md5,
                },
            }

            # 如果采用对象存储，文件直接上传至仓库，并将返回的目标路径传到后台，由后台进行校验并创建上传记录
            # TODO 后续应该由前端上传文件并提供md5
            if settings.STORAGE_TYPE in core_files_constants.StorageType.list_cos_member_values():
                storage = get_storage()

                try:
                    storage_path = storage.save(name=os.path.join(settings.UPLOAD_PATH, tf.name), content=tf)
                except Exception as e:
                    raise exceptions.PluginUploadError(plugin_name=tf.name, error=e)

                upload_params["data"].update(
                    {
                        # 最初文件上传的名称，后台会使用该文件名保存并覆盖同名文件
                        "file_name": tf.name,
                        "file_path": storage_path,
                        "download_url": storage.url(storage_path),
                    }
                )
            else:
                # 本地文件系统仍通过上传文件到Nginx并回调后台
                upload_params["files"] = {"package_file": tf}

            response = requests.post(**upload_params)

        return json.loads(response.content)

    @staticmethod
    def list_plugin(query_params: Dict):
        plugin_page = NodeApi.plugin_list(query_params)

        if query_params.get("simple_all"):
            return plugin_page

        operate_perms = []

        is_superuser = IamHandler().is_superuser(get_request_username())

        if not is_superuser and settings.USE_IAM:
            perms = IamHandler().fetch_policy(get_request_username(), {IamActionType.plugin_pkg_operate})
            operate_perms = perms[IamActionType.plugin_pkg_operate]

        for plugin in plugin_page["list"]:
            plugin.update(
                {
                    "category": constants.CATEGORY_DICT.get(plugin["category"], plugin["category"]),
                    "deploy_type": constants.DEPLOY_TYPE_DICT.get(plugin["deploy_type"], plugin["deploy_type"]),
                }
            )
            plugin["permissions"] = {
                "operate": plugin["id"] in operate_perms if not is_superuser and settings.USE_IAM else True
            }
        return plugin_page

    @staticmethod
    def list_plugin_host(
        params: dict,
        view_action: str = constants.IamActionType.plugin_view,
        op_action: str = constants.IamActionType.plugin_operate,
    ):
        """
        查询插件下主机
        :param params: 仅校验后的查询条件
        :param view_action: 查看权限
        :param op_action: 操作权限
        :return: 主机列表
        """
        # 用户有权限的业务
        user_biz = CmdbHandler().biz_id_name({"action": view_action})

        # 用户主机操作权限
        operate_bizs = CmdbHandler().biz_id_name({"action": op_action})

        host_tools = HostHandler()

        if params["pagesize"] != -1:
            begin = (params["page"] - 1) * params["pagesize"]
            end = (params["page"]) * params["pagesize"]
        else:
            begin = None
            end = None
            # 跨页全选模式，仅返回用户有权限操作的主机
            user_biz = operate_bizs

        params["conditions"] = params["conditions"] if "conditions" in params else []
        # 查询指定插件
        params["conditions"].append({"key": params["project"], "value": [-1]})
        params["conditions"].extend(tools.HostV2Tools.parse_nodes2conditions(params.get("nodes", []), operate_bizs))

        # 生成sql查询主机
        hosts_sql = host_tools.multiple_cond_sql(params, user_biz, plugin=True).exclude(
            bk_host_id__in=params.get("exclude_hosts", [])
        )

        fetch_fields = ["bk_cloud_id", "bk_biz_id", "bk_host_id", "os_type", "inner_ip", "status"]

        hosts = list(hosts_sql[begin:end].values(*fetch_fields))

        bk_cloud_ids = [host["bk_cloud_id"] for host in hosts]
        bk_host_ids = [host["bk_host_id"] for host in hosts]

        # 获得云区域名称
        cloud_name = dict(
            models.Cloud.objects.filter(bk_cloud_id__in=bk_cloud_ids).values_list("bk_cloud_id", "bk_cloud_name")
        )
        cloud_name[0] = DEFAULT_CLOUD_NAME

        plugin_process_status_list = models.ProcessStatus.objects.filter(
            bk_host_id__in=bk_host_ids, name=params["project"]
        ).values("bk_host_id", "name", "version", "status", "id")

        host_process_status = {}
        for process_status in plugin_process_status_list:
            host_process_status[process_status["bk_host_id"]] = process_status

        # 填充云区域、业务名称、插件状态
        for host in hosts:
            host["bk_cloud_name"] = cloud_name.get(host["bk_cloud_id"])
            host["bk_biz_name"] = user_biz.get(host["bk_biz_id"], "")
            host["plugin_status"] = {params["project"]: host_process_status.get(host["bk_host_id"], {})}

        return {"total": hosts_sql.count(), "list": hosts}

    @staticmethod
    def fetch_config_variables(config_tpl_ids):
        config_tpls = list(
            models.PluginConfigTemplate.objects.filter(id__in=config_tpl_ids, is_release_version=True).values(
                "id", "name", "version", "is_main", "creator", "content"
            )
        )
        diff = set(config_tpl_ids) - {tpl["id"] for tpl in config_tpls}
        if diff:
            raise exceptions.PluginConfigTplNotExistError(_("插件配置模板{ids}不存在或已下线").format(ids=diff))

        for config_tpl in config_tpls:
            if config_tpl["is_main"]:
                # 主配置暂不支持用户自定义
                config_tpl["variables"] = {}
            else:

                shield_content = tools.PluginV2Tools.shield_tpl_unparse_content(config_tpl["content"])
                config_tpl["variables"] = tools.PluginV2Tools.simplify_var_json(
                    tools.PluginV2Tools.parse_tpl2var_json(shield_content)
                )
            config_tpl.pop("content")
        return config_tpls

    @staticmethod
    def history(query_params: Dict):
        packages = NodeApi.plugin_history(query_params)
        if not packages:
            return packages
        nodes_counter = tools.PluginV2Tools.get_packages_node_numbers(
            [packages[0]["project"]], ["os", "cpu_arch", "version"]
        )
        for package in packages:
            package["nodes_number"] = nodes_counter.get(
                f"{package['os']}_{package['cpu_arch']}_{package['version']}", 0
            )
        return packages

    @staticmethod
    def operate(job_type: str, plugin_name: str, scope: Dict, steps: List[Dict]):
        bk_biz_scope = list(set([node["bk_biz_id"] for node in scope["nodes"]]))

        CmdbHandler().check_biz_permission(bk_biz_scope, IamActionType.plugin_operate)

        base_create_kwargs = {
            "is_main": True,
            "run_immediately": True,
            "plugin_name": plugin_name,
            # 非策略订阅在SaaS侧定义为一次性下发操作
            "category": models.Subscription.CategoryType.ONCE,
            "scope": scope,
            "bk_biz_scope": bk_biz_scope,
        }

        if job_type == constants.JobType.MAIN_INSTALL_PLUGIN:
            create_data = {**base_create_kwargs, "steps": steps}
            tools.PolicyTools.parse_steps(create_data, settings_key="config", simple_key="configs")
            tools.PolicyTools.parse_steps(create_data, settings_key="params", simple_key="params")

            create_data["steps"][0]["config"]["job_type"] = job_type
        else:
            config_templates = models.PluginConfigTemplate.objects.filter(plugin_name=plugin_name, is_main=True)
            create_data = {
                **base_create_kwargs,
                "steps": [
                    {
                        "config": {
                            "config_templates": distinct_dict_list(
                                [
                                    {"name": conf_tmpl.name, "version": "latest", "is_main": True}
                                    for conf_tmpl in config_templates
                                ]
                            ),
                            "plugin_name": plugin_name,
                            "plugin_version": "latest",
                            "job_type": job_type,
                        },
                        "type": "PLUGIN",
                        "id": plugin_name,
                        "params": {},
                    }
                ],
            }

        create_result = NodeApi.create_subscription(create_data)
        create_result.update(
            tools.PolicyTools.create_job(
                job_type=job_type,
                subscription_id=create_result["subscription_id"],
                task_id=create_result["task_id"],
                bk_biz_scope=create_data["bk_biz_scope"],
            )
        )
        return create_result

    @staticmethod
    def fetch_package_deploy_info(projects: List[str], keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        获取插件包部署信息
        :param projects: 插件包
        :param keys: 聚合关键字
        :return: 聚合关键字 - 插件包部署信息
        """

        cache_deploy_number_template = "plugin_v2:fetch_package_deploy_info:{project}:{keys_combine_str}"

        # 以project & keys 粒度查询已缓存的数据
        cache_key__project_key_str__deploy_number_map = cache.get_many(
            cache_deploy_number_template.format(project=project, keys_combine_str="|".join(keys))
            for project in projects
        )

        projects__hit = set()
        key_str__deploy_number_cache_map = {}
        # 将缓存结构转化为查询函数的返回格式，并记录projects的命中情况
        for cache_key, project_key_str__deploy_number_map in cache_key__project_key_str__deploy_number_map.items():
            project_hit = cache_key.split(":", 3)[2]
            projects__hit.add(project_hit)

            key_str__deploy_number_cache_map.update(project_key_str__deploy_number_map)

        params_list = []
        projects__not_hit = list(set(projects) - projects__hit)
        if len(projects__not_hit) <= settings.CONCURRENT_NUMBER:
            for project in projects__not_hit:
                params_list.append({"projects": [project], "keys": keys})
        else:
            # 指定的projects太多，此时切片并发执行
            slice_projects_list = list_slice(projects__not_hit, limit=5)
            for slice_projects in slice_projects_list:
                params_list.append({"projects": slice_projects, "keys": keys})

        project_key_str__deploy_number_map_list: List[Dict[str, int]] = batch_call(
            func=tools.PluginV2Tools.get_packages_node_numbers, params_list=params_list, get_data=lambda x: x
        )
        key_str__deploy_number_uncache_map = dict(ChainMap(*project_key_str__deploy_number_map_list))

        # 按project维度重组查询所得的各个插件包部署数量
        project__key_str__deploy_number_map = defaultdict(dict)
        for key_str, deploy_number in key_str__deploy_number_uncache_map.items():
            project = key_str.split("_", 1)[0]
            project__key_str__deploy_number_map[project].update({key_str: deploy_number})

        # 缓存此前未命中的数据，仅保存查询时间较长的
        for project, project_key_str__deploy_number_map in project__key_str__deploy_number_map.items():
            # 过期时间分散设置，防止缓存雪崩
            cache.set(
                cache_deploy_number_template.format(project=project, keys_combine_str="|".join(keys)),
                project_key_str__deploy_number_map,
                constants.TimeUnit.DAY + random.randint(constants.TimeUnit.DAY, 2 * constants.TimeUnit.DAY),
            )

        key_str__deploy_info_map = {}
        all_key_str__deploy_number_map = dict(
            ChainMap(key_str__deploy_number_uncache_map, key_str__deploy_number_cache_map)
        )
        # 组装返回结构，此处虽然仅需部署数量信息，保留字典结构以便后续接口返回信息拓展
        for key_str, deploy_number in all_key_str__deploy_number_map.items():
            key_str__deploy_info_map[key_str] = {"nodes_number": deploy_number}
        return key_str__deploy_info_map
