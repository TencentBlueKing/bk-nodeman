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
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import ModelViewSet
from apps.node_man.handlers.plugin import PluginHandler
from apps.node_man.models import GsePluginDesc, Host, Packages, ProcessStatus
from apps.node_man.serializers.plugin import (
    GsePluginSerializer,
    OperateSerializer,
    PluginListSerializer,
    ProcessPackageSerializer,
    ProcessStatusSerializer,
)
from apps.utils.local import get_request_username


class GsePluginViewSet(ModelViewSet):
    """
    获取agent运行状态和版本信息
    """

    model = GsePluginDesc
    queryset = GsePluginDesc.objects.all().order_by("-id")
    serializer_class = GsePluginSerializer
    http_method_names = ["get", "post"]

    def get_queryset(self):
        category = self.kwargs.get("category")
        if category is not None:
            self.queryset = self.queryset.filter(category=category)
        return self.queryset

    def list(self, *args, **kwargs):
        """
        @api {GET} /plugin/{{pk}}/process/ 查询插件列表,pk为official, external 或 scripts
        @apiName list_process
        @apiGroup plugin
        @apiSuccessExample {json} 成功返回:
        [{
            "id":14,
            "name":"bklogbeat",
            "description":"windows日志文件采集",
            "description_en":"Windows log collector",
            "scenario":"数据平台，蓝鲸监控，日志检索等和日志相关的数据. 首次使用插件管理进行操作前，先到日志检索/数据平台等进行设置插件的功能项",
            "scenario_en":"Log collection on data, bkmonitor, log-search apps",
            "category":"official",
            "config_file":"bklogbeat.conf",
            "config_format":"yaml",
            "use_db":false,
            "is_binary":true,
            "auto_launch":false
        }]
        """
        return super().list(*args, **kwargs)


class PluginViewSet(ModelViewSet):
    model = Host

    @action(detail=False, methods=["POST"], serializer_class=PluginListSerializer)
    def search(self, request):
        """
        @api {POST} /plugin/search/ 查询插件列表
        @apiName list_host
        @apiGroup plugin
        @apiParam {Int[]} [bk_biz_id] 业务ID
        @apiParam {Int[]} [bk_host_id] 主机ID
        @apiParam {List} [conditions] 搜索条件，支持os_type, ip, status <br>
        version, bk_cloud_id, node_from 和 模糊搜索query
        @apiParam {Int[]} [exclude_hosts] 跨页全选排除主机
        @apiParam {Int} [page] 当前页数
        @apiParam {Int} [pagesize] 分页大小
        @apiParam {Boolean} [only_ip] 只返回IP
        @apiParam {Boolean} [detail] 是否为详情,为True显示主进程信息
        @apiSuccessExample {json} 成功返回:
        {
            "total": 2,
            "list": [
                {
                    "status": "RUNNING",
                    "version": "1.6.2",
                    "bk_cloud_id": 0,
                    "bk_biz_id": 2,
                    "bk_host_id": 15302,
                    "node_type": "AGENT",
                    "os_type": "LINUX",
                    "inner_ip": "127.0.0.1",
                    "node_from": "NODE_MAN",
                    "status_display": "正常",
                    "bk_cloud_name": "直连区域",
                    "bk_biz_name": "蓝鲸",
                    "job_result": {},
                    "plugin_status": [
                        [
                            {
                                "name": "basereport",
                                "subscription_statistics": {
                                    "running": 1,
                                    "unknown": 0,
                                    "terminated": 1,
                                    "not_installed": 0
                                },
                                "subscription_tasks": [
                                    {
                                        "id": 8236,
                                        "plugin_name": "basereport",
                                        "name": "--",
                                        "status": "RUNNING",
                                        "version": "1.2.3",
                                        "update_time": "2020-07-21 14:39:41+0800",
                                        "is_auto_trigger": true,
                                        "deploy_type": "自动",
                                        "config_template": "aa.conf",
                                        "config_template_version": "5.6.6",
                                        "install_path": "/a/b"
                                    },
                                    {
                                        "id": 8237,
                                        "plugin_name": "basereport",
                                        "name": "--",
                                        "status": "TERMINATED",
                                        "version": "1.2.4",
                                        "update_time": "2020-07-21 14:39:41+0800",
                                        "is_auto_trigger": true,
                                        "deploy_type": "手动",
                                        "config_template": "bb.conf",
                                        "config_template_version": "6.7.8",
                                        "install_path": "/data/inst/"
                                    }
                                ],
                                "status": "RUNNING",
                                "deploy_type": "远程",
                                "config_template": "ff.conf",
                                "config_template_version": "9.9.9.",
                                "install_path": "/f/",
                                "version": "10.2.1",
                                "host_id": 15302,
                                "job_result": {}
                            },
                            {
                                "name": "processbeat",
                                "subscription_statistics": {
                                    "running": 0,
                                    "unknown": 1,
                                    "terminated": 0,
                                    "not_installed": 0
                                },
                                "subscription_tasks": [
                                    {
                                        "id": 8291,
                                        "plugin_name": "processbeat",
                                        "name": "--",
                                        "status": "UNKNOWN",
                                        "version": "1.0.1",
                                        "update_time": "2020-07-21 14:39:41+0800",
                                        "is_auto_trigger": true,
                                        "deploy_type": "自动",
                                        "config_template": "cc.conf",
                                        "config_template_version": "8.8.8",
                                        "install_path": "/c/d/"
                                    }
                                ],
                                "status": "RUNNING",
                                "deploy_type": "自动",
                                "config_template": "ffff.conf",
                                "config_template_version": "0.2.3",
                                "install_path": "/b/f",
                                "version": "1.4.0",
                                "host_id": 15302,
                                "job_result": {}
                            }
                        ]
                    ],
                    "operate_permission": true,
                    "update_time": "--"
                },
                {
                    "status": "RUNNING",
                    "version": "1.6.2",
                    "bk_cloud_id": 0,
                    "bk_biz_id": 13,
                    "bk_host_id": 15272,
                    "node_type": "AGENT",
                    "os_type": "LINUX",
                    "inner_ip": "127.0.0.2",
                    "node_from": "NODE_MAN",
                    "status_display": "正常",
                    "bk_cloud_name": "直连区域",
                    "bk_biz_name": "bcs测试",
                    "job_result": {},
                    "plugin_status": [
                        [
                            {
                                "name": "basereport",
                                "subscription_statistics": {},
                                "subscription_tasks": {},
                                "status": "RUNNING",
                                "deploy_type": "远程",
                                "config_template": "ff.conf",
                                "config_template_version": "9.9.9.",
                                "install_path": "/f/",
                                "version": "10.2.1",
                                "host_id": 15272,
                                "job_result": {}
                            },
                            {
                                "name": "processbeat",
                                "subscription_statistics": {},
                                "subscription_tasks": {},
                                "status": "RUNNING",
                                "deploy_type": "自动",
                                "config_template": "ffff.conf",
                                "config_template_version": "0.2.3",
                                "install_path": "/b/f",
                                "version": "1.4.0",
                                "host_id": 15272,
                                "job_result": {}
                            }
                        ]
                    ],
                    "operate_permission": true,
                    "update_time": "--"
                }
            ]
        }
        """

        # 处理
        hosts = PluginHandler.list(self.validated_data)
        return Response(hosts)

    @action(detail=False, methods=["POST"], serializer_class=OperateSerializer)
    def operate(self, request):
        """
        @api {POST} /plugin/operate/ 插件操作类任务
        @apiDescription 用于插件的各类操作。<br>
        bk_host_id和exclude_hosts必填一个。<br>
        若填写了 exclude_hosts ，则代表跨页全选模式。<br>
        注意, 云区域ID、业务ID等筛选条件，仅在跨页全选模式下有效。<br>
        @apiName operate_plugin
        @apiGroup plugin
        @apiParam {String} job_type 任务类型
        @apiParam {Object[]} plugin_params 插件信息
        @apiParam {String} plugin_params.name 插件名称
        @apiParam {String} [plugin_params.version] 插件版本
        @apiParam {String} [plugin_params.keep_config] 是否保留原有配置文件
        @apiParam {String} [plugin_params.no_restart] 是否仅更新文件，不重启进程
        @apiParam {List} [plugin_params_list] 插件信息列表，2.1.x 插件参数，用于支持批量操作，传参要求同 plugin_params
        @apiParam {String} [bk_biz_id] 业务ID
        @apiParam {List} [condition] 搜索条件，支持os_type, ip, status <br>
        version, bk_cloud_id, node_from 和 模糊搜索query
        @apiParam {Int[]} [exclude_hosts] 跨页全选排除主机
        @apiParam {Int[]} [bk_host_id] 主机ID
        主机ID和跨页全选排除主机必选一个
        @apiParamExample {Json} 安装请求参数
        {
            "job_type": "START_PLUGIN",
            "bk_host_id": [7731, 7732],
            "plugin_params": {"name": "basereport", "version": "10.1.12"},
            "plugin_params_list": [
                {"name": "basereport", "version": "10.1.12"},
                {"name": "bkunifylogbeat", "version": "7.1.32"}
            ]
        }
        @apiSuccessExample {json} 成功返回:
        {
            "basereport": 1,
            "bkunifylogbeat": 2
        }
        """
        return Response(PluginHandler.operate(self.validated_data, get_request_username()))

    @action(detail=False, methods=["GET"])
    def statistics(self, request):
        """
        @api {GET} /plugin/statistics/ 获取插件统计数据
        @apiDescription 根据业务、插件、版本等维度，统计插件在主机的安装数量
        @apiName plugin_statistics
        @apiGroup plugin
        @apiSuccessExample {json} 成功返回:
        [
            {
                "bk_biz_id": 2,
                "plugin_name": "basereport",
                "version": "1.2.3",
                "host_count": 1
            },
            {
                "bk_biz_id": 2,
                "plugin_name": "processbeat",
                "version": "10.1.2",
                "host_count": 2
            }
        ]
        """
        return Response(PluginHandler.get_statistics())


class PackagesViews(ModelViewSet):
    model = Packages
    serializer_class = ProcessPackageSerializer

    def list(self, request, *args, **kwargs):
        """
        @api {GET} /plugin/{{pk}}/package/ 查询进程包列表,pk为具体进程名
        @apiName list_package
        @apiGroup plugin
        @apiParam {String} os 系统类型
        @apiSuccessExample {json} 成功返回:
        [
                {
                    "id":2,
                    "pkg_name":"basereport-10.1.12.tgz",
                    "version":"10.1.12",
                    "module":"gse_plugin",
                    "project":"basereport",
                    "pkg_size":4561957,
                    "pkg_path":"/data/bkee/miniweb/download/linux/x86_64",
                    "md5":"046779753b6709635db0c861a1b0020e",
                    "pkg_mtime":"2019-11-01 20:46:52.404139",
                    "pkg_ctime":"2019-11-01 20:46:52.404139",
                    "location":"http://x.x.x.x/download/linux/x86_64",
                    "os":"linux",
                    "cpu_arch":"x86_64"
                },
                {
                    "id":1,
                    "pkg_name":"basereport-10.1.9.tgz",
                    "version":"10.1.9",
                    "module":"gse_plugin",
                    "project":"basereport",
                    "pkg_size":4562217,
                    "pkg_path":"/data/bkee/miniweb/download/linux/x86_64",
                    "md5":"6fe084f450352b1fa598a41a72800bc8",
                    "pkg_mtime":"2019-08-26 19:17:56.905309",
                    "pkg_ctime":"2019-08-26 19:17:56.905309",
                    "location":"http://x.x.x.x/download/linux/x86_64",
                    "os":"linux",
                    "cpu_arch":"x86_64"
                }
            ]
        """
        project = kwargs["process"]
        os_type = request.query_params.get("os", "")
        queryset = PluginHandler.get_packages(project, os_type)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["GET"], detail=False)
    def fetch_version(self, request, *args, **kwargs):
        """
        @api {GET} /plugin/{{plugin_name}}/package/fetch_version/ 获取插件最新版本
        @apiName fetch_version
        @apiGroup plugin
        @apiParam {String} plugin_name 插件名称
        @apiParam {String} os_type 系统类型
        @apiParam {String} is_lastest 是否最新版本
        @apiParamExample {json} 请求参数:
        {
            "plugin_name": "basereport",
            "cpu_arch": "x86_64"
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "package_id": 1,
                "os_type": "Linux x64",
                "lastest_version": "v2.4",
                "description": "我是版本描述"
            },
            {
                "package_id": 2,
                "os_type": "Linux x32",
                "lastest_version": "v2.3"，
                "description": "我是版本描述"
            }
        ]
        [
            {
                "package_id": 1,
                "os_type": "Linux x64",
                "version": "v2.4",
                "status": "已上线",
                "config_template_version": "2.3.4",
                "updated_at": "2020-07-31 18:00:00",
                "host_count":10000,
                "description": "我是版本描述"
            },
            {
                "package_id": 2,
                "os_type": "Linux x64",
                "version": "v2.4",
                "status": "已上线",
                "config_template_version": "2.3.4",
                "updated_at": "2020-07-31 18:00:00",
                "host_count":10000,
                "description": "我是版本描述"
            },
        ]
        """
        return Response(
            [
                {"id": 1, "os_type": "Linux x64", "version": "v2.4", "cpu_arch": "x86_64"},
                {"id": 2, "os_type": "Linux x32", "version": "v2.3", "cpu_arch": "x86_64"},
            ]
        )

    def retrieve(self, request, *args, **kwargs):
        """
        @api {GET} /plugin/{{plugin_name}}/package/{{pk}}/ 获取插件包信息
        @apiName fetch_package_info
        @apiGroup plugin
        @apiSuccessExample {json} 成功返回:
        [
            {
                "package_id": 1,
                "os_type": "Linux x64",
                "version": "v2.4",
                "status": "已上线",
                "config_template_version": "2.3.4",
                "updated_at": "2020-07-31 18:00:00",
                "description": "我是版本描述",
                "config_template": [
                    {
                        "name": "xx.xml",
                        "is_main": True,
                        "params": {
                            "log_path": "/data/log/"
                        }
                    }
                ]
            },
            {
                "package_id": 2,
                "os_type": "Linux x64",
                "version": "v2.4",
                "status": "已上线",
                "config_template_version": "2.3.4",
                "updated_at": "2020-07-31 18:00:00",
                "description": "我是版本描述",
                "config_template": [
                    {
                        "name": "xx.xml",
                        "is_main": False,
                        "params": {
                            "log_path": "/data/log/"
                        }
                    }
                ]
            },
        ]
        """
        return Response(
            [
                {
                    "package_id": 1,
                    "os_type": "Linux x64",
                    "version": "v2.4",
                    "status": "已上线",
                    "config_template_version": "2.3.4",
                    "updated_at": "2020-07-31 18:00:00",
                    "description": "我是版本描述",
                    "config_template": [{"name": "xx.xml", "is_main": True, "params": {"log_path": "/data/log/"}}],
                },
                {
                    "package_id": 2,
                    "os_type": "Linux x64",
                    "version": "v2.4",
                    "status": "已上线",
                    "config_template_version": "2.3.4",
                    "updated_at": "2020-07-31 18:00:00",
                    "description": "我是版本描述",
                    "config_template": [{"name": "xx.xml", "is_main": False, "params": {"log_path": "/data/log/"}}],
                },
            ]
        )


class ProcessStatusViewSet(ModelViewSet):
    model = ProcessStatus
    serializer_class = ProcessStatusSerializer

    @action(methods=["POST"], detail=False, url_path="status")
    def process_status(self, request, *args, **kwargs):
        """
        @api {POST} /plugin/process/status/ 查询主机进程状态信息
        @apiName list_process_status
        @apiGroup plugin
        @apiParam {Int[]} bk_host_ids 主机ID
        @apiSuccessExample {json} 请求示例:
        {
            "bk_host_ids": [1,2]
        }
        @apiSuccessExample {json} 成功返回:
        {
            "result": true,
            "code": 0,
            "message": ""
            "data": [
                {
                    "bk_host_id": 1,
                    "name": "gseagent",
                    "status": "RUNNING",
                    "version": "1.60.54"
                },
                {
                    "bk_host_id": 2,
                    "name": "gseagent",
                    "status": "RUNNING",
                    "version": "1.60.54"
                }
            ]
        }
        """
        bk_host_ids = request.data.get("bk_host_ids", [])
        queryset = PluginHandler.get_process_status(bk_host_ids)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
