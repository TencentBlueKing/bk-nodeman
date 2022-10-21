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

GSE_AGENT_CONFIG_TMPL: str = """
{
    "run_mode": __BK_GSE_RUN_MODE__,
    "cloud_id": __BK_GSE_CLOUD_ID__,
    "zone_id": "__BK_GSE_ZONE_ID__",
    "city_id": "__BK_GSE_CITY_ID__",
    "access": {
        "cluster_endpoints": "__BK_GSE_ACCESS_CLUSTER_ENDPOINTS__",
        "data_endpoints": "__BK_GSE_ACCESS_DATA_ENDPOINTS__",
        "file_endpoints": "__BK_GSE_ACCESS_FILE_ENDPOINTS__"
    },
    "base": {
        "tls_ca_file": "__BK_GSE_AGENT_BASE_TLS_CA_FILE__",
        "tls_cert_file": "__BK_GSE_AGENT_BASE_TLS_CERT_FILE__",
        "tls_key_file": "__BK_GSE_AGENT_BASE_TLS_KEY_FILE__",
        "tls_passwd_file": "__BK_GSE_AGENT_BASE_TLS_PASSWORD_FILE__",
        "processor_num": __BK_GSE_AGENT_BASE_PROCESSOR_NUM__,
        "processor_size": __BK_GSE_AGENT_BASE_PROCESSOR_SIZE__
    },
    "proxy": {
        "tls_ca_file": "__BK_GSE_PROXY_TLS_CA_FILE__",
        "tls_cert_file": "__BK_GSE_PROXY_TLS_CERT_FILE__",
        "tls_key_file": "__BK_GSE_PROXY_TLS_KEY_FILE__",
        "tls_passwd_file": "__BK_GSE_PROXY_TLS_PASSWORD_FILE__",
        "bind_ip": "__BK_GSE_PROXY_BIND_IP__",
        "bind_port": __BK_GSE_PROXY_BIND_PORT__,
        "thread_num": __BK_GSE_PROXY_THREAD_NUM__
    },
    "task": {
        "proc_event_data_id": __BK_GSE_TASK_PROC_EVENT_DATA_ID__,
        "concurrence_count": __BK_GSE_TASK_CONCURRENCE_COUNT__,
        "queue_wait_timeout_ms": __BK_GSE_TASK_QUEUE_WAIT_TIMEOUT_MS__,
        "executor_queue_size": __BK_GSE_TASK_EXECUTOR_QUEUE_SIZE__,
        "schedule_queue_size": __BK_GSE_TASK_SCHEDULE_QUEUE_SIZE__,
        "host_code_page_name": "__BK_GSE_TASK_HOST_CODE_PAGE_NAME__",
        "script_file_clean_batch_count": __BK_GSE_TASK_SCRIPT_FILE_CLEAN_BATCH_COUNT__,
        "script_file_clean_starup_clock_time": __BK_GSE_TASK_SCRIPT_FILE_CLEAN_STARTUP_CLOCK_TIME__,
        "script_file_expire_time_hour": __BK_GSE_TASK_SCRIPT_FILE_EXPIRE_TIME_HOUR__,
        "script_file_prefix": "__BK_GSE_TASK_SCRIPT_FILE_PREFIX__"
    },
    "data": {
        "ipc": "__BK_GSE_DATA_IPC__",
        "ipc_thread_num": __BK_GSE_DATA_IPC_RECV_THREAD_NUM__
    },
    "logger": {
        "path": "__BK_GSE_LOG_PATH__",
        "level": "__BK_GSE_LOG_LEVEL__",
        "filesize_mb": __BK_GSE_LOG_FILESIZE_MB__,
        "filenum": __BK_GSE_LOG_FILENUM__,
        "rotate": __BK_GSE_LOG_ROTATE__,
        "flush_interval_ms": __BK_GSE_LOG_FLUSH_INTERVAL_MS__
    },
    "extra_config_directory": "__BK_GSE_EXTRA_CONFIG_DIRECTORY__"
}
"""


GSE_DATA_PROXY_CONFIG_TMPL: str = """
{
    "run_mode": "proxy",
    "logger": {
        "path": "__BK_GSE_LOG_PATH__",
        "level": "__BK_GSE_LOG_LEVEL__",
        "filesize_mb": __BK_GSE_LOG_FILESIZE_MB__,
        "filenum": __BK_GSE_LOG_FILENUM__,
        "rotate": __BK_GSE_LOG_ROTATE__,
        "flush_interval_ms": __BK_GSE_LOG_FLUSH_INTERVAL_MS__
    },
    "metric": {
        "exporter_bind_ip": "__BK_GSE_DATA_METRIC_EXPORTER_IP__",
        "exporter_bind_port": __BK_GSE_DATA_METRIC_EXPORTER_PORT__
    },
    "dataflow": {
        "receiver": [
            {
                "name": "agent_service",
                "protocol": 1,
                "bind_ip": "__BK_GSE_DATA_AGENT_TCP_BIND_IP__",
                "bind_port": __BK_GSE_DATA_AGENT_TCP_BIND_PORT__,
                "ca_file": "__BK_GSE_DATA_AGENT_TLS_CA_FILE__",
                "cert_file": "__BK_GSE_DATA_AGENT_TLS_CERT_FILE__",
                "key_file": "__BK_GSE_DATA_AGENT_TLS_KEY_FILE__",
                "passwd_file": "__BK_GSE_DATA_AGENT_TLS_PASSWORD_FILE__",
                "thread_num": __BK_GSE_DATA_AGENT_TCP_SERVER_THREAD_NUM__,
                "protostack": 4,
                "max_message_size": __BK_GSE_DATA_AGENT_TCP_SERVER_MAX_MESSAGE_SIZE__,
                "backlog": 4096
            }
        ],
        "exporter": [
            {
                "name": "e_proxy",
                "type": 9,
                "protocol": "tcp",
                "ca_file": "__BK_GSE_DATA_PROXY_TLS_CA_FILE__",
                "cert_file": "__BK_GSE_DATA_PROXY_TLS_CERT_FILE__",
                "key_file": "__BK_GSE_DATA_PROXY_TLS_KEY_FILE__",
                "passwd_file": "__BK_GSE_DATA_PROXY_TLS_PASSWORD_FILE__",
                "endpoints": "__BK_GSE_DATA_PROXY_ENDPOINTS__"
            }
        ],
        "channel": [
            {
                "name": "c_agent",
                "decode": 8,
                "receiver": "agent_service",
                "thread_num": __BK_GSE_DATA_AGENT_TCP_SERVER_THREAD_NUM__,
                "exporter":[
                    "e_proxy"
                ]
            }
        ]
    }
}
"""
