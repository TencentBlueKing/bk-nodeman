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
from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import ModelViewSet
from apps.node_man import exceptions
from apps.node_man.constants import IamActionType
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.handlers.permission import PackagePermission
from apps.node_man.handlers.plugin_v2 import PluginV2Handler
from apps.node_man.models import GsePluginDesc
from apps.node_man.serializers import plugin_v2
from apps.utils.local import get_request_username
from common.api import NodeApi


class PluginV2ViewSet(ModelViewSet):
    model = GsePluginDesc
    queryset = None
    permission_classes = (PackagePermission,)

    def list(self, request, *args, **kwargs):
        """
        @api {GET} /v2/plugin/ 插件列表
        @apiName list_plugin
        @apiGroup plugin_v2
        @apiParam {String} [search] 插件别名&名称模糊搜索
        @apiParam {Boolean} [simple_all] 返回全部数据（概要信息，`id`, `description`, `name`），默认`False`
        @apiParam {Int} [page] 当前页数，默认`1`
        @apiParam {Int} [pagesize] 分页大小，默认`10`
        @apiParam {object} [sort] 排序
        @apiParam {String=["name", "category", "creator", "scenario", "description"]} [sort.head] 排序字段
        @apiParam {String=["ASC", "DEC"]} [sort.sort_type] 排序类型
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 成功返回:
        {
            "total": 2,
            "list": [
                {
                    "id": 1,
                    "description": "系统基础信息采集",
                    "name": "basereport",
                    "category": "官方插件",
                    "nodes_number": 123,
                    "source_app_code": "bk_nodeman",
                    "scenario": "CMDB上的实时数据，蓝鲸监控里的主机监控，包含CPU，内存，磁盘等",
                    "deploy_type": "整包部署"
                },
                {
                    "id": 2,
                    "description": "监控采集器",
                    "name": "bkmonitorbeat",
                    "category": "第三方插件",
                    "nodes_number": 321,
                    "source_app_code": "bk_monitor",
                    "scenario": "蓝鲸监控采集器，支持多种协议及多任务的采集，提供多种运行模式和热加载机制",
                    "deploy_type": "Agent自动部署"
                }
            ]
        }
        """
        self.serializer_class = plugin_v2.PluginListSerializer
        return Response(PluginV2Handler.list_plugin(self.validated_data))

    def retrieve(self, request, *args, **kwargs):
        """
        @api {GET} /v2/plugin/{{pk}}/ 插件详情
        @apiName retrieve_plugin
        @apiGroup plugin_v2
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 成功返回:
        {
            "id": 1,
            "description": "系统基础信息采集",
            "name": "basereport",
            "category": "官方插件",
            "source_app_code": "bk_nodeman",
            "scenario": "CMDB上的实时数据，蓝鲸监控里的主机监控，包含CPU，内存，磁盘等",
            "deploy_type": "整包部署",
            "plugin_packages": [
                {
                    "id": 1,
                    "pkg_name": "basereport-10.1.12.tgz",
                    "project": "basereport",
                    "version": "10.1.12",
                    "config_templates": [
                        {"id": 1, "name": "basereport.conf", "version": "10.1", "is_main": true}
                    ],
                    "os": "linux",
                    "cpu_arch": "x86_64",
                    "support_os_cpu": "linux_x86_64",
                    "pkg_mtime": "2019-11-25 21:58:30",
                    "is_ready": True
                },
                {
                    "id": 2,
                    "pkg_name": "bkmonitorbeat-1.7.1.tgz",
                    "project": "bkmonitorbeat",
                    "version": "1.7.1",
                    "config_templates": [
                        {"id": 1, "name": "child1.conf", "version": "1.0", "is_main": false},
                        {"id": 2, "name": "child2.conf", "version": "1.1", "is_main": false},
                        {"id": 3, "name": "bkmonitorbeat.conf", "version": "0.1", "is_main": true}
                    ],
                    "os": "windows",
                    "cpu_arch": "x86",
                    "support_os_cpu": "windows_x86",
                    "pkg_mtime": "2019-11-25 21:58:30",
                    "is_ready": True
                }
            ]
        }
        """

        is_superuser = IamHandler().is_superuser(get_request_username())

        perms_ids = []
        if not is_superuser:
            # 校验权限
            perms_ids = IamHandler().fetch_policy(get_request_username(), [IamActionType.plugin_pkg_operate])[
                IamActionType.plugin_pkg_operate
            ]

        data = NodeApi.plugin_retrieve({"plugin_id": kwargs["pk"]})
        data["permissions"] = {"operate": int(kwargs["pk"]) in perms_ids if not is_superuser else True}
        return Response(data)

    def update(self, request, *args, **kwargs):
        """
        @api {PUT} /v2/plugin/{{pk}}/  编辑插件
        @apiName update_plugin
        @apiGroup plugin_v2
        @apiParam {String} description 插件别名
        @apiParamExample {Json} 请求参数
        {
            "description": "bkcloud",
        }
        """
        self.serializer_class = plugin_v2.PluginEditSerializer
        gse_plugin_desc = GsePluginDesc.objects.filter(id=kwargs["pk"]).first()
        if not gse_plugin_desc:
            raise exceptions.PluginNotExistError(_("不存在ID为: {id} 的插件").format(id=kwargs["pk"]))

        gse_plugin_desc.description = self.validated_data["description"]
        gse_plugin_desc.save(update_fields=["description"])
        return Response({})

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.PluginListHostSerializer)
    def list_plugin_host(self, request):
        """
        @api {POST} /v2/plugin/list_plugin_host/  查询插件下主机
        @apiName list_plugin_host
        @apiGroup plugin_v2
        @apiParam {String} project 插件名称
        @apiParam {Int[]} [bk_biz_id] 业务ID
        @apiParam {Int[]} [bk_host_id] 主机ID
        @apiParam {List} [conditions] 搜索条件，支持os_type, ip, status, version, bk_cloud_id, node_from <br>
        query: IP、操作系统、Agent状态、Agent版本、云区域 单/多模糊搜索 <br>
        topology: 拓扑搜索，传入bk_set_ids, bk_module_ids
        @apiParam {List} [nodes] 拓扑节点, 例如：[{"bk_biz_id": 1, "bk_inst_id": 10, "bk_obj_id": "module"}, ...]
        @apiParam {Int[]} [exclude_hosts] 跨页全选排除主机
        @apiParam {Int} [page] 当前页数，默认为`1`
        @apiParam {Int} [pagesize] 分页大小，默认为`10`，`-1` 表示跨页全选
        @apiParamExample {Json} 请求参数
        {
            "description": "bkcloud",
        }
        :param request:
        :return: {
            "total": 1,
            "list": [
                {
                    "bk_cloud_id": 1,
                    "bk_cloud_name": "云区域名称",
                    "bk_biz_id": 2,
                    "bk_biz_name": "业务名称",
                    "bk_host_id": 1,
                    "os_type": "linux",
                    "inner_ip": "127.0.0.1",
                    "status": "RUNNING",
                    "plugin_status": {
                        "test_plugin": {
                            "version": "1.0.0",
                            "status": "RUNNING"
                        }
                    }
                }
            ]
        }
        """
        return Response(PluginV2Handler.list_plugin_host(params=self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.PluginRegisterSerializer)
    def create_register_task(self, request):
        """
        @api {POST} /v2/plugin/create_register_task/ 创建注册任务
        @apiName create_register_task
        @apiGroup plugin_v2
        @apiParam {String} file_name 文件名
        @apiParam {Boolean} is_release 是否已发布
        @apiParam {Boolean} [is_template_load] 是否需要读取配置文件，缺省默认为`false`
        @apiParam {Boolean} [is_template_overwrite] 是否可以覆盖已经存在的配置文件，缺省默认为`false`
        @apiParam {List} [select_pkg_abs_paths] 指定注册包相对路径列表，缺省默认全部导入
        @apiParamExample {Json} 请求参数
        {
            "file_name": "bkunifylogbeat-7.1.28.tgz",
            "is_release": True,
            "select_pkg_abs_paths": ["bkunifylogbeat_linux_x86_64/bkunifylogbeat"]
        }
        @apiSuccessExample {json} 成功返回:
        {
            "job_id": 1
        }
        """
        return Response(NodeApi.create_register_task(self.validated_data))

    @action(detail=False, methods=["GET"], serializer_class=plugin_v2.PluginRegisterTaskSerializer)
    def query_register_task(self, request):
        """
        @api {GET} /v2/plugin/query_register_task/ 查询插件注册任务
        @apiName query_register_task
        @apiGroup plugin_v2
        @apiParam {Int} job_id 任务ID
        @apiParamExample {Json} 请求参数
        {
            "job_id": 1
        }
        @apiSuccessExample {json} 成功返回:
        {
            "is_finish": False,
            "status": "RUNNING",
            "message": "~",
        }
        """
        return Response(NodeApi.query_register_task(self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.PkgStatusOperationSerializer)
    def package_status_operation(self, request):
        """
        @api {POST} /v2/plugin/package_status_operation/ 插件包状态类操作
        @apiName package_status_operation
        @apiGroup plugin_v2
        @apiParam {String} operation 状态操作 `release`-`上线`，`offline`-`下线` `ready`-`启用`，`stop`-`停用`
        @apiParam {Int[]} [id] 插件包id列表，`id`和（`name`, `version`）至少有一个
        @apiParam {String} [name] 插件包名称
        @apiParam {String} [version] 版本号
        @apiParam {String} [cpu_arch] CPU类型，`x86` `x86_64` `powerpc`
        @apiParam {String} [os] 系统类型，`linux` `windows` `aix`
        @apiParam {String[]} [md5_list] md5列表
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 返回操作成功的插件包id列表:
        [1, 2, 4]
        """
        return Response(NodeApi.package_status_operation(self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.ExportSerializer)
    def create_export_task(self, request):
        """
        @api {POST} /v2/plugin/create_export_task/ 触发插件打包导出
        @apiName create_export_plugin_task
        @apiGroup plugin_v2
        @apiParam {Object} query_params 插件信息，version, project, os[可选], cpu_arch[可选]
        @apiParam {String} category 插件类别
        @apiParamExample {Json} 请求参数
        {
            "category": "gse_plugin",
            "query_params": {
                "project": "test_plugin",
                "version": "1.0.0"
            }
        }
        @apiSuccessExample {json} 成功返回:
        {
            "job_id": 1
        }
        """
        params = self.validated_data
        params["creator"] = get_request_username()
        return Response(NodeApi.create_export_task(params))

    @action(detail=False, methods=["GET"], serializer_class=plugin_v2.QueryExportTaskSerializer)
    def query_export_task(self, request):
        """
        @api {GET} /v2/plugin/query_export_task/ 获取一个导出任务结果
        @apiName query_export_plugin_task
        @apiGroup plugin_v2
        @apiParam {Int} job_id 任务ID
        @apiParamExample {Json} 请求参数
        {
            "job_id": 1
        }
        @apiSuccessExample {json} 成功返回:
        {
            "is_finish": True,
            "is_failed": False,
            "download_url": "http://127.0.0.1//backend/export/download/",
            "error_message": "haha"
        }
        """
        return Response(NodeApi.query_export_task(self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.PluginParseSerializer)
    def parse(self, request):
        """
        @api {POST} /v2/plugin/parse/ 解析插件包
        @apiName plugin_parse
        @apiGroup plugin_v2
        @apiParam {String} file_name 文件名
        @apiParamExample {Json} 请求参数
        {
            "file_name": "basereport-10.1.12.tgz"
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "result": True,
                "message": "新增插件",
                "pkg_abs_path": "basereport_linux_x86_64/basereport",
                "pkg_name": "basereport-10.1.12",
                "project": "basereport",
                "version": "10.1.12",
                "category": "官方插件",
                "config_templates": [
                    {"name": "child1.conf", "version": "1.0", "is_main": false},
                    {"name": "child2.conf", "version": "1.1", "is_main": false},
                    {"name": "basereport-main.config", "version": "0.1", "is_main": true}
                ],
                "os": "x86_64",
                "cpu_arch": "linux",
                "description": "高性能日志采集"
            },
            {
                "result": False,
                "message": "缺少project.yaml文件",
                "pkg_abs_path": "external_bkmonitorbeat_windows_x32/bkmonitorbeat",
                "pkg_name": None,
                "project": None,
                "version": None,
                "category": None,
                "config_templates": [],
                "os": "x32",
                "cpu_arch": "windows",
                "description": None
            },
        ]
        """
        return Response(NodeApi.parse(self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.PluginStatusOperationSerializer)
    def plugin_status_operation(self, request):
        """
        @api {POST} /v2/plugin/plugin_status_operation/ 插件状态类操作
        @apiName plugin_status_operation
        @apiGroup plugin_v2
        @apiParam {String} operation 状态操作 `ready`-`启用`，`stop`-`停用`
        @apiParam {Int[]} id 插件id列表
        @apiParamExample {Json} 请求参数
        {
            "operation": "stop",
            "id": [1, 2]
        }
        @apiSuccessExample {json} 返回操作成功的插件id列表:
        [1, 2]
        """
        return Response(NodeApi.plugin_status_operation(self.validated_data))

    @action(detail=True, methods=["GET"], serializer_class=plugin_v2.PluginQueryHistorySerializer)
    def history(self, request, pk):
        """
        @api {GET} /v2/plugin/{{pk}}/history/ 插件包历史
        @apiName plugin_history
        @apiGroup plugin_v2
        @apiParam {String} [os] 系统类型，`windows` `linux` `aix`
        @apiParam {String} [cpu_arch] cpu位数，`x86` `x86_64` `powerpc`
        @apiParam {Int[]} [pkg_ids] 插件包id列表
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "id": 1,
                "pkg_name": "basereport-1.0.tgz",
                "project": "basereport",
                "version": "1.0",
                "pkg_size": 4391830,
                "md5": "35bf230be9f3c1b878ef7665be34e14e",
                "nodes_number": 1,
                "config_templates": [
                    {"id": 1, "name": "bkunifylogbeat.conf", "version": "1.0", "is_main": false},
                    {"id": 2, "name": "bkunifylogbeat1.conf", "version": "1.1", "is_main": false},
                    {"id": 3, "name": "bkunifylogbeat-main.config", "version": "0.1", "is_main": true}
                ],
                "pkg_mtime": "2019-11-25 21:58:30",
                "is_ready": True,
                "is_release_version": True
            },
            {
                "id": 2,
                "pkg_name": "basereport-1.1.tgz",
                "project": "basereport",
                "version": "1.1",
                "md5": "35bf230be9f3c1b878ef7665be34e14e",
                "nodes_number": 1,
                "pkg_size": 4391830,
                "config_templates": [
                    {"id": 4, "name": "child1.conf", "version": "1.0", "is_main": false},
                    {"id": 5, "name": "child2.conf", "version": "2.0", "is_main": false},
                    {"id": 6, "name": "bkunifylogbeat-main.config", "version": "0.2", "is_main": true}
                ],
                "pkg_mtime": "2019-11-25 22:01:30",
                "is_ready": True,
                // 最新上传的包
                "is_newest": True,
                "is_release_version": True
            },
        ]
        """
        params = self.validated_data
        params["plugin_id"] = pk
        return Response(PluginV2Handler.history(params))

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.PluginUploadSerializer)
    def upload(self, request):
        """
        @api {POST} /v2/plugin/upload/ 插件上传
        @apiName plugin_upload
        @apiGroup plugin_v2
        @apiParam {File} package_file 插件压缩包
        @apiParam {String} [module] 插件类别，缺省默认为`gse_plugin`
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 成功返回:
        {
            "id": 3,
            "name": "test_plugin-7.1.28.tgz",
            "pkg_size": 5587006
        }
        """
        ser = self.serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        return JsonResponse(PluginV2Handler.upload(package_file=data["package_file"], module=data["module"]))

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.PluginFetchConfigVarsSerializer)
    def fetch_config_variables(self, request):
        """
        @api {POST} /v2/plugin/fetch_config_variables/ 获取配置模板参数
        @apiName fetch_config_variables
        @apiGroup plugin_v2
        @apiParam {Int[]} config_tpl_ids 配置模板id列表
        @apiParamExample {Json} 请求参数
        {
            "config_tpl_ids": [1, 2]
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "id": 1,
                "name": "bkmonitorbeat.conf",
                "version": "1.0.0",
                "is_main": true,
                "creator": "system",
                "variables": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "title": "tasks",
                            "type": "array",
                            "items": {
                                "title": "task",
                                "type": "object",
                                "properties": {
                                    "bk_biz_id": {
                                        "title": "bk_biz_id",
                                        "_required": true,
                                        "type": "any"
                                    },
                                    "task_list": {
                                        "title": "task_list",
                                        "type": "array",
                                        "items": {
                                            "title": "task",
                                            "type": "object",
                                            "properties": {
                                                "pattern": {
                                                    "title": "pattern",
                                                    "type": "string",
                                                    "_required": true
                                                },
                                                "name": {
                                                    "title": "name",
                                                    "_required": true,
                                                    "type": "any"
                                                }
                                            }
                                        },
                                        "_required": true
                                    },
                                    "labels": {
                                        "title": "labels",
                                        "type": "array",
                                        "items": {
                                            "type": "any"
                                        },
                                        "_required": true
                                    },
                                    "task_id": {
                                        "title": "task_id",
                                        "_required": true,
                                        "type": "any"
                                    },
                                    "target": {
                                        "title": "target",
                                        "_required": true,
                                        "type": "any"
                                    },
                                    "dataid": {
                                        "title": "dataid",
                                        "_required": true,
                                        "type": "any"
                                    },
                                    "path_list": {
                                        "title": "path_list",
                                        "type": "array",
                                        "items": {
                                            "title": "path",
                                            "type": "any"
                                        },
                                        "_required": true
                                    }
                                }
                            },
                            "_required": true
                        },
                        "config_name": {
                            "title": "config_name",
                            "default": "keyword_task",
                            "type": "string"
                        },
                        "config_version": {
                            "title": "config_version",
                            "default": "1.1.1",
                            "type": "string"
                        }
                    }
                }
            },
            {
                "id": 2,
                "name": "bkmonitorbeat.conf",
                "version": "1.0.0",
                "is_main": true,
                "creator": "system",
                "variables": {
                    "type": "object",
                    "properties": {
                        "bk_biz_id": {
                            "title": "bk_biz_id",
                            "_required": true,
                            "type": "any"
                        },
                        "labels": {
                            "title": "labels",
                            "type": "array",
                            "items": {
                                "type": "any"
                            },
                            "_required": true
                        },
                        "task_id": {
                            "title": "task_id",
                            "_required": true,
                            "type": "any"
                        },
                        "config_version": {
                            "title": "config_version",
                            "_required": true,
                            "type": "any"
                        },
                        "max_timeout": {
                            "title": "max_timeout",
                            "default": 100,
                            "type": "number"
                        },
                        "dataid": {
                            "title": "dataid",
                            "_required": true,
                            "type": "any"
                        },
                        "period": {
                            "title": "period",
                            "_required": true,
                            "type": "any"
                        },
                        "min_period": {
                            "title": "min_period",
                            "default": 3,
                            "type": "number"
                        },
                        "command": {
                            "title": "command",
                            "_required": true,
                            "type": "any"
                        },
                        "timeout": {
                            "title": "timeout",
                            "default": 60,
                            "type": "number"
                        },
                        "config_name": {
                            "title": "config_name",
                            "_required": true,
                            "type": "any"
                        }
                    }
                }
            }
        ]
        """
        return Response(PluginV2Handler.fetch_config_variables(self.validated_data["config_tpl_ids"]))

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.PluginOperateSerializer)
    def operate(self, request):
        """
        @api {POST} /v2/plugin/operate/ 插件操作
        @apiName operate_plugin
        @apiGroup plugin_v2
        @apiParam {String} plugin_name 插件名称
        @apiParam {String} job_type 任务类型
        @apiParam {Object} scope 操作范围
        @apiParam {String} [scope.object_type] CMDB对象类型，可选 `SERVICE`, `HOST`，默认取`HOST`
        @apiParam {String} scope.node_type CMDB节点类型，可选 `TOPO`, `INSTANCE`
        @apiParam {Object[]} scope.nodes 节点列表 <br/>
        // object_type=HOST & node_type=TOPO <br/>
        `[{"bk_biz_id": 1, "bk_inst_id": 100, "bk_obj_id": "set"}]` <br/>
        // object_type=HOST & node_type=INSTANCE <br/>
        `[{"bk_biz_id": 1, "bk_host_id": 200}]`

        @apiParam {Object[]} steps 插件安装列表，选择插件更新/安装时必填
        @apiParam {String} steps.id 插件名称，在一个列表中不允许重复
        @apiParam {String} [steps.type] 步骤类型，可选 `AGENT`, `PLUGIN`，默认是`PLUGIN`

        @apiParam {Object[]} steps.configs 步骤配置列表
        @apiParam {Object[]} steps.params 步骤参数列表
        @apiParamExample {Json} 请求例子:
        {
            "name": "yunchao策略",
            "scope": {
                "object_type": "HOST",
                "node_type": "TOPO",
                "nodes": [
                    {"bk_biz_id": 1, "bk_inst_id": 100, "bk_obj_id": "set"},
                    {"bk_biz_id": 2, "bk_inst_id": 10, "bk_obj_id": "module"}
                ]
            },
            "steps": [
                {
                    "id": "yunchao",
                    "type": "PLUGIN",
                    "configs": [
                        {
                            "cpu_arch": "x86_64",
                            "os_type": "linux",
                            "version": "1.0.1",
                            "config_templates": [
                                {"name": "bk.conf", "version": "*", "is_main": True}
                            ]
                        },
                        {
                            "cpu_arch": "x64",
                            "os_type": "windows",
                            "version": "1.0.2",
                            "config_templates": [
                                {"name": "bk.conf", "version": "*"}
                            ]
                        }
                    ],
                    "params": [
                        {
                            "cpu_arch": "x86_64",
                            "os_type": "linux",
                            "port_range": "9102,10000-10005,20103,30000-30100",
                            "context": {
                                "--web.listen-host": "127.0.0.1",
                                "--web.listen-port": "{{ control_info.port }}"
                            }
                        },
                        {
                            "cpu_arch": "x64",
                            "os_type": "windows",
                            "port_range": "9102,10000-10005,20103,30000-30100",
                            "context": {
                                "--web.listen-host": "127.0.0.1",
                                "--web.listen-port": "{{ control_info.port }}"
                            }
                        }
                    ]
                }
            ]
        }
        @apiSuccessExample {json} 成功返回: 策略id
        {
            "job_id": 1
        }
        """
        params = self.validated_data
        return Response(
            PluginV2Handler.operate(
                job_type=params["job_type"],
                plugin_name=params["plugin_name"],
                scope=params["scope"],
                steps=params.get("steps"),
            )
        )

    @action(detail=False, methods=["POST"], serializer_class=plugin_v2.FetchPackageDeployInfoSerializer)
    def fetch_package_deploy_info(self, request):
        """
        @api {POST} /v2/plugin/fetch_package_deploy_info/ 获取插件包部署信息
        @apiName fetch_package_deploy_info
        @apiGroup plugin_v2
        @apiParam {String[]} projects 插件名称列表
        @apiParam {String[]} keys 聚合关键字，可选：os/version/cpu_arch
        @apiParamExample {Json} 请求参数
        {
            "projects": ["bkmonitorbeat", "basereport"],
            "keys": ["os"]
        }
        @apiSuccessExample {json} 返回操作成功的插件id列表:
        {
            "basereport_linux": {"nodes_number": 128025},
            "bkmonitorbeat_linux": {"nodes_number": 128030},
            "basereport_windows": {"nodes_number": 5},
            "bkmonitorbeat_windows": {"nodes_number": 5},
        }
        """
        return Response(
            PluginV2Handler.fetch_package_deploy_info(
                projects=self.validated_data["projects"], keys=["project"] + self.validated_data["keys"]
            )
        )
