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
from io import BytesIO

from django.http import StreamingHttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet
from apps.node_man.handlers.excel import ExcelHandler
from apps.node_man.serializers.excel import (
    ExcelDownloadSerializer,
    ExcelUploadSerializer,
)

EXCEL_VIEW_TAGS = ["excel"]


class ExcelHandlerViewSet(APIViewSet):
    @swagger_auto_schema(
        operation_summary="获取excel模板",
        responses={status.HTTP_200_OK: ExcelDownloadSerializer()},
        tags=EXCEL_VIEW_TAGS,
    )
    @action(detail=False, methods=["GET"], serializer_class=ExcelDownloadSerializer)
    def download(self, request):
        """
        @api {GET} /excel/download/ 获取excel模板
        @apiName download_excel
        @apiGroup Excel
        @apiParamExample {Json} 请求例子:
        {
        }
        @apiSuccessExample {Json} 成功返回:
        {
        }
        """

        file = ExcelHandler().generate_excel_template()
        output = BytesIO()
        file.save(output)
        output.seek(0)

        filename = "bk_nodeman_info.xlsx"
        response = StreamingHttpResponse(streaming_content=output)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers["Content-Disposition"] = 'attachment;filename="{}"'.format(filename)
        return response

    @swagger_auto_schema(
        operation_summary="上传excel",
        request_body=ExcelUploadSerializer(),
        tags=EXCEL_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=ExcelUploadSerializer)
    def upload(self, request):
        """
        @api {POST} /excel/upload/ 上传excel
        @apiName upload_excel
        @apiGroup Excel
        @apiParam {File} file excel文件
        @apiParamExample {Form} 请求例子:
        {
            "file": file
        }
        @apiSuccessExample {Json} 成功返回:
        {
        }
        """
        ser = self.serializer_class(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        file = data["file"]

        return Response(ExcelHandler().analyze_excel(file))
