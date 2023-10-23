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
import sys

import env


def monitor_report_config():
    boot_cmd = " ".join(sys.argv)
    print(boot_cmd)
    if "celery -A apps.backend worker" in boot_cmd:
        try:
            q_conf_index = sys.argv.index("-Q")
        except ValueError as e:
            sys.stdout.write(
                "[!]can't found -Q option in command: %s, skip celery monitor report config: %s\n" % (boot_cmd, e)
            )
            return

        try:
            queues = sys.argv[q_conf_index + 1]
        except IndexError as e:
            sys.stdout.write(
                "[!]can't found -Q value in command: %s, skip celery monitor report config: %s\n" % (boot_cmd, e)
            )
            return

        # 只对存在以下队列的情况进行上报
        monitor_queues = ["backend", "backend_additional_task", "default", "service_schedule", "pipeline_priority"]
        if not any([monitor_queue in queues for monitor_queue in monitor_queues]):
            sys.stdout.write("[!]can't found er queue in command: %s, skip celery monitor report config\n" % boot_cmd)
            return

        proc_type = "celery"
        try:
            n_conf_index = sys.argv.index("-n")
        except ValueError as e:
            # 没有 get 到，说明是单 workers 场景
            instance_tmpl = "celery@%h-%i"
            sys.stdout.write("[!]can't found -n option in command: %s, use default -> celery@xxx: %s\n" % (boot_cmd, e))
        else:
            # %i 区分单 workers 多进程的情况
            # -n 区分单主机多 workers 的情况
            instance_tmpl = sys.argv[n_conf_index + 1] + "-%i"

        from bk_monitor_report.contrib.celery import MonitorReportStep  # noqa

        from apps.backend.celery import app as celery_app  # noqa
        from apps.prometheus.reporter import MonitorReporter  # noqa

        reporter = MonitorReporter(
            data_id=env.BKAPP_MONITOR_REPORTER_DATA_ID,  # 监控 Data ID
            access_token=env.BKAPP_MONITOR_REPORTER_ACCESS_TOKEN,  # 自定义上报 Token
            target=env.BKAPP_MONITOR_REPORTER_TARGET,  # 上报唯一标志符
            url=env.BKAPP_MONITOR_REPORTER_URL,  # 上报地址
            report_interval=env.BKAPP_MONITOR_REPORTER_REPORT_INTERVAL,  # 上报周期，秒
            chunk_size=env.BKAPP_MONITOR_REPORTER_CHUNK_SIZE,  # 上报指标分块大小
            proc_type=proc_type,
            instance_tmpl=instance_tmpl,
        )

        # 针对多进程worker需要做特殊梳理，在worker进程中进行reporter start
        prefork_config_check = [("-P", "-P prefork"), ("--pool", "--pool=prefork")]
        if any([config[0] in boot_cmd and config[1] not in boot_cmd for config in prefork_config_check]):
            MonitorReportStep.setup_reporter(reporter)
            celery_app.steps["worker"].add(MonitorReportStep)
        else:
            # prefork 场景下，每个进程都会有一个 Reporter
            from celery.signals import worker_process_init  # noqa

            worker_process_init.connect(reporter.start, weak=False)

        sys.stdout.write(
            "[Monitor reporter] init success, proc_type -> %s, instance_tmpl -> %s \n" % (proc_type, instance_tmpl)
        )

        sys.stdout.write("[Monitor reporter] init success\n")

    else:
        from apps.prometheus.reporter import MonitorReporter  # noqa

        match_proc_name = None
        proc_names = [
            "gunicorn",
            "runserver",
            "sync_host_event",
            "sync_host_relation_event",
            "sync_process_event",
            "apply_resource_watched_events",
        ]

        for proc_name in proc_names:
            if proc_name in boot_cmd:
                match_proc_name = proc_name
                break

        if not match_proc_name:
            sys.stdout.write("[!]unknown boot cmd: %s, skip monitor report config\n" % boot_cmd)
            return
        else:
            sys.stdout.write("[Monitor reporter] match_proc_name %s \n" % match_proc_name)

        if match_proc_name in ["gunicorn", "runserver"]:
            # gunicorn -w 参数会派生出 n 个进程，每个进程都有一个 Reporter
            # Worker 模型：https://docs.gunicorn.org/en/latest/design.html?highlight=gthread#server-model
            proc_type = "web"
            instance_tmpl = str(match_proc_name) + "@%h-%P"
        else:
            # 单进程运行，无需 pid
            proc_type = "sync"
            instance_tmpl = str(match_proc_name) + "@%h"

        reporter = MonitorReporter(
            data_id=env.BKAPP_MONITOR_REPORTER_DATA_ID,  # 监控 Data ID
            access_token=env.BKAPP_MONITOR_REPORTER_ACCESS_TOKEN,  # 自定义上报 Token
            target=env.BKAPP_MONITOR_REPORTER_TARGET,  # 上报唯一标志符
            url=env.BKAPP_MONITOR_REPORTER_URL,  # 上报地址
            report_interval=env.BKAPP_MONITOR_REPORTER_REPORT_INTERVAL,  # 上报周期，秒
            chunk_size=env.BKAPP_MONITOR_REPORTER_CHUNK_SIZE,  # 上报指标分块大小
            proc_type=proc_type,
            instance_tmpl=instance_tmpl,
        )
        reporter.start()

        sys.stdout.write(
            "[Monitor reporter] init success, proc_type -> %s, instance_tmpl -> %s \n" % (proc_type, instance_tmpl)
        )
