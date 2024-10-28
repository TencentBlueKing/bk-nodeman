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
from django.db.transaction import atomic
from django.utils.translation import ugettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import ModelViewSet
from apps.node_man import models
from apps.node_man.exceptions import ApIdIsUsing, DuplicateAccessPointNameException
from apps.node_man.handlers.ap import APHandler
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.handlers.permission import GlobalSettingPermission
from apps.node_man.serializers.ap import ListSerializer, UpdateOrCreateSerializer
from apps.utils.local import get_request_username

AP_VIEW_TAGS = ["ap"]


class ApViewSet(ModelViewSet):
    model = models.AccessPoint
    serializer_class = UpdateOrCreateSerializer
    permission_classes = (GlobalSettingPermission,)

    @swagger_auto_schema(
        operation_id="ap_list",
        operation_summary="查询任务列表",
        tags=AP_VIEW_TAGS,
        extra_overrides={"is_register_apigw": True},
    )
    def list(self, request, *args, **kwargs):
        """
        @api {GET} /ap/ 查询接入点列表
        @apiName list_ap
        @apiGroup Ap
        @apiSuccessExample {Json} 成功返回
        [{
            "id": 1,
            "name": "接入点名称",
            "zk_hosts": [
                {
                    "zk_ip": "127.0.0.1",
                    "zk_port: 111,
                },
                {
                    "zk_ip": "127.0.0.2",
                    "zk_port: 222,
                }
            ]
            "zk_user": "username",
            "zk_password": "zk_password",
            "servers": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2"
                }
            ],
            "package_inner_url": "http://127.0.0.1/download/",
            "package_outer_url": "http://127.0.0.2/download/",
            "agent_config": {
                "linux": {
                    "setup_path": "/usr/local/gse",
                    "data_path": "/usr/local/gse/data",
                    "run_path": "/usr/local/gse/run",
                    "log_path": "/usr/local/gse/log"
                },
                "windows": {
                    "setup_path": "/usr/local/gse",
                    "data_path": "/usr/local/gse/data",
                    "log_path": "/usr/local/gse/log"
                }
            },
            "description": "描述"
        }]
        """

        queryset = models.AccessPoint.objects.all()
        serializer = ListSerializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="返回正在被使用的接入点",
        tags=AP_VIEW_TAGS,
    )
    @action(detail=False, methods=["GET"])
    def ap_is_using(self, request):
        """
        @api {get} /ap/ap_is_using/ 返回正在被使用的接入点
        @apiName ap_is_using
        @apiGroup Ap
        """
        using_ap_ids = list(models.Cloud.objects.values_list("ap_id", flat=True).distinct())
        return Response(using_ap_ids)

    @swagger_auto_schema(
        operation_summary="查询接入点详情",
        tags=AP_VIEW_TAGS,
    )
    def retrieve(self, request, *args, **kwargs):
        """
        @api {GET} /ap/{{pk}}/ 查询接入点详情
        @apiName retrieve_ap
        @apiGroup Ap
        @apiSuccessExample {Json} 成功返回
        {
            "id": 1,
            "name": "接入点名称",
            "zk_hosts": [
                {
                    "zk_ip": "127.0.0.1",
                    "zk_port: 111,
                },
                {
                    "zk_ip": "127.0.0.2",
                    "zk_port: 222,
                }
            ]
            "zk_user": "username",
            "zk_password": "zk_password",
            "servers": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2"
                }
            ],
            "package_inner_url": "http://127.0.0.1/download/",
            "package_outer_url": "http://127.0.0.2/download/",
            "agent_config": {
                "linux": {
                    "setup_path": "/usr/local/gse",
                    "data_path": "/usr/local/gse/data",
                    "run_path": "/usr/local/gse/run",
                    "log_path": "/usr/local/gse/log"
                },
                "windows": {
                    "setup_path": "/usr/local/gse",
                    "data_path": "/usr/local/gse/data",
                    "log_path": "/usr/local/gse/log"
                }
            },
            "description": "描述"
        }
        """

        queryset = models.AccessPoint.objects.get(id=kwargs["pk"])
        serializer = ListSerializer(queryset)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="新增接入点",
        tags=AP_VIEW_TAGS,
    )
    def create(self, request, *args, **kwargs):
        """
        @api {POST} /ap/ 新增接入点
        @apiName create_ap
        @apiGroup Ap
        @apiParam {String} name 接入点名称
        @apiParam {Object[]} servers 服务器列表
        @apiParam {String} servers.inner_ip 内网IP
        @apiParam {String} servers.outer_ip 外网IP
        @apiParam {String} package_inner_url 安装包内网地址
        @apiParam {String} package_outer_url 安装包外网地址

        @apiParam {Object[]} zk_hosts ZK服务器
        @apiParam {String} zk_hosts.zk_ip ZK IP地址
        @apiParam {Int} zk_hosts.port ZK端口
        @apiParam {String} zk_account ZK账号
        @apiParam {String} zk_password ZK密码

        @apiParam {Object} agent_config Agent配置信息
        @apiParam {Object} agent_config.linux Linux Agent配置信息
        @apiParam {String} agent_config.linux.setup_path Linux Agent安装路径
        @apiParam {String} agent_config.linux.data_path Linux Agent数据文件路径
        @apiParam {String} agent_config.linux.run_path Linux Agent运行路径
        @apiParam {String} agent_config.linux.log_path Linux Agent日志文件路径

        @apiParam {Object} agent_config.windows Windows配置信息
        @apiParam {String} agent_config.windows.setup_path Windows Agent安装路径
        @apiParam {String} agent_config.windows.data_path Windows Agent数据文件路径
        @apiParam {String} agent_config.windows.log_path Windows Agent日志文件路径

        @apiParam {String} description 描述

        @apiParamExample {Json} 请求参数
        {
            "name": "接入点名称",
            "zk_hosts": [
                {
                    "zk_ip": "127.0.0.1",
                    "zk_port: 111,
                },
                {
                    "zk_ip": "127.0.0.2",
                    "zk_port: 222,
                }
            ]
            "zk_user": "username",
            "zk_password": "zk_password",
            "servers": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2"
                }
            ],
            "btfileserver": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2"
                }
            ],
            "dataserver": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2"
                }
            ],
            "taskserver": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2"
                }
            ],
            "package_inner_url": "http://127.0.0.1/download/",
            "package_outer_url": "http://127.0.0.2/download/",
            "agent_config": {
                "linux": {
                    "setup_path": "/usr/local/gse",
                    "data_path": "/usr/local/gse/data",
                    "run_path": "/usr/local/gse/run",
                    "log_path": "/usr/local/gse/log"
                },
                "windows": {
                    "setup_path": "/usr/local/gse",
                    "data_path": "/usr/local/gse/data",
                    "log_path": "/usr/local/gse/log"
                }
            },
            "description": "描述"
        }
        """

        # 判断名称是否重复

        name = self.validated_data["name"]
        if models.AccessPoint.objects.filter(name=name):
            raise DuplicateAccessPointNameException()

        with atomic():
            ap = super().create(request, *args, **kwargs)

            if settings.USE_IAM:
                # 将创建者返回权限中心
                ok, message = IamHandler.return_resource_instance_creator(
                    "ap", ap.data["id"], ap.data["name"], get_request_username()
                )
                if not ok:
                    raise PermissionError(_("权限中心创建关联权限失败: {}".format(message)))

            return ap

    @swagger_auto_schema(
        operation_summary="编辑接入点",
        tags=AP_VIEW_TAGS,
    )
    def update(self, request, *args, **kwargs):
        """
        @api {PUT} /ap/{{pk}}/ 编辑接入点
        @apiName update_ap
        @apiGroup Ap
        @apiParam {String} name 接入点名称
        @apiParam {Object[]} servers 服务器列表
        @apiParam {String} servers.inner_ip 内网IP
        @apiParam {String} servers.outer_ip 外网IP
        @apiParam {String} package_inner_url 安装包内网地址
        @apiParam {String} package_outer_url 安装包外网地址

        @apiParam {Object[]} zk_hosts ZK服务器
        @apiParam {String} zk_hosts.zk_ip ZK IP地址
        @apiParam {Int} zk_hosts.port ZK端口
        @apiParam {String} zk_account ZK账号
        @apiParam {String} zk_password ZK密码

        @apiParam {Object} agent_config Agent配置信息
        @apiParam {Object} agent_config.linux Linux Agent配置信息
        @apiParam {String} agent_config.linux.setup_path Linux Agent安装路径
        @apiParam {String} agent_config.linux.data_path Linux Agent数据文件路径
        @apiParam {String} agent_config.linux.run_path Linux Agent运行路径
        @apiParam {String} agent_config.linux.log_path Linux Agent日志文件路径

        @apiParam {Object} agent_config.windows Windows配置信息
        @apiParam {String} agent_config.windows.setup_path Windows Agent安装路径
        @apiParam {String} agent_config.windows.data_path Windows Agent数据文件路径
        @apiParam {String} agent_config.windows.log_path Windows Agent日志文件路径

        @apiParam {String} description 描述

        @apiParamExample {Json} 请求参数
        {
            "name": "接入点名称",
            "servers": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2"
                }
            ],
            "package_inner_url": "http://127.0.0.1/download/",
            "package_outer_url": "http://127.0.0.2/download/",
            "agent_config": {
                "linux": {
                    "setup_path": "/usr/local/gse",
                    "data_path": "/usr/local/gse/data",
                    "run_path": "/usr/local/gse/run",
                    "log_path": "/usr/local/gse/log"
                },
                "windows": {
                    "setup_path": "/usr/local/gse",
                    "data_path": "/usr/local/gse/data",
                    "log_path": "/usr/local/gse/log"
                }
            },
            "description": "描述"
        }
        """
        # 暂时去掉接入点的使用判断，需要补充更细致的逻辑
        # hosts = Host.objects.filter(ap_id=kwargs["pk"]).only("inner_ip")
        #
        # if hosts.exists():
        #     host_ips = list(hosts.values_list("inner_ip", flat=True))
        #     raise ApIdIsUsing(_(f"该接入点正在被主机 {host_ips} 使用，不允许修改"))

        # 判断名称是否重复
        name = self.validated_data["name"]
        if models.AccessPoint.objects.filter(name=name).exclude(id=kwargs["pk"]):
            raise DuplicateAccessPointNameException()

        # 保存修改
        ap = models.AccessPoint.objects.get(id=kwargs["pk"])

        for kwarg in self.validated_data:
            # 页面没有端口信息修改入口，暂不
            if kwarg == "port_config":
                continue
            # 修改 ap[kwarg] 为 self.validated_data[kwarg]
            setattr(ap, kwarg, self.validated_data[kwarg])
        ap.save()

        return Response({})

    @swagger_auto_schema(
        operation_summary="删除接入点",
        tags=AP_VIEW_TAGS,
    )
    def destroy(self, request, *args, **kwargs):
        """
        @api {DELETE} /ap/{{pk}}/ 删除接入点
        @apiName delete_ap
        @apiGroup Ap
        """

        if int(kwargs["pk"]) == -1:
            raise ApIdIsUsing("默认接入点不允许删除")

        clouds = models.Cloud.objects.filter(ap_id=kwargs["pk"])
        if clouds.exists():
            cloud_names = list(clouds.values_list("bk_cloud_name", flat=True))
            raise ApIdIsUsing(_(f"该接入点正在被「管控区域」 {cloud_names} 使用"))
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="初始化插件信息",
        tags=AP_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"])
    def init_plugin(self, request):
        """
        @api {POST} /ap/init_plugin/ 初始化插件信息
        @apiName init_plugin_data
        @apiGroup Ap
        @apiParam {String} ap_id 接入点ID
        """

        return Response(APHandler().init_plugin_data(get_request_username()))

    @swagger_auto_schema(
        operation_summary="接入点可用性测试",
        tags=AP_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"])
    def test(self, request, *args, **kwargs):
        """
        @api {POST} /ap/test/ 接入点可用性测试
        @apiName test_ap
        @apiGroup Ap
        @apiParam {Object[]} servers 服务器列表
        @apiParam {String} servers.inner_ip 内网IP
        @apiParam {String} servers.outer_ip 外网IP
        @apiParam {String} package_inner_url 安装包内网地址
        @apiParam {String} package_outer_url 安装包外网地址
        @apiParamExample {Json} 请求参数
        {
            "servers": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2"
                }
            ],
            "package_inner_url": "http://127.0.0.1/download/",
            "package_outer_url": "http://127.0.0.2/download/"
        }
        @apiSuccessExample {json} 成功返回:
        {
            "test_result": false,
            "test_logs": [
              {
                "log_level": "INFO",
                "log": "检测 127.0.0.1 连接正常"
              },
              {
                "log_level": "ERROR",
                "log": "检测 127.0.0.1 下载失败"
              }
            ]
        }
        """
        test_result, test_logs = models.AccessPoint.test(request.data)
        return Response({"test_result": test_result, "test_logs": test_logs})
