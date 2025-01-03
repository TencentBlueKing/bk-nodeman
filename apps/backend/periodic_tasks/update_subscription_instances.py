# -*- coding: utf-8 -*-
import logging

from celery import current_app
from django.db.models import Value

from apps.backend.subscription.constants import SUBSCRIPTION_UPDATE_INTERVAL
from apps.backend.subscription.tasks import update_subscription_instances_chunk
from apps.backend.subscription.tools import (
    by_biz_dispatch_task_queue,
    get_biz_ids_gby_queue,
)
from apps.node_man import models
from apps.utils.periodic_task import calculate_countdown

logger = logging.getLogger("celery")


@current_app.task(
    run_every=SUBSCRIPTION_UPDATE_INTERVAL,
    queue="backend",  # 这个是用来在代码调用中指定队列的，例如： update_subscription_instances.delay()
    options={"queue": "backend"},  # 这个是用来celery beat调度指定队列的
)
def update_subscription_instances():
    """
    定时触发订阅任务
    """
    if not models.GlobalSettings.get_config("SUBSCRIPTION_TRIGGER", True):
        # 关闭订阅自动巡检
        return

    subscriptions = models.Subscription.objects.filter(enable=Value(1), is_deleted=Value(0)).values(
        "id", "bk_biz_id", "bk_biz_scope"
    )
    subscription_ids = [subscription["id"] for subscription in subscriptions]
    subscription_id__biz_ids_map = {
        subscription["id"]: subscription["bk_biz_scope"] + [subscription["bk_biz_id"]] for subscription in subscriptions
    }
    biz_ids_gby_queue = get_biz_ids_gby_queue()

    count = len(subscription_ids)
    for index, subscription_id in enumerate(subscription_ids):
        # 把订阅平均分布到10分钟内执行，用于削峰
        countdown = calculate_countdown(count=count, index=index, duration=SUBSCRIPTION_UPDATE_INTERVAL)
        task_queue = by_biz_dispatch_task_queue(biz_ids_gby_queue, subscription_id__biz_ids_map[subscription_id])
        logger.info(f"subscription({subscription_id}) will be run after {countdown} seconds in queue ({task_queue}).")
        update_subscription_instances_chunk.apply_async(([subscription_id],), countdown=countdown, queue=task_queue)
