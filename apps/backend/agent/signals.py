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
from django.dispatch import receiver

from pipeline.engine.signals import activity_failed, pipeline_end, pipeline_revoke


@receiver(pipeline_end)
def pipeline_end_handler(sender, root_pipeline_id, **kwargs):
    pass


@receiver(activity_failed)
def activity_failed_handler(pipeline_id, *args, **kwargs):
    pass


@receiver(pipeline_revoke)
def pipeline_revoke_handler(sender, root_pipeline_id, **kwargs):
    pass
