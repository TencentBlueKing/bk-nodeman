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
from collections import ChainMap

from apps.node_man import constants, models

from .. import utils

DEFAULT_SUBSCRIPTION_ID = 1

DEFAULT_SUB_TASK_ID = 1


INSTANCE_INFO = {
    "host": {
        "set": [2],
        "module": [3],
        "operator": utils.DEFAULT_USERNAME,
        "bk_biz_id": utils.DEFAULT_BK_BIZ_ID,
        "bk_os_bit": "",
        "bk_host_id": 1,
        "bk_os_name": "",
        "bk_os_type": "1",
        "bk_biz_name": utils.DEFAULT_BK_BIZ_NAME,
        "bk_cloud_id": constants.DEFAULT_CLOUD,
        "bk_host_name": "",
        "bk_cpu_module": "",
        "bk_bak_operator": utils.DEFAULT_USERNAME,
        "bk_host_innerip": utils.DEFAULT_IP,
        "bk_host_outerip": utils.DEFAULT_IP,
        "bk_supplier_account": "0",
    },
    "process": {},
}

SUBSCRIPTION_MODEL_DATA = {
    "id": DEFAULT_SUBSCRIPTION_ID,
    # 软删除
    "is_deleted": False,
    "deleted_time": None,
    "deleted_by": None,
    # 订阅目标
    "bk_biz_id": utils.DEFAULT_BK_BIZ_ID,
    "object_type": models.Subscription.ObjectType.HOST,
    "node_type": models.Subscription.NodeType.TOPO,
    "nodes": [{"bk_biz_id": utils.DEFAULT_BK_BIZ_ID, "bk_obj_id": "biz", "bk_inst_id": utils.DEFAULT_BK_BIZ_ID}],
    "target_hosts": None,
    # 创建信息
    "from_system": "blueking",
    "update_time": "2021-07-09 05:03:40.750453+00:00",
    "create_time": "2021-07-08 08:20:19.827648+00:00",
    "creator": utils.DEFAULT_USERNAME,
    # 订阅属性
    "plugin_name": "bkmonitorbeat",
    "enable": False,
    "is_main": True,
    "category": None,
}

POLICY_MODEL_DATA = dict(
    ChainMap(
        {
            "name": "bkmonitorbeat-策略",
            "category": models.Subscription.CategoryType.POLICY,
            # 区别于普通订阅，策略支持多业务下发，业务通过bk_biz_scope指定
            "bk_biz_id": None,
            "bk_biz_scope": [1, 2, 3],
            "enable": True,
            "pid": -1,
        },
        SUBSCRIPTION_MODEL_DATA,
    )
)


SUB_AGENT_STEP_MODEL_DATA = {
    "id": 1,
    "subscription_id": DEFAULT_SUBSCRIPTION_ID,
    "step_id": constants.SubStepType.AGENT.lower(),
    "type": constants.SubStepType.AGENT,
    "config": {"job_type": constants.JobType.INSTALL_AGENT},
    "params": {"context": {}, "blueking_language": "zh-hans"},
}


SUB_TASK_MODEL_DATA = {
    "id": DEFAULT_SUB_TASK_ID,
    "subscription_id": DEFAULT_SUBSCRIPTION_ID,
    "scope": {
        "nodes": [{"bk_biz_id": 2, "bk_obj_id": "biz", "bk_inst_id": 2}],
        "bk_biz_id": None,
        "node_type": models.Subscription.NodeType.TOPO,
        "object_type": models.Subscription.ObjectType.HOST,
        "need_register": False,
    },
    "actions": {
        "host|instance|host|1": {"bkmonitorbeat": "MAIN_INSTALL_PLUGIN"},
        "host|instance|host|2": {"bkmonitorbeat": "MAIN_INSTALL_PLUGIN"},
        "host|instance|host|3": {"bkmonitorbeat": "MAIN_INSTALL_PLUGIN"},
        "host|instance|host|4": {"bkmonitorbeat": "MAIN_INSTALL_PLUGIN"},
    },
    "create_time": "2021-07-09 05:03:40.801614+00:00",
    "err_msg": None,
    "is_ready": True,
    "is_auto_trigger": False,
    "pipeline_id": "45f9d4adc1c24e499891c69bc80172bc",
}

SUB_INST_RECORD_MODEL_DATA = {
    "id": 1,
    "task_id": DEFAULT_SUB_TASK_ID,
    "subscription_id": DEFAULT_SUBSCRIPTION_ID,
    "is_latest": True,
    "instance_id": "host|instance|host|1",
    # 安装时，注册到cmdb后会插入bk_host_id
    "instance_info": INSTANCE_INFO,
    "steps": [
        {
            "id": "bkmonitorbeat",
            "type": constants.SubStepType.PLUGIN,
            "action": constants.JobType.MAIN_INSTALL_PLUGIN,
            "extra_info": {},
            "pipeline_id": "3341978fe1f33b2b99615818df5c7a89",
        }
    ],
    "pipeline_id": "3341978fe1f33b2b99615818df5c7a89",
}
