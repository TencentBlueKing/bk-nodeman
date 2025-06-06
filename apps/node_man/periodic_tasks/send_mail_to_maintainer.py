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
import collections
from typing import Any, Dict, List, Set

from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings
from django.db.models import QuerySet

from apps.node_man import constants, models
from common.api import CCApi
from common.api.modules.taihu_apis import taihu_client
from common.log import logger


def send_mail_to_maintainer(task_id):
    logger.info(f"start send_mail_to_maintainer, task_id -> {task_id}")

    query_kwargs = {"fields": ["bk_biz_id", "bk_biz_name", "bk_biz_maintainer"]}
    try:
        biz_infos: List[Dict[str, Any]] = CCApi.search_business(query_kwargs)["info"]
        # 去除业务运维为空的数据
        biz_infos: List[Dict[str, Any]] = [biz_info for biz_info in biz_infos if biz_info["bk_biz_maintainer"]]
        # 构建成业务ID映射业务信息字典
        biz_id_biz_info_map: Dict[int, Dict[str, Any]] = {biz_info["bk_biz_id"]: biz_info for biz_info in biz_infos}
    except Exception as e:
        logger.exception(f"get business info error: {str(e)}")
        return

    # 异常Agent HostID
    terminated_agent: QuerySet = models.ProcessStatus.objects.filter(
        status=constants.ProcStateType.TERMINATED, name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME
    ).values_list("bk_host_id", flat=True)
    # 异常bkmonitorbeat HostID
    terminated_plugin: QuerySet = models.ProcessStatus.objects.filter(
        status=constants.ProcStateType.TERMINATED, name="bkmonitorbeat"
    ).values_list("bk_host_id", flat=True)

    agent_counter, plugin_counter = collections.Counter(), collections.Counter()

    for chunk_size in range(0, terminated_agent.count(), constants.PROC_CHUNK_SIZE):
        bulk_terminated_agent: Set[int] = set(terminated_agent[chunk_size : chunk_size + constants.PROC_CHUNK_SIZE])
        bk_biz_ids = models.Host.objects.filter(bk_host_id__in=bulk_terminated_agent).values_list(
            "bk_biz_id", flat=True
        )

        agent_counter.update(collections.Counter(bk_biz_ids))

    for chunk_size in range(0, terminated_plugin.count(), constants.PROC_CHUNK_SIZE):
        bulk_terminated_plugin: Set[int] = set(terminated_plugin[chunk_size : chunk_size + constants.PROC_CHUNK_SIZE])
        bk_biz_ids = models.Host.objects.filter(bk_host_id__in=bulk_terminated_plugin).values_list(
            "bk_biz_id", flat=True
        )
        plugin_counter.update(collections.Counter(bk_biz_ids))

    final_handle_biz = set(agent_counter.keys()) | set(plugin_counter.keys())
    biz_blacklist = models.GlobalSettings.get_config(
        key=models.GlobalSettings.KeyEnum.SEND_MAIL_BIZ_BLACKLIST.value, default=[]
    )
    for bk_biz_id in final_handle_biz:
        biz_info = biz_id_biz_info_map.get(bk_biz_id)
        # 没有运维信息的业务、在黑名单中的不发送邮件
        if not biz_info or bk_biz_id in biz_blacklist:
            continue
        biz_name = biz_info["bk_biz_name"]
        biz_maintainer = biz_info["bk_biz_maintainer"]
        try:
            taihu_client.send_mail(
                to=biz_maintainer,
                title="业务-{}-ID-{}:Agent-bkmonitorbeat状态异常通知".format(biz_name, bk_biz_id),
                content="Agent异常数量: {}, bkmonitorbeat异常数量: {}, 详情点击<a href={} target='_blank'>节点管理</a>".format(
                    agent_counter[bk_biz_id], plugin_counter[bk_biz_id], settings.BK_NODEMAN_URL
                ),
            )
        except Exception as e:
            logger.exception(f"bk_biz_id -> {bk_biz_id} send mail to maintainer error: {str(e)}")
            continue

    logger.info(f"send mail to maintainer success, task_id -> {task_id}")


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(hour="9", minute="0", day_of_week="*", day_of_month="*", month_of_year="*"),
)
def send_mail_to_maintainer_periodic_task():
    """定时发送邮件给运维"""
    task_id = send_mail_to_maintainer_periodic_task.request.id
    send_mail_to_maintainer(task_id)
