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
from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.conf.urls import url
from django.urls import include
from iam import IAM
from iam.contrib.django.dispatcher import DjangoBasicResourceApiDispatcher
from rest_framework import routers

from apps.node_man import views
from apps.node_man.iam_provider import (
    ApResourceProvider,
    BusinessResourceProvider,
    CloudResourceProvider,
    PackageResourceProvider,
    StrategyResourceProvider,
)
from apps.node_man.views import (
    ap,
    cloud,
    cmdb,
    debug,
    host,
    install_channel,
    job,
    meta,
    permission,
    plugin,
    policy,
    tjj,
)
from apps.node_man.views.healthz import HealthzViewSet
from apps.node_man.views.host_v2 import HostV2ViewSet
from apps.node_man.views.plugin import GsePluginViewSet
from apps.node_man.views.plugin_v2 import PluginV2ViewSet

iam = IAM(settings.APP_CODE, settings.SECRET_KEY, settings.BK_IAM_INNER_HOST, settings.BK_COMPONENT_API_URL)

router = routers.DefaultRouter(trailing_slash=True)

router.register(r"ap", ap.ApViewSet, basename="ap")
router.register(r"cloud", cloud.CloudViewSet, basename="cloud")
router.register(r"install_channel", install_channel.InstallChannelViewSet, basename="install_channel")
router.register(r"host", host.HostViewSet, basename="host")
router.register(r"v2/host", HostV2ViewSet, basename="host_v2")
router.register(r"job", job.JobViewSet, basename="job")
router.register(r"permission", permission.PermissionViewSet, basename="permission")
router.register(r"cmdb", cmdb.CmdbViews, basename="cmdb")
router.register(r"debug", debug.DebugViews, basename="debug")
router.register(r"meta", meta.MetaViews, basename="meta")
router.register(r"tjj", tjj.TjjViews, basename="tjj")
router.register(r"policy", policy.PolicyViewSet, basename="policy")
router.register(r"plugin/(?P<category>\w+)/process", GsePluginViewSet)
router.register(r"plugin", plugin.PluginViewSet, basename="plugin")
router.register(r"plugin/(?P<process>\w+)/package", plugin.PackagesViews, basename="package")
router.register(r"plugin/process", plugin.ProcessStatusViewSet, basename="process_status")
router.register(r"v2/plugin", PluginV2ViewSet, basename="plugin_v2")
router.register(r"healthz", HealthzViewSet, basename="healthz")

biz_dispatcher = DjangoBasicResourceApiDispatcher(iam, settings.BK_IAM_SYSTEM_ID)
biz_dispatcher.register("biz", BusinessResourceProvider())
cloud_dispatcher = DjangoBasicResourceApiDispatcher(iam, settings.BK_IAM_SYSTEM_ID)
cloud_dispatcher.register("cloud", CloudResourceProvider())
ap_dispatcher = DjangoBasicResourceApiDispatcher(iam, settings.BK_IAM_SYSTEM_ID)
ap_dispatcher.register("ap", ApResourceProvider())
strategy_dispatcher = DjangoBasicResourceApiDispatcher(iam, settings.BK_IAM_SYSTEM_ID)
strategy_dispatcher.register("strategy", StrategyResourceProvider())
package_dispatcher = DjangoBasicResourceApiDispatcher(iam, settings.BK_IAM_SYSTEM_ID)
package_dispatcher.register("package", PackageResourceProvider())

urlpatterns = [
    url(r"^$", views.index),
    url(r"ping", views.ping),
    url(r"api/", include(router.urls)),
    url(r"api/iam/v1/biz", biz_dispatcher.as_view([login_exempt])),
    url(r"api/iam/v1/cloud", cloud_dispatcher.as_view([login_exempt])),
    url(r"api/iam/v1/ap", ap_dispatcher.as_view([login_exempt])),
    url(r"api/iam/v1/strategy", strategy_dispatcher.as_view([login_exempt])),
    url(r"api/iam/v1/package", package_dispatcher.as_view([login_exempt])),
]
