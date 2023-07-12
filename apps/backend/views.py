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
import os
import time
from typing import Dict

import ujson as json
from bkcrypto.contrib.django.ciphers import symmetric_cipher_manager
from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from apps.backend.constants import (
    REDIS_AGENT_CONF_KEY_TPL,
    REDIS_INSTALL_CALLBACK_KEY_TPL,
)
from apps.backend.serializers.views import PackageDownloadSerializer
from apps.backend.subscription.steps.agent_adapter import legacy
from apps.backend.subscription.steps.agent_adapter.adapter import AgentStepAdapter
from apps.backend.utils.redis import REDIS_INST
from apps.core.files.storage import get_storage
from apps.exceptions import ValidationError
from apps.node_man import constants, models
from apps.node_man.handlers import base_info
from apps.node_man.models import Host, JobSubscriptionInstanceMap
from pipeline.service import task_service

logger = logging.getLogger("app")


# 记录日志并设置过期时间
# 使用 lua 脚本合并 Redis 请求，保证操作的原子性，同时减少网络 IO
# unpack(ARGV, 2) 对 table（lua 中的 list / dict）解包，2 为切片的起始位置（lua 索引从 1 开始），实现日志添加到列表
# ARGV[1] 过期时间（单位 seconds）
LPUSH_AND_EXPIRE_SCRIPT = """
local length
length = redis.call("lpush", KEYS[1], unpack(ARGV, 2))
redis.call("expire", KEYS[1], ARGV[1])
return length
"""

try:
    LPUSH_AND_EXPIRE_FUNC = REDIS_INST.register_script(script=LPUSH_AND_EXPIRE_SCRIPT)
except Exception as e:
    LPUSH_AND_EXPIRE_FUNC = None
    logger.exception(e)


@login_exempt
@csrf_exempt
def get_gse_config(request):
    """
    @api {POST} /get_gse_config/ 获取配置
    @apiName get_gse_config
    @apiGroup subscription
    """
    data = json.loads(request.body)

    bk_cloud_id = int(data.get("bk_cloud_id"))
    filename = data.get("filename")
    node_type = data.get("node_type")
    inner_ip = data.get("inner_ip")
    token = data.get("token")

    decrypted_token = _decrypt_token(token)
    if inner_ip != decrypted_token["inner_ip"] or bk_cloud_id != decrypted_token["bk_cloud_id"]:
        err_msg = "token[{token}] 非法, 请求参数为: {data}, token解析为: {decrypted_token}".format(
            token=token, data=data, decrypted_token=decrypted_token
        )
        logger.error(err_msg)
        raise PermissionError(err_msg)

    config = REDIS_INST.get(REDIS_AGENT_CONF_KEY_TPL.format(file_name=filename, sub_inst_id=decrypted_token["inst_id"]))
    if config:
        return HttpResponse(config.decode())

    subscription_id: int = models.SubscriptionInstanceRecord.objects.get(id=decrypted_token["inst_id"]).subscription_id
    # 安装 Agent step 只会有一个，如后续需要扩展，在 token 里补充 subscription_step_id
    sub_step_obj: models.SubscriptionStep = models.SubscriptionStep.objects.filter(
        subscription_id=subscription_id
    ).first()

    try:
        host = Host.objects.get(bk_host_id=decrypted_token["bk_host_id"])
        ap_id_obj_map: Dict[int, models.AccessPoint] = models.AccessPoint.ap_id_obj_map()
        host_ap: models.AccessPoint = ap_id_obj_map[int(decrypted_token["host_ap_id"])]
        agent_step_adapter: AgentStepAdapter = AgentStepAdapter(
            subscription_step=sub_step_obj, gse_version=host_ap.gse_version
        )
        if filename in ["bscp.yaml"]:
            config = legacy.generate_bscp_config(host=host)
        else:
            config = agent_step_adapter.get_config(host=host, ap=host_ap, filename=filename, node_type=node_type)
    except Exception as e:
        logging.error(f"get_gse_config error: params:{data}, error: {e}")
        return HttpResponse(config, status=500)

    return HttpResponse(config)


@login_exempt
@csrf_exempt
def report_log(request):
    """
    @api {POST} /report_log/ 上报日志
    @apiName report_log
    @apiGroup subscription
    @apiParam {object} request
    @apiParamExample {Json} 请求参数
    {
        "task_id": "node_id",
        "token": "",
        "logs": [
            {
                "timestamp": "1580870937",
                "level": "INFO",
                "step": "check_deploy_result",
                "log": "gse agent has been deployed successfully",
                "status": "DONE"
            }
        ]
    }
    """
    logger.info(f"[report_log]: {request.body}")
    data = json.loads(str(request.body, encoding="utf8").replace('\\"', "'").replace("\\", "/"))

    token = data.get("token")
    decrypted_token = _decrypt_token(token)

    if decrypted_token.get("task_id") != data["task_id"]:
        logger.error(f"token[{token}] 非法, task_id为:{data['task_id']}, token解析为: {decrypted_token}")
        raise PermissionError("what are you doing?")

    # 把日志写入redis中，由install service中的schedule方法统一读取，避免频繁callback
    name = REDIS_INSTALL_CALLBACK_KEY_TPL.format(sub_inst_id=decrypted_token["inst_id"])
    json_dumps_logs = [json.dumps(log) for log in data["logs"]]
    # 日志会被 Service 消费并持久化，在 Redis 保留一段时间便于排查「主机 -api-> Redis -log-> DB」 上的问题
    LPUSH_AND_EXPIRE_FUNC(keys=[name], args=[constants.TimeUnit.DAY] + json_dumps_logs)
    return JsonResponse({})


@login_exempt
@csrf_exempt
def job_callback(request):
    """
    作业平台回调，回调数据格式为:
    {
        "job_instance_id": 12345,
        "status": 2,
        "step_instance_list": [
            {
                "step_instance_id": 16271,
                "status": 3
            },
            {
                "step_instance_id": 16272,
                "status": 2
            }
        ]
    }
    """
    data = json.loads(request.body)
    logger.info("[job_callback] {}".format(request.body))
    job_sub_map = JobSubscriptionInstanceMap.objects.get(job_instance_id=data["job_instance_id"])
    task_service.callback(job_sub_map.node_id, data)
    return JsonResponse({})


def _decrypt_token(token: str) -> dict:
    """
    解析token
    """
    try:
        token_decrypt = symmetric_cipher_manager.cipher().decrypt(token)
    except Exception as err:
        logger.error(f"{token} 解析失败")
        raise err
    bk_host_id, inner_ip, bk_cloud_id, task_id, timestamp, inst_id, host_ap_id = token_decrypt.split("|")
    return_value = {
        "bk_host_id": bk_host_id,
        "inner_ip": inner_ip,
        "bk_cloud_id": int(bk_cloud_id),
        "task_id": task_id,
        "timestamp": timestamp,
        "inst_id": inst_id,
        "host_ap_id": host_ap_id,
    }
    # timestamp 超过1小时，认为是非法请求
    if time.time() - float(timestamp) > 3600:
        raise PermissionError(f"token[{token}] 非法, timestamp超时不符合预期, {return_value}")
    return return_value


@login_exempt
def version(request):
    return JsonResponse(base_info.BaseInfoHandler.version())


@login_exempt
def tools_download(request):
    """
    用于script tools目录下的小文件下载
    :param request:
    :return:
    """
    ser = PackageDownloadSerializer(data=request.GET)
    if not ser.is_valid():
        logger.error("failed to valid request data for->[%s] maybe something go wrong?" % ser.errors)
        raise ValidationError(_("请求参数异常 [{err}]，请确认后重试").format(err=ser.errors))
    filename = ser.data["file_name"]
    file_path = os.path.join(settings.DOWNLOAD_PATH, filename)
    storage = get_storage()
    if not storage.exists(file_path):
        raise ValidationError(_("文件不存在：file_path -> {file_path}").format(file_path=file_path))
    response = StreamingHttpResponse(streaming_content=storage.open(file_path, mode="rb"))
    return response
