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
from ..base import ComponentAPI


class CollectionsGSE(object):
    """Collections of GSE APIS"""

    def __init__(self, client):
        self.client = client

        self.get_agent_info = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/get_agent_info/",
            description=u"Agent心跳信息查询",
        )
        self.get_agent_status = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/get_agent_status/",
            description=u"Agent在线状态查询",
        )
        self.get_proc_operate_result = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/get_proc_operate_result/",
            description=u"查询进程操作结果",
        )
        self.get_proc_status = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/get_proc_status/",
            description=u"查询进程状态信息",
        )
        self.operate_proc = ComponentAPI(
            client=self.client, method="POST", path="/api/c/compapi{bk_api_ver}/gse/operate_proc/", description=u"进程操作"
        )
        self.register_proc_info = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/register_proc_info/",
            description=u"注册进程信息",
        )
        self.unregister_proc_info = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/unregister_proc_info/",
            description=u"注销进程信息",
        )
        self.proc_create_session = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/proc_create_session/",
            description=u"进程管理：新建 session",
        )
        self.proc_get_task_result_by_id = ComponentAPI(
            client=self.client,
            method="GET",
            path="/api/c/compapi{bk_api_ver}/gse/proc_get_task_result_by_id/",
            description=u"进程管理：获取任务结果",
        )
        self.proc_run_command = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/proc_run_command/",
            description=u"进程管理：执行命令",
        )
        self.update_proc_info = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/update_proc_info/",
            description=u"进程管理：更新进程信息",
        )
        self.get_proc_status = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/get_proc_status/",
            description="查询进程状态",
        )
        self.sync_proc_status = ComponentAPI(
            client=self.client,
            method="POST",
            path="/api/c/compapi{bk_api_ver}/gse/sync_proc_status/",
            description="同步进程状态",
        )
