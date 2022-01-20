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
from apps.node_man import models
from apps.node_man.handlers.permission import PolicyPermission
from apps.node_man.handlers.policy import PolicyHandler
from apps.node_man.serializers import policy
from common.api import NodeApi


class PolicyViewSet(ModelViewSet):
    model = models.Subscription
    queryset = None
    permission_classes = (PolicyPermission,)

    def retrieve(self, request, *args, **kwargs):
        """
        @api {GET} /policy/{{pk}}/ 策略详细
        @apiName policy_info
        @apiGroup policy
        @apiSuccessExample {json} 成功返回:
        {
            "subscription_id": 1,
            "name": "yunchao策略",
            "plugin_info": {
                "id": 1,
                "name": "yunchao",
                "description": "yunchao",
                "source_app_code": "test_app",
                "category": "官方插件",
                "deploy_type": "整包部署"
            }
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
                            "nodes_number": 10,
                            "config_templates": [
                                {"name": "bk.conf", "version": "*", "is_main": True}
                            ]
                        },
                        {
                            "cpu_arch": "x64",
                            "os_type": "windows",
                            "version": "1.0.2",
                            "nodes_number": 15,
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
        """
        return Response(PolicyHandler.policy_info(kwargs["pk"]))

    def update(self, request, *args, **kwargs):
        """
        @api {PUT} /policy/{{pk}}/  编辑策略概要信息
        @apiName update_policy_info
        @apiGroup policy
        @apiParam {String} name 策略名称
        @apiParamExample {Json} 请求参数
        {
            "name": "策略名称1",
        }
        """
        self.serializer_class = policy.SimpleUpdatePolicySerializer
        PolicyHandler.update_policy_info(
            username=request.user.username, policy_id=kwargs["pk"], update_data=self.validated_data
        )
        return Response({})

    @action(detail=False, methods=["POST"], serializer_class=policy.SearchDeployPolicySerializer)
    def search(self, request):
        """
        @api {POST} /policy/search/ 查询策略列表
        @apiName list_policy
        @apiGroup policy
        @apiParam {Int[]} [bk_biz_ids] 业务ID列表, 不传取全业务
        @apiParam {Object[]} [conditions] 查询条件
        @apiParam {String} [conditions.key] 查询关键字，`query`表示多字段模糊搜索，目前仅支持`name`, `plugin_name` <br/>
        `key`为`plugin_name`, `name` 表示对相应字段的精确查询
        @apiParam {String[]} [conditions.value] 查询值，单值查询
        @apiParam {object} [sort] 排序
        @apiParam {String=["name", "plugin_name", "creator", "update_time", "nodes_scope", "bk_biz_scope"]} ...
        [sort.head] 排序字段
        @apiParam {String=["ASC", "DEC"]} [sort.sort_type] 排序类型
        @apiParam {Int} [page] 当前页数
        @apiParam {Int} [pagesize] 分页大小
        @apiSuccessExample {json} 成功返回:
        {
            "total": 10,
            "list": [
                {
                    "id": 1097,
                    "name": "蓝鲸监控",
                    "plugin_name": "bkmonitorbeat",
                    "bk_biz_scope": [{"bk_biz_id": 2, "bk_biz_name": "蓝鲸"}],
                    "update_time": "2021-05-28 16:10:47+0800",
                    "creator": "admin",
                    "enable": True,
                    "children": [
                        {
                            "id": 1085,
                            "name": "蓝鲸监控单主机",
                            "plugin_name": "bkmonitorbeat",
                            "bk_biz_scope": [{"bk_biz_id": 2, "bk_biz_name": "蓝鲸"}],
                            "update_time": "2021-05-31 12:12:14+0800",
                            "creator": "admin",
                            "enable": False,
                            "pid": 1097,
                            "configs": [{"os": "linux", "cpu_arch": "x86_64", "version": "1.12.92"}],
                            "need_to_upgrade": False,
                            "permissions": {"edit": True},
                            "job_result": {
                                "task": {
                                    "id": 683028, "subscription_id": 1085, "is_ready": True, "is_auto_trigger": False
                                },
                                "job_id": 1138,
                                "is_auto_trigger": False,
                                "status": "SUCCESS",
                                "type": "PLUGIN",
                                "step_type": "PLUGIN",
                                "op_type": "INSTALL",
                                "op_type_display": "安装",
                                "step_type_display": "插件",
                            },
                            "associated_host_num": 1
                        }
                    ],
                    "configs": [
                        {"os": "windows", "cpu_arch": "x86_64", "version": "1.12.92"},
                        {"os": "linux", "cpu_arch": "x86_64", "version": "1.12.92"},
                    ],
                    "need_to_upgrade": False,
                    "permissions": {"edit": True},
                    "job_result": {
                        "task": {"id": 683081, "subscription_id": 1097, "is_ready": True, "is_auto_trigger": False},
                        "job_id": 1177,
                        "is_auto_trigger": True,
                        "status": "PART_FAILED",
                        "type": "PLUGIN",
                        "step_type": "PLUGIN",
                        "op_type": "START",
                        "op_type_display": "启动",
                        "step_type_display": "插件",
                    },
                    "associated_host_num": 7
                }
            ]
        }
        """
        return Response(PolicyHandler.search_deploy_policy(query_params=self.validated_data))

    @action(detail=False, methods=["GET"])
    def fetch_common_variable(self, request):
        """
        @api {GET} /policy/fetch_common_variable/ 获取公共变量
        @apiName fetch_common_variable
        @apiGroup policy
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 成功返回:
        {
            "linux": [
                {
                    "key": "{{control_info.gse_agent_home}}",
                    "value": "/data/gse/home",
                    "description": "我是描述"
                },
                {
                    "key": "{{control_info.log_path}}",
                    "value": "/data/log",
                    "description": "我是描述"
                }
            ],
            "windows": [
                {
                    "key": "{{control_info.gse_agent_home}}",
                    "value": "\\data\\gse\\home",
                    "description": "我是描述"
                },
                {
                    "key": "{{control_info.log_path}}",
                    "value": "\\data\\log",
                    "description": "我是描述"
                }
            ]
        }
        """

        return Response(
            {
                "linux": [
                    {"key": "{{control_info.gse_agent_home}}", "value": "/data/gse/home", "description": "我是描述"},
                    {"key": "{{control_info.log_path}}", "value": "/data/log", "description": "我是描述"},
                ],
                "windows": [
                    {"key": "{{control_info.gse_agent_home}}", "value": "\\data\\gse\\home", "description": "我是描述"},
                    {"key": "{{control_info.log_path}}", "value": "\\data\\log", "description": "我是描述"},
                ],
            }
        )

    @action(detail=False, methods=["POST"], serializer_class=policy.FetchPolicyTopoSerializer)
    def fetch_policy_topo(self, request):
        """
        @api {POST} /policy/fetch_policy_topo/ 插件策略拓扑
        @apiName fetch_policy_topo
        @apiGroup policy
        @apiParam {Int[]} [bk_biz_ids] 业务ID列表, 不传取全业务
        @apiParam {String} [plugin_name] 插件名称
        @apiParam {String} [keyword] 关键字
        @apiParam {Boolean} [is_lazy] 是否采取懒加载策略（仅返回一级节点），默认为False
        @apiSuccessExample {json} 成功返回:
        [
            {
                "id": "basereport",
                "name": "basereport",
                "type": "plugin",
                "children": [{"id": 1140, "name": "测试哈哈哈哈哈哈", "type": "policy"}]
            },
            {
                "id": "bkmonitorbeat",
                "name": "bkmonitorbeat",
                "type": "plugin",
                "children": [{"id": 1146, "name": "测试任务历史耗时", "type": "policy"}]
            }
        ]
        """
        return Response(
            PolicyHandler.fetch_policy_topo(
                bk_biz_ids=self.validated_data.get("bk_biz_ids"),
                plugin_name=self.validated_data.get("plugin_name"),
                keyword=self.validated_data.get("keyword"),
                is_lazy=self.validated_data["is_lazy"],
            )
        )

    @action(detail=False, methods=["POST"], serializer_class=policy.SelectReviewSerializer)
    def selected_preview(self, request):
        """
        @api {POST} /policy/selected_preview/ 策略执行预览（预览所选范围）
        @apiName policy_preview
        @apiGroup policy
        @apiParam {List} [conditions] 搜索条件，支持os_type, ip, status, version, bk_cloud_id, node_from <br>
        query: IP、操作系统、Agent状态、Agent版本、云区域 单/多模糊搜索 <br>
        topology: 拓扑搜索，传入bk_set_ids, bk_module_ids
        @apiParam {Int} [page] 当前页数，默认为`1`
        @apiParam {Int} [pagesize] 分页大小，默认为`10`

        @apiParam {Int} [policy_id] 策略ID，`scope`、`policy_id`必须传入一个，同传时优先使用`policy_id`
        @apiParam {Boolean} [with_hosts] 对于TOPO创建的订阅，with_hosts = `true`时顺带返回TOPO下所有主机的信息，默认是`true`
        @apiParam {Object} [scope] 策略范围
        @apiParam {String} [scope.object_type] CMDB对象类型，可选 `SERVICE`, `HOST`，默认取`HOST`
        @apiParam {String} scope.node_type CMDB节点类型，可选 `TOPO`, `INSTANCE`
        @apiParam {Object[]} scope.nodes 节点列表 <br/>
        // object_type=HOST & node_type=TOPO <br/>
        `[{"bk_biz_id": 1, "bk_inst_id": 100, "bk_obj_id": "set"}]` <br/>
        // object_type=HOST & node_type=INSTANCE <br/>
        `[{"bk_biz_id": 1, "bk_host_id": 200}]`

        @apiParam {Object[]} [steps] 插件安装列表
        @apiParam {String} steps.id 插件名称，在一个列表中不允许重复
        @apiParam {String} [steps.type] 步骤类型，可选 `AGENT`, `PLUGIN`，默认是`PLUGIN`

        @apiParam {Object[]} steps.configs 步骤配置列表
        @apiParam {Object[]} steps.params 步骤参数列表
        @apiSuccessExample {json} 成功返回:
        {
            // 部署实例为TOPO时展示
            "nodes": [
                {
                    "bk_biz_id": 2,
                    "bk_inst_id": 10,
                    "bk_obj_id": "custom",
                    "bk_inst_name": "自定义层级节点"
                },
                {
                    "bk_biz_id": 3,
                    "bk_inst_id": 3,
                    "bk_obj_id": "biz"
                    "bk_inst_name": "我是一个业务节点"
                }
            ],
            // with_hosts=true时展示
            "total": 188,
            "list": [
                {
                    "bk_host_id": 1,
                    "inner_ip": "127.0.0.1",
                    "bk_cloud_id": 1,
                    "bk_biz_id": 1,
                    "bk_cloud_name": "嘿嘿",
                    "bk_biz_name": "王者荣耀",
                    "os_type": "LINUX",
                    "cpu_arch": "x86",
                    "status": "RUNNING",
                    "current_version": "1.0.0",
                    "target_version": "2.0.0"
                },
                {
                    "bk_host_id": 2,
                    "inner_ip": "127.0.0.2",
                    "bk_cloud_id": 2,
                    "bk_biz_id": 2,
                    "bk_cloud_name": "哈哈",
                    "bk_biz_name": "和平精英",
                    "cpu_arch": "x86_64",
                    "os_type": "WINDOWS",
                    "status": "TERMINATED",
                    "current_version": "1.0.0",
                    "target_version": "2.0.0"
                },
            ]
        }
        """
        return Response(PolicyHandler.selected_preview(query_params=self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=policy.MigratePreviewSerializer)
    def migrate_preview(self, request):
        """
        @api {POST} /policy/migrate_preview/ 策略执行预览（计算变更详情）
        @apiName migrate_preview
        @apiGroup policy
        @apiParam {Int} [policy_id] 策略ID，`scope`、`policy_id`必须传入一个，同传时优先使用`policy_id`
        @apiParam {String} [category] 订阅类型，可选 `policy`, `once`，默认取`policy`
        @apiParam {Object} [scope] 策略范围
        @apiParam {String} [scope.object_type] CMDB对象类型，可选 `SERVICE`, `HOST`，默认取`HOST`
        @apiParam {String} scope.node_type CMDB节点类型，可选 `TOPO`, `INSTANCE`
        @apiParam {Object[]} scope.nodes 节点列表 <br/>
        // object_type=HOST & node_type=TOPO <br/>
        `[{"bk_biz_id": 1, "bk_inst_id": 100, "bk_obj_id": "set"}]` <br/>
        // object_type=HOST & node_type=INSTANCE <br/>
        `[{"bk_biz_id": 1, "bk_host_id": 200}]`

        @apiParam {Object[]} [steps] 插件安装列表
        @apiParam {String} steps.id 插件名称，在一个列表中不允许重复
        @apiParam {String} [steps.type] 步骤类型，可选 `AGENT`, `PLUGIN`，默认是`PLUGIN`

        @apiParam {Object[]} steps.configs 步骤配置列表
        @apiParam {Object[]} steps.params 步骤参数列表
        @apiSuccessExample {json} 成功返回:
        [
            {
                "action_id": "MAIN_INSTALL_PLUGIN",
                "action_name": "安装插件",
                "list": [
                    {
                        "ip": "127.0.0.1",
                        "bk_cloud_id": 1,
                        "bk_biz_id": 2,
                        "migrate_reason": {
                            "migrate_type": "",
                            "current_version": "10.7.32",
                            "target_version": "10.7.33"
                        },
                        "bk_biz_name": "蓝鲸",
                        "bk_cloud_name": "云区域名称"
                    }
                ]
            },
            {
                "action_id": "MAIN_STOP_PLUGIN",
                "action_name": "停止插件",
                "list": [
                    {
                        "ip": "127.0.0.1",
                        "bk_cloud_id": 0,
                        "bk_biz_id": 3,
                        "migrate_reason": {},
                        "bk_biz_name": "job_test",
                        "bk_cloud_name": "直连区域"
                    }
                ]
            },
            {
                "action_id": "IGNORED",
                "action_name": "IGNORED",
                "list": [
                    {
                        "ip": "127.0.0.1",
                        "bk_biz_name": null,
                        "bk_cloud_id": 0,
                        "bk_cloud_name": "直连区域",
                        "msg": "当前部署策略(层级biz)已被策略[主机策略(ID:1057)](层级host)抑制"
                    }
                ]
            }
        ]
        """
        return Response(PolicyHandler.migrate_preview(query_params=self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=policy.CreatePolicySerializer)
    def create_policy(self, request):
        """
        @api {POST} /policy/create_policy/ 创建策略
        @apiName create_policy
        @apiGroup policy
        @apiParam {Object} scope 策略范围
        @apiParam {String} [scope.object_type] CMDB对象类型，可选 `SERVICE`, `HOST`，默认取`HOST`
        @apiParam {String} scope.node_type CMDB节点类型，可选 `TOPO`, `INSTANCE`
        @apiParam {Object[]} scope.nodes 节点列表 <br/>
        // object_type=HOST & node_type=TOPO <br/>
        `[{"bk_biz_id": 1, "bk_inst_id": 100, "bk_obj_id": "set"}]` <br/>
        // object_type=HOST & node_type=INSTANCE <br/>
        `[{"bk_biz_id": 1, "bk_host_id": 200}]`

        @apiParam {Object[]} steps 插件安装列表
        @apiParam {String} steps.id 插件名称，在一个列表中不允许重复
        @apiParam {String} [steps.type] 步骤类型，可选 `AGENT`, `PLUGIN`，默认是`PLUGIN`

        @apiParam {Object[]} steps.configs 步骤配置列表
        @apiParam {Object[]} steps.params 步骤参数列表
        @apiParam {Object[]} [pid] 父策略ID，默认创建父策略
        @apiParamExample {Json} 请求例子:
        {
            "pid": 100,
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
        return Response(PolicyHandler.create_deploy_policy(self.validated_data))

    @action(detail=True, methods=["POST"], serializer_class=policy.CreatePolicySerializer)
    def update_policy(self, request, pk):
        """
        @api {POST} /policy/{{pk}}/update_policy/ 更新策略
        @apiName update_policy
        @apiGroup policy
        @apiParam {Object} scope 策略范围
        @apiParam {String} [scope.object_type] CMDB对象类型，可选 `SERVICE`, `HOST`，默认取`HOST`
        @apiParam {String} scope.node_type CMDB节点类型，可选 `TOPO`, `INSTANCE`
        @apiParam {Object[]} scope.nodes 节点列表 <br/>
        // object_type=HOST & node_type=TOPO <br/>
        `[{"bk_biz_id": 1, "bk_inst_id": 100, "bk_obj_id": "set"}]` <br/>
        // object_type=HOST & node_type=INSTANCE <br/>
        `[{"bk_biz_id": 1, "bk_host_id": 200}]`

        @apiParam {Object[]} steps 插件安装列表
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
        @apiSuccessExample {json} 成功返回:
        {
            "job_id": 1
        }
        """
        return Response(PolicyHandler.update_policy(update_data=self.validated_data, policy_id=pk))

    @action(detail=True, methods=["GET"])
    def upgrade_preview(self, request, pk):
        """
        @api {GET} /policy/{{pk}}/upgrade_preview/ 升级预览
        @apiName upgrade_preview
        @apiGroup policy
        @apiSuccessExample {json} 成功返回:
        [
            {
                "cpu_arch": "x86",
                "os": "linux",
                "latest_version": "1.10.32",
                "current_version_list": [
                    {
                        "cpu_arch": "x86",
                        "os": "linux",
                        "current_version": "1.10.32",
                        "nodes_number": 1
                    },
                    {
                        "cpu_arch": "x86",
                        "os": "linux",
                        "current_version": "1.11.35",
                        "nodes_number": 3
                    }
                ],
                "is_latest": true
            },
            {
                "cpu_arch": "x86",
                "os": "linux",
                "latest_version": "1.10.32",
                "current_version_list": [
                    {
                        "cpu_arch": "x86",
                        "os": "linux",
                        "current_version": "1.0.0",
                        "nodes_number": 11
                    }
                ],
                "is_latest": false,
                "version_scenario": "processbeat: 主机进程信息采集器 - V1.10.32"
            }
        ]
        """
        return Response(PolicyHandler.upgrade_preview(policy_id=pk))

    @action(detail=False, methods=["POST"], serializer_class=policy.PluginPreSelectionSerializer)
    def plugin_preselection(self, request):
        """
        @api {POST} /policy/plugin_preselection/ plugin_preselection
        @apiName policy_preselection
        @apiGroup policy
        """
        return Response(
            PolicyHandler.plugin_preselection(
                plugin_id=self.validated_data["plugin_id"], scope=self.validated_data["scope"]
            )
        )

    @action(detail=False, methods=["GET"], serializer_class=policy.HostPolicySerializer)
    def host_policy(self, request):
        """
        @api {GET} /policy/host_policy/ 主机策略列表
        @apiDescription 根据host_id查询对应的所有策略
        @apiName host_policy
        @apiGroup policy
        @apiSuccessExample {json} 成功返回:
        [
            {
                "name": "测试任务",
                "plugin_name": "processbeat",
                "auto_trigger": true,
                "plugin_version": "1.0.1",
                "status": "FAILED",
                "update_time": "2020-08-28 15:00:12+0800"
            }
        ]
        """
        # todo 支持业务查询
        bk_host_id = self.validated_data["bk_host_id"]
        result = NodeApi.query_host_policy({"bk_host_id": bk_host_id})
        return Response(result)

    @action(detail=False, methods=["POST"], serializer_class=policy.PolicyOperateSerializer)
    def operate(self, request):
        """
        @api {POST} /policy/operate/ 策略操作
        @apiDescription 策略操作，停用/停用并删除/启用
        @apiName policy_operate
        @apiGroup policy
        @apiParam {Int} policy_id 策略ID
        @apiParam {String} op_type 策略操作类型 "START", "STOP", "STOP_AND_DELETE", "DELETE"
        @apiParam {Boolean} [only_disable] 仅停用策略，保持插件运行
        @apiSuccessExample {json} 成功返回:
        {
            "job_id": 1,
            "subscription_id": 1,
            "task_id": 2
        }
        """
        return Response(
            PolicyHandler.policy_operate(
                self.validated_data["policy_id"], self.validated_data["op_type"], self.validated_data["only_disable"]
            )
        )

    @action(detail=False, methods=["POST"], serializer_class=policy.RollbackPreview)
    def rollback_preview(self, request):
        """
        @api {POST} /policy/rollback_preview/ 策略回滚预览
        @apiDescription 策略回滚预览
        @apiName rollback_preview
        @apiGroup policy
        @apiParam {Int} policy_id 策略ID
        @apiParam {List} [conditions] 搜索条件，支持os_type, ip, status, version, bk_cloud_id, node_from <br>
        query: IP、操作系统、Agent状态、Agent版本、云区域 单/多模糊搜索 <br>
        topology: 拓扑搜索，传入bk_set_ids, bk_module_ids
        @apiParam {Int} [page] 当前页数，默认为`1`
        @apiParam {Int} [pagesize] 分页大小，默认为`10`
        @apiSuccessExample {json} 成功返回:
        [
            {
                "status": "RUNNING",
                "bk_cloud_id": 0,
                "bk_biz_id": 2,
                "bk_host_id": 4,
                "os_type": "LINUX",
                "inner_ip": "127.0.0.1",
                "cpu_arch": "x86_64",
                "bk_cloud_name": "直连区域",
                "bk_biz_name": "蓝鲸",
                "bk_host_innerip": "127.0.0.1",
                "target_policy": {
                  "id": 1124,
                  "name": "basereport-蓝鲸",
                  "bk_obj_id": "biz",
                  "type": "TRANSFER_TO_ANOTHER",
                  "msg": "转移到优先级最高的策略"
                }
            }
        ]
        """
        return Response(PolicyHandler.rollback_preview(self.validated_data["policy_id"], self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=policy.FetchPolicyAbnormalInfoSerializer)
    def fetch_policy_abnormal_info(self, request):
        """
        @api {POST} /policy/fetch_policy_abnormal_info/ 获取策略异常信息
        @apiDescription 获取策略异常信息
        @apiName fetch_policy_abnormal_info
        @apiGroup policy
        @apiParam {Int[]} policy_ids 策略ID列表
        @apiSuccessExample {json} 成功返回:
        {
            "1": {"abnormal_host_ids": [4, 5], "abnormal_host_count": 2},
            "2": {"abnormal_host_ids": [1, 10], "abnormal_host_count": 2}
        }
        """
        policy_ids = self.validated_data["policy_ids"]
        return Response(PolicyHandler.fetch_policy_abnormal_info(policy_ids=policy_ids))
