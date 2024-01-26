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
from django.conf.urls import include, url
from rest_framework import routers as drf_routers

from apps.backend import views
from apps.backend.agent.views import AgentViewSet
from apps.backend.healthz.views import HealthzViewSet
from apps.backend.plugin.views import PluginViewSet, export_download, upload_package
from apps.backend.subscription.views import SubscriptionViewSet
from apps.backend.sync_task.views import SyncTaskViewSet

urlpatterns = [
    url(r"^version/?$", views.version),
]

if settings.BK_BACKEND_CONFIG or settings.IN_TEST or settings.DEBUG:
    routers = drf_routers.DefaultRouter(trailing_slash=True)
    routers.register("plugin", PluginViewSet, basename="plugin")
    routers.register("subscription", SubscriptionViewSet, basename="subscription")
    routers.register("healthz", HealthzViewSet, basename="healthz")
    routers.register("sync_task", SyncTaskViewSet, basename="sync_task")
    routers.register("agent", AgentViewSet, basename="agent")
    export_routers = drf_routers.DefaultRouter(trailing_slash=True)
    urlpatterns.extend(
        [
            url(r"api/", include(routers.urls)),
            url(r"^package/upload/$", upload_package),
            url(r"^export/download/$", export_download, name="export_download"),
            url(r"^export/", include(export_routers.urls)),
            url(r"^get_gse_config/", views.get_gse_config),
            url(r"^report_log/", views.report_log),
            url(r"^api/job_callback/", views.job_callback),
            url(r"tools/download/", views.tools_download),
        ]
    )
