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
from kombu import Connection

from config.default import CELERY_QUEUES

from .checker import CheckerRegister

register = CheckerRegister.rabbitmq


@register.status()
def status(manager, result):
    """rabbitmq队列长度状态"""
    try:
        BROKER_URL = settings.BROKER_URL
        if not BROKER_URL.startswith("amqp://"):
            BROKER_URL = "amqp://guest:guest@localhost:5672//"
        conn = Connection(BROKER_URL)
        conn.connect()
        channel = conn.channel()
        block_queue_infos = []
        block_queue_flag = False
        for queue_info in CELERY_QUEUES:
            queue = channel.queue_declare(queue=queue_info.name, passive=True)
            message_count = queue.message_count
            # 记录阻塞的队列信息
            if message_count > settings.RABBITMQ_MAX_MESSAGE_COUNT:
                block_queue_flag = True
                block_queue_infos.append(f"【{queue_info.name}】 队列消息数为 {message_count}")
        if block_queue_flag:
            result.fail(message=block_queue_infos, value="")
        else:
            result.ok(message="", value="")
    except Exception as e:
        result.fail(message=f"获取rabbitmq队列信息失败，{e}", value="")
