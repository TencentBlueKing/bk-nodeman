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
import copy

from apps.mock_data.common_unit import host
from apps.node_man import constants

# 操作类接口一般返回的是 task_id
OP_RESULT = {"task_id": "GSETASK:S:202111161138323563236795:143"}
GSE_PROCESS_VERSION = "1.7.17"
GSE_PROCESS_NAME = "test_process"

GET_AGENT_ALIVE_STATUS_DATA = {
    f"{constants.DEFAULT_CLOUD}:{host.DEFAULT_IP}": {
        "ip": host.DEFAULT_IP,
        "bk_cloud_id": constants.DEFAULT_CLOUD,
        "bk_agent_alive": constants.BkAgentStatus.ALIVE.value,
    }
}

GET_AGENT_NOT_ALIVE_STATUS_DATA = {
    f"{constants.DEFAULT_CLOUD}:{host.DEFAULT_IP}": {
        "ip": host.DEFAULT_IP,
        "bk_cloud_id": constants.DEFAULT_CLOUD,
        "bk_agent_alive": constants.BkAgentStatus.NOT_ALIVE.value,
    }
}

GET_AGENT_INFO_DATA = {
    f"{constants.DEFAULT_CLOUD}:{host.DEFAULT_IP}": {
        "ip": host.DEFAULT_IP,
        "version": GSE_PROCESS_VERSION,
        "bk_cloud_id": 0,
        "parent_ip": host.DEFAULT_IP,
        "parent_port": 50000,
    }
}

GET_PROC_OPERATE_RESULT = {
    f"{constants.DEFAULT_CLOUD}:{host.DEFAULT_IP}:{constants.GSE_NAMESPACE}:sub_870_host_1_host_exp002": {
        "content": '{\n   "value" : [\n      {\n         "funcID" : "",\n'
        '         "instanceID" : "",\n        '
        ' "procName" : "host_exp002",\n         "result" : "success",\n'
        '         "setupPath" : "/usr/local/gse/external_plugins/sub_870'
        '_host_1/host_exp002"\n      }\n   ]\n}\n',
        "error_code": 0,
        "error_msg": "success",
    }
}

GSE_V2_AGENT_STATE_DATA = {
    "bk_agent_id": f"{constants.DEFAULT_CLOUD}:{host.DEFAULT_IP}",
    "bk_cloud_id": constants.DEFAULT_CLOUD,
    "version": GSE_PROCESS_VERSION,
    "run_mode": 0,
    "status_code": constants.GseAgentStatusCode.RUNNING.value,
}

GSE_V2_AGENT_NOT_ALIVE_STATE_DATA = {
    **GSE_V2_AGENT_STATE_DATA,
    "status_code": constants.GseAgentStatusCode.STOPPED.value,
}


GET_V2_AGENT_STATE_DATA_LIST = [GSE_V2_AGENT_STATE_DATA]

GET_V2_AGENT_NOT_ALIVE_STATE_LIST = [GSE_V2_AGENT_NOT_ALIVE_STATE_DATA]

GET_AGENT_INFO_LIST_DATA = [
    {
        "code": 0,
        "message": "OK",
        "bk_agent_id": f"{constants.DEFAULT_CLOUD}:{host.DEFAULT_IP}",
        "bk_cloud_id": constants.DEFAULT_CLOUD,
        "bk_host_ip": host.DEFAULT_IP,
        "bk_os_type": "linux",
        "report_time": 1632830304777,
        "parent_ip": host.DEFAULT_IP,
        "parent_port": 0,
        "version": GSE_PROCESS_VERSION,
        "cpu_rate": 12.34,
        "mem_rate": 56.78,
        "start_time": 1632830300,
        "run_mode": 0,
        "status_code": constants.GseAgentStatusCode.RUNNING.value,
        "status": "running",
        "last_status_code": constants.GseAgentStatusCode.RUNNING.value,
        "last_status": "running",
        "remark": "",
    }
]

GET_PROC_STATUS_DATA = {
    "proc_infos": [
        {
            # 需要根据不同参数补充 hosts 或者 bk_agent_id, 详见 mock_get_proc_status
            "status": constants.GseProcessStatusCode.STOPPED.value,
            "version": GSE_PROCESS_VERSION,
            "isauto": constants.GseProcessAutoCode.AUTO.value,
            "meta": {
                "name": GSE_PROCESS_NAME,
                "namespace": constants.GSE_NAMESPACE,
                "labels": {"proc_name": GSE_PROCESS_NAME},
            },
        }
    ]
}


def mock_get_agent_info_list(params):
    agent_info_list = copy.deepcopy(GET_AGENT_INFO_LIST_DATA)
    for index, agent_info in enumerate(agent_info_list):
        agent_info["bk_agent_id"] = params["agent_id_list"][index]
    return agent_info_list


def mock_v2_cluster_list_agent_state_return(params):
    agent_state_list = []
    for agent_id in params["agent_id_list"]:
        agent_state_list.append({**GSE_V2_AGENT_STATE_DATA, "bk_agent_id": agent_id})
    return agent_state_list


def mock_get_proc_status(params):
    pro_status_data = copy.deepcopy(GET_PROC_STATUS_DATA)
    if "hosts" in params:
        hosts = params["hosts"]
    else:
        hosts = []
        for agent_id in params["agent_id_list"]:
            bk_cloud_id, ip = agent_id.split(":")
            hosts.append({"bk_cloud_id": bk_cloud_id, "ip": ip})

    for index, host_info in enumerate(hosts):
        pro_status_data["proc_infos"][index]["bk_agent_id"] = f"{host_info['bk_cloud_id']}:{host_info['ip']}"
        pro_status_data["proc_infos"][index]["host"] = {"ip": host_info["ip"], "bk_cloud_id": host_info["bk_cloud_id"]}
    # 添加返回一个不存在的key来模拟额外返回的case
    not_exist_proc_info = copy.deepcopy(pro_status_data["proc_infos"][0])
    not_exist_proc_info["bk_agent_id"] = "not_exist_proc_info_agent_id"
    pro_status_data["proc_infos"].append(not_exist_proc_info)
    return pro_status_data


def mock_upgrade_to_agent_id(params):
    return {"success": [f'{host_info["bk_cloud_id"]}:{host_info["ip"]}' for host_info in params["hosts"]], "failed": []}
