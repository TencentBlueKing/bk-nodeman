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
import random
import time

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.db.utils import IntegrityError

from apps.component.esbclient import client_v2
from apps.node_man import constants as const
from apps.node_man.models import (
    AccessPoint,
    GlobalSettings,
    Host,
    IdentityData,
    ProcessStatus,
    ResourceWatchEvent,
    Subscription,
)
from apps.node_man.periodic_tasks.sync_cmdb_host import (
    _generate_host,
    update_or_create_host_base,
)

logger = logging.getLogger("app")

RESOURCE_WATCH_HOST_CURSOR_KEY = "resource_watch_host_cursor"
RESOURCE_WATCH_HOST_RELATION_CURSOR_KEY = "resource_watch_host_relation_cursor"
RESOURCE_WATCH_PROCESS_CURSOR_KEY = "resource_watch_process_cursor"
APPLY_RESOURCE_WATCHED_EVENTS_KEY = "apply_resource_watched_events"


def set_cursor(data, cursor_key):
    new_cursor = data["bk_events"][-1]["bk_cursor"]
    cache.set(cursor_key, new_cursor, 120)


def random_key():
    return "{}{}{}".format(
        int(time.time()), random.randint(10000, 99999), "".join(random.sample(str(int(time.time())), 5))
    )


def is_lock(config_key, id_key):
    """
    此函数用于多机部署时标识当前是否是自己在跑
    :param config_key: 数据库记录相关信息的键
    :param id_key: 标识自己的key
    """
    current_time = int(time.time())
    config = GlobalSettings.get_config(key=config_key, default={})
    if not config.get("key"):
        # 没有key开始抢占
        try:
            GlobalSettings.set_config(key=config_key, value={"key": id_key, "time": current_time})
        except IntegrityError:
            # 说明已被其它进程设置本进程不处理
            return False
    elif current_time - config["time"] > 60:
        # 说明key过期开始抢占
        # 先删除等待70s后创建以消除多机部署的时间差
        try:
            GlobalSettings.objects.get(key=config_key).delete()
        except GlobalSettings.DoesNotExist:
            pass

        # 防止同一进程瞬间创建
        time.sleep(70)

        try:
            GlobalSettings.set_config(key=config_key, value={"key": id_key, "time": int(time.time())})
        except IntegrityError:
            return False
    elif config["key"] != id_key:
        # 说明不是自己
        return False

    else:
        # 说明为自己更新key
        GlobalSettings.update_config(key=config_key, value={"key": id_key, "time": current_time})

    return True


def _resource_watch(cursor_key, kwargs):
    # 用于标识自己
    id_key = random_key()
    while True:
        if not is_lock(cursor_key, id_key):
            time.sleep(60)
            continue

        bk_cursor = cache.get(cursor_key)
        if bk_cursor:
            kwargs["bk_cursor"] = bk_cursor

        data = client_v2.cc.resource_watch(kwargs)
        if not data["bk_watched"]:
            # 记录最新cursor
            set_cursor(data, cursor_key)
            continue

        objs = []
        for event in data["bk_events"]:
            if cursor_key == RESOURCE_WATCH_HOST_RELATION_CURSOR_KEY and event["bk_event_type"] == "delete":
                # 不记录主机关系的删除事件
                continue
            objs.append(
                ResourceWatchEvent(
                    bk_cursor=event["bk_cursor"],
                    bk_event_type=event["bk_event_type"],
                    bk_resource=event["bk_resource"],
                    bk_detail=event["bk_detail"],
                )
            )
        ResourceWatchEvent.objects.bulk_create(objs)

        # 记录最新cursor
        set_cursor(data, cursor_key)


def sync_resource_watch_host_event():
    """
    拉取主机事件
    """
    kwargs = {
        "bk_resource": const.ResourceType.host,
        "bk_fields": ["bk_host_innerip", "bk_os_type", "bk_host_id", "bk_cloud_id", "bk_host_outerip"],
    }

    _resource_watch(RESOURCE_WATCH_HOST_CURSOR_KEY, kwargs)


def sync_resource_watch_host_relation_event():
    """
    拉取主机关系事件
    """
    kwargs = {
        "bk_resource": const.ResourceType.host_relation,
    }

    _resource_watch(RESOURCE_WATCH_HOST_RELATION_CURSOR_KEY, kwargs)


def sync_resource_watch_process_event():
    """
    拉取进程
    """
    kwargs = {"bk_resource": const.ResourceType.process}
    _resource_watch(RESOURCE_WATCH_PROCESS_CURSOR_KEY, kwargs)


def delete_host(bk_host_id):
    Host.objects.filter(bk_host_id=bk_host_id).delete()
    IdentityData.objects.filter(bk_host_id=bk_host_id).delete()
    ProcessStatus.objects.filter(bk_host_id=bk_host_id).delete()


def list_biz_host(bk_biz_id, bk_host_id):
    kwargs = {
        "bk_biz_id": bk_biz_id,
        "fields": ["bk_host_id", "bk_cloud_id", "bk_host_innerip", "bk_host_outerip", "bk_os_type", "bk_os_name"],
        "host_property_filter": {
            "condition": "AND",
            "rules": [{"field": "bk_host_id", "operator": "equal", "value": bk_host_id}],
        },
        "page": {"start": 0, "limit": 1},
    }
    data = client_v2.cc.list_biz_hosts(kwargs)
    if data.get("info") or []:
        return data["info"][0]
    return {}


def apply_resource_watched_events():
    id_key = random_key()
    config_key = APPLY_RESOURCE_WATCHED_EVENTS_KEY

    while True:

        if not is_lock(config_key, id_key):
            time.sleep(60)
            continue
        event = ResourceWatchEvent.objects.order_by("create_time").first()
        if not event:
            time.sleep(10)
            continue

        event_bk_biz_id = event.bk_detail.get("bk_biz_id")
        try:
            if event.bk_event_type in ["update", "create"] and event.bk_resource == const.ResourceType.host:
                _, need_delete_host_ids = update_or_create_host_base(None, None, [event.bk_detail])
                if need_delete_host_ids:
                    delete_host(need_delete_host_ids[0])
            elif event.bk_event_type in ["create"] and event.bk_resource == const.ResourceType.host_relation:
                # 查询主机信息创建或者更新
                bk_host_id = event.bk_detail["bk_host_id"]
                host_obj = Host.objects.filter(bk_host_id=bk_host_id).first()
                if host_obj:
                    if host_obj.bk_biz_id != event_bk_biz_id:
                        # 更新业务
                        host_obj.bk_biz_id = event_bk_biz_id
                        host_obj.save()
                else:
                    host = list_biz_host(event_bk_biz_id, bk_host_id)
                    if host:
                        ap_id = (
                            const.DEFAULT_AP_ID if AccessPoint.objects.count() > 1 else AccessPoint.objects.first().id
                        )
                        host_data, identify_data, process_status_data = _generate_host(
                            event_bk_biz_id, host, host["bk_host_innerip"], host["bk_host_outerip"], ap_id
                        )
                        # 与注册CC原子存在同时写入的可能，防止更新进行强制插入
                        try:
                            host_data.save(force_insert=True)
                            identify_data.save(force_insert=True)
                            process_status_data.save(force_insert=True)
                        except IntegrityError:
                            pass

            elif event.bk_event_type in ["delete"]:
                delete_host(event.bk_detail["bk_host_id"])

            if event_bk_biz_id and settings.USE_CMDB_SUBSCRIPTION_TRIGGER:
                try:
                    # 触发订阅
                    trigger_nodeman_subscription(event_bk_biz_id)
                except Exception as e:
                    logger.exception(
                        "[trigger_nodeman_subscription] bk_biz_id->({}) handler error: {}".format(
                            event.bk_detail["bk_biz_id"], e
                        )
                    )

        except Exception as err:
            logger.exception("apply_resource_watched_events events: {} error: {}".format(event.bk_detail, err))

        # 删除事件记录
        event.delete()


def trigger_nodeman_subscription(bk_biz_id):
    """
    主动触发节点管理订阅变更
    :param bk_biz_id: 业务ID
    """
    debounce_flag_key = f"subscription_debounce_flag__biz__{bk_biz_id}"
    debounce_window_key = f"subscription_debounce_window__biz__{bk_biz_id}"

    is_debounced = cache.get(debounce_flag_key)
    debounce_time = cache.get(debounce_window_key, 0)

    if is_debounced:
        # 已经有待执行的任务在队列中，触发了防抖机制，则直接退出
        logger.info(
            "[trigger_nodeman_subscription] bk_biz_id->({}) is debounced, "
            "debounce_time->({})".format(bk_biz_id, debounce_time)
        )
        return

    def cal_next_debounce_window(current_time):
        """
        计算出下一次的防抖窗口
        """
        windows = const.CMDB_SUBSCRIPTION_DEBOUNCE_WINDOWS

        if current_time < windows[0][0]:
            # 防抖时间下限
            return windows[0]

        if current_time > windows[-1][0]:
            # 防抖时间上限
            return windows[0]

        for index in range(len(windows) - 1):
            if windows[index][0] <= current_time < windows[index + 1][0]:
                return windows[index + 1]
        return windows[-1]

    debounce_time, debounce_window = cal_next_debounce_window(debounce_time)

    from apps.backend.subscription.tasks import update_subscription_instances_chunk

    # 获取当前业务的订阅ID，进行变更判断。使用celery变更将于 debounce_time 后执行
    subscription_ids = list(
        Subscription.objects.filter(Q(bk_biz_id=bk_biz_id) | Q(bk_biz_scope__contains=bk_biz_id))
        .filter(
            enable=True,
            is_deleted=False,
            node_type__in=[
                Subscription.NodeType.TOPO,
                Subscription.NodeType.SERVICE_TEMPLATE,
                Subscription.NodeType.SET_TEMPLATE,
            ],
        )
        .values_list("id", flat=True)
    )

    if not subscription_ids:
        logger.info("[trigger_nodeman_subscription] bk_biz_id->({}) no subscriptions to run".format(bk_biz_id))

    update_subscription_instances_chunk.apply_async(
        kwargs={"subscription_ids": subscription_ids}, countdown=debounce_time
    )

    # 设置 debounce_flag_key 声明已经开始了防抖，过期时间为 debounce_time。即当上面的celery任务开始执行后，防抖限制解除
    cache.set(debounce_flag_key, True, debounce_time)

    # 设置 debounce_window_key 声明限流
    # 当在防抖窗口的时间范围内又触发了变更，会导致防抖窗口的增加。避免过于频繁地触发变更
    # 当超出了防抖窗口的事件发生变更，防抖窗口就会重新计算
    cache.set(debounce_window_key, debounce_time, debounce_window)

    logger.info(
        "[trigger_nodeman_subscription] bk_biz_id->({}) debounce windows refreshed->({}/{}), "
        "following subscriptions will be run->({}),".format(bk_biz_id, debounce_time, debounce_window, subscription_ids)
    )
