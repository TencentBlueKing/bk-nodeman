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

SUBSCRIPTION_INFO_RESPONSE = [
    {
        "id": 1521,
        "name": "string",
        "enable": False,
        "category": "once",
        "plugin_name": "",
        "bk_biz_scope": [],
        "scope": {
            "bk_biz_id": 2,
            "object_type": "SERVICE",
            "node_type": "TOPO",
            "nodes": [
                {"bk_host_id": 12},
                {"bk_obj_id": "module", "bk_inst_id": 33},
                {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0},
                {
                    "ip": "127.0.0.1",
                    "bk_cloud_id": 1,
                    "instance_info": {
                        "key": "",
                        "port": 22,
                        "ap_id": 1,
                        "account": "root",
                        "os_type": "LINUX",
                        "login_ip": "127.0.0.1",
                        "password": "UWs9",
                        "username": "admin",
                        "auth_type": "PASSWORD",
                        "bk_biz_id": 337,
                        "data_path": "/var/lib/gse",
                        "is_manual": False,
                        "retention": -1,
                        "bk_os_type": "1",
                        "bk_biz_name": "xxxxxx",
                        "bk_cloud_id": 1,
                        "bk_cloud_name": "xxxx",
                        "bt_speed_limit": "",
                        "host_node_type": "PROXY",
                        "bk_host_innerip": "127.0.0.1",
                        "bk_host_outerip": "127.0.0.1",
                        "install_channel_id": 1,
                        "bk_supplier_account": "0",
                        "peer_exchange_switch_for_agent": 1,
                    },
                    "bk_supplier_account": "0",
                },
            ],
        },
        "pid": -1,
        "target_hosts": [{"ip": "127.0.0.1", "bk_cloud_id": "0", "bk_supplier_id": "0"}],
        "steps": [
            {
                "id": "agent",
                "type": "AGENT",
                "config": {"job_type": "INSTALL_AGENT"},
                "params": {"context": {}, "blueking_language": "zh-hans"},
            },
            {
                "id": "main:bkunifylogbeat",
                "type": "PLUGIN",
                "config": {
                    "job_type": "MAIN_INSTALL_PLUGIN",
                    "plugin_name": "bkunifylogbeat",
                    "check_and_skip": True,
                    "plugin_version": "latest",
                    "config_templates": [{"name": "bkunifylogbeat.conf", "is_main": True, "version": "latest"}],
                    "is_version_sensitive": False,
                },
                "params": {"context": {}},
            },
            {
                "id": "mysql_exporter",
                "type": "PLUGIN",
                "config": {
                    "plugin_name": "mysql_exporter",
                    "plugin_version": "2.3",
                    "config_templates": [
                        {"os": "windows", "name": "config.yaml", "version": "2", "cpu_arch": "x86_64"},
                        {"os": "windows", "name": "env.yaml", "version": "2", "cpu_arch": "x86_64"},
                    ],
                },
                "params": {
                    "context": {"--web.listen-host": "127.0.0.1", "--web.listen-port": "{{ control_info.port }}"},
                    "port_range": "9102,10000-10005,20103,30000-30100",
                },
            },
            {
                "id": "bkmonitorbeat",
                "type": "PLUGIN",
                "config": {
                    "plugin_name": "bkmonitorbeat",
                    "plugin_version": "1.7.0",
                    "config_templates": [{"name": "bkmonitorbeat_exporter.yaml", "version": "1"}],
                },
                "params": {
                    "context": {
                        "labels": {
                            "$for": "cmdb_instance.scopes",
                            "$body": {
                                "bk_target_ip": "{{ cmdb_instance.host.bk_host_innerip }}",
                                "bk_target_topo_id": "{{ scope.bk_inst_id }}",
                                "bk_target_cloud_id": "{{ cmdb_instance.host.bk_cloud_id }}",
                                "bk_collect_config_id": 1,
                                "bk_target_topo_level": "{{ scope.bk_obj_id }}",
                                "bk_target_service_category_id": "{{ cmdb_instance.service.service_category_id }}",
                                "bk_target_service_instance_id": "{{ cmdb_instance.service.id }}",
                            },
                            "$item": "scope",
                        },
                        "metrics_url": "XXX",
                    }
                },
            },
        ],
    }
]


SUBSCRIPTION_CREATE_RESPONSE = {"subscription_id": 1, "task_id": 1}
SUBSCRIPTION_RETRY_RESPONSE = {"task_id": 1}
SUBSCRIPTION_TASK_RESULT_RESPONSE = {
    "data": {
        "total": 1,
        "list": [
            {
                "task_id": 1,
                "record_id": 1,
                "instance_id": "host|instance|host|127.0.0.1-0-0",
                "create_time": "2020-12-23 16:46:01",
                "pipeline_id": "149cb17976da4040b75523d495886b3d",
                "start_time": "2020-12-23 16:46:01",
                "finish_time": "2020-12-23 16:47:08",
                "instance_info": {
                    "host": {
                        "bk_biz_id": 4,
                        "bk_host_id": 1,
                        "bk_biz_name": "测试业务",
                        "bk_cloud_id": 0,
                        "bk_cloud_name": "直连区域",
                        "bk_host_innerip": "127.0.0.1",
                        "bk_supplier_account": "0",
                    },
                    "service": {},
                },
                "status": "SUCCESS",
                "steps": [
                    {
                        "id": "agent",
                        "type": "AGENT",
                        "action": "INSTALL_AGENT",
                        "extra_info": {},
                        "pipeline_id": "ac9db1d43b5d438886f08ad8c771005e",
                        "finish_time": "2020-12-23 16:47:08",
                        "start_time": "2020-12-23 16:46:01",
                        "create_time": "2020-12-23 16:46:01",
                        "status": "SUCCESS",
                        "node_name": "[agent] 安装",
                        "step_code": None,
                        "target_hosts": [
                            {
                                "pipeline_id": "d7e4d0e1235941609b4367114dcfe029",
                                "node_name": "[INSTALL_AGENT] 安装 0:127.0.0.1",
                                "sub_steps": [
                                    {
                                        "pipeline_id": "913dc70fd5844639b8d72c9d3d7717fc",
                                        "index": 0,
                                        "node_name": "注册主机到配置平台",
                                        "finish_time": "2020-12-23 16:46:01",
                                        "start_time": "2020-12-23 16:46:01",
                                        "create_time": "2020-12-23 16:46:01",
                                        "status": "SUCCESS",
                                    },
                                    {
                                        "pipeline_id": "e8a16636b1f94640aa3928f19ef87eb9",
                                        "index": 1,
                                        "node_name": "选择接入点",
                                        "finish_time": "2020-12-23 16:46:01",
                                        "start_time": "2020-12-23 16:46:01",
                                        "create_time": "2020-12-23 16:46:01",
                                        "status": "SUCCESS",
                                    },
                                    {
                                        "pipeline_id": "b99c6872c3eb4c479423514f2d3b00ec",
                                        "index": 2,
                                        "node_name": "安装",
                                        "finish_time": "2020-12-23 16:46:32",
                                        "start_time": "2020-12-23 16:46:01",
                                        "create_time": "2020-12-23 16:46:01",
                                        "status": "SUCCESS",
                                    },
                                    {
                                        "pipeline_id": "d7f55570fe714c28b7cca56064833be9",
                                        "index": 3,
                                        "node_name": "查询Agent状态",
                                        "finish_time": "2020-12-23 16:46:52",
                                        "start_time": "2020-12-23 16:46:32",
                                        "create_time": "2020-12-23 16:46:01",
                                        "status": "SUCCESS",
                                    },
                                    {
                                        "pipeline_id": "d17003f106a64d88b8038e77ea9db29b",
                                        "index": 4,
                                        "node_name": "托管 processbeat 插件进程",
                                        "finish_time": "2020-12-23 16:46:58",
                                        "start_time": "2020-12-23 16:46:52",
                                        "create_time": "2020-12-23 16:46:01",
                                        "status": "SUCCESS",
                                    },
                                    {
                                        "pipeline_id": "81aeb52bb37945788b3d254979854651",
                                        "index": 5,
                                        "node_name": "托管 exceptionbeat 插件进程",
                                        "finish_time": "2020-12-23 16:47:03",
                                        "start_time": "2020-12-23 16:46:58",
                                        "create_time": "2020-12-23 16:46:01",
                                        "status": "SUCCESS",
                                    },
                                    {
                                        "pipeline_id": "53a5644de57c4c818fef2e38227aebc2",
                                        "index": 6,
                                        "node_name": "托管 basereport 插件进程",
                                        "finish_time": "2020-12-23 16:47:08",
                                        "start_time": "2020-12-23 16:47:03",
                                        "create_time": "2020-12-23 16:46:01",
                                        "status": "SUCCESS",
                                    },
                                    {
                                        "pipeline_id": "54a91fb0720f47c59fea2dfbf64f4d77",
                                        "index": 7,
                                        "node_name": "更新任务状态",
                                        "finish_time": "2020-12-23 16:47:08",
                                        "start_time": "2020-12-23 16:47:08",
                                        "create_time": "2020-12-23 16:46:01",
                                        "status": "SUCCESS",
                                    },
                                ],
                                "finish_time": "2020-12-23 16:47:08",
                                "start_time": "2020-12-23 16:46:01",
                                "create_time": "2020-12-23 16:46:01",
                                "status": "SUCCESS",
                            }
                        ],
                    }
                ],
            }
        ],
        "status_counter": {"SUCCESS": 1, "total": 1},
    }
}
