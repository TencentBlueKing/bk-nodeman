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
import logging
import random
import time
import typing
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.db.utils import IntegrityError

from apps.backend.subscription.tools import (
    by_biz_dispatch_task_queue,
    get_biz_ids_gby_queue,
)
from apps.component.esbclient import client_v2
from apps.node_man import constants
from apps.node_man.models import GlobalSettings, Host, ResourceWatchEvent, Subscription
from apps.prometheus import metrics
from apps.utils.cache import format_cache_key

logger = logging.getLogger("app")

RESOURCE_WATCH_HOST_CURSOR_KEY = "resource_watch_host_cursor"
RESOURCE_WATCH_HOST_RELATION_CURSOR_KEY = "resource_watch_host_relation_cursor"
RESOURCE_WATCH_PROCESS_CURSOR_KEY = "resource_watch_process_cursor"
APPLY_RESOURCE_WATCHED_EVENTS_KEY = "apply_resource_watched_events"


class BaseEventPreprocessHelper:
    @staticmethod
    def get_scope_from_event(event: typing.Dict) -> typing.Any:
        """
        从事件中获取 scope，目前仅考虑业务ID，后续可按场景扩展
        :param event:
        :return:
        """
        return event["bk_detail"].get("bk_biz_id")

    @staticmethod
    def fill_scope_to_event(events: typing.List[typing.Dict]):
        """
        填充 scope 到事件
        :param events:
        :return:
        """
        pass

    @classmethod
    def event_convergence(cls, events: typing.List[typing.Dict]) -> typing.List[typing.Dict]:
        """
        事件收敛
        :param events:
        :return:
        """
        scope__event_map: typing.Dict[typing.Any, typing.Dict] = {}
        for event in events:
            scope: int = cls.get_scope_from_event(event)
            if scope:
                # 对相同的 scope 仅保留一则数据
                scope__event_map[scope] = event
        return list(scope__event_map.values())

    @classmethod
    def do_preprocess(cls, events: typing.List[typing.Dict]) -> typing.List[typing.Dict]:
        cls.fill_scope_to_event(events)
        return cls.event_convergence(events)


class HostEventPreprocessHelper(BaseEventPreprocessHelper):
    @staticmethod
    def fill_scope_to_event(events: typing.List[typing.Dict]):
        """
        填充 scope 到事件
        :param events:
        :return:
        """
        host_ids: typing.Set[int] = {event["bk_detail"]["bk_host_id"] for event in events}
        if not host_ids:
            return

        # 从 DB 取出主机ID对应的业务ID
        # DB 主机属于缓存，不准确但大致有参考意义
        # - 新增：触发的事件属于 host_relation，即使无业务ID也会被其他类型事件消费
        # - 删除 / 更新：可以获取到更新前的业务快照
        host_infos: typing.List[typing.Dict] = Host.objects.filter(bk_host_id__in=host_ids).values(
            "bk_biz_id", "bk_host_id"
        )
        host_id__biz_id_map: typing.Dict[int, int] = {}
        # 构建主机ID - 业务关联关系
        for host_info in host_infos:
            host_id__biz_id_map[host_info["bk_host_id"]] = host_info["bk_biz_id"]
        # 没有关联关系，提前返回
        if not host_id__biz_id_map:
            return
        # 填充业务ID到事件
        for event in events:
            bk_biz_id: typing.Optional[int] = host_id__biz_id_map.get(event["bk_detail"]["bk_host_id"])
            if bk_biz_id:
                event["bk_detail"]["bk_biz_id"] = bk_biz_id


RESOURCE_TYPE__EVENT_HELPER_MAP: typing.Dict[str, typing.Type[BaseEventPreprocessHelper]] = {
    constants.ResourceType.host: HostEventPreprocessHelper,
    constants.ResourceType.process: BaseEventPreprocessHelper,
    constants.ResourceType.host_relation: BaseEventPreprocessHelper,
}


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

    logger.info(f"[{cursor_key}] start: id_key -> {id_key}")

    while True:
        if not is_lock(cursor_key, id_key):
            logger.error(f"[{cursor_key}] failed to get lock: id_key -> {id_key}")
            time.sleep(60)
            logger.info(f"[{cursor_key}] will try to acquire the lock, if there is no error output, it means listening")
            continue

        bk_cursor = cache.get(cursor_key)
        if bk_cursor:
            kwargs["bk_cursor"] = bk_cursor

        data = client_v2.cc.resource_watch(kwargs)
        if not data["bk_watched"]:
            # 记录最新cursor
            set_cursor(data, cursor_key)
            continue

        event_helper: typing.Type[BaseEventPreprocessHelper] = RESOURCE_TYPE__EVENT_HELPER_MAP[kwargs["bk_resource"]]

        objs = [
            ResourceWatchEvent(
                bk_cursor=event["bk_cursor"],
                bk_event_type=event["bk_event_type"],
                bk_resource=event["bk_resource"],
                bk_detail=event["bk_detail"],
            )
            for event in event_helper.do_preprocess(data["bk_events"])
        ]
        ResourceWatchEvent.objects.bulk_create(objs)

        for obj in objs:
            metrics.app_resource_watch_events_total.labels(
                type="producer", bk_resource=obj.bk_resource, bk_event_type=obj.bk_event_type
            ).inc()

        logger.info(f"[{cursor_key}] receive new resource watch event: count -> {len(objs)}")

        # 记录最新cursor
        set_cursor(data, cursor_key)


def sync_resource_watch_host_event():
    """
    拉取主机事件
    """
    kwargs = {
        "bk_resource": constants.ResourceType.host,
        "bk_fields": ["bk_host_innerip", "bk_os_type", "bk_host_id", "bk_cloud_id", "bk_host_outerip"],
    }

    _resource_watch(RESOURCE_WATCH_HOST_CURSOR_KEY, kwargs)


def sync_resource_watch_host_relation_event():
    """
    拉取主机关系事件
    """
    kwargs = {"bk_resource": constants.ResourceType.host_relation}

    _resource_watch(RESOURCE_WATCH_HOST_RELATION_CURSOR_KEY, kwargs)


def sync_resource_watch_process_event():
    """
    拉取进程
    """
    kwargs = {"bk_resource": constants.ResourceType.process}
    _resource_watch(RESOURCE_WATCH_PROCESS_CURSOR_KEY, kwargs)


def apply_resource_watched_events():
    def _get_event_str(_event):
        return "<Event({bk_cursor}) info -> [{bk_event_type}|{bk_resource}|{bk_biz_id}]>".format(
            bk_cursor=_event["bk_cursor"],
            bk_event_type=event["bk_event_type"],
            bk_resource=event["bk_resource"],
            bk_biz_id=event["bk_detail"].get("bk_biz_id"),
        )

    id_key = random_key()
    config_key = APPLY_RESOURCE_WATCHED_EVENTS_KEY

    logger.info(f"[{config_key}] start: id_key -> {id_key}")

    while True:

        if not is_lock(config_key, id_key):
            logger.error(f"[{config_key}] failed to get lock: id_key -> {id_key}")
            time.sleep(60)
            logger.info(f"[{config_key}] will try to acquire the lock, if there is no error output, it means listening")
            continue

        apply_resource_watched_events_controller = GlobalSettings.get_config(
            GlobalSettings.KeyEnum.APPLY_RESOURCE_WATCHED_EVENTS_CONTROLLER_KEY.value
        )
        if not apply_resource_watched_events_controller:
            apply_resource_watched_events_controller = {"limit": 10, "seconds_to_wait_for_no_events": 10}
            GlobalSettings.set_config(
                GlobalSettings.KeyEnum.APPLY_RESOURCE_WATCHED_EVENTS_CONTROLLER_KEY.value,
                apply_resource_watched_events_controller,
            )

        logger.info(f"[{config_key}] load events_controller -> {apply_resource_watched_events_controller}")

        events = ResourceWatchEvent.objects.order_by("create_time")[
            0 : apply_resource_watched_events_controller["limit"]
        ].values()
        if not events:
            time.sleep(apply_resource_watched_events_controller["seconds_to_wait_for_no_events"])
            continue

        events_after_convergence = HostEventPreprocessHelper.event_convergence(events)

        logger.info(f"[{config_key}] length of events_after_convergence -> {len(events_after_convergence)}")
        for event in events_after_convergence:
            event_str = _get_event_str(event)
            event_bk_biz_id = event["bk_detail"].get("bk_biz_id")
            metrics.app_resource_watch_events_total.labels(type="convergence", bk_resource="-", bk_event_type="-").inc()
            logger.info(f"[{config_key}] event being consumed -> {event_str}")
            try:
                if event_bk_biz_id:
                    metrics.app_resource_watch_biz_events_total.labels(bk_biz_id=event_bk_biz_id).inc()
                if event_bk_biz_id:
                    # 触发同步CMDB
                    trigger_sync_cmdb_host(bk_biz_id=event_bk_biz_id)

                if event_bk_biz_id and settings.USE_CMDB_SUBSCRIPTION_TRIGGER:
                    try:
                        # 触发订阅
                        trigger_nodeman_subscription(event_bk_biz_id)
                    except Exception as e:
                        logger.exception(
                            f"[trigger_nodeman_subscription] failed: bk_biz_id -> {event_bk_biz_id}, " f"error -> {e}"
                        )

            except Exception as err:
                logger.exception(f"[{config_key}] failed: event -> {event_str}, error -> {err}")

        # 删除事件记录
        ResourceWatchEvent.objects.filter(bk_cursor__in=[event["bk_cursor"] for event in events]).delete()
        for event in events:
            metrics.app_resource_watch_events_total.labels(
                type="consumer", bk_resource=event["bk_resource"], bk_event_type=event["bk_event_type"]
            ).inc()


def func_debounce_decorator(func):
    """
    函数防抖装饰器
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = format_cache_key(func, *args, **kwargs)
        debounce_flag_key = f"debounce_flag__{cache_key}"
        debounce_window_key = f"debounce_window__{cache_key}"

        is_debounced = cache.get(debounce_flag_key)
        debounce_time = cache.get(debounce_window_key, 0)

        if is_debounced:
            # 已经有待执行的任务在队列中，触发了防抖机制，则直接退出
            logger.info(
                f"[{func.__name__}] with params {args}, {kwargs} is debounced, " f"debounce_time->({debounce_time})"
            )
            return

        def cal_next_debounce_window(current_time):
            """
            计算出下一次的防抖窗口
            """
            windows = constants.CMDB_SUBSCRIPTION_DEBOUNCE_WINDOWS

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

        func_result = func(*args, **kwargs, debounce_time=debounce_time)

        # 设置 debounce_flag_key 声明已经开始了防抖，过期时间为 debounce_time。即当上面的celery任务开始执行后，防抖限制解除
        cache.set(debounce_flag_key, True, debounce_time)

        # 设置 debounce_window_key 声明限流
        # 当在防抖窗口的时间范围内又触发了变更，会导致防抖窗口的增加。避免过于频繁地触发变更
        # 当超出了防抖窗口的事件发生变更，防抖窗口就会重新计算
        cache.set(debounce_window_key, debounce_time, debounce_window)

        logger.info(
            f"[{func.__name__}] with params {args}, {kwargs}."
            f"debounce windows refreshed->({debounce_time}/{debounce_window}), "
        )

        return func_result

    return wrapper


@func_debounce_decorator
def trigger_sync_cmdb_host(bk_biz_id, debounce_time=0):
    """
    主动触发CMDB主机同步，复用周期任务的同步逻辑，保证结果的一致性
    :param bk_biz_id: 业务ID
    :param debounce_time: 防抖时间
    """
    from apps.node_man.periodic_tasks.sync_cmdb_host import sync_cmdb_host_periodic_task

    metrics.app_resource_watch_trigger_total.labels(
        method="sync_cmdb_host", bk_biz_id=bk_biz_id, debounce_time=debounce_time
    ).inc()
    sync_cmdb_host_periodic_task.apply_async(kwargs={"bk_biz_id": bk_biz_id}, countdown=debounce_time)

    logger.info(f"[trigger_sync_cmdb_host] bk_biz_id -> {bk_biz_id} will be run after {debounce_time} s")


@func_debounce_decorator
def trigger_nodeman_subscription(bk_biz_id, debounce_time=0):
    """
    主动触发节点管理订阅变更
    :param bk_biz_id: 业务ID
    :param debounce_time: 防抖时间
    """
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

    metrics.app_resource_watch_trigger_total.labels(
        method="subscription", bk_biz_id=bk_biz_id, debounce_time=debounce_time
    ).inc()

    biz_ids_gby_queue = get_biz_ids_gby_queue()
    task_queue: str = by_biz_dispatch_task_queue(biz_ids_gby_queue, [bk_biz_id])

    update_subscription_instances_chunk.apply_async(
        kwargs={"subscription_ids": subscription_ids}, countdown=debounce_time, queue=task_queue
    )

    logger.info(
        f"[trigger_nodeman_subscription] following subscriptions "
        f"will be run -> ({subscription_ids}) after {debounce_time} s"
        f" in queue -> ({task_queue})"
    )
