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

from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import ModelViewSet
from apps.node_man.handlers.job import JobHandler
from apps.node_man.handlers.permission import JobPermission
from apps.node_man.models import Job
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


class JobViewSet(ModelViewSet):
    model = Job
    permission_classes = (JobPermission,)

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

    @action(detail=True, methods=["POST"], serializer_class=RetrieveSerializer)
    def details(self, request, *args, **kwargs):
        """
        @api {POST} /job/{{pk}}/details/ 查询任务详情
        @apiName retrieve_job
        @apiGroup Job
        @apiParam {List} [conditions] 条件
        @apiParam {Int} page 当前页数
        @apiParam {Int} pagesize 分页大小
        @apiSuccessExample {json} 成功返回:
        {
            "total": 100,
            "list": [
                {
                    "bk_host_id": 1,
                    "inner_ip": "127.0.0.1",
                    "bk_cloud_id": 1,
                    "bk_cloud_name": "云区域名称",
                    "bk_biz_id": 2,
                    "bk_biz_name": "业务名称",
                    "status": "RUNNING",
                    "status_display": "正在执行"
                }
            ],
            "statistics": {
                "success_count": 200,
                "failed_count": 100,
                "running_count": 100,
                "total_count": 100
            },
            "status": "RUNNING"
        }
        """
        return Response(JobHandler(job_id=kwargs["pk"]).retrieve(self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=InstallSerializer)
    def install(self, request):
        """
        @api {POST} /job/install/ 安装类任务
        @apiDescription 新安装Agent、新安装Proxy、重装、替换等操作
        @apiName install_job
        @apiGroup Job
        @apiParam {String} job_type 任务类型
        @apiParam {Object[]} hosts 主机信息
        @apiParam {Number} host.bk_cloud_id 云区域ID
        @apiParam {Number} [host.ap_id] 接入点ID
        @apiParam {Number} [hosts.bk_host_id] 主机ID, 创建时可选, 更改时必选
        @apiParam {String="Windows","Linux","AIX"} hosts.os_type 操作系统类型
        @apiParam {Number} hosts.bk_biz_id 业务ID
        @apiParam {String} hosts.inner_ip 内网IP
        @apiParam {String} [hosts.outer_ip] 外网IP
        @apiParam {String} [hosts.login_ip] 登录IP
        @apiParam {String} [hosts.data_ip] 数据IP
        @apiParam {String} hosts.account 账户名
        @apiParam {Number} hosts.port 端口
        @apiParam {String} hosts.auth_type 认证类型
        @apiParam {String} [hosts.password] 密码
        @apiParam {String} [hosts.key] 密钥
        @apiParam {Number} [hosts.retention] 密码保留天数
        @apiParam {Number} [replace_host_id] 要替换的ProxyID，替换proxy时使用
        @apiParamExample {Json} 安装请求参数
        {
            "job_type": "INSTALL_AGENT",
            "hosts": [
                {
                    "bk_cloud_id": 1,
                    "ap_id": 1,
                    "bk_biz_id": 2,
                    "os_type": "Linux",
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2",
                    "login_ip": "127.0.0.3",
                    "data_ip": "127.0.0.4",
                    "account": "root",
                    "port": 22,
                    "auth_type": "PASSWORD",
                    "password": "password",
                    "key": "key"
                }
            ],
            "retention": 1,
            "replace_host_id": 1
        }
        @apiSuccessExample {json} 成功返回:
        {
            "job_id": 35,
            "ip_filter": []
        }
        """
        validated_data = self.validated_data
        hosts = validated_data["hosts"]
        op_type = validated_data["op_type"]
        node_type = validated_data["node_type"]
        job_type = validated_data["job_type"]
        ticket = request.COOKIES.get("TCOA_TICKET") or validated_data.get("tcoa_ticket")
        return Response(
            JobHandler().install(
                hosts,
                op_type,
                node_type,
                job_type,
                ticket,
            )
        )

    @action(detail=False, methods=["POST"], serializer_class=OperateSerializer)
    def operate(self, request):
        """
        @api {POST} /job/operate/ 操作类任务
        @apiDescription 用于只有bk_host_id参数的主机下线、重启等操作。<br>
        bk_host_id和exclude_hosts必填一个。<br>
        若填写了 exclude_hosts ，则代表跨页全选模式。<br>
        注意, 云区域ID、业务ID等筛选条件，仅在跨页全选模式下有效。<br>
        @apiName operate_job
        @apiGroup Job
        @apiParam {String} job_type 任务类型
        @apiParam {String} [bk_biz_id] 业务ID
        @apiParam {List} [conditions] 搜索条件，支持os_type, ip, status <br>
        version, bk_cloud_id, node_from 和 模糊搜索query
        @apiParam {Int[]} [exclude_hosts] 跨页全选排除主机
        @apiParam {Int[]} [bk_host_id] 主机ID
        主机ID和跨页全选排除主机必选一个
        @apiParamExample {Json} 安装请求参数
        {
            "job_type": "RESTART_PROXY",
            "bk_host_id": [7731, 7732]
        }
        """
        validated_data = self.validated_data
        job_type = validated_data["job_type"]
        bk_host_ids = validated_data["bk_host_ids"]
        bk_biz_scope = validated_data["bk_biz_scope"]
        return Response(JobHandler().operate(job_type, bk_host_ids, bk_biz_scope))

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

    @action(detail=True, methods=["GET"], serializer_class=FetchCommandSerializer)
    def get_job_commands(self, request, *args, **kwargs):
        """
        @api {GET} /job/{{pk}}/get_job_commands/ 获取安装命令
        @apiName get_job_commands
        @apiGroup Job
        @apiParam {Number} job_id 任务ID
        @apiParam {Number} bk_host_id 主机ID，-1时返回每个云区域的安装命令
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
