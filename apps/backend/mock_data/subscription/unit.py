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

from apps.node_man import models

POLICY_MODEL_DATA = {
    "id": 1154,
    "is_deleted": False,
    "deleted_time": None,
    "deleted_by": None,
    "name": "bkmonitorbeat-策略",
    "bk_biz_id": None,
    "object_type": models.Subscription.ObjectType.HOST,
    "node_type": models.Subscription.NodeType.TOPO,
    "nodes": [{"bk_biz_id": 2, "bk_obj_id": "biz", "bk_inst_id": 2}],
    "target_hosts": None,
    "from_system": "blueking",
    "update_time": "2021-07-09 05:03:40.750453+00:00",
    "create_time": "2021-07-08 08:20:19.827648+00:00",
    "creator": "admin",
    "enable": True,
    "is_main": True,
    "category": models.Subscription.CategoryType.POLICY,
    "plugin_name": "bkmonitorbeat",
    "bk_biz_scope": [1, 2, 3],
    "pid": -1,
}


SUB_TASK_MODEL_DATA = {
    "id": 683196,
    "subscription_id": 1154,
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
