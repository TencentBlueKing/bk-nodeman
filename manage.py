#!/usr/bin/env python
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
import os
import sys

if __name__ == "__main__":

    # if ('celery' in sys.argv) and ('worker' in sys.argv):
    #     sys.argv = [word for word in sys.argv if "autoscale" not in word] + \
    #                ["-P", "eventlet", "-c", "100"]
    #     from eventlet import monkey_patch
    #
    #     monkey_patch()
    #
    #     if ("beat" not in sys.argv) and ("celerybeat" not in sys.argv) and ("backend" not in sys.argv):
    #         try:
    #             Popen("/cache/.bk/env/bin/python /data/app/code/manage.py celery worker -Q backend".split())
    #         except Exception:
    #             pass

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
