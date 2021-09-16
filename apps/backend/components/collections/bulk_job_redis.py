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
import hashlib
import logging

import six
import ujson as json
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.backend.api.job import JobClient
from apps.backend.components.collections import bulk_job
from apps.backend.components.collections.job import JobBaseService
from apps.node_man import constants, models
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

logger = logging.getLogger("app")

REDIS_INST = bulk_job.RedisInstSingleTon.get_inst()


class JobBulkPushFileV2Service(JobBaseService):
    ACTION_NAME = "BULK_PUSH_FILE_V2"
    ACTION_DESCRIPTION = "批量分发文件-Redis优化"
    REDIS_CACHE_PREFIX = f"nodeman:v2:{ACTION_NAME.lower()}"

    @classmethod
    def get_md5(cls, content):
        md5 = hashlib.md5()
        md5.update(content.encode("utf-8"))
        return md5.hexdigest()

    @classmethod
    def ip_info_str(cls, host_info):
        return f"{host_info['ip']}-{host_info['bk_cloud_id']}-{constants.DEFAULT_SUPPLIER_ID}"

    @classmethod
    def redis_result(cls, result):
        return result.decode() if isinstance(result, bytes) else result

    def push_file_lock_name(self, task_id):
        return "{redis_cache_prefix}:task_id:{task_id}:status:{status}".format(
            redis_cache_prefix=self.REDIS_CACHE_PREFIX, task_id=task_id, status=bulk_job.SchedulePollType.TRIGGER_JOB
        )

    def poll_status_lock_name(self, task_id):
        return "{redis_cache_prefix}:task_id:{task_id}:status:{status}".format(
            redis_cache_prefix=self.REDIS_CACHE_PREFIX,
            task_id=task_id,
            status=bulk_job.SchedulePollType.POLL_FILE_PUSH_STATUS,
        )

    def hash_ip_status_key(self, task_id):
        return "{redis_cache_prefix}:task_id:{task_id}:ip:status".format(
            redis_cache_prefix=self.REDIS_CACHE_PREFIX, task_id=task_id
        )

    def hash_ip_job_instance_id_key(self, task_id):
        return "{redis_cache_prefix}:task_id:{task_id}:ip:job_instance_id".format(
            redis_cache_prefix=self.REDIS_CACHE_PREFIX, task_id=task_id
        )

    def hash_job_last_poll_time_key(self, task_id):
        return "{redis_cache_prefix}:task_id:{task_id}:last_poll_time".format(
            redis_cache_prefix=self.REDIS_CACHE_PREFIX, task_id=task_id
        )

    def zset_source_files_wait_key(self, bk_biz_id, task_id, file_source):
        md5 = self.get_md5("|".join(sorted(file_source[0]["files"])))
        return "{redis_cache_prefix}:bk_biz_id:{bk_biz_id}:task_id:{task_id}:file_paths_md5:{md5}:wait".format(
            redis_cache_prefix=self.REDIS_CACHE_PREFIX,
            bk_biz_id=bk_biz_id,
            task_id=task_id,
            md5=md5,
        )

    def bulk_expire(self, bk_biz_id, task_id, file_source, timeout=POLLING_TIMEOUT * 10):
        REDIS_INST.expire(self.hash_ip_status_key(task_id), timeout)
        REDIS_INST.expire(self.hash_ip_job_instance_id_key(task_id), timeout)
        REDIS_INST.expire(self.hash_job_last_poll_time_key(task_id), timeout)
        REDIS_INST.expire(self.zset_source_files_wait_key(bk_biz_id, task_id, file_source), timeout)

    def ip_status(self, task_id, host_info):
        return self.redis_result(
            REDIS_INST.hget(name=self.hash_ip_status_key(task_id), key=self.ip_info_str(host_info))
        )

    def waiting_push_count(self, bk_biz_id, task_id, file_source):
        return REDIS_INST.zcard(self.zset_source_files_wait_key(bk_biz_id, task_id, file_source))

    def validate_not_job(self, data):
        task_id = data.get_one_of_inputs("task_id")
        host_info = data.get_one_of_inputs("host_info")
        log_context = data.get_one_of_inputs("context")

        if self.ip_status(task_id, host_info) == constants.JobIpStatusType.not_job:
            return True
        # 分发作业已被其他原子触发，需要进入作业轮询状态
        self.log_info(
            "host[{ip_info_str}] push file job trigger by other act".format(ip_info_str=self.ip_info_str(host_info)),
            log_context,
        )
        data.outputs.schedule_poll_type = bulk_job.SchedulePollType.POLL_FILE_PUSH_STATUS
        data.outputs.polling_time = 0
        return False

    def bulk_push_file(self, data):

        bk_biz_id = data.get_one_of_outputs("bk_biz_id")
        task_id = data.get_one_of_inputs("task_id")
        host_info = data.get_one_of_inputs("host_info")
        log_context = data.get_one_of_inputs("context")
        file_source = data.get_one_of_inputs("file_source")
        file_target_path = data.get_one_of_inputs("file_target_path")
        job_client = JobClient(**data.get_one_of_inputs("job_client"))

        ip_info_str_list_undecode = REDIS_INST.zrange(
            name=self.zset_source_files_wait_key(bk_biz_id, task_id, file_source), start=0, end=-1
        )
        ip_info_str_list = [
            self.redis_result(ip_info_str_undecode) for ip_info_str_undecode in ip_info_str_list_undecode
        ]
        ip_list = []
        for ip_info_str in ip_info_str_list:
            ip, bk_cloud_id, bk_supplier_id = ip_info_str.split("-")
            ip_list.append({"ip": ip, "bk_cloud_id": int(bk_cloud_id), "bk_supplier_id": int(bk_supplier_id)})

        task_name = f"NODEMAN_BULK_PUSH_FILE_{task_id}_{len(ip_list)}"
        job_instance_id = job_client.fast_push_file(ip_list, file_target_path, file_source, task_name, POLLING_TIMEOUT)

        # 清空已分发的等待队列
        REDIS_INST.zrem(self.zset_source_files_wait_key(bk_biz_id, task_id, file_source), *ip_info_str_list_undecode)

        # 记录目标主机对应的job_instance_id
        REDIS_INST.hmset(
            self.hash_ip_job_instance_id_key(task_id),
            {ip_info_str: job_instance_id for ip_info_str in ip_info_str_list},
        )

        # 更新主机状态
        REDIS_INST.hmset(
            self.hash_ip_status_key(task_id),
            {ip_info_str: constants.JobIpStatusType.pending for ip_info_str in ip_info_str_list},
        )

        # 记录最后轮询作业的时间，在当前时间减去休眠时间
        REDIS_INST.hset(
            name=self.hash_job_last_poll_time_key(task_id),
            key=job_instance_id,
            value=timezone.now().timestamp() - POLLING_INTERVAL,
        )

        self.log_info(
            "JobBulkPushFileV2Service fast_push_file called with params:\n "
            "bk_biz_id: {bk_biz_id}, \n"
            "task_name: {task_name}, \n "
            "ip_number: {ip_number}, \n"
            "file_target_path: {file_target_path}, \n "
            "file_source: {file_source}, \n "
            "trigger_ip_info: {ip_info_str}, \n"
            "job_instance_id: {job_instance_id} \n".format(
                bk_biz_id=bk_biz_id,
                task_name=task_name,
                ip_number=len(ip_list),
                file_target_path=file_target_path,
                file_source=json.dumps(file_source, indent=2),
                ip_info_str=self.ip_info_str(host_info),
                job_instance_id=job_instance_id,
            ),
            log_context,
        )
        return job_instance_id

    def execute(self, data, parent_data):
        host_info = data.get_one_of_inputs("host_info")
        file_target_path = data.get_one_of_inputs("file_target_path")
        file_source = data.get_one_of_inputs("file_source")
        log_context = data.get_one_of_inputs("context")
        task_id = data.get_one_of_inputs("task_id")
        bk_biz_id = (
            settings.BLUEKING_BIZ_ID
            if settings.JOB_VERSION == "V3"
            else data.get_one_of_inputs("job_client")["bk_biz_id"]
        )

        self.log_info(
            "JobBulkPushFileV2Service called with params:\n ip_list:{}, file_target_path:{}, file_source:{}.".format(
                json.dumps(host_info, indent=2),
                file_target_path,
                json.dumps(file_source, indent=2),
            ),
            log_context,
        )
        if not all(
            [isinstance(host_info, dict), isinstance(file_target_path, six.string_types), isinstance(file_source, list)]
        ):
            self.log_error("JobBulkPushFileV2Service params checked failed.", log_context)
            data.outputs.ex_data = "参数校验失败"
            return False

        # 记录目标IP状态
        add_ip_status_result = REDIS_INST.hset(
            name=self.hash_ip_status_key(task_id),
            key=self.ip_info_str(host_info),
            value=constants.JobIpStatusType.not_job,
        )

        # 记录一条带时间戳的待分发记录
        add_wait_record_result = REDIS_INST.zadd(
            self.zset_source_files_wait_key(bk_biz_id, task_id, file_source),
            timezone.now().timestamp(),
            self.ip_info_str(host_info),
        )

        if not all([add_wait_record_result, add_ip_status_result]):
            self.log_error(
                "JobBulkPushFileV2Service create file push record failed: "
                "add_ip_status_result[{add_ip_status_result}], "
                "add_wait_record_result[{add_wait_record_result}]".format(
                    add_ip_status_result=add_ip_status_result, add_wait_record_result=add_wait_record_result
                ),
                log_context,
            )
            data.outputs.ex_data = "创建文件等待分发记录失败"
            return False

        self.log_info("JobBulkPushFileV2Service execute finish.", log_context)

        data.outputs.polling_time = 0
        data.outputs.schedule_poll_type = bulk_job.SchedulePollType.TRIGGER_JOB
        data.outputs.bk_biz_id = bk_biz_id

        return True

    def schedule(self, data, parent_data, callback_data=None):

        bk_biz_id = data.get_one_of_outputs("bk_biz_id")
        polling_time = data.get_one_of_outputs("polling_time")
        schedule_poll_type = data.get_one_of_outputs("schedule_poll_type")

        task_id = data.get_one_of_inputs("task_id")
        log_context = data.get_one_of_inputs("context")
        host_info = data.get_one_of_inputs("host_info")
        file_source = data.get_one_of_inputs("file_source")

        ip_info_str = self.ip_info_str(host_info)

        if schedule_poll_type == bulk_job.SchedulePollType.TRIGGER_JOB:
            self.log_info(
                "host[{ip_info_str}]: keep trigger_job status [{times}] times".format(
                    ip_info_str=ip_info_str, times=int(polling_time / POLLING_INTERVAL)
                ),
                log_context,
            )

            # 主机分发任务已被其他原子触发，直接进入作业轮询状态
            if not self.validate_not_job(data):
                return True

            if any(
                [
                    polling_time + POLLING_INTERVAL > (POLLING_TIMEOUT / 20),
                    self.waiting_push_count(bk_biz_id, task_id, file_source) > bulk_job.TRIGGER_THRESHOLD,
                ]
            ):
                with bulk_job.RedisLock(self.push_file_lock_name(task_id)) as identifier:
                    if identifier is None:
                        # 锁已被其他原子占用，轮询等待
                        data.outputs.polling_time = polling_time + POLLING_INTERVAL
                        return True
                    # 主机分发任务已被其他原子触发，直接进入作业轮询状态
                    if not self.validate_not_job(data):
                        self.log_info("host[{ip_info_str}]: lock return".format(ip_info_str=ip_info_str), log_context)
                        return True

                    # 将需要分发同类文件的主机批量下发
                    self.bulk_push_file(data)

                    # 设置原子所有用到的Redis键值对过期时间
                    # TODO: 也可以考虑把这些key存到DB，后续开个周期任务定时刷
                    self.bulk_expire(bk_biz_id, task_id, file_source)

                    # 状态变更为分发作业状态轮询, 轮询时间重置
                    data.outputs.schedule_poll_type = bulk_job.SchedulePollType.POLL_FILE_PUSH_STATUS
                    data.outputs.polling_time = 0
                    return True
            else:
                # 没有触发下发文件, 继续轮询等待
                data.outputs.polling_time = polling_time + POLLING_INTERVAL
                return True

        elif schedule_poll_type == bulk_job.SchedulePollType.POLL_FILE_PUSH_STATUS:
            job_instance_id = int(
                self.redis_result(
                    REDIS_INST.hget(self.hash_ip_job_instance_id_key(task_id), self.ip_info_str(host_info))
                )
            )
            ip_status = self.ip_status(task_id, host_info)

            # 1. 当前机器下发作业已有结果，结束轮询，执行下一个原子或失败
            if ip_status in [constants.JobIpStatusType.success, constants.JobIpStatusType.failed]:
                msg = "JOB(task_id: [{task_id}]) push file to IP({ip}) {status}.".format(
                    task_id=job_instance_id, ip=ip_info_str, status=ip_status
                )
                if ip_status == constants.JobIpStatusType.success:
                    self.log_info(msg, log_context)
                else:
                    self.log_error(msg, log_context)
                self.finish_schedule()
                return ip_status == constants.JobIpStatusType.success

            # 2. 进入同步块，查询作业状态
            with bulk_job.RedisLock(self.poll_status_lock_name(task_id)) as identifier:
                # 2.1. 已有其他Pipeline在轮询作业，放弃竞争锁
                if identifier is None:
                    data.outputs.polling_time = polling_time + POLLING_INTERVAL
                    return True

                # 2.2. 作业仍在执行状态时，如5秒内有其他Pipeline轮询，直接跳过，否则轮询
                last_poll_time = self.redis_result(
                    REDIS_INST.hget(self.hash_job_last_poll_time_key(task_id), job_instance_id)
                )
                if timezone.now().timestamp() < float(last_poll_time) + POLLING_INTERVAL:
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
                ip_status_map = {}
                for ip_status, ip_infos in task_result.items():
                    # 空列表或者仍是pending的状态无需重复刷新
                    if not ip_infos or ip_status == constants.JobIpStatusType.pending:
                        continue
                    ip_status_map.update({self.ip_info_str(ip_info): ip_status for ip_info in ip_infos})
                if ip_status_map:
                    REDIS_INST.hmset(self.hash_ip_status_key(task_id), ip_status_map)

                # 2.4. 刷新轮询job作业状态时间
                REDIS_INST.hset(self.hash_job_last_poll_time_key(task_id), job_instance_id, timezone.now().timestamp())

                # 2.5. 超时并且作业未完成时原子执行失败，作业完成并且超时，下一次轮询就能得知上传文件执行结果
                if polling_time + POLLING_INTERVAL > POLLING_TIMEOUT and not is_finished:
                    self.log_error(
                        "JOB(job_instance_id: [{}], host: [{}]) schedule timeout.".format(job_instance_id, ip_info_str),
                        log_context,
                    )
                    data.outputs.ex_data = "任务轮询超时"
                    self.finish_schedule()
                    return False
                data.outputs.polling_time = polling_time + POLLING_INTERVAL
                return True

    def inputs_format(self):
        return [
            Service.InputItem(name="task_id", key="task_id", type="int", required=True),
            Service.InputItem(name="job_client", key="job_client", type="dict", required=True),
            Service.InputItem(name="host_info", key="host_info", type="dict", required=True),
            Service.InputItem(name="file_target_path", key="file_target_path", type="str", required=True),
            Service.InputItem(name="file_source", key="file_source", type="list", required=True),
        ]

    def outputs_format(self):
        return [
            Service.OutputItem(name="task_result", key="task_result", type="dict"),
            Service.OutputItem(name="polling_time", key="polling_time", type="int"),
            Service.OutputItem(name="schedule_poll_type", key="schedule_poll_type", type="str"),
        ]


class BulkPushUpgradePackageV2Service(JobBulkPushFileV2Service):
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

        # 根据节点类型、位数、系统等组装包名
        gse_type = "proxy" if host.node_type == constants.NodeType.PROXY else "client"
        package_name = f"gse_{gse_type}-{os_type}-{host.cpu_arch}_upgrade.tgz"
        files = [package_name]

        # windows机器需要添加解压文件
        if os_type == constants.OsType.WINDOWS.lower():
            files.extend(["7z.dll", "7z.exe"])
        file_source = [{"files": [f"{nginx_path}/{file}" for file in files]}]

        # 增加ip字段
        host_info["ip"] = host_info["bk_host_innerip"]

        data.inputs.file_source = file_source

        data.outputs.package_name = package_name
        return super().execute(data, parent_data)


class JobBulkPushFileV2Component(Component):
    name = "JobBulkPushFileV2Component"
    code = "job_bulk_push_file_v2"
    bound_service = JobBulkPushFileV2Service


class BulkPushUpgradePackageV2Component(Component):
    name = _("批量下发升级包")
    code = "bulk_push_upgrade_package_v2"
    bound_service = BulkPushUpgradePackageV2Service
