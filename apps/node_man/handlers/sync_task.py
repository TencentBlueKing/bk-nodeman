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
from apps.iam import Permission
from apps.iam.exceptions import PermissionDeniedError
from apps.node_man import constants
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.iam.handlers import resources
from apps.node_man.handlers.iam import IamHandler
from common.api import NodeApi


class SyncTaskHandler:
    @staticmethod
    def without_permission(bk_biz_id_list, iam_action):
        iam_resources = []
        for bk_biz_id in bk_biz_id_list:
            iam_resources.append(resources.Business.create_instance(bk_biz_id))
        apply_data, apply_url = Permission().get_apply_data([iam_action], iam_resources)
        raise PermissionDeniedError(action_name=iam_action, apply_url=apply_url, permission=apply_data)

    def sync_cmdb_host(self, params):
        bk_biz_id = params["bk_biz_id"]
        # 校验用户是否具有对应业务权限
        iam_action = constants.IamActionType.agent_operate
        user_biz = CmdbHandler().biz_id_name({"action": iam_action})

        if bk_biz_id and bk_biz_id not in user_biz:
            self.without_permission(bk_biz_id, iam_action)

        if bk_biz_id:
            all_biz = [biz_info["bk_biz_id"] for biz_info in IamHandler().fetch_biz()]
            biz_diff_set = list(set(all_biz) - set(user_biz))
            if biz_diff_set:
                self.without_permission(biz_diff_set, iam_action)

        return NodeApi.create_sync_task(**params)
