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

from asgiref.sync import SyncToAsync
from django.db import DEFAULT_DB_ALIAS, connections


def inside_transaction(using=None):
    """
    判断是否处于事务中
    :param using:
    :return:
    """
    if using is None:
        using = DEFAULT_DB_ALIAS
    return connections[using].in_atomic_block


def close_old_connections(*args, **kwargs):
    """
    关闭无用 DB 连接
    保留位置参数和关键字传输，以适配 hook
    :param args:
    :param kwargs:
    :return:
    """
    # 事务内不关闭连接，避免抛出 django.db.transaction.TransactionManagementError
    if inside_transaction():
        return
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()


class SyncToAsyncWithDbConnsClean(SyncToAsync):
    """
    带有清理 DB 旧连接的协程适配器
    asgiref.sync.sync_to_async 仅在 MySQL 连接存活情况下可用，易引发 MySQL server has gone away
    """

    def thread_handler(self, loop, *args, **kwargs):
        close_old_connections()
        try:
            return super().thread_handler(loop, *args, **kwargs)
        finally:
            close_old_connections()


sync_to_async = SyncToAsyncWithDbConnsClean
