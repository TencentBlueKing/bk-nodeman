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

import uuid

from apps.node_man import constants
from apps.node_man.models import ProcessStatus

# 通用的mock数据

# 主机常用属性
MOCK_BK_BIZ_ID = 1
MOCK_BK_CLOUD_ID = 99999
MOCK_IP = "127.0.0.1"
MOCK_HOST_ID = 233333
# 主机数量(用于批量构造)
MOCK_HOST_NUM = 10
# 其他各种ID
MOCK_ID = 99
# 各种日期
MOCK_DATA = "2021-12-20"
# 各种端口
MOCK_PORT = 80
# 各种版本
MOCK_VERSION = "1.1.13"

# test_sync_proc_status_task 相关数据

MOCK_PROC_NAME = "test_proc"
MOCK_HOST = {
    "bk_biz_id": MOCK_BK_BIZ_ID,
    "bk_host_id": MOCK_HOST_ID,
    "inner_ip": MOCK_IP,
    "outer_ip": MOCK_IP,
    "bk_cloud_id": MOCK_BK_CLOUD_ID,
    "node_from": "CMDB",
}
MOCK_PROC_STATUS = {
    "status": constants.ProcStateType.TERMINATED,
    "is_latest": True,
    "bk_host_id": MOCK_HOST["bk_host_id"],
    "name": MOCK_PROC_NAME,
    "source_type": ProcessStatus.SourceType.DEFAULT,
    "proc_type": constants.ProcType.PLUGIN,
}
MOCK_GET_PROC_STATUS = {
    "proc_infos": [
        {
            "host": {"ip": MOCK_HOST["inner_ip"], "bk_cloud_id": MOCK_HOST["bk_cloud_id"]},
            "status": 1,
            "version": MOCK_VERSION,
            "isauto": True,
            "meta": {"name": MOCK_PROC_NAME, "namespace": "nodeman", "labels": {"proc_name": MOCK_PROC_NAME}},
        }
    ]
}

# test_clean_relation_task 相关数据

MOCK_IDENTITY_DATA = {
    "bk_host_id": MOCK_HOST["bk_host_id"],
    "account": "test",
    "password": "123456789",
    "port": MOCK_PORT,
    "key": "u8YSHkdwnc8wJ8di",
    "extra_data": "",
    "retention": 1,
    "updated_at": MOCK_DATA,
}
MOCK_RECORD = {
    "uid": str(uuid.uuid4()),
    "url": "https://www.baidu.com",
    "request_message": "",
    "operator": "test_man",
    "request_host": MOCK_IP,
    "response_message": "",
    "date_created": MOCK_DATA,
}
MOCK_SUBSCRIPTION_INSTANCE_RECORD = {
    "id": MOCK_ID,
    "task_id": MOCK_ID,
    "subscription_id": MOCK_ID,
    "steps": "",
    "instance_id": "host|instance|host|13",
    "instance_info": {"host": {**MOCK_HOST, **{"password": 123456, "key": 123456}}, "scope": []},
    "update_time": "2021-12-01 09:49:08",
    "create_time": "2021-12-01 09:49:08",
    "need_clean": True,
    "is_latest": True,
}
MOCK_RESOURCE_WATCH_EVENT = {"bk_cursor": "", "bk_event_type": "update", "bk_resource": "host", "bk_detail": MOCK_HOST}

# test_sync_agent_status_task 相关数据

MOCK_GET_AGENT_STATUS = {
    f"{MOCK_BK_CLOUD_ID}:{MOCK_IP}": {"ip": MOCK_IP, "bk_cloud_id": MOCK_BK_CLOUD_ID, "bk_agent_alive": 1}
}
MOCK_GET_AGENT_INFO = {
    f"{MOCK_BK_CLOUD_ID}:{MOCK_IP}": {
        "parent_port": MOCK_PORT,
        "parent_ip": MOCK_IP,
        "ip": MOCK_IP,
        "bk_cloud_id": MOCK_BK_CLOUD_ID,
        "version": MOCK_VERSION,
    }
}

# test_sync_cmdb_cloud_area 相关数据

MOCK_SEARCH_CLOUD_AREA = {"count": 1, "info": [{"bk_cloud_id": MOCK_BK_CLOUD_ID, "bk_cloud_name": "test_cloud"}]}

# test gse_svr_discovery 相关数据

MOCK_KAZOOCLIENT_CHILDREN_DATA = {
    "/gse/config/server/dataserver/all": ["127.0.0.1", "127.0.0.2", "127.0.0.3"],
    "/gse/config/server/taskserver/all": ["127.0.0.1", "127.0.0.2", "127.0.0.3"],
    "/gse/config/server/btfiles/all": ["127.0.0.1", "127.0.0.2", "127.0.0.3"],
}
MOCK_AP_FIELD_MAP = [
    {"inner_ip": "127.0.0.1", "outer_ip": "127.0.0.1"},
    {"inner_ip": "127.0.0.2", "outer_ip": "127.0.0.2"},
    {"inner_ip": "127.0.0.3", "outer_ip": "127.0.0.3"},
]
