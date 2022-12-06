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
from django.test import TestCase

from apps.backend.utils.data_renderer import nested_render_data


class TestDataRenderer(TestCase):
    def test_nested_render_data(self):
        template = """
# 最大超时时间
max_timeout: {{ max_timeout | default(100, true) }}s
# 最小检测间隔
min_period: {{ min_period | default(3, true) }}s

dataid: {{ dataid }}

tasks:
  - task_id: {{ task_id }}
    bk_biz_id: {{ bk_biz_id }}
    # 周期
    period: {{ period }}s
    # 超时
    timeout: {{ timeout | default(60, true) }}s
    module:
      module: prometheus
      metricsets: ["collector"]
      enabled: true
      hosts: ["{{ metric_url }}"]
      metrics_path: ''
      namespace: {{ config_name }}
      dataid: {{ dataid }}
      {% if diff_metrics %}diff_metrics:
      {% for metric in diff_metrics %}- {{ metric }}
      {% endfor %}
      {% endif %}
    {% if labels %}labels:
    {% for lb in labels %}{% for key, value in lb.items() %}{{ "-" if loop.first else " "  }} {{ key }}: "{{ value }}"
    {% endfor %}{% endfor %}
    {% endif %}
"""
        cmdb_instance = {
            "host": {
                "bk_state": None,
                "operator": "admin",
                "bk_biz_id": 2005000194,
                "bk_os_bit": "64-bit",
                "bk_host_id": 2000059046,
                "bk_os_name": "",
                "bk_os_type": "1",
                "bk_agent_id": "",
                "bk_biz_name": "测试业务",
                "bk_cloud_id": 0,
                "bk_isp_name": "0",
                "bk_host_name": "VM-1-158-centos",
                "bk_cloud_name": "直连区域",
                "bk_cpu_module": "Intel(R) Xeon(R) Platinum 8361HC CPU @ 2.60GHz",
                "bk_os_version": "",
                "bk_state_name": None,
                "bk_bak_operator": "admin",
                "bk_host_innerip": "127.0.0.1",
                "bk_host_outerip": "",
                "bk_province_name": None,
                "bk_host_innerip_v6": "",
                "bk_host_outerip_v6": "",
                "bk_supplier_account": "tencent",
            },
            "scope": [
                {"ip": None, "bk_obj_id": "module", "bk_inst_id": 2000027189},
                {"ip": None, "bk_obj_id": "module", "bk_inst_id": 2000027190},
            ],
            "process": {
                "redis": {
                    "user": "mysql",
                    "timeout": None,
                    "pid_file": "",
                    "priority": None,
                    "proc_num": 1,
                    "stop_cmd": "",
                    "bind_info": [
                        {
                            "ip": "127.0.0.1",
                            "port": "30000",
                            "type": "redis",
                            "enable": True,
                            "protocol": "1",
                            "approval_status": "1",
                            "template_row_id": 0,
                        }
                    ],
                    "bk_biz_id": 2005000194,
                    "last_time": "2022-11-18T07:37:53.844Z",
                    "start_cmd": "/usr/local/redis/bin/redis-server",
                    "work_path": "",
                    "auto_start": False,
                    "reload_cmd": "",
                    "create_time": "2022-11-18T07:04:38.503Z",
                    "description": "",
                    "restart_cmd": "",
                    "bk_func_name": "redis",
                    "bk_process_id": 2000044686,
                    "face_stop_cmd": "",
                    "bk_process_name": "redis",
                    "bk_start_check_secs": None,
                    "bk_supplier_account": "tencent",
                    "service_instance_id": 2000026335,
                    "bk_start_param_regex": "127.0.0.1:30000",
                }
            },
            "service": {
                "id": 2000026335,
                "name": "127.0.0.1_redis_30000",
                "labels": {
                    "CMDB_LABEL_1": "something",
                    "CMDB_LABEL_2": "anything",
                },
                "creator": "admin",
                "modifier": "admin",
                "bk_biz_id": 2005000194,
                "last_time": "2022-11-18T07:07:02.733Z",
                "bk_host_id": 2000059046,
                "create_time": "2022-11-18T07:04:38.394Z",
                "bk_module_id": 2000027189,
                "bk_supplier_account": "tencent",
                "service_template_id": 0,
            },
        }
        monitor_context = {
            "host": "127.0.0.1",
            "port": "{{ step_data.redis_exporter_v1450.control_info.listen_port }}",
            "dataid": "1577712",
            "labels": {
                "$for": "cmdb_instance.scope",
                "$body": {
                    "bk_target_ip": "{{ cmdb_instance.host.bk_host_innerip }}",
                    "bk_target_topo_id": "{{ scope.bk_inst_id }}",
                    "bk_target_cloud_id": "{{ cmdb_instance.host.bk_cloud_id[0].id "
                    "if cmdb_instance.host.bk_cloud_id is iterable "
                    "and cmdb_instance.host.bk_cloud_id is not string "
                    "else cmdb_instance.host.bk_cloud_id }}",
                    "bk_collect_config_id": 76,
                    "bk_target_topo_level": "{{ scope.bk_obj_id }}",
                    "bk_target_service_category_id": "{{ cmdb_instance.service.service_category_id "
                    "| default('', true) }}",
                    "bk_target_service_instance_id": "{{ cmdb_instance.service.id }}",
                    "CMDB_LABEL_1": "{{ cmdb_instance.service.labels['CMDB_LABEL_1'] }}",
                    "CMDB_LABEL_2": "{{ cmdb_instance.service.labels['CMDB_LABEL_2'] }}",
                },
                "$item": "scope",
            },
            "period": "60",
            "task_id": "76",
            "timeout": "60",
            "bk_biz_id": "2005000194",
            "namespace": "redis_exporter_v1450",
            "metric_url": "127.0.0.1:{{ step_data.redis_exporter_v1450.control_info.listen_port }}/metrics",
            "config_name": "redis_exporter_v1450",
            "max_timeout": "60",
            "diff_metrics": [],
            "config_version": "1.0",
        }

        nodeman_context = {
            "cmdb_instance": cmdb_instance,
            "target": cmdb_instance,
            "step_data": {"redis_exporter_v1450": {"control_info": {"listen_port": 7000}}},
        }
        rendered_monitor_context = nested_render_data(monitor_context, nodeman_context)
        nodeman_context.update(rendered_monitor_context)

        content = nested_render_data(template, nodeman_context)
        # 注意，由于在三引号（"""）的包裹中，一行内如果是纯空格会被忽略，造成断言失败，因此通过 \n 的方式书写 expect_content
        expect_content = """
# 最大超时时间
max_timeout: 60s
# 最小检测间隔
min_period: 3s

dataid: 1577712

tasks:
  - task_id: 76
    bk_biz_id: 2005000194
    # 周期
    period: 60s
    # 超时
    timeout: 60s
    module:
      module: prometheus
      metricsets: ["collector"]
      enabled: true
      hosts: ["127.0.0.1:7000/metrics"]
      metrics_path: \'\'
      namespace: redis_exporter_v1450
      dataid: 1577712
      \n    labels:
    - bk_target_ip: "127.0.0.1"
      bk_target_topo_id: "2000027189"
      bk_target_cloud_id: "0"
      bk_collect_config_id: "76"
      bk_target_topo_level: "module"
      bk_target_service_category_id: ""
      bk_target_service_instance_id: "2000026335"
      CMDB_LABEL_1: "something"
      CMDB_LABEL_2: "anything"
    - bk_target_ip: "127.0.0.1"
      bk_target_topo_id: "2000027190"
      bk_target_cloud_id: "0"
      bk_collect_config_id: "76"
      bk_target_topo_level: "module"
      bk_target_service_category_id: ""
      bk_target_service_instance_id: "2000026335"
      CMDB_LABEL_1: "something"
      CMDB_LABEL_2: "anything"
    \n    """
        self.assertEqual(content, expect_content)
