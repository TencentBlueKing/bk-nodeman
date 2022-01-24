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

config_tpl_1 = """
#================================ Outputs =====================================
output.bkpipe:
  endpoint: {{ plugin_path.endpoint }}
  synccfg: true
path.logs: {{ plugin_path.log_path }}
path.data: {{ plugin_path.data_path }}
path.pid: {{ plugin_path.pid_path }}

#================================ Logging ======================================
# Available log levels are: critical, error, warning, info, debug
logging.level: error

logging.to_files: true
logging.files:
max_procs: 1


############################# bkmonitorbeat ######################################
bkmonitorbeat:
  node_id: 0
  ip: 127.0.0.1
  bk_cloud_id: 0
  # 主机CMDB信息hostid文件路径
  host_id_path: {{ plugin_path.host_id }}
  # 子任务目录
  include: {{ plugin_path.subconfig_path }}
  # 当前节点所属业务
  bk_biz_id: 1
  # stop/reload旧任务清理超时
  clean_up_timeout: 1s
  # 事件管道缓冲大小
  event_buffer_size: 10
  # 启动模式：daemon（正常模式）,check（执行一次，测试用）
  mode: daemon

  #### heart_beat config #####
  # 心跳配置
  heart_beat:
    global_dataid: 1100001
    child_dataid: 1100002
    period: 60s
    publish_immediately: true

  #### tcp_task child config #####
  # tcp任务全局设置
  #  tcp_task:
  #    dataid: 101176
  #    # 缓冲区最大空间
  #    max_buffer_size: 10240
  #    # 最大超时时间
  #    max_timeout: 30s
  #    # 最小检测间隔
  #    min_period: 3s
  #    # 任务列表
  #    tasks:
  #      - task_id: 1
  #        bk_biz_id: 1
  #        period: 60s
  #        # 检测超时（connect+read总共时间）
  #        timeout: 3s
  #        target_host: 127.0.0.1
  #        target_port: 9202
  #        available_duration: 3s
  #        # 请求内容
  #        request: hi
  #        # 请求格式（raw/hex）
  #        request_format: raw
  #        # 返回内容
  #        response: hi
  #        # 内容匹配方式
  #        response_format: eq

  #### udp_task child config #####
  #  udp_task:
  #    dataid: 0
  #    # 缓冲区最大空间
  #    max_buffer_size: 10240
  #    # 最大超时时间
  #    max_timeout: 30s
  #    # 最小检测间隔
  #    min_period: 3s
  #    # 最大重试次数
  #    max_times: 3
  #    # 任务列表
  #    tasks:
  #      - task_id: 5
  #        bk_biz_id: 1
  #        times: 3
  #        period: 60s
  #        # 检测超时（connect+read总共时间）
  #        timeout: 3s
  #        target_host: 127.0.0.1
  #        target_port: 9201
  #        available_duration: 3s
  #        # 请求内容
  #        request: hello
  #        # 请求格式（raw/hex）
  #        request_format: raw
  #        # 返回内容
  #        response: hello
  #        # 内容匹配方式
  #        response_format: eq

  #### http_task child config #####
  #  http_task:
  #    dataid: 0
  #    # 缓冲区最大空间
  #    max_buffer_size: 10240
  #    # 最大超时时间
  #    max_timeout: 30s
  #    # 最小检测间隔
  #    min_period: 3s
  #    # 任务列表
  #    tasks:
  #      - task_id: 5
  #        bk_biz_id: 1
  #        period: 60s
  #        # proxy: http://proxy.qq.com:8000
  #        # 是否校验证书
  #        insecure_skip_verify: false
  #        disable_keep_alives: false
  #        # 检测超时（connect+read总共时间）
  #        timeout: 3s
  #        # 采集步骤
  #        steps:
  #          - url: http://127.0.0.1:9203/path/to/test
  #            method: GET
  #            headers:
  #              referer: http://bk.tencent.com
  #            available_duration: 3s
  #            request: ""
  #            # 请求格式（raw/hex）
  #            request_format: raw
  #            response: "/path/to/test"
  #            # 内容匹配方式
  #            response_format: eq
  #            response_code: 200,201

  #### metricbeat_task child config #####
  #  metricbeat_task:
  #    dataid: 0
  #    # 缓冲区最大空间
  #    max_buffer_size: 10240
  #    # 最大超时时间
  #    max_timeout: 100s
  #    # 最小检测间隔
  #    min_period: 3s
  #    tasks:
  #      - task_id: 5
  #        bk_biz_id: 1
  #        # 周期
  #        period: 60s
  #        # 超时
  #        timeout: 60s
  #        module:
  #          module: mysql
  #          metricsets: ["allstatus"]
  #          enabled: true
  #          hosts: ["root:mysql123@tcp(127.0.0.1:3306)/"]

  #### script_task child config #####
  #  script_task:
  #    dataid: 0
  #    tasks:
  #      - bk_biz_id: 2
  #        command: echo 'value' 45
  #        dataid: 0
  #        period: 1m
  #        task_id: 7
  #        timeout: 60s
  #        user_env: {}

  #### keyword_task child config #####
  #  keyword_task:
  #    dataid: 0
  #    tasks:
  #      - task_id: 5
  #        bk_biz_id: 2
  #        dataid: 12345
  #        # 采集文件路径
  #        paths:
  #          - '/var/log/messages'
  #
  #        # 需要排除的文件列表，正则表示
  #        # exclude_files:
  #
  #        # 文件编码类型
  #        encoding: 'utf-8'
  #        # 文件未更新需要删除的超时等待
  #        close_inactive: '86400s'
  #        # 上报周期
  #        report_period: '1m'
  #        # 日志关键字匹配规则
  #        keywords:
  #          - name: HttpError
  #            pattern: '.*ERROR.*'
  #
  #        # 结果输出格式
  #        # output_format: 'event'
  #
  #        # 上报时间单位，默认ms
  #        # time_unit: 'ms'
  #
  #        # 采集目标
  #        target: '0:127.0.0.1'
  #        # 注入的labels
  #        labels:
  #          - bk_target_service_category_id: ""
  #            bk_collect_config_id: "59"
  #            bk_target_cloud_id: "0"
  #            bk_target_topo_id: "1"
  #            bk_target_ip: "127.0.0.1"
  #            bk_target_service_instance_id: ""
  #            bk_target_topo_level: "set"
"""

config_tpl_2 = """
type: http
name: {{ config_name | default("http_task", true) }}
version: {{ config_version| default("1.1.1", true) }}

dataid: {{ data_id | default(1011, true) }}
max_buffer_size: {{ max_buffer_size | default(10240, true) }}
max_timeout: {{ max_timeout | default("30s", true) }}
min_period: {{ min_period | default("3s", true) }}
tasks: {% for task in tasks %}
  - task_id: {{ task.task_id }}
    bk_biz_id: {{ task.bk_biz_id }}
    period: {{ task.period }}
    available_duration: {{ task.available_duration }}
    insecure_skip_verify: {{ task.insecure_skip_verify | lower }}
    disable_keep_alives: {{ task.disable_keep_alives | lower }}
    timeout: {{ task.timeout | default("3s", true) }}
    steps: {% for step in task.steps %}
      - url: {{ step.url }}
        method: {{ step.method }}
        headers: {% for key,value in step.headers.items() %}
            {{ key }}: {{ value }}
        {% endfor %}
        available_duration: {{ step.available_duration }}
        request: {{ step.request or '' }}
        request_format: {{ step.request_format | default("raw", true) }}
        response: {{ step.response or '' }}
        response_format: {{ step.response_format | default("eq", true) }}
        response_code: {{ step.response_code }}{% endfor %}{% endfor %}
"""

config_tpl_3 = """
type: ping
name: {{ config_name | default("icmp_task", true) }}
version: {{ config_version| default("1.1.1", true) }}


dataid: {{ data_id | default(1100003, true) }}
max_buffer_size: {{ max_buffer_size | default(10240, true) }}
max_timeout: {{ max_timeout | default("100s", true) }}
min_period: {{ min_period | default("3s", true) }}
tasks: {% for task in tasks %}
  - task_id: {{ task.task_id }}
    bk_biz_id: {{ task.bk_biz_id }}
    period: {{ task.period }}
    timeout: {{ task.timeout | default("3s", true) }}
    max_rtt: {{ task.max_rtt }}
    total_num: {{ task.total_num }}
    ping_size: {{ task.size }}
    targets: {% for host in task.target_hosts %}
        - target: {{ host.ip}}
          target_type: {{ host.target_type | default("ip", true)}}{% endfor %}{% endfor %}
"""

config_tpl_4 = """
type: keyword
name: {{ config_name | default("keyword_task", true) }}
version: {{ config_version| default("1.1.1", true) }}

dataid: 0

tasks: {% for task in tasks %}
   - task_id: {{ task.task_id }}
     bk_biz_id: {{ task.bk_biz_id }}
     dataid: {{ task.dataid | int }}
     paths:{% for path in task.path_list %}
       - '{{ path }}'{% endfor %}
     encoding: '{{ task.encoding | lower}}'
     close_inactive: '86400s'
     report_period: '1m'
     keywords:{% for task in task.task_list %}
       - name: '{{ task['name'] }}'
         pattern: '{{ task['pattern'] | replace("'", "''") }}'{% endfor %}
     target: '{{ task.target }}'
     labels:{% for label in task.labels %}
          {% for key, value in label.items() %}{{ "-" if loop.first else " "  }} {{ key }}: "{{ value }}"
          {% endfor %}{% endfor %}
{% endfor %}
"""

config_tpl_5 = """
type: keyword
"""
