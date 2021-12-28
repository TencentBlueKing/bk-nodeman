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

from functools import wraps
from unittest.mock import patch

from django.core.cache import cache

from apps.node_man.models import Host
from apps.node_man.periodic_tasks.resource_watch_task import (
    apply_resource_watched_events,
    sync_resource_watch_host_event,
    sync_resource_watch_host_relation_event,
    sync_resource_watch_process_event,
)
from apps.utils.unittest.testcase import CustomBaseTestCase

from . import mock_data
from .utils import MockClient


def exception_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TypeError:
            pass

    return wrapper


class TestResourceWatchTask(CustomBaseTestCase):
    def init_db(self):
        Host.objects.get_or_create(**mock_data.MOCK_HOST)

    @exception_handler
    def _apply_resource_watched_events(self):
        apply_resource_watched_events()

    # mock掉GlobalSettings.update_config是为了让循环函数只执行一次
    @patch("apps.node_man.periodic_tasks.resource_watch_task.GlobalSettings.update_config", InterruptedError)
    @patch("apps.node_man.periodic_tasks.resource_watch_task.client_v2", MockClient)
    def test_sync_resource_watch_host_event(self):
        self.init_db()

        @exception_handler
        def _sync_resource_watch_host_event():
            sync_resource_watch_host_event()

        _sync_resource_watch_host_event()
        self._apply_resource_watched_events()

        # 简单验证一下ip是否更改了, 从而证明了成功监视到数据更改并更新
        self.assertEqual(Host.objects.get(bk_host_id=mock_data.MOCK_HOST_ID).inner_ip, "127.0.0.9")

    @patch("apps.node_man.periodic_tasks.resource_watch_task.GlobalSettings.update_config", InterruptedError)
    @patch("apps.node_man.periodic_tasks.resource_watch_task.client_v2", MockClient)
    def test_sync_resource_watch_host_relation_event(self):
        @exception_handler
        def _sync_resource_watch_host_relation_event():
            sync_resource_watch_host_relation_event()

        _sync_resource_watch_host_relation_event()
        self._apply_resource_watched_events()

        # 验证是否成功创建了主机，从而证明了成功监视到host_relation
        self.assertEqual(Host.objects.filter(bk_biz_id=999).count(), 1)

    @patch("apps.node_man.periodic_tasks.resource_watch_task.GlobalSettings.update_config", InterruptedError)
    @patch("apps.node_man.periodic_tasks.resource_watch_task.client_v2", MockClient)
    def test_sync_resource_watch_process_event(self):
        @exception_handler
        def _sync_resource_watch_process_event():
            sync_resource_watch_process_event()

        _sync_resource_watch_process_event()
        self._apply_resource_watched_events()

        # 验证是否触发了订阅，从而证明是否监视进程改变
        bk_biz_id = 999
        debounce_window_key = f"subscription_debounce_window__biz__{bk_biz_id}"
        self.assertEqual(bool(cache.get(debounce_window_key)), True)
