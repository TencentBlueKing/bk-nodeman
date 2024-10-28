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

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import ModelViewSet
from apps.node_man.handlers.job import JobHandler
from apps.node_man.handlers.permission import JobPermission
from apps.node_man.models import Job
from apps.node_man.serializers import response
from apps.node_man.serializers.job import (
    FetchCommandSerializer,
    InstallSerializer,
    JobInstanceOperateSerializer,
    JobInstancesOperateSerializer,
    ListSerializer,
    OperateSerializer,
    RetrieveSerializer,
)
from apps.utils.local import get_request_username

JOB_VIEW_TAGS = ["job"]


class JobViewSet(ModelViewSet):
    model = Job
    permission_classes = (JobPermission,)

    @swagger_auto_schema(
        operation_summary="查询任务列表",
        tags=JOB_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=ListSerializer)
    def job_list(self, request, *args, **kwargs):
        """
        @api {POST} /job/job_list/ 查询任务列表
        @apiName list_job
        @apiGroup Job
        @apiParam {List} job_id 任务ID
        @apiParam {List} [job_type] 任务类型
        @apiParam {List} [status] 状态
        @apiParam {List} [created_by] 执行者
        @apiParam {List} [bk_biz_id] 业务ID
        @apiParam {Int} page 当前页数
        @apiParam {Int} pagesize 分页大小
        @apiParam {object} [sort] 排序
        @apiParam {String=["total_count", "failed_count","success_count"]} [sort.head] 排序字段
        @apiParam {String=["ASC", "DEC"]} [sort.sort_type] 排序类型
        @apiParamExample {Json} 请求例子:
        {
            "page": 1,
            "pagesize": 20,
            "job_type": ["INSTALL_AGENT"]
        }
        @apiSuccessExample {json} 成功返回:
        {
            "total": 100,
            "list": [
                {
                    "id": 1,
                    "job_type": "INSTALL_PROXY",
                    "job_type_display": "安装Proxy",
                    "creator": "admin",
                    "start_time": "2019-10-08 11:10:10",
                    "cost_time": 120,
                    "status": "RUNNING",
                    "bk_biz_scope_display": ["蓝鲸", "layman"]
                    "statistics": {
                        "success_count": 200,
                        "failed_count": 100,
                        "running_count": 100,
                        "total_count": 100
                    }
                }
            ]
        }
        """
        return Response(JobHandler().list(self.validated_data, get_request_username()))

    @swagger_auto_schema(
        operation_id="job_details",
        operation_summary="查询任务详情",
        responses={status.HTTP_200_OK: response.JobLogResponseSerializer()},
        tags=JOB_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=True, methods=["POST"], serializer_class=RetrieveSerializer)
    def details(self, request, *args, **kwargs):
        """
        @api {POST} /job/{{pk}}/details/ 查询任务详情
        @apiName retrieve_job
        @apiGroup Job
        """
        return Response(JobHandler(job_id=kwargs["pk"]).retrieve(self.validated_data))

    @swagger_auto_schema(
        operation_id="job_install",
        operation_summary="安装类任务",
        operation_description="安装作业任务, 新安装Agent、新安装Proxy、重装、替换等操作",
        responses={status.HTTP_200_OK: response.JobInstallSerializer()},
        tags=JOB_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["POST"], serializer_class=InstallSerializer)
    def install(self, request):
        """
        @api {POST} /job/install/ 安装类任务
        @apiDescription 新安装Agent、新安装Proxy、重装、替换等操作
        @apiName install_job
        @apiGroup Job
        """
        validated_data = self.validated_data
        hosts = validated_data["hosts"]
        op_type = validated_data["op_type"]
        node_type = validated_data["node_type"]
        job_type = validated_data["job_type"]
        ticket = request.COOKIES.get("TCOA_TICKET") or validated_data.get("tcoa_ticket")
        extra_params = {
            "is_install_latest_plugins": validated_data["is_install_latest_plugins"],
            "is_install_other_agent": validated_data["is_install_other_agent"],
            "script_hooks": validated_data.get("script_hooks", []),
        }
        extra_config = validated_data.get("agent_setup_info") or {}
        return Response(JobHandler().install(hosts, op_type, node_type, job_type, ticket, extra_params, extra_config))

    @swagger_auto_schema(
        operation_id="job_operate",
        operation_summary="操作类任务",
        operation_description="用于只有bk_host_id参数的主机下线、重启等操作",
        responses={status.HTTP_200_OK: response.JobOperateSerializer()},
        tags=JOB_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=False, methods=["POST"], serializer_class=OperateSerializer)
    def operate(self, request):
        """
        @api {POST} /job/operate/ 操作类任务
        @apiDescription 用于只有bk_host_id参数的主机下线、重启等操作。<br>
        bk_host_id和exclude_hosts必填一个。<br>
        若填写了 exclude_hosts ，则代表跨页全选模式。<br>
        注意, 管控区域ID、业务ID等筛选条件，仅在跨页全选模式下有效。<br>
        @apiName operate_job
        @apiGroup Job
        """
        validated_data = self.validated_data
        job_type = validated_data["job_type"]
        hosts = validated_data["hosts"]
        bk_biz_scope = validated_data["bk_biz_scope"]
        extra_params = {
            "is_install_latest_plugins": validated_data["is_install_latest_plugins"],
            "is_install_other_agent": validated_data["is_install_other_agent"],
        }
        extra_config = validated_data.get("agent_setup_info") or {}
        return Response(JobHandler().operate(job_type, hosts, bk_biz_scope, extra_params, extra_config))

    @swagger_auto_schema(
        operation_summary="重试任务",
        tags=JOB_VIEW_TAGS,
    )
    @action(detail=True, methods=["POST"], serializer_class=JobInstancesOperateSerializer)
    def retry(self, request, *args, **kwargs):
        """
        @api {POST} /job/{{pk}}/retry/ 重试任务
        @apiName retry_job
        @apiGroup Job
        @apiParam {Number[]} instance_id_list 主机ID列表
        @apiParamExample {Json} 重装、升级等请求参数
        {
            "instance_id_list": [1, 2, 3]
        }
        """
        return Response(JobHandler(job_id=kwargs["pk"]).retry(request.data.get("instance_id_list")))

    @swagger_auto_schema(
        operation_summary="终止任务",
        tags=JOB_VIEW_TAGS,
    )
    @action(detail=True, methods=["POST"], serializer_class=JobInstancesOperateSerializer)
    def revoke(self, request, *args, **kwargs):
        """
        @api {POST} /job/{{pk}}/revoke/ 终止任务
        @apiName revoke_job
        @apiGroup Job
        @apiParam {Number[]} instance_id_list 主机ID列表
        @apiParamExample {Json} 请求样例
        {
            "instance_id_list": [1, 2, 3]
        }
        """
        return Response(JobHandler(job_id=kwargs["pk"]).revoke(request.data.get("instance_id_list", [])))

    @swagger_auto_schema(
        operation_summary="原子粒度重试任务",
        tags=JOB_VIEW_TAGS,
    )
    @action(detail=True, methods=["POST"], serializer_class=JobInstanceOperateSerializer)
    def retry_node(self, request, *args, **kwargs):
        """
        @api {POST} /job/{{pk}}/retry_node/ 原子粒度重试任务
        @apiName retry_node
        @apiGroup Job
        @apiParam {String} instance_id 实例id
        @apiParamExample {Json} 重试时请求参数
        {
            "instance_id": host|instance|host|127.0.0.1-0-0
        }
        @apiSuccessExample {json} 成功返回:
        {
            "result": true,
            "data": {
                "retry_node_id": "6f48169ed1193574961757a57d03a778",
                "retry_node_name": "安装"
            },
            "code": 0,
            "message": ""
        }
        """
        return Response(JobHandler(job_id=kwargs["pk"]).retry_node(request.data.get("instance_id", None)))

    @swagger_auto_schema(
        operation_id="get_job_log",
        operation_summary="查询日志",
        query_serializer=JobInstanceOperateSerializer(),
        responses={status.HTTP_200_OK: response.JobLogResponseSerializer()},
        tags=JOB_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    @action(detail=True, serializer_class=JobInstanceOperateSerializer)
    def log(self, request, *args, **kwargs):
        """
        @api {GET} /job/{{pk}}/log/ 查询日志
        @apiName get_job_log
        @apiGroup Job
        @apiParam {Number} job_id 任务ID
        @apiParam {Number} instance_id 实例ID
        @apiParamExample {Json} 重装、升级等请求参数
        {
            "bk_host_id": 1
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "step": "检查网络连通性",
                "status": "success",
                "log": "checking network……\nok"
            },
            {
                "step": "检查用户",
                "status": "success",
                "log": "checking user……\nusername is root\nok"
            }
        ]
        """
        return Response(JobHandler(job_id=kwargs["pk"]).get_log(request.query_params["instance_id"]))

    @swagger_auto_schema(
        operation_summary="查询日志",
        tags=JOB_VIEW_TAGS,
    )
    @action(detail=True, methods=["POST"], serializer_class=JobInstanceOperateSerializer)
    def collect_log(self, request, *args, **kwargs):
        """
        @api {POST} /job/{{pk}}/collect_log/ 查询日志
        @apiName collect_job_log
        @apiGroup Job
        @apiParam {Number} job_id 任务ID
        @apiSuccessExample {json} 成功返回:
        {
            "celery_id": "c0072075-730b-461b-8c3e-1f00095b7348"
        },
        """
        return Response(JobHandler(job_id=kwargs["pk"]).collect_log(request.data.get("instance_id")))

    @swagger_auto_schema(
        operation_summary="获取安装命令",
        tags=JOB_VIEW_TAGS,
    )
    @action(detail=True, methods=["GET"], serializer_class=FetchCommandSerializer)
    def get_job_commands(self, request, *args, **kwargs):
        """
        @api {GET} /job/{{pk}}/get_job_commands/ 获取安装命令
        @apiName get_job_commands
        @apiGroup Job
        @apiParam {Number} job_id 任务ID
        @apiParam {Number} bk_host_id 主机ID
        @apiSuccessExample {json} 成功返回:
        {
            bk_cloud_id: {
                'win_commands': '',
                'pre_commands': '',
                'run_commands': ''
            }
        },
        """
        validated_data = self.validated_data
        return Response(
            JobHandler(job_id=kwargs["pk"]).get_commands(
                request_bk_host_id=validated_data["bk_host_id"],
                is_uninstall=validated_data["is_uninstall"],
            )
        )
