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
import requests
from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from django_prometheus.exports import ExportToDjangoView

from apps.backend.serializers.views import PackageDownloadSerializer
from apps.exceptions import ValidationError
from apps.node_man.handlers import base_info


@never_cache
def index(request):
    return render(request, "index.html")


@login_exempt
def ping(request):
    return HttpResponse("pong")


@login_exempt
def version(request):
    return JsonResponse(base_info.BaseInfoHandler.version())


@login_exempt
def metrics(request):
    return ExportToDjangoView(request)


def tools_download(request):
    ser = PackageDownloadSerializer(data=request.GET)
    if not ser.is_valid():
        raise ValidationError(_("请求参数异常 [{err}]，请确认后重试").format(err=ser.errors))
    file_name = ser.data["file_name"]
    backend_resp = requests.get(settings.DEFAULT_FILE_DOWNLOAD_API, params={"file_name": file_name}, stream=True)
    response = StreamingHttpResponse(streaming_content=backend_resp)
    response.headers["Content-Type"] = "application/octet-stream"
    response.headers["Content-Disposition"] = 'attachment;filename="{}"'.format(file_name)
    return response
