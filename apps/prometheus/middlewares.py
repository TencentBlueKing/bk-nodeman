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
from django.utils.deprecation import MiddlewareMixin
from django_prometheus.conf import NAMESPACE
from django_prometheus.middleware import Metrics
from prometheus_client import Counter


class NodeManMetrics(Metrics):
    def register(self):
        self.requests_by_view_app_code = self.register_metric(
            Counter,
            "django_http_requests_by_view_app_code",
            "Count of requests by view, app_code.",
            ["view", "app_code"],
            namespace=NAMESPACE,
        )


class NodeManAfterMiddleware(MiddlewareMixin):
    metrics_cls = NodeManMetrics

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.metrics = self.metrics_cls.get_instance()

    def label_metric(self, metric, request, response=None, **labels):
        return metric.labels(**labels) if labels else metric

    def _app_code(self, request):
        return request.META.get("HTTP_BK_APP_CODE", settings.APP_CODE)

    def process_view(self, request, view_func, *view_args, **view_kwargs):
        if hasattr(request, "resolver_match"):
            name = request.resolver_match.view_name or "<unnamed view>"
            self.label_metric(
                self.metrics.requests_by_view_app_code, request, view=name, app_code=self._app_code(request)
            ).inc()
