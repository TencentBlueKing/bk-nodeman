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
from django.conf import settings
from django.urls import include, re_path
from rest_framework import routers as drf_routers

from apps.backend import views
from apps.backend.healthz.views import HealthzViewSet
from apps.backend.plugin.views import PluginViewSet, export_download, upload_package
from apps.backend.subscription.views import SubscriptionViewSet
from apps.backend.sync_task.views import SyncTaskViewSet

urlpatterns = [
    re_path(r"^version/?$", views.version),
]

if settings.BK_BACKEND_CONFIG or settings.IN_TEST or settings.DEBUG:
    routers = drf_routers.DefaultRouter(trailing_slash=True)
    routers.register("plugin", PluginViewSet, basename="plugin")
    routers.register("subscription", SubscriptionViewSet, basename="subscription")
    routers.register("healthz", HealthzViewSet, basename="healthz")
    routers.register("sync_task", SyncTaskViewSet, basename="sync_task")
    export_routers = drf_routers.DefaultRouter(trailing_slash=True)
    urlpatterns.extend(
        [
            re_path(r"api/", include(routers.urls)),
            re_path(r"^package/upload/$", upload_package),
            re_path(r"^export/download/$", export_download, name="export_download"),
            re_path(r"^export/", include(export_routers.urls)),
            re_path(r"^get_gse_config/", views.get_gse_config),
            re_path(r"^report_log/", views.report_log),
            re_path(r"^api/job_callback/", views.job_callback),
            re_path(r"tools/download/", views.tools_download),
        ]
    )
