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
from django.db import models
from django.utils.translation import ugettext_lazy as _


class DataAPIRecord(models.Model):

    request_datetime = models.DateTimeField()
    url = models.CharField(max_length=128, db_index=True)
    module = models.CharField(max_length=64, db_index=True)
    method = models.CharField(max_length=16)
    method_override = models.CharField(max_length=16, null=True)
    query_params = models.TextField()

    response_result = models.BooleanField()
    response_code = models.CharField(max_length=16, db_index=True)
    response_data = models.TextField()
    response_message = models.CharField(max_length=1024, null=True)
    response_errors = models.TextField(null=True, default=None)

    cost_time = models.FloatField()
    request_id = models.CharField(max_length=64, db_index=True)

    class Meta:
        verbose_name = _("【平台日志】API调用日志")
        verbose_name_plural = _("【平台日志】API调用日志")
        app_label = "api"
