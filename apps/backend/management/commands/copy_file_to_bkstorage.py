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

from __future__ import absolute_import, unicode_literals

import os
import threading
from queue import Queue
from typing import List, Optional

from django.core.management.base import BaseCommand

from apps.core.files.storage import get_storage
from apps.utils import files


def get_dir_files_to_queue(
    file_worker_queue: Queue, source_dir_path: str, ignored_dir_names: Optional[List[str]] = None
):
    """
    将目录下文件保存到队列
    :param file_worker_queue: FIFO队列
    :param source_dir_path: 源目录路径
    :param ignored_dir_names: 忽略的目录名称
    :return:
    """
    source_file_paths = files.fetch_file_paths_from_dir(dir_path=source_dir_path, ignored_dir_names=ignored_dir_names)

    for source_file_path in source_file_paths:
        # TODO 暂时过滤掉空文件，看后续如何处理
        if not os.path.getsize(source_file_path):
            continue

        file_worker_queue.put(source_file_path)


def copy_queue_files_to_storage(file_worker_queue: Queue, source_dir_path: str, target_dir_path: str):
    """
    从队列取出文件上传到制品库
    :param file_worker_queue: FIFO队列
    :param source_dir_path: 源目录路径
    :param target_dir_path: 目的目录路径
    :return:
    """
    while True:
        if file_worker_queue.empty():
            return

        storage = get_storage(file_overwrite=True)
        source_file_path = file_worker_queue.get(block=True, timeout=0.1)
        file_relative_path = source_file_path.replace(source_dir_path + os.path.sep, "")
        with open(source_file_path, mode="rb") as target_file_fs:
            target_file_path = os.path.join(target_dir_path, file_relative_path)
            storage.save(name=target_file_path, content=target_file_fs)

        file_worker_queue.task_done()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("source_path", help="请输入源地址", type=str)
        parser.add_argument("dest_path", help="请输入目的地址", type=str)
        parser.add_argument("-t", "--thread_num", help="请输入线程数量, 线程数不用过多, 主要受到带宽限制", type=int)
        parser.add_argument("-d", "--delete", help="删除指定目录文件(非递归删除, 仅作测试)")

    def handle(self, *args, **options):
        # start_time = time.time()
        source_path = options["source_path"]
        dest_path = options["dest_path"]
        thread_num = options.get("thread_num", 10)
        file_worker_queue = Queue(maxsize=0)

        if options.get("delete"):
            storage = get_storage(file_overwrite=True)
            to_delete_file_path = options.get("delete")
            for file in storage.listdir(to_delete_file_path)[1]:
                storage.delete(os.path.join(to_delete_file_path, file))
            return

        get_dir_files_to_queue(file_worker_queue, source_path)

        for _thread_index in range(thread_num):
            threading.Thread(
                target=copy_queue_files_to_storage, args=(file_worker_queue, source_path, dest_path, _thread_index)
            ).start()

        # file_worker_queue.join()
        # end_time = time.time()
