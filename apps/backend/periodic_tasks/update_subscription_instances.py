# -*- coding: utf-8 -*-
import logging

from celery.task import periodic_task

from apps.backend.subscription.constants import SUBSCRIPTION_UPDATE_INTERVAL
from apps.backend.subscription.tasks import update_subscription_instances_chunk
from apps.node_man import models
from apps.utils.periodic_task import calculate_countdown

logger = logging.getLogger("celery")


@periodic_task(
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

    subscription_ids = list(
        models.Subscription.objects.filter(enable=True, is_deleted=False).values_list("id", flat=True)
    )
    count = len(subscription_ids)
    for index, subscription_id in enumerate(subscription_ids):
        # 把订阅平均分布到10分钟内执行，用于削峰
        countdown = calculate_countdown(count=count, index=index, duration=SUBSCRIPTION_UPDATE_INTERVAL)
        logger.info(f"subscription({subscription_id}) will be run after {countdown} seconds.")
        update_subscription_instances_chunk.apply_async(([subscription_id],), countdown=countdown)
