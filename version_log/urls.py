# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2019 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.conf.urls import url
from django.views.i18n import JavaScriptCatalog

from version_log import views

app_name = "version_log"

urlpatterns = (
    # 版本日志单页面
    url(r"^$", views.version_logs_page, name="version_log_page"),
    # 获取版本日志块页面（用于对话框场景）
    url(r"^block/$", views.version_logs_block, name="block"),
    # 获取版本日志列表
    url(r"^version_logs_list/$", views.version_logs_list, name="version_logs_list"),
    # 获取版本日志详情
    url(r"^version_log_detail/", views.get_version_log_detail, name="version_log_detail"),
    url(r"^jsi18n/$", JavaScriptCatalog.as_view(), name="javascript-catalog"),
)
