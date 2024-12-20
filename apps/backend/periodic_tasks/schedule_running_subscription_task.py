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
import json
from datetime import timedelta
from typing import Any, Dict, List, Set

from celery.task import periodic_task
from django.db.models import QuerySet
from django.utils import timezone

from apps.backend import constants
from apps.backend.subscription.handler import SubscriptionHandler
from apps.backend.utils.redis import REDIS_INST
from apps.node_man import constants as node_man_constants
from apps.node_man import models
from common.log import logger


def get_need_clean_subscription_app_code():
    """
    获取配置需要清理的appcode
    """
    app_codes: List[str] = models.GlobalSettings.get_config(
        key=models.GlobalSettings.KeyEnum.NEED_CLEAN_SUBSCRIPTION_APP_CODE.value, default=[]
    )
    return app_codes


@periodic_task(run_every=constants.UPDATE_SUBSCRIPTION_TASK_INTERVAL, queue="backend", options={"queue": "backend"})
def schedule_update_subscription():
    logger.info("start schedule update subscription")
    name: str = constants.UPDATE_SUBSCRIPTION_REDIS_KEY_TPL
    # 取出该hashset中所有的参数
    update_params: Dict[str, bytes] = REDIS_INST.hgetall(name=name)
    # 删除该hashset内的所有参数
    REDIS_INST.delete(name)
    results = []
    if not update_params:
        return
    for update_param in update_params.values():
        # redis取出为bytes类型，需进行解码后转字典
        params = json.loads(update_param.decode())
        subscription_id = params["subscription_id"]
        try:
            result: Dict[str, int] = SubscriptionHandler.update_subscription(params=params)
        except Exception as e:
            logger.exception(f"{subscription_id} update subscription failed with error: {e}")
            result = {"subscription_id": subscription_id, "update_result": False}
        results.append(result)
    logger.info(f"update subscription with results: {results}, length -> {len(results)} ")


@periodic_task(run_every=constants.UPDATE_SUBSCRIPTION_TASK_INTERVAL, queue="backend", options={"queue": "backend"})
def schedule_run_subscription():
    logger.info("start schedule run subscription")
    name: str = constants.RUN_SUBSCRIPTION_REDIS_KEY_TPL
    length: int = min(REDIS_INST.llen(name), constants.MAX_RUN_SUBSCRIPTION_TASK_COUNT)
    run_params: List[bytes] = REDIS_INST.lrange(name, -length, -1)
    REDIS_INST.ltrim(name, 0, -length - 1)
    run_params.reverse()
    results = []
    if not run_params:
        return
    for run_param in run_params:
        # redis取出为bytes类型，需进行解码后转字典
        params = json.loads(run_param.decode())
        subscription_id = params["subscription_id"]
        scope = params["scope"]
        actions = params["actions"]
        try:
            result: Dict[str, int] = SubscriptionHandler(subscription_id).run(scope=scope, actions=actions)
        except Exception as e:
            logger.exception(f"{subscription_id} run subscription failed with error: {e}")
            result = {"subscription_id": subscription_id, "run_result": False}
        results.append(result)
    logger.info(f"run subscription with results: {results}, length -> {len(results)}")


@periodic_task(
    run_every=constants.HANDLE_UNINSTALL_REST_SUBSCRIPTION_TASK_INTERVAL,
    queue="default",
    options={"queue": "default"},
)
def clean_deleted_subscription():
    """
    清理被删除且有卸载残留的订阅
    """
    query_kwargs: Dict[str, Any] = {
        "is_deleted": True,
        "from_system": "bkmonitorv3",
        "deleted_time__range": (
            timezone.now() - timedelta(hours=constants.SUBSCRIPTION_DELETE_HOURS),
            timezone.now(),
        ),
    }

    # 卸载有残留的订阅开启订阅巡检的生命周期允许为12h，需要再次设置为软删，减少资源消耗
    again_delete_query_kwargs: Dict[str, Any] = {
        "enable": True,
        "from_system": "bkmonitorv3",
        "deleted_time__range": (
            timezone.now() - timedelta(hours=3 * constants.SUBSCRIPTION_DELETE_HOURS),
            timezone.now() - timedelta(hours=2 * constants.SUBSCRIPTION_DELETE_HOURS),
        ),
    }

    app_codes = get_need_clean_subscription_app_code()
    if app_codes:
        query_kwargs.pop("from_system")
        query_kwargs["from_system__in"] = app_codes
        again_delete_query_kwargs.pop("from_system")
        again_delete_query_kwargs["from_system__in"] = app_codes
    need_reset_deleted_subscription_qs: QuerySet = models.Subscription.objects.filter(**again_delete_query_kwargs)
    if need_reset_deleted_subscription_qs.exists():
        # 使用update方法，不会刷新删除时间
        need_reset_deleted_subscription_qs.update(enable=False, is_deleted=True)
        changed_subscription_ids = list(need_reset_deleted_subscription_qs.values_list("id", flat=True))
        # 记录再次被软删除的订阅ID
        logger.info(
            f"reset subscription{changed_subscription_ids} is_deleted, length -> {len(changed_subscription_ids)}"
        )
    # 查询6个小时内被删除的订阅
    subscription_qs: QuerySet = models.Subscription.objects.filter(**query_kwargs)

    if not subscription_qs.exists():
        # 没有被删除的订阅
        return
    # 被删除的订阅ID
    deleted_subscription_ids: Set[int] = set(subscription_qs.values_list("id", flat=True))
    # 被删除且卸载残留(失败)的订阅
    failed_subscription_qs: QuerySet = models.SubscriptionInstanceRecord.objects.filter(
        subscription_id__in=deleted_subscription_ids, is_latest=True, status=node_man_constants.StatusType.FAILED
    )
    if not failed_subscription_qs.exists():
        # 没有失败的订阅实例
        return
    # 被删除且有卸载残留的订阅ID
    failed_subscription_ids: Set[int] = set(failed_subscription_qs.values_list("subscription_id", flat=True))
    # 将订阅下的实例更新为空，并且开启订阅巡检
    models.Subscription.objects.filter(id__in=failed_subscription_ids, is_deleted=True).update(
        nodes=[], is_deleted=False, enable=True
    )

    logger.info(
        f"set {failed_subscription_ids} nodes be null and enable auto trigger, length -> {len(failed_subscription_ids)}"
    )
