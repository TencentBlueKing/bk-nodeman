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
from django.db.models import F

from apps.backend.subscription import tools
from apps.node_man import models
from common.log import logger


def activity_failed_handler(pipeline_id, pipeline_activity_id, *args, **kwargs):
    # 插件部署失败后，重试次数 +1
    instance_record = models.SubscriptionInstanceRecord.objects.filter(pipeline_id=pipeline_id).first()
    if instance_record is None:
        base_log = f"pipeline_id -> [{pipeline_id}], pipeline_activity_id -> [{pipeline_activity_id}]"
        if models.SubscriptionInstanceStatusDetail.objects.filter(node_id=pipeline_activity_id).exists():
            logger.info(f"{base_log} activity_failed_handler skipped: 重构后【进程重试次数自增】已迁移至base，详细查看节点日志。")
        else:
            logger.error(f"{base_log} activity_failed_handler error: 订阅实例不存在。")
        return
    group_id = tools.create_group_id(instance_record.subscription, instance_record.instance_info)
    models.ProcessStatus.objects.filter(
        source_type=models.ProcessStatus.SourceType.SUBSCRIPTION,
        source_id=instance_record.subscription_id,
        group_id=group_id,
    ).update(retry_times=F("retry_times") + 1)
    logger.error("[activity failed] {}, {}".format(instance_record.subscription_id, group_id))
