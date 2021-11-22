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
import os
import random
import threading
import time
from queue import Queue
from typing import List, Optional

from django.core.management.base import BaseCommand

from apps.core.files.storage import get_storage
from apps.utils import files

from . import utils

log_and_print = utils.get_log_and_print("copy_file_to_storage")


def add_dir_file_paths_to_queue(
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
        file_worker_queue.put(source_file_path)


def copy_files_to_storage(
    storage_type: str,
    file_worker_queue: Queue,
    source_dir_path: str,
    target_dir_path: str,
    file_num: int = str,
    is_delete: bool = False,
):
    """
    从队列取出文件上传到制品库
    :param storage_type: 存储源类型
    :param file_worker_queue: FIFO队列
    :param source_dir_path: 源目录路径
    :param target_dir_path: 目的目录路径
    :param file_num: 文件数量
    :param is_delete: 是否删除
    :return:
    """
    storage = get_storage(storage_type=storage_type, file_overwrite=True)

    while True:
        if file_worker_queue.empty():
            return
        source_file_path = file_worker_queue.get(block=True, timeout=0.1)
        file_relative_path = source_file_path.replace(source_dir_path + os.path.sep, "")
        target_file_path = os.path.join(target_dir_path, file_relative_path)
        if is_delete:
            try:
                storage.delete(name=target_file_path)
            except Exception:
                pass
        else:
            with open(source_file_path, mode="rb") as target_file_fs:
                storage.save(name=target_file_path, content=target_file_fs)

        if random.randint(1, 10) == 1:
            log_and_print(f"{format(((file_num - file_worker_queue.qsize()) / file_num) * 100, '.2f')} %")

        file_worker_queue.task_done()


class Command(BaseCommand):
    """
    上传文件压测 (16G 8核 317个文件 2.6G) - 蓝鲸制品库
    -t=1  cost_time -> 106.67s
    -t=1  cost_time -> 38s
    -t=5  cost_time -> 27.01s
    -t=10 cost_time -> 21.49s
    -t=15 cost_time -> 20.56s
    -t=20 cost_time -> 23.68s
    -t=25 cost_time -> 24.1s
    """

    def add_arguments(self, parser):
        parser.add_argument("--source_path", help="源目录路径", type=str)
        parser.add_argument("--dest_path", help="目标目录路径", type=str)
        parser.add_argument("--storage_type", help="存储类型", type=str)
        parser.add_argument("-t", "--thread_num", help="线程数量, 线程数不用过多, 主要受到带宽限制", type=int)
        parser.add_argument("--delete", action="store_true", help="是否删除目标源相关文件")

    def handle(self, *args, **options):
        start_time = time.time()
        source_path = options["source_path"]
        dest_path = options["dest_path"]
        storage_type = options["storage_type"]
        thread_num = options.get("thread_num", 10)

        # 文件名称入队
        file_worker_queue = Queue(maxsize=0)
        add_dir_file_paths_to_queue(
            file_worker_queue=file_worker_queue, source_dir_path=source_path, ignored_dir_names=["__pycache__"]
        )

        queue_size = file_worker_queue.qsize()
        log_and_print(f"pending files in queue: {queue_size}")

        for _thread_index in range(thread_num):
            threading.Thread(
                target=copy_files_to_storage,
                args=(storage_type, file_worker_queue, source_path, dest_path, queue_size, options["delete"]),
            ).start()

        # 阻塞直到所有进程执行结束
        file_worker_queue.join()

        end_time = time.time()
        log_and_print(f"cost_time -> {round(end_time - start_time, 2)}s")
