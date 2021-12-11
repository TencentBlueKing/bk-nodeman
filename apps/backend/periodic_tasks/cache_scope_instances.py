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
import logging

from celery.task import periodic_task, task
from django.core.cache import caches

from apps.backend.subscription import constants, tools
from apps.node_man import models
from apps.utils.md5 import count_md5
from apps.utils.periodic_task import calculate_countdown

logger = logging.getLogger("celery")
cache = caches["db"]


@task(queue="default", ignore_result=True)
def get_instances_by_scope_task(subscription_id):
    subscription = models.Subscription.objects.get(id=subscription_id)
    scope_md5 = count_md5(subscription.scope)
    logger.info(
        f"[cache_scope_instances] (subscription: {subscription_id}) start."
        f" scope_md5: {scope_md5}, scope: {subscription.scope}"
    )
    # 查询后会进行缓存，详见 get_instances_by_scope 的装饰器 func_cache_decorator
    tools.get_instances_by_scope(subscription.scope)
    logger.info(f"[cache_subscription_scope_instances] (subscription: {subscription_id}) end.")


@periodic_task(
    run_every=constants.SUBSCRIPTION_UPDATE_INTERVAL,
    queue="backend",
    options={"queue": "backend"},
)
def cache_scope_instances():
    """定时缓存订阅范围实例，用于提高 instance_status、statistics 等接口的速度"""
    subscriptions = models.Subscription.objects.filter(enable=True, is_deleted=False)
    count = subscriptions.count()
    for index, subscription in enumerate(subscriptions):
        countdown = calculate_countdown(count=count, index=index, duration=constants.SUBSCRIPTION_UPDATE_INTERVAL)
        logger.info(f"[cache_scope_instances] ({subscription.id}) will be run after {countdown} seconds.")
        get_instances_by_scope_task.apply_async((subscription.id,), countdown=countdown)
