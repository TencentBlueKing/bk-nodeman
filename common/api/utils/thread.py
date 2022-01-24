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

import threading

from apps.utils.local import activate_request, get_request


class FuncThread(threading.Thread):
    def __init__(self, func, params, result_key, results):
        self.func = func
        self.params = params
        self.result_key = result_key
        self.results = results
        self.requests = get_request()
        super().__init__()

    def run(self):
        activate_request(self.requests)
        if self.params:
            self.results[self.result_key] = self.func(self.params)
        else:
            self.results[self.result_key] = self.func()


class MultiExecuteFunc(object):
    """
    基于多线程的批量并发执行函数
    """

    def __init__(self):
        self.results = {}
        self.task_list = []

    def append(self, result_key, func, params=None):
        if result_key in self.results:
            raise ValueError(f"result_key: {result_key} is duplicate. Please rename it.")
        task = FuncThread(func=func, params=params, result_key=result_key, results=self.results)
        self.task_list.append(task)
        task.start()

    def run(self):
        for task in self.task_list:
            task.join()
        return self.results
