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
import json

from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.urls import include, re_path
from iam import IAM
from iam.contrib.django.dispatcher import (
    DjangoBasicResourceApiDispatcher,
    InvalidPageException,
)
from iam.contrib.django.dispatcher.dispatchers import fail_response, logger
from iam.contrib.django.dispatcher.exceptions import KeywordTooShortException
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
    password,
    permission,
    plugin,
    policy,
)
from apps.node_man.views.excel import ExcelHandlerViewSet
from apps.node_man.views.healthz import HealthzViewSet
from apps.node_man.views.host_v2 import HostV2ViewSet
from apps.node_man.views.plugin import GsePluginViewSet
from apps.node_man.views.plugin_v2 import PluginV2ViewSet
from apps.node_man.views.sync_task import SyncTaskViewSet
from apps.utils.local import get_tenant_id

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
router.register(r"tjj", password.PasswordViews, basename="tjj")
router.register(r"policy", policy.PolicyViewSet, basename="policy")
router.register(r"plugin/(?P<category>\w+)/process", GsePluginViewSet)
router.register(r"plugin", plugin.PluginViewSet, basename="plugin")
router.register(r"plugin/(?P<process>[\w-]+)/package", plugin.PackagesViews, basename="package")
router.register(r"plugin/process", plugin.ProcessStatusViewSet, basename="process_status")
router.register(r"v2/plugin", PluginV2ViewSet, basename="plugin_v2")
router.register(r"healthz", HealthzViewSet, basename="healthz")
router.register(r"sync_task", SyncTaskViewSet, basename="sync_task")
router.register(r"excel", ExcelHandlerViewSet, basename="excel")


class ResourceApiDispatcher(DjangoBasicResourceApiDispatcher):
    def __init__(self, system):
        self.system = system
        self._provider = {}

    def _get_options(self, request):
        opts = {"language": request.META.get("HTTP_BLUEKING_LANGUAGE", "zh-cn")}
        if "HTTP_X_BK_TENANT_ID" in request.META:
            opts["bk_tenant_id"] = request.META["HTTP_X_BK_TENANT_ID"]
        else:
            opts["bk_tenant_id"] = "default"
        return opts

    def _dispatch(self, request):

        request_id = request.META.get("HTTP_X_REQUEST_ID", "")

        iam_client = IAM(settings.APP_CODE, settings.SECRET_KEY, settings.BK_IAM_APIGATEWAY_URL, get_tenant_id())
        # auth check
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        auth_allowed = iam_client.is_basic_auth_allowed(self.system, auth)

        if not auth_allowed:
            logger.error("resource request(%s) auth failed with auth param: %s", request_id, auth)
            return fail_response(401, "basic auth failed", request_id)

        # load json data
        try:
            data = json.loads(request.body)
        except Exception:
            logger.error("resource request(%s) failed with invalid body: %s", request_id, request.body)
            return fail_response(400, "request body is not a valid json", request_id)

        # check basic params
        method = data.get("method")
        resource_type = data.get("type")
        if not (method and resource_type):
            logger.error(
                "resource request(%s) failed with invalid data: %s. method and type required", request_id, data
            )
            return fail_response(400, "method and type is required field", request_id)

        # check resource type
        if resource_type not in self._provider:
            logger.error("resource request(%s) failed with unsupported resource type: %s", request_id, resource_type)
            return fail_response(404, "unsupported resource type: {}".format(resource_type), request_id)

        # check method and process
        processor = getattr(self, "_dispatch_{}".format(method), None)
        if not processor:
            logger.error("resource request(%s) failed with unsupported method: %s", request_id, method)
            return fail_response(404, "unsupported method: {}".format(method), request_id)

        logger.info("resource request(%s) with filter: %s, page: %s", request_id, data.get("filter"), data.get("page"))
        try:
            return processor(request, data, request_id)
        except InvalidPageException as e:
            return fail_response(422, str(e), request_id)
        except KeywordTooShortException as e:
            return fail_response(406, str(e), request_id)
        except Exception as e:
            logger.exception("resource request(%s) failed with exception: %s", request_id, e)
            return fail_response(500, str(e), request_id)


biz_dispatcher = ResourceApiDispatcher(settings.BK_IAM_SYSTEM_ID)
biz_dispatcher.register("biz", BusinessResourceProvider())
cloud_dispatcher = ResourceApiDispatcher(settings.BK_IAM_SYSTEM_ID)
cloud_dispatcher.register("cloud", CloudResourceProvider())
ap_dispatcher = ResourceApiDispatcher(settings.BK_IAM_SYSTEM_ID)
ap_dispatcher.register("ap", ApResourceProvider())
strategy_dispatcher = ResourceApiDispatcher(settings.BK_IAM_SYSTEM_ID)
strategy_dispatcher.register("strategy", StrategyResourceProvider())
package_dispatcher = ResourceApiDispatcher(settings.BK_IAM_SYSTEM_ID)
package_dispatcher.register("package", PackageResourceProvider())

urlpatterns = [
    re_path(r"^$", views.index),
    re_path(r"^ping/?$", views.ping),
    re_path(r"^version/?$", views.version),
    re_path(r"^metrics/?$", views.metrics),
    re_path(r"^logout/?$", views.user_exit),
    re_path(r"^tools/download/$", views.tools_download),
    re_path(r"api/", include(router.urls)),
    re_path(r"api/iam/v1/biz", biz_dispatcher.as_view([login_exempt])),
    re_path(r"api/iam/v1/cloud", cloud_dispatcher.as_view([login_exempt])),
    re_path(r"api/iam/v1/ap", ap_dispatcher.as_view([login_exempt])),
    re_path(r"api/iam/v1/strategy", strategy_dispatcher.as_view([login_exempt])),
    re_path(r"api/iam/v1/package", package_dispatcher.as_view([login_exempt])),
]
