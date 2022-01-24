# coding: utf-8
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""


from django.conf import settings
from django.db import close_old_connections, connection

from .checker import CheckerRegister

register = CheckerRegister.database


@register.status()
def status(manager, result):
    """数据库状态"""
    close_old_connections()
    connection.connect()
    if connection.is_usable():
        result.ok(value="ok")
    else:
        result.fail(message="connection is not usable", value=False)

    with connection.cursor() as cursor:
        cursor.execute(f"select * FROM information_schema.processlist where db='{settings.APP_CODE}'")
        rows = cursor.fetchall()
        for row in rows:
            command, time, state = row[4], row[5], row[6]
            first_condition = command != "Sleep"
            second_condition = time > 60
            third_condition = state
            if all([first_condition, second_condition, third_condition]):
                result.fail(
                    message="Slow query exists",
                    value="The sql({}) has been executed for {} seconds".format(row[-1], time),
                )
