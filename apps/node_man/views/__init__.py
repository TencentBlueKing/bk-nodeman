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
import os

from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django_prometheus.exports import ExportToDjangoView

from apps.backend.serializers.views import PackageDownloadSerializer
from apps.core.files.storage import get_storage
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


@csrf_exempt
def download_tools(request):
    """
    用于script tools目录下的小文件下载
    :param request:
    :return:
    """
    ser = PackageDownloadSerializer(data=request.GET)
    if not ser.is_valid():
        raise ValidationError(_("请求参数异常 [{err}]，请确认后重试").format(err=ser.errors))
    filename = ser.data["file_name"]
    file_path = os.path.join(settings.PROJECT_ROOT, "script_tools", filename)
    storage = get_storage()
    if not storage.exists(file_path):
        raise ValidationError(_("文件不存在：file_path -> {file_path}").format(file_path=file_path))
    storage = get_storage()
    response = StreamingHttpResponse(streaming_content=storage.open(file_path, mode="rb"))
    response.headers["Content-Type"] = "application/octet-stream"
    response.headers["Content-Disposition"] = 'attachment;filename="{}"'.format(filename)
    return response
