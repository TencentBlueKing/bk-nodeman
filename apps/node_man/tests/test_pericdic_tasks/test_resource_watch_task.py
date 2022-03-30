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

from functools import wraps
from unittest import mock
from unittest.mock import MagicMock, patch

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

    @patch("apps.node_man.periodic_tasks.resource_watch_task.GlobalSettings.update_config", InterruptedError)
    @patch("apps.node_man.periodic_tasks.resource_watch_task.client_v2", MockClient)
    @patch("apps.node_man.periodic_tasks.resource_watch_task.trigger_sync_cmdb_host", MagicMock())
    def test_sync_resource_watch_host_relation_event(self):
        @exception_handler
        def _sync_resource_watch_host_relation_event():
            sync_resource_watch_host_relation_event()

        _sync_resource_watch_host_relation_event()
        self._apply_resource_watched_events()
        from apps.node_man.periodic_tasks.resource_watch_task import (
            trigger_sync_cmdb_host,
        )

        trigger_sync_cmdb_host.assert_has_calls([mock.call(bk_biz_id=999)])

    @patch("apps.node_man.periodic_tasks.resource_watch_task.GlobalSettings.update_config", InterruptedError)
    @patch("apps.node_man.periodic_tasks.resource_watch_task.client_v2", MockClient)
    def test_sync_resource_watch_process_event(self):
        @exception_handler
        def _sync_resource_watch_process_event():
            sync_resource_watch_process_event()

        _sync_resource_watch_process_event()
        self._apply_resource_watched_events()

        # 验证是否触发了订阅，从而证明是否监视进程改变
        debounce_window_key = "debounce_window__trigger_nodeman_subscription_404407a5290c409be67c50f4494f5f9f"
        self.assertEqual(bool(cache.get(debounce_window_key)), True)
