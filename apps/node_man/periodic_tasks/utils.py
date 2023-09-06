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
import logging
import time
import typing
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Union

import ujson as json
from django.conf import settings

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT, JobIPStatus
from apps.backend.api.errors import JobPollTimeout
from apps.component.esbclient import client_v2
from apps.core.gray.tools import GrayTools
from apps.exceptions import ValidationError
from apps.node_man import constants, models
from common.api import JobApi
from env.constants import GseVersion

logger = logging.getLogger("app")


def query_bk_biz_ids(task_id):
    biz_data = client_v2.cc.search_business({"fields": ["bk_biz_id"]})
    bk_biz_ids = [biz["bk_biz_id"] for biz in biz_data.get("info") or [] if biz["default"] == 0]

    # 排除掉黑名单业务的主机同步，比如 SA 业务，包含大量主机但无需同步
    bk_biz_ids = list(
        set(bk_biz_ids)
        - set(
            models.GlobalSettings.get_config(
                key=models.GlobalSettings.KeyEnum.SYNC_CMDB_HOST_BIZ_BLACKLIST.value, default=[]
            )
        )
    )

    logger.info(f"[query_bk_biz_ids] synchronize full business: task_id -> {task_id}, count -> {len(bk_biz_ids)}")

    return bk_biz_ids


class JobDemand(object):
    @classmethod
    def poll_task_result(cls, job_instance_id: int):
        """
        轮询直到任务完成
        :param job_instance_id: job任务id
        :return: 与 get_task_result 同
        """
        polling_time = 0
        result = cls.get_task_result(job_instance_id)
        while not result["is_finished"]:
            if polling_time > POLLING_TIMEOUT:
                logger.error(
                    "user->[{}] called api->[get_task_result] but got JobExecuteTimeout.".format(
                        settings.BACKEND_JOB_OPERATOR
                    )
                )
                raise JobPollTimeout({"job_instance_id": job_instance_id})

            # 每次查询后，睡觉
            polling_time += POLLING_INTERVAL
            time.sleep(POLLING_INTERVAL)

            result = cls.get_task_result(job_instance_id)

        return result

    @classmethod
    def get_task_result(cls, job_instance_id: int):
        """
        获取执行结果
        :param job_instance_id: job任务id
        :return: example: {
                    "success": [
                        {
                            'ip': 127.0.0.1,
                            'bk_cloud_id': 0,
                            'host_id': 1,
                            'log_content': 'xx',
                        }
                    ],
                    "pending": [],
                    "failed": []
                }
        """
        params = {
            "job_instance_id": job_instance_id,
            "bk_biz_id": settings.BLUEKING_BIZ_ID,
            "bk_scope_type": constants.BkJobScopeType.BIZ_SET.value,
            "bk_scope_id": settings.BLUEKING_BIZ_ID,
            "bk_username": settings.BACKEND_JOB_OPERATOR,
            "return_ip_result": True,
        }
        job_status = JobApi.get_job_instance_status(params)
        is_finished = job_status["finished"]
        host_infos__gby_job_status = defaultdict(list)
        step_instance_id = job_status["step_instance_list"][0]["step_instance_id"]
        for instance in job_status["step_instance_list"][0]["step_ip_result_list"]:
            if settings.BKAPP_ENABLE_DHCP:
                host_info = {"ip": instance["ip"], "bk_cloud_id": instance["bk_cloud_id"]}
            else:
                host_info = {"bk_host_id": instance["bk_host_id"]}
            host_infos__gby_job_status[instance["status"]].append(host_info)
        logger.info(
            "user->[{}] called api->[{}] and got response->[{}].".format(
                settings.BACKEND_JOB_OPERATOR, job_instance_id, json.dumps(job_status)
            )
        )

        task_result = {
            "success": [],
            "pending": [],
            "failed": [],
        }
        for status, hosts in host_infos__gby_job_status.items():
            if status == JobIPStatus.SUCCESS:
                key = "success"
            elif status in (
                JobIPStatus.WAITING_FOR_EXEC,
                JobIPStatus.RUNNING,
            ):
                key = "pending"
            else:
                key = "failed"

            for host in hosts:
                base_log_params = {
                    "job_instance_id": job_instance_id,
                    "bk_biz_id": settings.BLUEKING_BIZ_ID,
                    "bk_scope_type": constants.BkJobScopeType.BIZ_SET.value,
                    "bk_scope_id": settings.BLUEKING_BIZ_ID,
                    "bk_username": settings.BACKEND_JOB_OPERATOR,
                    "step_instance_id": step_instance_id,
                }
                host_interaction_params: Dict[str, Union[str, int]] = (
                    {"bk_host_id": host["bk_host_id"]}
                    if settings.BKAPP_ENABLE_DHCP
                    else {"ip": host["ip"], "bk_cloud_id": host["bk_cloud_id"]}
                )
                log_result = JobApi.get_job_instance_ip_log({**base_log_params, **host_interaction_params})
                if settings.BKAPP_ENABLE_DHCP:
                    task_result[key].append(
                        {
                            "ip": host["ip"],
                            "bk_cloud_id": host["bk_cloud_id"],
                            "log_content": log_result["log_content"],
                        }
                    )
                else:
                    task_result[key].append(
                        {"bk_host_id": host["bk_host_id"], "log_content": log_result["log_content"]}
                    )

        return {"is_finished": is_finished, "task_result": task_result}


@dataclass
class SyncHostApMapConfig:
    enable: bool = False
    default_ap_id: typing.Dict[str, typing.Dict[str, int]] = None
    gray_ap_map: typing.Dict[str, typing.Dict[str, int]] = None
    cloud_ap_id_map: typing.Dict[str, typing.Dict[str, int]] = None
    ap_id_obj_map: typing.Dict[str, typing.Dict[str, int]] = None

    def __post_init__(self):
        if self.enable:
            if self.default_ap_id is None:
                raise ValidationError(
                    "Please check the default ap id mapping. "
                    'Example: {"enable": true, "default_ap_id": {"V1": 1, "V2": 2}}'
                )
            self.gray_ap_map = GrayTools.get_gray_ap_map()
            self.cloud_ap_id_map = models.Cloud.cloud_ap_id_map()
            self.ap_id_obj_map = models.AccessPoint.ap_id_obj_map()


def get_sync_host_ap_map_config() -> SyncHostApMapConfig:
    ap_map_config: typing.Dict[str, typing.Any] = models.GlobalSettings.get_config(
        key=models.GlobalSettings.KeyEnum.SYNC_HOST_AP_MAP_CONFIG.value, default={}
    )
    return SyncHostApMapConfig(**ap_map_config)


def get_host_ap_id(
    default_ap_id: int, bk_cloud_id: int, ap_map_config: SyncHostApMapConfig, is_gse2_gray: bool = False
) -> int:
    # 获取配置
    if default_ap_id != constants.DEFAULT_AP_ID or not ap_map_config.enable:
        # 只有一个接口的情况直接返回 或未开启配置
        return default_ap_id

    # 获取开关和映射
    if bk_cloud_id == constants.DEFAULT_CLOUD:
        # 直连区域, 如果灰度完成取2.0接入点
        ap_id: int = [
            ap_map_config.default_ap_id[GseVersion.V1.value],
            ap_map_config.default_ap_id[GseVersion.V2.value],
        ][is_gse2_gray]
    else:
        # 非直连区域, 取管控区域或者对应的映射接入点
        gray_ap_map = ap_map_config.gray_ap_map
        cloud_ap_id_map = ap_map_config.cloud_ap_id_map
        ap_id_obj_map = ap_map_config.ap_id_obj_map
        if any(
            [
                ap_id_obj_map[cloud_ap_id_map[bk_cloud_id]].gse_version == GseVersion.V2.value,
                ap_id_obj_map[cloud_ap_id_map[bk_cloud_id]].gse_version == GseVersion.V1.value and not is_gse2_gray,
            ]
        ):
            # 1.管控区域版本为V2代表此管控区域下的所有业务均已灰度
            # 2.管控区域版本为V1并且业务未灰度情况
            ap_id: int = cloud_ap_id_map[bk_cloud_id]
        elif is_gse2_gray:
            # 管控区域版本为V1业务已灰度情况取与之映射的V2 Ap_id
            try:
                ap_id: int = gray_ap_map[cloud_ap_id_map[bk_cloud_id]]
            except KeyError:
                logger.error(
                    f"No mapping found corresponding to cloud area access point id. "
                    f"bk_cloud_id->{bk_cloud_id} ap_id->{ap_id}"
                )
                ap_id: int = default_ap_id

    return ap_id
