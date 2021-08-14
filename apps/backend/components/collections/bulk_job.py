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

import logging
import math
import threading
import traceback
import uuid
from datetime import timedelta

import six
import ujson as json
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.backend.api.job import JobClient
from apps.backend.components.collections.job import JobBaseService
from apps.node_man import constants, models
from pipeline.apps import CLIENT_GETTER
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

logger = logging.getLogger("app")

TRIGGER_THRESHOLD = 300


class RedisInstSingleTon:
    _inst_lock = threading.Lock()
    _inst_name = "redis_inst"

    @classmethod
    def get_inst(cls):
        if hasattr(cls, cls._inst_name):
            return getattr(cls, cls._inst_name)
        with cls._inst_lock:
            if hasattr(cls, cls._inst_name):
                return getattr(cls, cls._inst_name)
            if hasattr(settings, "REDIS"):
                mode = settings.REDIS.get("mode") or "single"
                try:
                    setattr(cls, cls._inst_name, CLIENT_GETTER[mode]())
                except Exception:
                    # fall back to single node mode
                    logger.error("redis client init error: %s" % traceback.format_exc())
                    setattr(cls, cls._inst_name, None)
            else:
                logger.error("can not find REDIS in settings!")
                setattr(cls, cls._inst_name, None)
        return getattr(cls, cls._inst_name)


class RedisLock:
    redis_inst = RedisInstSingleTon.get_inst()

    def __init__(self, lock_name: str = None, lock_expire: int = POLLING_INTERVAL * 4):
        self.lock_name = lock_name
        self.lock_expire = lock_expire

    def __enter__(self):
        if self.lock_name is None:
            logger.error("can not use None key")
            return None
        self.identifier = self.acquire_lock_with_timeout(self.lock_name, self.lock_expire)
        return self.identifier

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.identifier is None:
            return False
        self.release_lock(self.lock_name, self.identifier)

    def acquire_lock_with_timeout(self, lock_name, lock_expire: int = POLLING_INTERVAL * 4):
        """
        获得锁
        :param lock_name: 锁名
        :param lock_expire: 锁过期时间
        :return: success: identifier failed: None
        """
        identifier = str(uuid.uuid4())
        lock_name = f"lock:{lock_name}"
        lock_timeout = int(math.ceil(lock_expire))
        # 如果不存在这个锁则加锁并设置过期时间，避免死锁
        if self.redis_inst.set(lock_name, identifier, ex=lock_timeout, nx=True):
            return identifier
        # 锁已存在并被持有，此时放弃排队竞争，直接返回None
        return None

    def release_lock(self, lock_name, identifier):
        """
        释放锁
        :param lock_name: 锁的名称
        :param identifier: 锁的标识
        :return:
        """
        unlock_script = """
        if redis.call("get",KEYS[1]) == ARGV[1] then
            return redis.call("del",KEYS[1])
        else
            return 0
        end
        """
        lock_name = f"lock:{lock_name}"
        unlock = self.redis_inst.register_script(unlock_script)
        result = unlock(keys=[lock_name], args=[identifier])
        return result


class SchedulePollType(object):
    # 轮询分发状态
    POLL_FILE_PUSH_STATUS = "POLL_FILE_PUSH_STATUS"
    # 等待或触发分发任务
    TRIGGER_JOB = "TRIGGER_JOB"


class JobBulkPushFileService(JobBaseService):
    ACTION_NAME = "BULK_PUSH_FILE"
    ACTION_DESCRIPTION = _("批量分发文件")

    def get_push_file_lock_name(self, task_id):
        return f"{self.ACTION_NAME}[{task_id}][{SchedulePollType.TRIGGER_JOB}]"

    def get_poll_status_lock_name(self, task_id):
        return f"{self.ACTION_NAME}[{task_id}][{SchedulePollType.POLL_FILE_PUSH_STATUS}]"

    def bulk_push_file(self, data, pf_records: list, push_file_record: models.PushFileRecord):
        job_client = JobClient(**data.get_one_of_inputs("job_client"))
        file_source = data.get_one_of_inputs("file_source")
        file_target_path = data.get_one_of_inputs("file_target_path")
        log_context = data.get_one_of_inputs("context")
        task_id = data.get_one_of_inputs("task_id")

        ip_list = []
        for pf_record in pf_records:
            ip_list.append(
                {
                    "ip": pf_record["ip"],
                    "bk_cloud_id": pf_record["bk_cloud_id"],
                    "bk_supplier_id": constants.DEFAULT_SUPPLIER_ID,
                }
            )
        task_name = f"NODEMAN_BULK_PUSH_FILE_{task_id}_{len(ip_list)}"
        job_instance_id = job_client.fast_push_file(ip_list, file_target_path, file_source, task_name, POLLING_TIMEOUT)
        # 更新任务状态
        models.PushFileRecord.objects.filter(id__in=[pf_record["id"] for pf_record in pf_records]).update(
            job_instance_id=job_instance_id, ip_status=constants.JobIpStatusType.pending, update_time=timezone.now()
        )
        self.log_info(
            "JobBulkPushFileService fast_push_file called with params:\n "
            "task_name: {task_name}, \n "
            "ip_number: {ip_number}, \n"
            "file_target_path: {file_target_path}, \n "
            "file_source: {file_source}, \n "
            "trigger_job_record_id: {record_id}, \n"
            "job_instance_id: {job_instance_id} \n".format(
                task_name=task_name,
                ip_number=len(ip_list),
                file_target_path=file_target_path,
                file_source=json.dumps(file_source, indent=2),
                record_id=push_file_record.id,
                job_instance_id=job_instance_id,
            ),
            log_context,
        )
        return job_instance_id

    def validate_not_job_record(self, data):
        push_file_record_id = data.get_one_of_outputs("push_file_record_id")
        log_context = data.get_one_of_inputs("context")

        push_file_record = models.PushFileRecord.objects.get(id=push_file_record_id)
        # 已被其他原子触发作业，取该记录的作业实例ID
        if push_file_record.ip_status != constants.JobIpStatusType.not_job:
            self.log_info(
                "Push file record[{record_id}] trigger by other act".format(record_id=push_file_record.id),
                log_context,
            )
            # 状态变更为分发作业状态轮询, 轮询时间重置
            data.outputs.schedule_poll_type = SchedulePollType.POLL_FILE_PUSH_STATUS
            data.outputs.polling_time = 0
            return {"result": False, "push_file_record": push_file_record}
        return {"result": True, "push_file_record": push_file_record}

    def execute(self, data, parent_data):
        host_info = data.get_one_of_inputs("host_info")
        file_target_path = data.get_one_of_inputs("file_target_path")
        file_source = data.get_one_of_inputs("file_source")
        log_context = data.get_one_of_inputs("context")

        subscription_id = data.get_one_of_inputs("subscription_id")
        task_id = data.get_one_of_inputs("task_id")
        instance_id = data.get_one_of_inputs("instance_id")
        os_type = data.get_one_of_inputs("os_type")

        self.log_info(
            "JobBulkPushFileService called with params:\n ip_list:{}, file_target_path:{}, file_source:{}.".format(
                json.dumps(host_info, indent=2),
                file_target_path,
                json.dumps(file_source, indent=2),
            ),
            log_context,
        )
        if not all(
            [isinstance(host_info, dict), isinstance(file_target_path, six.string_types), isinstance(file_source, list)]
        ):
            self.log_error("JobBulkPushFileService params checked failed.", log_context)
            data.outputs.ex_data = "参数校验失败"
            return False

        record = models.SubscriptionInstanceRecord.objects.filter(
            subscription_id=subscription_id, task_id=task_id, instance_id=instance_id
        ).first()
        if record is None:
            msg = "订阅实例记录[subscription_id: {sub_id}, task_id: {task_id}, instance_id: {instance_id}]不存在".format(
                sub_id=subscription_id, task_id=task_id, instance_id=instance_id
            )
            self.log_error(msg, log_context)
            data.outputs.ex_data = msg
            return False

        push_file_record = models.PushFileRecord.objects.create(
            subscription_id=record.subscription_id,
            task_id=record.task_id,
            record_id=record.id,
            ip=host_info["ip"],
            bk_cloud_id=host_info["bk_cloud_id"],
            os_type=os_type,
            # 下发插件包场景下只下发一个包
            file_source_path=file_source[0]["files"][0],
            update_time=timezone.now(),
        )
        self.log_info(
            "JobBulkPushFileService execute finish, push_file_record[{id}]".format(id=push_file_record.id), log_context
        )
        data.outputs.polling_time = 0
        data.outputs.push_file_record_id = push_file_record.id
        data.outputs.schedule_poll_type = SchedulePollType.TRIGGER_JOB
        return True

    def schedule(self, data, parent_data, callback_data=None):
        schedule_poll_type = data.get_one_of_outputs("schedule_poll_type")
        polling_time = data.get_one_of_outputs("polling_time")
        push_file_record_id = data.get_one_of_outputs("push_file_record_id")

        task_id = data.get_one_of_inputs("task_id")
        log_context = data.get_one_of_inputs("context")

        if schedule_poll_type == SchedulePollType.TRIGGER_JOB:
            self.log_info(
                "push_file_record[{id}]: keep trigger_job status [{times}] times".format(
                    id=push_file_record_id, times=int(polling_time / POLLING_INTERVAL)
                )
            )
            validate_return = self.validate_not_job_record(data)
            push_file_record = validate_return["push_file_record"]
            # 分发文件搁置请求已被其他原子触发
            if not validate_return["result"]:
                return True

            # 取出等待上传的记录
            pf_record_qs = models.PushFileRecord.objects.filter(
                subscription_id=push_file_record.subscription_id,
                task_id=push_file_record.task_id,
                ip_status=constants.JobIpStatusType.not_job,
                os_type=push_file_record.os_type,
                file_source_path=push_file_record.file_source_path,
            )

            # 超时或者等待分发作业超过阈值
            # TODO: 更希望是超时直接分发存量，按阈值实际上不够灵活，在这里需要设定合适超时时间
            if polling_time + POLLING_INTERVAL > (POLLING_TIMEOUT / 20) or pf_record_qs.count() > TRIGGER_THRESHOLD:
                with RedisLock(self.get_push_file_lock_name(task_id)) as identifier:
                    if identifier is None:
                        # 锁已被其他原子占用，轮询等待
                        data.outputs.polling_time = polling_time + POLLING_INTERVAL
                        return True

                    # 分发文件搁置请求已被其他原子触发，无需分发文件，释放锁并进入作业轮询状态
                    validate_return = self.validate_not_job_record(data)
                    if not validate_return["result"]:
                        self.log_info(
                            "Push file record[{record_id}]: lock return".format(record_id=push_file_record_id)
                        )
                        return True

                    pf_records = list(pf_record_qs.values())
                    self.bulk_push_file(data, pf_records, push_file_record)

                    # 状态变更为分发作业状态轮询, 轮询时间重置
                    data.outputs.schedule_poll_type = SchedulePollType.POLL_FILE_PUSH_STATUS
                    data.outputs.polling_time = 0
                    return True
            else:
                # 没有触发下发文件, 继续轮询等待
                data.outputs.polling_time = polling_time + POLLING_INTERVAL
                return True

        elif schedule_poll_type == SchedulePollType.POLL_FILE_PUSH_STATUS:
            push_file_record = models.PushFileRecord.objects.get(id=push_file_record_id)
            job_instance_id = push_file_record.job_instance_id

            # 1. 当前机器下发作业已有结果，结束轮询，执行下一个原子或失败
            if push_file_record.ip_status in [constants.JobIpStatusType.success, constants.JobIpStatusType.failed]:
                msg = "JOB(task_id: [{task_id}]) push file to IP({ip}) {status}.".format(
                    task_id=job_instance_id, ip=push_file_record.ip, status=push_file_record.ip_status
                )
                if push_file_record.ip_status == constants.JobIpStatusType.success:
                    self.log_info(msg, log_context)
                else:
                    self.log_error(msg, log_context)
                self.finish_schedule()
                return push_file_record.ip_status == constants.JobIpStatusType.success

            # 2. 进入同步块，查询作业状态
            with RedisLock(self.get_poll_status_lock_name(task_id)) as identifier:
                # 2.1. 已有其他Pipeline在轮询作业，放弃竞争锁
                if identifier is None:
                    data.outputs.polling_time = polling_time + POLLING_INTERVAL
                    return True

                job_record_qs = models.PushFileRecord.objects.filter(job_instance_id=job_instance_id)

                # 2.2. 作业仍在执行状态时，如5秒内有其他Pipeline轮询，直接跳过，否则轮询
                if job_record_qs.filter(
                    job_polling_time__gt=timezone.now() - timedelta(seconds=POLLING_INTERVAL)
                ).exists():
                    data.outputs.polling_time = polling_time + POLLING_INTERVAL
                    return True

                job_client = JobClient(**data.get_one_of_inputs("job_client"))
                is_finished, task_result = job_client.get_task_result(job_instance_id)

                data.outputs.task_result = task_result
                self.log_info(
                    "JOB(task_id: [{job_instance_id}]) get schedule task result:\n"
                    "success_number: {success_number}, \n"
                    "failed_number: {failed_number}, \n"
                    "pending_number: {pending_number}.".format(
                        job_instance_id=job_instance_id,
                        success_number=len(task_result.get(constants.JobIpStatusType.success, [])),
                        failed_number=len(task_result.get(constants.JobIpStatusType.failed, [])),
                        pending_number=len(task_result.get(constants.JobIpStatusType.pending, [])),
                    ),
                    log_context,
                )

                # 2.3. 批量更新分发状态
                for ip_status, ip_infos in task_result.items():
                    if not ip_infos:
                        continue
                    # 原本是pending无需重复刷新状态
                    if ip_status == constants.JobIpStatusType.pending:
                        continue
                    job_record_qs.filter(ip__in=[ip_info["ip"] for ip_info in ip_infos]).update(
                        ip_status=ip_status, update_time=timezone.now(), is_finished=is_finished
                    )

                # 2.4. 刷新轮询job作业状态时间
                push_file_record.job_polling_time = timezone.now()
                push_file_record.save(update_fields=["job_polling_time"])

                # 2.5. 超时并且作业未完成时原子执行失败，作业完成并且超时，下一次轮询就能得知上传文件执行结果
                if polling_time + POLLING_INTERVAL > POLLING_TIMEOUT and not is_finished:
                    self.log_error(
                        "JOB(job_instance_id: [{}], record_id: [{}]) schedule timeout.".format(
                            job_instance_id, push_file_record_id
                        ),
                        log_context,
                    )
                    data.outputs.ex_data = "任务轮询超时"
                    self.finish_schedule()
                    return False

                data.outputs.polling_time = polling_time + POLLING_INTERVAL
                return True

    def inputs_format(self):
        return [
            Service.InputItem(name="subscription_id", key="subscription_id", type="int", required=True),
            Service.InputItem(name="task_id", key="task_id", type="int", required=True),
            Service.InputItem(name="instance_id", key="instance_id", type="str", required=True),
            Service.InputItem(name="os_type", key="os_type", type="str", required=True),
            Service.InputItem(name="job_client", key="job_client", type="dict", required=True),
            Service.InputItem(name="host_info", key="host_info", type="dict", required=True),
            Service.InputItem(name="file_target_path", key="file_target_path", type="str", required=True),
            Service.InputItem(name="file_source", key="file_source", type="list", required=True),
        ]

    def outputs_format(self):
        return [
            Service.OutputItem(name="polling_time", key="polling_time", type="int"),
            Service.OutputItem(name="task_result", key="task_result", type="dict"),
            Service.OutputItem(name="push_file_record_id", key="push_file_record_id", type="int"),
            Service.OutputItem(name="schedule_poll_type", key="schedule_poll_type", type="str"),
        ]


class BulkPushUpgradePackageService(JobBulkPushFileService):
    name = _("批量下发升级包")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        inputs = super().inputs_format()
        return inputs

    def outputs_format(self):
        outputs = super().outputs_format()
        outputs.append(Service.OutputItem(name="package_name", key="package_name", type="str", required=True))
        return outputs

    def execute(self, data, parent_data):
        self.logger.info(_("开始下发升级包"))
        host_info = data.get_one_of_inputs("host_info")
        host = models.Host.get_by_host_info(host_info)
        nginx_path = host.ap.nginx_path or settings.DOWNLOAD_PATH
        data.inputs.file_target_path = host.agent_config["temp_path"]

        os_type = host.os_type.lower()
        bk_os_bit = host_info.get("bk_os_bit")

        # 根据节点类型、位数、系统等组装包名
        arch = "x86" if bk_os_bit == "32-bit" else "x86_64"
        gse_type = "proxy" if host.node_type == constants.NodeType.PROXY else "client"
        package_name = f"gse_{gse_type}-{os_type}-{arch}_upgrade.tgz"
        files = [package_name]

        # windows机器需要添加解压文件
        if os_type == "windows":
            files.extend(["7z.dll", "7z.exe"])
        file_source = [
            {
                "files": [f"{nginx_path}/{file}" for file in files],
                "account": "root",
                "ip_list": [{"ip": settings.BKAPP_LAN_IP, "bk_cloud_id": 0}],
            }
        ]

        # 增加ip字段
        host_info["ip"] = host_info["bk_host_innerip"]

        data.inputs.file_source = file_source

        data.outputs.package_name = package_name
        return super().execute(data, parent_data)


class JobBulkPushFileComponent(Component):
    name = "JobBulkPushFileComponent"
    code = "job_bulk_push_file"
    bound_service = JobBulkPushFileService


class BulkPushUpgradePackageComponent(Component):
    name = _("批量下发升级包")
    code = "bulk_push_upgrade_package"
    bound_service = BulkPushUpgradePackageService
