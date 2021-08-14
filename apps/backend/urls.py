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
from django.conf.urls import include, url
from rest_framework import routers as drf_routers

from apps.backend import views
from apps.backend.healthz.views import HealthzViewSet
from apps.backend.plugin.views import (
    PluginViewSet,
    export_download,
    upload_package,
    upload_package_by_cos,
)
from apps.backend.subscription.views import SubscriptionViewSet

routers = drf_routers.DefaultRouter(trailing_slash=True)
routers.register("plugin", PluginViewSet, basename="plugin")
routers.register("subscription", SubscriptionViewSet, basename="subscription")
routers.register("healthz", HealthzViewSet, basename="healthz")
export_routers = drf_routers.DefaultRouter(trailing_slash=True)

urlpatterns = [
    url(r"api/", include(routers.urls)),
    url(r"^package/upload/$", upload_package),
    url(r"^package/upload_cos/$", upload_package_by_cos),
    url(r"^export/download/$", export_download, name="export_download"),
    url(r"^export/", include(export_routers.urls)),
    url(r"^get_gse_config/", views.get_gse_config),
    url(r"^report_log/", views.report_log),
    url(r"^api/job_callback/", views.job_callback),
]
