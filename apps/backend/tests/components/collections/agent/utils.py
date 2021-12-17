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
import copy

from django.conf import settings
from mock import MagicMock

from apps.backend.api.constants import JobDataStatus, JobIPStatus
from apps.backend.subscription import tools
from apps.node_man import constants as const
from apps.node_man import models

DEFAULT_CREATOR = "admin"

DEFAULT_BIZ_ID_NAME = {"bk_biz_id": "10", "bk_biz_name": "测试Pipeline原子专用"}

DEFAULT_CLOUD_NAME = "直连区域"

DEFAULT_AP_ID = const.DEFAULT_AP_ID

DEFAULT_NODE_TYPE = "INSTANCE"

DEFAULT_OBJ_TYPE = "HOST"

DEFAULT_INSTANCE_ID = "host|instance|host|127.0.0.1-0-0"

CALLBACK_URL = "http://127.0.0.1/backend"

# ---------订阅任务id参数--------------
SUBSCRIPTION_ID = 61

SUBSCRIPTION_INSTANCE_RECORD_ID = 95

SUBSCRIPTION_TASK_ID = 91

JOB_ID = 56

JOB_TASK_ID = 100

BK_HOST_ID = 23333

# 当前原子任务id
JOB_TASK_PIPELINE_ID = "1ae89ce9deec319bbd8727a0c4b2ca82"

# 安装线的pipeline id
INSTANCE_RECORD_ROOT_PIPELINE_ID = "98d467d07e453e1b9f24e77c8c6743fb"

# 测试伪造ip
TEST_IP = "127.0.0.1"
CHANNEL_TEST_IP = "127.0.0.2"

# Job作业实例id
JOB_INSTANCE_ID = 10000

# ---------mock path--------------
SSH_MAN_MOCK_PATH = "apps.backend.components.collections.agent.SshMan"

CLIENT_V2_MOCK_PATH = "apps.backend.components.collections.agent.client_v2"

JOB_CLIENT_MOCK_PATH = "apps.backend.api.job.get_client_by_user"

JOB_VERSION_MOCK_PATH = "apps.backend.api.job.settings.JOB_VERSION"

POLLING_TIMEOUT_MOCK_PATH = "apps.backend.components.collections.job.POLLING_TIMEOUT"


# 目标主机信息
INSTANCE_INFO = {
    "key": "",
    "port": 22,
    "ap_id": const.DEFAULT_AP_ID,
    "account": "root",
    "os_type": const.OsType.LINUX,
    "login_ip": "",
    "password": "MTIyMTM0",
    "username": DEFAULT_CREATOR,
    "auth_type": const.AuthType.PASSWORD,
    "bk_biz_id": DEFAULT_BIZ_ID_NAME["bk_biz_id"],
    "is_manual": False,
    "retention": 1,
    "bk_os_type": const.BK_OS_TYPE[const.OsType.LINUX],
    "bk_biz_name": DEFAULT_BIZ_ID_NAME["bk_biz_name"],
    "bk_cloud_id": const.DEFAULT_CLOUD,
    "bk_cloud_name": DEFAULT_CLOUD_NAME,
    "host_node_type": const.NodeType.AGENT,
    "bk_host_innerip": TEST_IP,
    "bk_host_outerip": "",
    "bk_supplier_account": "0",
    "peer_exchange_switch_for_agent": 1,
}

ACT_INPUTS = {
    "host_info": dict(list(INSTANCE_INFO.items()) + [("bt_speed_limit", "None")]),
    # 注册后会填充该值
    "bk_host_id": "",
    "description": "安装....",
    "blueking_language": "zh-hans",
}

HOST_PARAMS = {
    "bk_host_id": BK_HOST_ID,
    "bk_biz_id": DEFAULT_BIZ_ID_NAME["bk_biz_id"],
    "bk_cloud_id": const.DEFAULT_CLOUD,
    "inner_ip": TEST_IP,
    "outer_ip": None,
    "login_ip": TEST_IP,
    "data_ip": None,
    "os_type": "LINUX",
    "node_type": const.NodeType.AGENT,
    "node_from": "NODE_MAN",
    "ap_id": const.DEFAULT_AP_ID,
    "upstream_nodes": [],
    "is_manual": 0,
    "extra_data": {"bt_speed_limit": None, "peer_exchange_switch_for_agent": 1},
}

IDENTITY_DATA_PARAMS = {
    "bk_host_id": BK_HOST_ID,
    "auth_type": const.AuthType.PASSWORD,
    "account": "root",
    "password": "aes_str:::H4MFaqax",
    "port": 22,
    "key": "aes_str:::LXqh",
    "extra_data": {},
    "retention": 1,
}

SUBSCRIPTION_PARAMS = {
    "id": SUBSCRIPTION_ID,
    "object_type": DEFAULT_OBJ_TYPE,
    "node_type": DEFAULT_NODE_TYPE,
    # 对于Pipeline原子的测试都只用一台主机
    "nodes": [
        {
            "ip": INSTANCE_INFO["bk_host_innerip"],
            "bk_cloud_id": const.DEFAULT_CLOUD,
            "instance_info": INSTANCE_INFO,
            "bk_supplier_account": "0",
        }
    ],
    "creator": DEFAULT_CREATOR,
}

SUBSCRIPTION_TASK_PARAMS = {
    "id": SUBSCRIPTION_TASK_ID,
    "subscription_id": SUBSCRIPTION_ID,  # 根据实际创建进行修改
    "scope": {
        "nodes": [
            {
                "ip": INSTANCE_INFO["bk_host_innerip"],
                "bk_cloud_id": const.DEFAULT_CLOUD,
                "instance_info": INSTANCE_INFO,
                "bk_supplier_account": "0",
            }
        ],
        "node_type": DEFAULT_NODE_TYPE,
        "object_type": DEFAULT_OBJ_TYPE,
        "need_register": True,
    },
    "actions": {
        # 每台主机都有一个实例id，最后根据补参重新生成
        DEFAULT_INSTANCE_ID: {
            # 默认安装任务
            "agent": const.JobType.INSTALL_AGENT
        }
    },
    # 是否为自动触发
    "is_auto_trigger": 0,
}

JOB_PARAMS = {
    "id": JOB_ID,
    "created_by": DEFAULT_CREATOR,
    "job_type": const.JobType.INSTALL_AGENT,
    "subscription_id": SUBSCRIPTION_ID,  # 根据实际创建进行修改
    # Pipeline原子默认只有一个安装任务
    "task_id_list": [SUBSCRIPTION_TASK_ID],
    "status": const.JobStatusType.RUNNING,
    "global_params": {},
    "statistics": {"total_count": 1, "failed_count": 0, "pending_count": 1, "running_count": 0, "success_count": 0},
    "bk_biz_scope": [DEFAULT_BIZ_ID_NAME["bk_biz_id"]],
    "error_hosts": [],
}

JOB_TASK_PARAMS = {
    "id": JOB_TASK_ID,
    "job_id": JOB_ID,
    # 没有注册到cmdb之前是空
    "bk_host_id": BK_HOST_ID,
    "instance_id": DEFAULT_INSTANCE_ID,
    "pipeline_id": JOB_TASK_PIPELINE_ID,
    "status": const.StatusType.RUNNING,
    "current_step": "正在安装",
}

SUBSCRIPTION_INSTANCE_RECORD_PARAMS = {
    "id": SUBSCRIPTION_INSTANCE_RECORD_ID,
    "task_id": SUBSCRIPTION_TASK_ID,
    "subscription_id": SUBSCRIPTION_ID,
    "instance_id": DEFAULT_INSTANCE_ID,
    # 安装时，注册到cmdb后会插入bk_host_id
    "instance_info": {"host": INSTANCE_INFO},
    "steps": [
        {
            "id": "agent",
            "type": const.NodeType.AGENT,
            "action": const.JobType.INSTALL_AGENT,
            "extra_info": {},
            "pipeline_id": "3341978fe1f33b2b99615818df5c7a89",
        }
    ],
    "pipeline_id": INSTANCE_RECORD_ROOT_PIPELINE_ID,
}

JOB_INSTANCE_ID_METHOD_RETURN = {
    "result": True,
    "code": 0,
    "message": "success",
    "data": {"job_instance_name": "API Quick Distribution File1521101427176", "job_instance_id": JOB_INSTANCE_ID},
}

JOB_GET_INSTANCE_LOG_RETURN = {
    "result": True,
    "code": 0,
    "message": "",
    "data": [
        {
            "is_finished": True,
            "step_instance_id": 90000,
            "name": "test",
            "status": JobDataStatus.SUCCESS,
            "step_results": [
                {
                    "ip_status": JobIPStatus.SUCCESS,
                    "tag": "xxx",
                    "ip_logs": [
                        {
                            "retry_count": 0,
                            "total_time": 60.599,
                            "start_time": "2020-08-05 14:39:30 +0800",
                            "end_time": "2020-08-05 14:40:31 +0800",
                            "ip": TEST_IP,
                            "bk_cloud_id": 0,
                            "error_code": 0,
                            "exit_code": 0,
                            "log_content": "success",
                        }
                    ],
                }
            ],
        }
    ],
}

GET_JOB_INSTANCE_STATUS_V2_C_RETURN = {
    "is_finished": False,
    "job_instance": {
        "job_instance_id": JOB_INSTANCE_ID,
        "bk_biz_id": DEFAULT_BIZ_ID_NAME["bk_biz_id"],
        "name": "API Quick execution script1521089795887",
        "operator": DEFAULT_CREATOR,
        "bk_job_id": 4355,
        "create_time": "2018-03-15 12:56:35 +0800",
        "status": JobDataStatus.PENDING,
    },
}


# 适用于 client_v2
JOB_INSTANCE_ID_METHOD_V2_C_RETURN = JOB_INSTANCE_ID_METHOD_RETURN["data"]


class SshManMockClient:
    def __init__(
        self,
        get_and_set_prompt_return=None,
        send_cmd_return_return=None,
        safe_close_return=None,
        ssh_return=None,
    ):
        self.get_and_set_prompt = MagicMock(return_value=get_and_set_prompt_return)
        self.send_cmd = MagicMock(return_value=send_cmd_return_return)
        self.safe_close = MagicMock(return_value=safe_close_return)
        self.ssh = MagicMock(return_value=ssh_return)


class GseMockClient:
    def __init__(self, get_agent_status_return=None, get_agent_info_return=None):
        self.gse = MagicMock()
        self.gse.get_agent_status = MagicMock(return_value=get_agent_status_return)
        self.gse.get_agent_info = MagicMock(return_value=get_agent_info_return)


class CMDBMockClient:
    def __init__(
        self,
        add_host_to_resource_result=None,
        search_business_result=None,
        list_biz_hosts_result=None,
        list_hosts_without_biz_result=None,
        find_host_biz_relations_result=None,
    ):
        self.cc = MagicMock()
        self.cc.add_host_to_resource = MagicMock(return_value=add_host_to_resource_result)
        self.cc.search_business = MagicMock(return_value=search_business_result)
        self.cc.list_biz_hosts = MagicMock(return_value=list_biz_hosts_result)
        self.cc.list_hosts_without_biz = MagicMock(return_value=list_hosts_without_biz_result)
        self.cc.find_host_biz_relations = MagicMock(return_value=find_host_biz_relations_result)


class JobMockClient:
    def __init__(
        self,
        fast_execute_script_return=None,
        get_job_instance_log_return=None,
        fast_push_file_return=None,
        push_config_file_return=None,
        get_job_instance_status_return=None,
    ):
        self.job = MagicMock()
        self.job.fast_execute_script = MagicMock(return_value=fast_execute_script_return)
        self.job.get_job_instance_log = MagicMock(return_value=get_job_instance_log_return)
        self.job.fast_push_file = MagicMock(return_value=fast_push_file_return)
        self.job.push_config_file = MagicMock(return_value=push_config_file_return)
        self.job.get_job_instance_status = MagicMock(return_value=get_job_instance_status_return)


class JobDemandMock:
    def __init__(self, poll_task_result_return=None):
        self.poll_task_result = MagicMock(return_value=poll_task_result_return)


class StorageMock:
    def __init__(self, get_file_md5_return=None, fast_transfer_file_return=None):
        self.get_file_md5 = MagicMock(return_value=get_file_md5_return)
        self.fast_transfer_file = MagicMock(return_value=fast_transfer_file_return)


class AgentTestObjFactory:
    @classmethod
    def replace_obj_attr_values(cls, obj, obj_attr_values):
        # 原地修改
        if obj_attr_values is None:
            return obj
        for attr, value in obj_attr_values.items():
            if attr not in obj:
                continue
            obj[attr] = value

    @classmethod
    def inputs(cls, attr_values=None, instance_info_attr_values=None):
        instance_info = copy.deepcopy(INSTANCE_INFO)
        inputs = copy.deepcopy(ACT_INPUTS)
        cls.replace_obj_attr_values(instance_info, instance_info_attr_values)
        inputs["host_info"] = dict(list(instance_info.items()) + [("bt_speed_limit", "None")])
        if "bt_speed_limit" in instance_info_attr_values:
            inputs["host_info"]["bt_speed_limit"] = instance_info_attr_values["bt_speed_limit"]
        cls.replace_obj_attr_values(inputs, attr_values)
        return inputs

    @classmethod
    def subscription_obj(cls, obj_attr_values=None, instance_info_attr_values=None, is_obj=False):
        instance_info = copy.deepcopy(INSTANCE_INFO)
        subscription_params = copy.deepcopy(SUBSCRIPTION_PARAMS)

        cls.replace_obj_attr_values(instance_info, instance_info_attr_values)
        if instance_info_attr_values is not None:
            subscription_params["nodes"][0]["instance_info"] = instance_info
            subscription_params["nodes"][0]["ip"] = instance_info["bk_host_innerip"]

        cls.replace_obj_attr_values(subscription_params, obj_attr_values)
        if not is_obj:
            subscription_params.pop("id", None)
        return models.Subscription(**subscription_params) if is_obj else subscription_params

    @classmethod
    def subscription_task_obj(cls, obj_attr_values=None, instance_info_attr_values=None, is_obj=False):
        instance_info = copy.deepcopy(INSTANCE_INFO)
        subscription_task_params = copy.deepcopy(SUBSCRIPTION_TASK_PARAMS)

        cls.replace_obj_attr_values(instance_info, instance_info_attr_values)
        if instance_info_attr_values is not None:
            subscription_task_params["scope"]["nodes"][0]["instance_info"] = instance_info
            subscription_task_params["scope"]["nodes"][0]["ip"] = instance_info["bk_host_innerip"]

        instance_id = tools.create_node_id(
            {
                "object_type": DEFAULT_OBJ_TYPE,
                "node_type": DEFAULT_NODE_TYPE,
                "bk_cloud_id": instance_info["bk_cloud_id"],
                "ip": instance_info["bk_host_innerip"],
            }
        )
        subscription_task_params["actions"].pop(DEFAULT_INSTANCE_ID)
        subscription_task_params["actions"] = {instance_id: {"agent": const.JobType.INSTALL_AGENT}}
        cls.replace_obj_attr_values(subscription_task_params, obj_attr_values)
        if not is_obj:
            subscription_task_params.pop("id", None)
        return models.SubscriptionTask(**subscription_task_params) if is_obj else subscription_task_params

    @classmethod
    def subscription_instance_record_obj(cls, obj_attr_values=None, instance_info_attr_values=None, is_obj=False):
        instance_info = copy.deepcopy(INSTANCE_INFO)
        subscription_instance_record_params = copy.deepcopy(SUBSCRIPTION_INSTANCE_RECORD_PARAMS)
        cls.replace_obj_attr_values(instance_info, instance_info_attr_values)
        if instance_info_attr_values is not None:
            subscription_instance_record_params["instance_info"]["host"] = instance_info

        subscription_instance_record_params["instance_id"] = tools.create_node_id(
            {
                "object_type": DEFAULT_OBJ_TYPE,
                "node_type": DEFAULT_NODE_TYPE,
                "bk_cloud_id": instance_info["bk_cloud_id"],
                "ip": instance_info["bk_host_innerip"],
            }
        )
        cls.replace_obj_attr_values(subscription_instance_record_params, obj_attr_values)
        return (
            models.SubscriptionInstanceRecord(**subscription_instance_record_params)
            if is_obj
            else subscription_instance_record_params
        )

    @classmethod
    def job_obj(cls, obj_attr_values=None, is_obj=False):
        job_params = copy.deepcopy(JOB_PARAMS)
        cls.replace_obj_attr_values(job_params, obj_attr_values)
        if not is_obj:
            job_params.pop("id", None)
        return models.Job(**job_params) if is_obj else job_params

    @classmethod
    def job_task_obj(cls, obj_attr_values=None, is_obj=False):
        job_task_params = copy.deepcopy(JOB_TASK_PARAMS)
        cls.replace_obj_attr_values(job_task_params, obj_attr_values)
        if not is_obj:
            job_task_params.pop("id", None)
        return models.JobTask(**job_task_params) if is_obj else job_task_params

    @classmethod
    def identity_data_obj(cls, obj_attr_values=None, is_obj=False):
        identity_data_params = copy.deepcopy(IDENTITY_DATA_PARAMS)
        cls.replace_obj_attr_values(identity_data_params, obj_attr_values)
        if not is_obj:
            identity_data_params.pop("id", None)
        return models.IdentityData(**identity_data_params) if is_obj else identity_data_params

    @classmethod
    def host_obj(cls, obj_attr_values=None, is_obj=False):
        host_params = copy.deepcopy(HOST_PARAMS)
        cls.replace_obj_attr_values(host_params, obj_attr_values)
        if not is_obj:
            host_params.pop("id", None)
        return models.Host(**host_params) if is_obj else host_params

    @classmethod
    def init_db(cls):
        # 初始化callback_url
        settings.BKAPP_NODEMAN_CALLBACK_URL = CALLBACK_URL
        settings.BKAPP_NODEMAN_OUTER_CALLBACK_URL = CALLBACK_URL

        subscription_params = cls.subscription_obj()
        subscription = models.Subscription.objects.create(**subscription_params)

        subscription_task_params = cls.subscription_task_obj(obj_attr_values={"subscription_id": subscription.id})
        subscription_task = models.SubscriptionTask.objects.create(**subscription_task_params)

        subscription_instance_record_params = cls.subscription_instance_record_obj(
            obj_attr_values={"subscription_id": subscription.id, "task_id": subscription_task.id}
        )
        subscription_instance_record = models.SubscriptionInstanceRecord.objects.create(
            **subscription_instance_record_params
        )

        job_params = cls.job_obj(
            obj_attr_values={"subscription_id": subscription.id, "task_id_list": [subscription_task.id]}
        )
        job = models.Job.objects.create(**job_params)

        job_task_params = cls.job_task_obj({"job_id": job.id})
        job_task = models.JobTask.objects.create(**job_task_params)

        host_params = cls.host_obj()
        host = models.Host.objects.create(**host_params)

        identity_data_params = cls.identity_data_obj()
        models.IdentityData.objects.create(**identity_data_params)

        return {
            "subscription_id": subscription.id,
            "subscription_task_id": subscription_task.id,
            "subscription_instance_record_id": subscription_instance_record.id,
            "job_id": job.id,
            "job_task_id": job_task.id,
            "bk_host_id": host.bk_host_id,
        }
