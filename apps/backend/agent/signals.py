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
from django.dispatch import receiver

from apps.backend.subscription.tools import update_job_status
from apps.node_man import constants, models
from pipeline.engine.signals import activity_failed, pipeline_end, pipeline_revoke


@receiver(pipeline_end)
def pipeline_end_handler(sender, root_pipeline_id, **kwargs):
    update_job_status(root_pipeline_id, False)
    models.JobTask.objects.filter(pipeline_id=root_pipeline_id).update(status=constants.JobStatusType.SUCCESS)


@receiver(activity_failed)
def activity_failed_handler(pipeline_id, *args, **kwargs):
    update_job_status(pipeline_id, False)
    models.JobTask.objects.filter(pipeline_id=pipeline_id).update(status=constants.JobStatusType.FAILED)


@receiver(pipeline_revoke)
def pipeline_revoke_handler(sender, root_pipeline_id, **kwargs):
    update_job_status(root_pipeline_id)
    models.JobTask.objects.filter(pipeline_id=root_pipeline_id).update(status=constants.JobStatusType.FAILED)
