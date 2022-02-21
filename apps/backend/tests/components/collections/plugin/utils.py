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

from apps.backend.api.constants import GseDataErrCode, JobDataStatus, JobIPStatus
from apps.backend.subscription import tools
from apps.backend.subscription.tools import create_group_id
from apps.exceptions import ComponentCallError
from apps.node_man import constants as const
from apps.node_man import models
from apps.node_man.models import SubscriptionStep

DEFAULT_CREATOR = "admin"

DEFAULT_BIZ_ID_NAME = {"bk_biz_id": "10", "bk_biz_name": "测试Pipeline原子专用"}

DEFAULT_CLOUD_NAME = "直连区域"

DEFAULT_AP_ID = const.DEFAULT_AP_ID

DEFAULT_NODE_TYPE = "INSTANCE"

DEFAULT_OBJ_TYPE = "HOST"

DEFAULT_INSTANCE_ID = "host|instance|host|127.0.0.1-0-0"

# ---------订阅任务id参数--------------
SUBSCRIPTION_ID = 61

SUBSCRIPTION_INSTANCE_RECORD_ID = 95

SUBSCRIPTION_TASK_ID = 91

SUBSCRIPTIONSTEP_ID = 101

SUBSCRIPTIONSTEP_STEP_ID = "basereport"

JOB_ID = 56

JOB_TASK_ID = 100

BK_HOST_ID = 23333

SERVICE_TEMPLATE_ID = 1
SERVICE_TEMPLATE_ID_2 = 2

# 当前原子任务id
JOB_TASK_PIPELINE_ID = "1ae89ce9deec319bbd8727a0c4b2ca82"

# 安装线的pipeline id
INSTANCE_RECORD_ROOT_PIPELINE_ID = "98d467d07e453e1b9f24e77c8c6743fb"

# 测试伪造ip
TEST_IP = "127.0.0.1"

# Job作业实例id
JOB_INSTANCE_ID = 10000

# 安装包ID
PKG_ID = 163

# ---------mock path--------------
PLUGIN_CLIENT_MOCK_PATH = "apps.backend.components.collections.plugin.JobApi"

JOB_JOBAPI = "apps.backend.components.collections.job.JobApi"

JOB_VERSION_MOCK_PATH = "apps.backend.api.job.settings.JOB_VERSION"

CMDB_CLIENT_MOCK_PATH = "apps.node_man.handlers.cmdb.client_v2"

PLUGIN_MULTI_THREAD_PATH = "apps.backend.components.collections.plugin.request_multi_thread"

JOB_MULTI_THREAD_PATH = "apps.backend.components.collections.job.request_multi_thread"

PLUGIN_GSEAPI = "apps.backend.components.collections.plugin.GseApi"
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
    "bk_host_id": BK_HOST_ID,
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
    "subscription_instance_ids": [],
    "subscription_step_id": "",
    "status": "",
    "enable": "",
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
    "enable": True,
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

PLUGIN_CONFIG_TEMPLATE_INFO = {
    "id": PKG_ID,
    "name": "basereport.conf",
    "is_main": True,
    "version": "1",
    "plugin_version": "*",
}

# basereport
PKG_PROJECT_NAME = "gseagent"
PKG_INFO = {
    "id": PKG_ID,
    "os": "linux",
    "module": "gse_plugin",
    "creator": DEFAULT_CREATOR,
    "project": PKG_PROJECT_NAME,
    "version": "10.8.50",
    "cpu_arch": "x86_64",
    "is_ready": True,
    "pkg_size": 1,
    "pkg_name": "basereport-10.8.50.tgz",
    "pkg_ctime": "2021-05-31 03:25:16.779281+00:00",
    "pkg_mtime": "2021-05-31 03:25:16.779281+00:00",
}

GSE_PLUGIN_DESC_INFO = {
    "name": PKG_PROJECT_NAME,
    "description": "description",
    "scenario": "",
    "category": const.CategoryType.official,
}

SUBSCRIPTION_STEP_PARAMS = {
    "id": SUBSCRIPTIONSTEP_ID,
    "subscription_id": SUBSCRIPTION_ID,
    "step_id": SUBSCRIPTIONSTEP_STEP_ID,
    "type": const.ProcType.PLUGIN,
    "config": {"details": [PKG_INFO]},
    "params": {
        "details": [
            {"context": {}, "os_type": "windows", "cpu_arch": "x86_64"},
            {"context": {}, "os_type": "linux", "cpu_arch": "x86_64"},
        ]
    },
}

PROCESS_STATUS_PARAMS = {
    "id": "",
    "name": PKG_PROJECT_NAME,
    "group_id": "",
    "bk_host_id": BK_HOST_ID,
    "status": const.ProcStateType.RUNNING,
    "proc_type": const.ProcType.PLUGIN,
    "configs": [],
}

PROC_CONTROL_INFO = {
    "id": "",
    "plugin_package_id": SUBSCRIPTION_ID,
    "install_path": "/usr/local/test",
    "log_path": "/var/lib/test",
    "data_path": "/var/lib/test",
    "pid_path": "/var/lib/test",
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
                            "bk_cloud_id": const.DEFAULT_CLOUD,
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


class GseMockClient:
    @classmethod
    def operate_proc_multi(cls, *args, **kwargs):
        return {"task_id": JOB_INSTANCE_ID}

    @classmethod
    def get_proc_operate_result(cls, *args, **kwargs):
        return {
            "result": True,
            "code": "",
            "data": {
                f"{const.DEFAULT_CLOUD}:{TEST_IP}:{const.GSE_NAMESPACE}:{PKG_PROJECT_NAME}": {
                    "error_code": GseDataErrCode.SUCCESS,
                    "error_msg": "",
                }
            },
        }


class CmdbClient:
    class cc:
        @classmethod
        def get_mainline_object_topo(cls, *args, **kwargs):
            return [
                {"bk_obj_id": "biz"},
                {"bk_obj_id": "set"},
                {"bk_obj_id": "module"},
                {"bk_obj_id": "host"},
            ]

        @classmethod
        def find_host_service_template(cls, *args, **kwargs):
            if len(args[0]["bk_host_id"]) > 1:
                # 模拟接口不存在的场景
                raise ComponentCallError()

            return [
                {
                    "bk_host_id": bk_host_id,
                    "service_template_id": [SERVICE_TEMPLATE_ID]
                    if bk_host_id == BK_HOST_ID
                    else [SERVICE_TEMPLATE_ID_2],
                }
                for bk_host_id in args[0]["bk_host_id"]
            ]


class JobMockClient:
    @classmethod
    def fast_transfer_file(cls, *args, **kwargs):
        return {"job_instance_name": "API Quick Distribution File1521101427176", "job_instance_id": JOB_INSTANCE_ID}

    @classmethod
    def get_job_instance_status(cls, *args, **kwargs):
        return {
            "finished": True,
            "job_instance": {
                "job_instance_id": JOB_INSTANCE_ID,
                "bk_biz_id": DEFAULT_BIZ_ID_NAME["bk_biz_id"],
                "status": const.BkJobIpStatus.SUCCEEDED,
            },
            "step_instance_list": [
                {
                    "status": const.BkJobIpStatus.SUCCEEDED,
                    "step_instance_id": 75,
                    "step_ip_result_list": [
                        {
                            "ip": TEST_IP,
                            "bk_cloud_id": const.DEFAULT_CLOUD,
                            "status": const.BkJobIpStatus.SUCCEEDED,
                            "error_code": 0,
                        }
                    ],
                }
            ],
        }

    @classmethod
    def fast_execute_script(cls, *args, **kwargs):
        return {"job_instance_name": "API Quick execution script1521100521303", "job_instance_id": JOB_INSTANCE_ID}

    @classmethod
    def push_config_file(cls, *args, **kwargs):
        return

    @classmethod
    def get_job_instance_ip_log(cls, *args, **kwargs):
        return {"ip": TEST_IP, "bk_cloud_id": const.DEFAULT_CLOUD, "log_content": "job_start\n"}


def request_multi_thread_client(func, params_list):
    return [func(**parms) for parms in params_list]


class PluginTestObjFactory:
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
    def gse_plugin_des_obj(cls, obj_attr_values=None, is_obj=False):
        gse_plugin_des_params = copy.deepcopy(GSE_PLUGIN_DESC_INFO)
        cls.replace_obj_attr_values(gse_plugin_des_params, obj_attr_values)
        if not is_obj:
            gse_plugin_des_params.pop("id", None)
        return models.GsePluginDesc(**gse_plugin_des_params) if is_obj else gse_plugin_des_params

    @classmethod
    def process_status_obj(cls, obj_attr_values=None, is_obj=False):
        process_status_params = copy.deepcopy(PROCESS_STATUS_PARAMS)
        cls.replace_obj_attr_values(process_status_params, obj_attr_values)
        if not is_obj:
            process_status_params.pop("id", None)
        return models.ProcessStatus(**process_status_params) if is_obj else process_status_params

    @classmethod
    def subscription_step_record_obj(cls, obj_attr_values=None, config_attr_values=None, is_obj=False):
        subscription_step_record_params = copy.deepcopy(SUBSCRIPTION_STEP_PARAMS)
        config_params = copy.deepcopy(PKG_INFO)
        config_params["config_templates"] = [PLUGIN_CONFIG_TEMPLATE_INFO]
        if config_attr_values is not None:
            cls.replace_obj_attr_values(config_params, config_attr_values)
            subscription_step_record_params["config"]["details"] = [config_params]

        cls.replace_obj_attr_values(subscription_step_record_params, obj_attr_values)
        if not is_obj:
            subscription_step_record_params.pop("id", None)
        return models.SubscriptionStep(**subscription_step_record_params) if is_obj else subscription_step_record_params

    @classmethod
    def package_obj(cls, obj_attr_values=None, is_obj=False):
        pkg_params = copy.deepcopy(PKG_INFO)
        cls.replace_obj_attr_values(pkg_params, obj_attr_values)
        if not is_obj:
            pkg_params.pop("id", None)
        return models.Packages(**pkg_params) if is_obj else pkg_params

    @classmethod
    def proc_control_obj(cls, obj_attr_values=None, is_obj=False):
        proc_control_params = copy.deepcopy(PROC_CONTROL_INFO)
        cls.replace_obj_attr_values(proc_control_params, obj_attr_values)
        if not is_obj:
            proc_control_params.pop("id", None)
        return models.ProcControl(**proc_control_params) if is_obj else proc_control_params

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
    def init_db(cls, init_subscription_param=None):
        subscription_params = cls.subscription_obj(obj_attr_values=init_subscription_param)
        subscription = models.Subscription.objects.create(**subscription_params)

        subscription_task_params = cls.subscription_task_obj(obj_attr_values={"subscription_id": subscription.id})
        subscription_task = models.SubscriptionTask.objects.create(**subscription_task_params)

        subscription_instance_record_params = cls.subscription_instance_record_obj(
            obj_attr_values={"subscription_id": subscription.id, "task_id": subscription_task.id}
        )
        subscription_instance_record = models.SubscriptionInstanceRecord.objects.create(
            **subscription_instance_record_params
        )

        package_params = cls.package_obj()
        packages = models.Packages.objects.create(**package_params)

        subscription_step_params = cls.subscription_step_record_obj(
            obj_attr_values={"subscription_id": subscription.id}, config_attr_values={"id": packages.id}
        )
        subscription_step = SubscriptionStep.objects.create(**subscription_step_params)

        gse_plugin_des_params = cls.gse_plugin_des_obj()
        models.GsePluginDesc.objects.create(**gse_plugin_des_params)

        process_status_params = cls.process_status_obj(
            obj_attr_values={"group_id": create_group_id(subscription, subscription_instance_record.instance_info)}
        )
        models.ProcessStatus.objects.create(**process_status_params)

        job_params = cls.job_obj(
            obj_attr_values={"subscription_id": subscription.id, "task_id_list": [subscription_task.id]}
        )
        job = models.Job.objects.create(**job_params)

        job_task_params = cls.job_task_obj({"job_id": job.id})
        job_task = models.JobTask.objects.create(**job_task_params)

        proc_control_params = cls.proc_control_obj(obj_attr_values={"plugin_package_id": packages.id})
        models.ProcControl.objects.create(**proc_control_params)

        host_params = cls.host_obj()
        host = models.Host.objects.create(**host_params)

        identity_data_params = cls.identity_data_obj()
        models.IdentityData.objects.create(**identity_data_params)

        return {
            "subscription_id": subscription.id,
            "subscription_task_id": subscription_task.id,
            "subscription_instance_record_id": subscription_instance_record.id,
            "subscription_step_id": subscription_step.id,
            "job_id": job.id,
            "job_task_id": job_task.id,
            "bk_host_id": host.bk_host_id,
        }
