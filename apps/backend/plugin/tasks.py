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

import logging
import traceback

from django.utils import timezone
from django.utils.translation import ugettext as _

from apps.backend.celery import app
from apps.backend.plugin import tools
from apps.backend.utils.pipeline_parser import PipelineParser as CustomPipelineParser
from apps.node_man import constants as const
from apps.node_man import models
from pipeline.service import task_service

logger = logging.getLogger("app")


# 注意，这里强行写入了queue为backend，因为发现settings中的CELERY_ROUTES失效
# 有哪位大锅有好的想法的话，可以考虑减少这个配置
@app.task(queue="backend")
def package_task(job_id, task_params):
    """
    执行一个指定的打包任务
    :param job_id: job ID
    :param task_params: 任务参数
    :return:
    """
    # 1. 判断任务是否存在 以及 任务类型是否符合预期
    try:
        job = models.Job.objects.get(id=job_id, job_type=const.JobType.PACKING_PLUGIN)

    except models.Job.DoesNotExist:
        logger.error("try to execute job-> {job_id} but is not exists".format(job_id=job_id))
        return False

    try:
        file_name = task_params["file_name"]
        is_release = task_params["is_release"]
        select_pkg_relative_paths = task_params.get("select_pkg_relative_paths")
        # 使用最后的一条上传记录
        upload_package_object = models.UploadPackage.objects.filter(file_name=file_name).order_by("-upload_time")[0]

        # 2. 执行任务
        tools.create_package_records(
            file_path=upload_package_object.file_path,
            file_name=upload_package_object.file_name,
            is_release=is_release,
            creator=task_params["bk_username"],
            select_pkg_relative_paths=select_pkg_relative_paths,
            is_template_load=task_params.get("is_template_load", False),
        )

    except PermissionError:
        detail = "failed to operate file for -> {msg}".format(msg=traceback.format_exc())
        logger.error(detail)
        job.global_params.update(err_msg=_("插件包目录操作无权限"), detail=detail)
        job.status = const.JobStatusType.FAILED

    except models.UploadPackage.DoesNotExist:
        detail = "failed to get upload_package for job-> {job_id}, task will not execute.".format(job_id=job_id)
        logger.error(detail)
        job.global_params.update(err_msg=_("插件包上传记录不存在"), detail=detail)
        job.status = const.JobStatusType.FAILED

    except Exception:
        detail = "failed to finish task-> {job_id} for-> {msg}".format(job_id=job_id, msg=traceback.format_exc())
        logger.error(detail)
        job.global_params.update(err_msg=_("插件包导入失败"), detail=detail)
        job.status = const.JobStatusType.FAILED
    else:
        job.status = const.JobStatusType.SUCCESS

    # 3. 更新任务状态
    job.end_time = timezone.now()
    job.save()

    if job.status == const.JobStatusType.SUCCESS:
        logger.info("task -> {job_id} has finish all job.".format(job_id=job.id))


@app.task(queue="backend")
def export_plugin(job_id):
    """
    开始导出一个插件
    :param job_id: 任务ID
    :return:
    """

    try:
        record = models.DownloadRecord.objects.get(id=job_id)
    except models.DownloadRecord.DoesNotExist:
        logger.error("record->[%s] not exists, nothing will do" % job_id)
        return

    record.execute()
    logger.info("record->[%s] execute success." % job_id)
    return


@app.task(queue="backend")
def run_pipeline(pipeline):
    task_service.run_pipeline(pipeline)


@app.task(queue="backend")
def stop_pipeline(pipeline_id, node_id):
    result = True
    message = "success"
    pipeline_parser = CustomPipelineParser([pipeline_id])
    state = pipeline_parser.get_node_state(node_id)["status"]
    if state == "RUNNING":
        # 正在调试的，直接强制终止
        task_service.forced_fail(node_id, ex_data="用户终止调试进程")
        operate_result = task_service.skip_activity(node_id)
        result = operate_result.result
        message = operate_result.message
    elif state == "PENDING":
        # 没在调试的，撤销任务
        operate_result = task_service.revoke_pipeline(pipeline_id)
        result = operate_result.result
        message = operate_result.message
    return result, message
