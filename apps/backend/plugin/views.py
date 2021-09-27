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

from __future__ import absolute_import, unicode_literals

import base64
import hashlib
import json
import logging
import os
import re
import shutil
from collections import defaultdict
from copy import deepcopy
from itertools import groupby
from operator import itemgetter

import six
from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import EmptyPage, Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from packaging import version
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.backend import constants as backend_const
from apps.backend import exceptions
from apps.backend.plugin import serializers, tasks, tools
from apps.backend.subscription.errors import (
    CreateSubscriptionTaskError,
    InstanceTaskIsRunning,
)
from apps.backend.subscription.handler import SubscriptionHandler
from apps.backend.subscription.tasks import run_subscription_task_and_create_instance
from apps.core.files import core_files_constants
from apps.core.files.storage import get_storage
from apps.exceptions import AppBaseException, ValidationError
from apps.generic import APIViewSet
from apps.node_man import constants as const
from apps.node_man import models
from apps.utils import files
from pipeline.engine.exceptions import InvalidOperationException
from pipeline.service import task_service
from pipeline.service.pipeline_engine_adapter.adapter_api import STATE_MAP

LOG_PREFIX_RE = re.compile(r"(\[\d{4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}.*?\] )")
logger = logging.getLogger("app")

# 接口到序列化器的映射关系
PluginAPISerializerClasses = dict(
    info=serializers.PluginInfoSerializer,
    release=serializers.ReleasePluginSerializer,
    package_status_operation=serializers.PkgStatusOperationSerializer,
    plugin_status_operation=serializers.PluginStatusOperationSerializer,
    create_config_template=serializers.CreatePluginConfigTemplateSerializer,
    release_config_template=serializers.ReleasePluginConfigTemplateSerializer,
    render_config_template=serializers.RenderPluginConfigTemplateSerializer,
    query_config_template=serializers.PluginConfigTemplateInfoSerializer,
    query_config_instance=serializers.PluginConfigInstanceInfoSerializer,
    start_debug=serializers.PluginStartDebugSerializer,
    create_plugin_register_task=serializers.PluginRegisterSerializer,
    query_plugin_register_task=serializers.PluginRegisterTaskSerializer,
    delete=serializers.DeletePluginSerializer,
    create_export_task=serializers.ExportSerializer,
    upload=serializers.PluginUploadSerializer,
    history=serializers.PluginQueryHistorySerializer,
    parse=serializers.PluginParseSerializer,
    list=serializers.PluginListSerializer,
    retrieve=serializers.GatewaySerializer,
)


class PluginViewSet(APIViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin):
    """
    插件相关API
    """

    queryset = ""

    # permission_classes = (BackendBasePermission,)

    def get_validated_data(self):
        """
        使用serializer校验参数，并返回校验后参数
        :return: dict
        """
        if self.request.method == "GET":
            data = self.request.query_params
        else:
            data = self.request.data

        # 从 esb 获取参数
        bk_username = self.request.META.get("HTTP_BK_USERNAME")
        bk_app_code = self.request.META.get("HTTP_BK_APP_CODE")

        data = data.copy()
        data.setdefault("bk_username", bk_username)
        data.setdefault("bk_app_code", bk_app_code)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        return deepcopy(serializer.validated_data)

    def get_serializer_class(self):
        """
        根据方法名返回合适的序列化器
        """
        return PluginAPISerializerClasses.get(self.action)

    """
    触发注册插件包及查询任务状态
    """

    @action(detail=False, methods=["POST"], url_path="create_register_task")
    def create_plugin_register_task(self, request):
        """
        @api {POST} /plugin/create_register_task/ 创建注册任务
        @apiName create_register_task
        @apiGroup backend_plugin
        @apiParam {String} file_name 文件名
        @apiParam {Boolean} is_release 是否已发布
        @apiParam {Boolean} [is_template_load] 是否需要读取配置文件，缺省默认为`false`
        @apiParam {Boolean} [is_template_overwrite] 是否可以覆盖已经存在的配置文件，缺省默认为`false`
        @apiParam {List} [select_pkg_abs_paths] 指定注册包相对路径列表，缺省默认全部导入
        @apiParamExample {Json} 请求参数
        {
            "file_name": "bkunifylogbeat-7.1.28.tgz",
            "is_release": True,
            "select_pkg_abs_paths": ["bkunifylogbeat_linux_x86_64/bkunifylogbeat"]
        }
        @apiSuccessExample {json} 成功返回:
        {
            "job_id": 1
        }
        """
        params = self.get_validated_data()
        file_name = params["file_name"]

        # 1. 判断是否存在需要注册的文件信息
        models_queryset = models.UploadPackage.objects.filter(file_name=file_name)
        if not models_queryset.exists():
            raise exceptions.UploadPackageNotExistError(_("找不到请求发布的文件，请确认后重试"))

        # 2. 创建一个新的task,返回任务ID
        job = models.Job.objects.create(
            created_by=params["bk_username"],
            job_type=const.JobType.PACKING_PLUGIN,
            # TODO 打包任务是否也用一次性订阅的方式下发
            subscription_id=-1,
            status=const.JobStatusType.RUNNING,
        )
        # 这个新的任务，应该是指派到自己机器上的打包任务
        tasks.package_task.delay(job.id, params)
        logger.info(
            "create job-> {job_id} to unpack file-> {file_name} plugin".format(job_id=job.id, file_name=file_name)
        )

        return Response({"job_id": job.id})

    @action(detail=False, methods=["GET"], url_path="query_register_task")
    def query_plugin_register_task(self, request):
        """
        @api {GET} /plugin/query_register_task/ 查询插件注册任务
        @apiName query_register_task
        @apiGroup backend_plugin
        @apiParam {Int} job_id 任务ID
        @apiParamExample {Json} 请求参数
        {
            "job_id": 1
        }
        @apiSuccessExample {json} 成功返回:
        {
            "is_finish": False,
            "status": "RUNNING",
            "message": "~",
        }
        """
        params = self.get_validated_data()
        job_id = params["job_id"]

        # 寻找这个任务对应的job_task
        try:
            job = models.Job.objects.get(id=job_id)

        except models.Job.DoesNotExist:
            logger.error("user try to query job->[%s] but is not exists." % job_id)
            raise exceptions.JobNotExistError(_("找不到请求的任务，请确认后重试"))

        return Response(
            {
                "is_finish": job.status in [const.JobStatusType.SUCCESS, const.JobStatusType.FAILED],
                "status": job.status,
                "message": job.global_params.get("err_msg"),
            }
        )

    @action(detail=False, methods=["GET"], url_path="info")
    def info(self, request):
        """
        @api {GET} /plugin/info/ 查询插件信息
        @apiName query_plugin_info
        @apiGroup backend_plugin
        """
        params = self.get_validated_data()
        plugin = params.pop("plugin")
        bk_username = params.pop("bk_username")
        bk_app_code = params.pop("bk_app_code")

        plugin_packages = plugin.get_packages(**params)

        result = []

        for package in plugin_packages:
            result.append(
                dict(
                    id=package.id,
                    name=plugin.name,
                    os=package.os,
                    cpu_arch=package.cpu_arch,
                    version=package.version,
                    is_release_version=package.is_release_version,
                    is_ready=package.is_ready,
                    pkg_size=package.pkg_size,
                    md5=package.md5,
                    location=package.location,
                    creator=bk_username,
                    source_app_code=bk_app_code,
                )
            )

        return Response(result)

    @action(detail=False, methods=["POST"], url_path="release")
    def release(self, request):
        """
        @api {POST} /plugin/release/ 发布（上线）插件包
        @apiName release_package
        @apiGroup backend_plugin
        @apiParam {Int[]} [id] 插件包id列表，`id`和（`name`, `version`）至少有一个
        @apiParam {String} [name] 插件包名称
        @apiParam {String} [version] 版本号
        @apiParam {String} [cpu_arch] CPU类型，`x86` `x86_64` `powerpc`
        @apiParam {String} [os] 系统类型，`linux` `windows` `aix`
        @apiParam {String[]} [md5_list] md5列表
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 返回上线的插件包id列表:
        [1, 2, 4]
        """
        params = self.get_validated_data()
        operator = params.pop("bk_username")
        params.pop("bk_app_code")

        try:
            if "id" in params:
                plugin_packages = models.GsePluginDesc.list_packages(
                    md5_list=params["md5_list"], package_ids=params["id"]
                )
            else:
                plugin_packages = models.GsePluginDesc.list_packages(
                    md5_list=params.pop("md5_list"), query_params=params
                )
        except ValueError as e:
            raise ValidationError(e)

        # 检查当前插件包是否启用，没有启用不允许上下线
        not_ready_pkgs = plugin_packages.filter(is_ready=False)
        if not_ready_pkgs.exists():
            raise exceptions.PackageStatusOpError(
                _("ID{ids}的插件包未启用，无法执行更改状态操作").format(ids=[pkg.id for pkg in not_ready_pkgs])
            )
        # 更新状态及操作人
        plugin_packages.update(is_release_version=True, creator=operator)
        return Response([package.id for package in plugin_packages])

    @action(detail=False, methods=["POST"], url_path="package_status_operation")
    def package_status_operation(self, request):
        """
        @api {POST} /plugin/package_status_operation/ 插件包状态类操作
        @apiName package_status_operation
        @apiGroup backend_plugin
        @apiParam {String} operation 状态操作 `release`-`上线`，`offline`-`下线` `ready`-`启用`，`stop`-`停用`
        @apiParam {Int[]} [id] 插件包id列表，`id`和（`name`, `version`）至少有一个
        @apiParam {String} [name] 插件包名称
        @apiParam {String} [version] 版本号
        @apiParam {String} [cpu_arch] CPU类型，`x86` `x86_64` `powerpc`
        @apiParam {String} [os] 系统类型，`linux` `windows` `aix`
        @apiParam {String[]} [md5_list] md5列表
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 返回操作成功的插件包id列表:
        [1, 2, 4]
        """
        params = self.get_validated_data()
        status_field_map = {
            const.PkgStatusOpType.release: {"is_release_version": True, "is_ready": True},
            const.PkgStatusOpType.offline: {"is_release_version": False, "is_ready": True},
            const.PkgStatusOpType.stop: {"is_ready": False},
        }
        operator = params.pop("bk_username")
        params.pop("bk_app_code")
        operation = params.pop("operation")
        md5_list = params.pop("md5_list")
        try:
            if "id" in params:
                plugin_packages = models.GsePluginDesc.list_packages(md5_list=md5_list, package_ids=params["id"])
            else:
                plugin_packages = models.GsePluginDesc.list_packages(md5_list=md5_list, query_params=params)
        except ValueError as e:
            raise ValidationError(e)
        # 更新状态及操作人
        plugin_packages.update(**status_field_map[operation], creator=operator)
        return Response([package.id for package in plugin_packages])

    @action(detail=False, methods=["POST"], url_path="delete")
    def delete(self, request):
        """
        @api {POST} /plugin/delete/ 删除插件
        @apiName delete_plugin
        @apiGroup backend_plugin
        """
        # TODO: 完成采集配置后需要添加检测逻辑
        params = self.get_validated_data()
        params.pop("bk_username")
        params.pop("bk_app_code")
        name = params["name"]

        models.GsePluginDesc.objects.filter(name=name).delete()
        packages = models.Packages.objects.filter(project=name)
        for package in packages:
            file_path = os.path.join(package.pkg_path, package.pkg_name)
            if os.path.exists(file_path):
                os.remove(file_path)

        packages.delete()
        models.ProcControl.objects.filter(project=name).delete()
        plugin_templates = models.PluginConfigTemplate.objects.filter(plugin_name=name)
        models.PluginConfigInstance.objects.filter(
            plugin_config_template__in=[template.id for template in plugin_templates]
        ).delete()

        return Response()

    @action(detail=False, methods=["POST"], url_path="create_config_template")
    def create_config_template(self, request):
        """
        @api {POST} /plugin/create_config_template/ 创建配置模板
        @apiName create_plugin_config_template
        @apiGroup backend_plugin
        """
        params = self.get_validated_data()
        bk_username = params.pop("bk_username")
        bk_app_code = params.pop("bk_app_code")

        plugin, created = models.PluginConfigTemplate.objects.update_or_create(
            plugin_name=params["plugin_name"],
            plugin_version=params["plugin_version"],
            name=params["name"],
            version=params["version"],
            defaults=dict(
                plugin_name=params["plugin_name"],
                plugin_version=params["plugin_version"],
                name=params["name"],
                version=params["version"],
                format=params["format"],
                content=params["content"],
                file_path=params["file_path"],
                is_release_version=params["is_release_version"],
                creator=bk_username,
                source_app_code=bk_app_code,
            ),
        )

        params["id"] = plugin.id
        return Response(params)

    @action(detail=False, methods=["POST"], url_path="release_config_template")
    def release_config_template(self, request):
        """
        @api {POST} /plugin/release_config_template/ 发布配置模板
        @apiName release_plugin_config_template
        @apiGroup backend_plugin
        """
        params = self.get_validated_data()
        bk_username = params.pop("bk_username")
        bk_app_code = params.pop("bk_app_code")

        if "id" in params:
            plugin_templates = models.PluginConfigTemplate.objects.filter(id__in=params["id"])
        else:
            plugin_templates = models.PluginConfigTemplate.objects.filter(**params)

        # 更改发布状态
        plugin_templates.update(is_release_version=True)

        result = []
        for template in plugin_templates:
            result.append(
                dict(
                    id=template.id,
                    plugin_name=template.plugin_name,
                    plugin_version=template.plugin_version,
                    name=template.name,
                    version=template.version,
                    format=template.format,
                    file_path=template.file_path,
                    is_release_version=template.is_release_version,
                    creator=bk_username,
                    content=template.content,
                    source_app_code=bk_app_code,
                )
            )

        return Response(result)

    @action(detail=False, methods=["POST"], url_path="render_config_template")
    def render_config_template(self, request):
        """
        @api {POST} /plugin/render_config_template/ 渲染配置模板
        @apiName render_plugin_config_template
        @apiGroup backend_plugin
        """
        params = self.get_validated_data()
        bk_username = params.pop("bk_username")
        bk_app_code = params.pop("bk_app_code")
        data = params.pop("data")

        try:
            if "id" in params:
                plugin_template = models.PluginConfigTemplate.objects.get(id=params["id"])
            else:
                plugin_template = models.PluginConfigTemplate.objects.get(**params)
        except models.PluginConfigTemplate.DoesNotExist:
            raise ValidationError("plugin template not found")

        instance = plugin_template.create_instance(data, bk_username, bk_app_code)

        return Response(
            dict(
                id=instance.id,
                md5=instance.data_md5,
                creator=instance.creator,
                source_app_code=instance.source_app_code,
            )
        )

    @action(detail=False, methods=["GET"], url_path="query_config_template")
    def query_config_template(self, request):
        """
        @api {GET} /plugin/query_config_template/ 查询配置模板
        @apiName query_plugin_config_template
        @apiGroup backend_plugin
        """
        params = self.get_validated_data()
        params.pop("bk_username")
        params.pop("bk_app_code")

        if "id" in params:
            plugin_templates = models.PluginConfigTemplate.objects.filter(id=params["id"])
        else:
            plugin_templates = models.PluginConfigTemplate.objects.filter(**params)

        result = []
        for template in plugin_templates:
            result.append(
                dict(
                    id=template.id,
                    plugin_name=template.plugin_name,
                    plugin_version=template.plugin_version,
                    name=template.name,
                    version=template.version,
                    format=template.format,
                    path=template.file_path,
                    is_release_version=template.is_release_version,
                    creator=template.creator,
                    content=base64.b64encode(template.content),
                    source_app_code=template.source_app_code,
                )
            )

        return Response(result)

    @action(detail=False, methods=["GET"], url_path="query_config_instance")
    def query_config_instance(self, request):
        """
        @api {GET} /plugin/query_config_instance/ 查询配置模板实例
        @apiName query_plugin_config_instance
        @apiGroup backend_plugin
        """
        params = self.get_validated_data()
        params.pop("bk_username")
        params.pop("bk_app_code")

        if "id" in params:
            plugin_instances = models.PluginConfigInstance.objects.filter(id=params["id"])
        else:
            plugin_templates = models.PluginConfigTemplate.objects.filter(**params)
            plugin_instances = models.PluginConfigInstance.objects.filter(
                plugin_config_template__in=[template.id for template in plugin_templates]
            )

        result = []

        for instance in plugin_instances:
            base64_content = base64.b64encode(instance.content)
            md5_client = hashlib.md5()
            md5_client.update(instance.content)
            md5 = md5_client.hexdigest()

            result.append(
                dict(
                    id=instance.id,
                    content=base64_content,
                    md5=md5,
                    creator=instance.creator,
                    source_app_code=instance.source_app_code,
                )
            )

        return Response(result)

    @action(detail=False, methods=["POST"], url_path="start_debug")
    def start_debug(self, request):
        """
        @api {POST} /plugin/start_debug/ 开始调试
        @apiName start_debug
        @apiGroup backend_plugin
        """
        params = self.get_validated_data()
        host_info = params["host_info"]
        plugin_name = params["plugin_name"]
        plugin_version = params["version"]

        try:
            host = models.Host.objects.get(
                bk_biz_id=host_info["bk_biz_id"],
                inner_ip=host_info["ip"],
                bk_cloud_id=host_info["bk_cloud_id"],
            )
        except models.Host.DoesNotExist:
            raise ValidationError("host does not exist")

        plugin_id = params.get("plugin_id")
        if plugin_id:
            try:
                package = models.Packages.objects.get(id=plugin_id)
            except models.Packages.DoesNotExist:
                raise exceptions.PluginNotExistError()
        else:
            os_type = host.os_type.lower()
            cpu_arch = host.cpu_arch
            try:
                package = models.Packages.objects.get(
                    project=params["plugin_name"], version=params["version"], os=os_type, cpu_arch=cpu_arch
                )
            except models.Packages.DoesNotExist:
                raise exceptions.PluginNotExistError(
                    plugin_name=params["plugin_name"], os_type=os_type, cpu_arch=cpu_arch
                )

        if not package.is_ready:
            raise ValidationError("plugin is not ready")

        configs = models.PluginConfigInstance.objects.in_bulk(params["config_ids"])

        # 渲染配置文件
        step_config_templates = []
        step_params_context = {}
        for config_id in params["config_ids"]:
            config = configs.get(config_id)
            if not config:
                raise ValidationError("config {} does not exist".format(config_id))
            config_template = config.template
            if config_template.plugin_name != package.project:
                raise ValidationError("config {} does not belong to plugin {}".format(config_id, package.project))

            step_config_templates.append(
                {"version": config_template.version, "name": config.render_name(config_template.name)}
            )
            step_params_context.update(json.loads(config.render_data))

        with transaction.atomic():
            subscription = models.Subscription.objects.create(
                bk_biz_id=host_info["bk_biz_id"],
                object_type=models.Subscription.ObjectType.HOST,
                node_type=models.Subscription.NodeType.INSTANCE,
                nodes=[host_info],
                enable=False,
                is_main=params.get("is_main", False),
                creator=request.user.username,
                category=models.Subscription.CategoryType.DEBUG,
            )

            # 创建订阅步骤
            models.SubscriptionStep.objects.create(
                subscription_id=subscription.id,
                step_id=plugin_name,
                type="PLUGIN",
                config={
                    "config_templates": step_config_templates,
                    "plugin_version": plugin_version,
                    "plugin_name": plugin_name,
                    "job_type": "DEBUG_PLUGIN",
                },
                params={"context": step_params_context},
            )
            subscription_task = models.SubscriptionTask.objects.create(
                subscription_id=subscription.id, scope=subscription.scope, actions={}
            )

            if subscription.is_running():
                raise InstanceTaskIsRunning()
            run_subscription_task_and_create_instance.delay(subscription, subscription_task)
            if subscription_task.err_msg:
                raise CreateSubscriptionTaskError(err_msg=subscription_task.err_msg)

        return Response({"task_id": subscription_task.id})

    @action(detail=False, methods=["POST"], url_path="stop_debug")
    def stop_debug(self, request):
        """
        @api {POST} /plugin/stop_debug/ 停止调试
        @apiName stop_debug
        @apiGroup backend_plugin
        """
        task_id = request.data["task_id"]

        try:
            task = models.SubscriptionTask.objects.get(pk=task_id)
            subscription = models.Subscription.objects.get(pk=task.subscription_id)
            step = models.SubscriptionStep.objects.get(subscription_id=task.subscription_id)
            pipeline_id = task.pipeline_id
            status = task_service.get_state(pipeline_id)
            is_finished = status["state"] == STATE_MAP["FINISHED"]
            is_running = status["state"] == STATE_MAP["RUNNING"]
        except (ObjectDoesNotExist, InvalidOperationException):
            # 不存在的直接跳过
            return Response()

        # 结束则忽略，只撤销正在运行的队列
        if is_finished:
            logger.info(f"plugin debug task has been finished, task_id: {task_id}")

        if is_running:
            revoke_result = task_service.revoke_pipeline(pipeline_id)
            if revoke_result.result:
                logger.info(f"plugin debug task has been revoked, pipeline id: {pipeline_id}")
            else:
                logger.error(f"plugin debug task revoke failed, pipeline id: {pipeline_id}")

            config = step.config
            config["job_type"] = backend_const.ActionNameType.STOP_DEBUG_PLUGIN
            step.config = config
            step.save()
            run_subscription_task_and_create_instance.delay(subscription, task)
        return Response()

    @action(detail=False, methods=["GET"], url_path="query_debug")
    def query_debug(self, request):
        """
        @api {GET} /plugin/query_debug/ 查询调试结果
        @apiName query_debug
        @apiGroup backend_plugin
        """
        task_id = int(request.query_params["task_id"])
        task = models.SubscriptionTask.objects.get(pk=task_id)
        subscription_handler = SubscriptionHandler(subscription_id=task.subscription_id)
        if not subscription_handler.check_task_ready([task.id]):
            return Response({"status": const.JobStatusType.PENDING, "step": "preparing", "message": _("调试任务准备中")})

        task_result = subscription_handler.task_result(task_id_list=[task_id], need_detail=True)
        try:
            steps = task_result[0]["steps"][0]["target_hosts"][0]["sub_steps"]
        except (IndexError, KeyError, TypeError):
            raise AppBaseException("查询调试结果错误")
        log_content = []
        status = const.JobStatusType.RUNNING
        step_name = ""
        for step in steps:
            log_content.append(_(" 开始{name} ").format(name=step["node_name"]).center(30, "*"))
            # debug 的日志，由于监控需要解析日志内容，因此这里把 [1900-01-01 00:00:00 INFO] 这些时间去掉
            cleaned_log = re.sub(LOG_PREFIX_RE, "", step["log"])
            log_content.append(cleaned_log)
            status = step["status"]
            step_name = step["step_code"]
            if status in (const.JobStatusType.PENDING, const.JobStatusType.RUNNING):
                # PENDING 状态也转为 RUNNING
                status = const.JobStatusType.RUNNING
                break

        return Response({"status": status, "step": step_name, "message": "\n".join(log_content)})

    @action(detail=False, methods=["POST"])
    def create_export_task(self, request):
        """
        @api {POST} /plugin/create_export_task/ 触发插件打包导出
        @apiName create_export_plugin_task
        @apiGroup backend_plugin
        @apiParam {Object} query_params 插件信息，version, project, os[可选], cpu_arch[可选]
        @apiParam {String} category 插件类别
        @apiParam {String} creator 创建者
        @apiParam {String} bk_app_code
        @apiParamExample {Json} 请求参数
        {
            "category": "gse_plugin",
            "query_params": {
                "project": "test_plugin",
                "version": "1.0.0"
            },
            "creator": "test_person",
            "bk_app_code": "bk_test_app"
        }
        @apiSuccessExample {json} 成功返回:
        {
            "job_id": 1
        }
        """

        params = self.get_validated_data()

        if "os" in params["query_params"]:
            params["query_params"]["os_type"] = params["query_params"].pop("os")

        record = models.DownloadRecord.create_record(
            category=params["category"],
            query_params=params["query_params"],
            creator=params["bk_username"],
            source_app_code=params["bk_app_code"],
        )
        logger.info(
            "user -> {username} request to export from system -> {bk_app_code} success created "
            "record -> {record_id}.".format(
                username=params["bk_username"], bk_app_code=params["bk_app_code"], record_id=record.id
            )
        )

        tasks.export_plugin.delay(record.id)
        logger.info("record-> {record_id} now is active to celery".format(record_id=record.id))

        return Response({"job_id": record.id})

    @action(detail=False, methods=["GET"])
    def query_export_task(self, request):
        """
        @api {GET} /plugin/query_export_task/ 获取一个导出任务结果
        @apiName query_export_plugin_task
        @apiGroup backend_plugin
        @apiParam {Int} job_id 任务ID
        @apiParamExample {Json} 请求参数
        {
            "job_id": 1
        }
        @apiSuccessExample {json} 成功返回:
        {
            "is_finish": True,
            "is_failed": False,
            "download_url": "http://127.0.0.1//backend/export/download/",
            "error_message": "haha"
        }
        """
        # 及时如果拿到None的job_id，也可以通过DB查询进行防御
        job_id = request.GET.get("job_id")

        try:
            record = models.DownloadRecord.objects.get(id=job_id)
        except models.DownloadRecord.DoesNotExist:
            logger.error("record-> {record_id} not exists, something go wrong?".format(record_id=job_id))
            raise ValueError(_("请求任务不存在，请确认后重试"))

        if record.is_failed or not record.file_path:
            download_url = ""
        else:
            # TODO: 此处后续需要提供一个统一的 storage.tmp_url(name) 方法，用于插件包的临时下载
            if settings.STORAGE_TYPE in core_files_constants.StorageType.list_cos_member_values():
                download_url = get_storage().url(record.file_path)
            else:
                download_url = "?".join([settings.BKAPP_NODEMAN_DOWNLOAD_API, record.download_params])

        response_data = {
            "is_finish": record.is_finish,
            "is_failed": record.is_failed,
            "download_url": download_url,
            "error_message": record.error_message,
        }

        logger.info(
            "export record -> {record_id} response_data -> {response_data}".format(
                record_id=job_id, response_data=response_data
            )
        )
        return Response(response_data)

    @action(detail=False, methods=["POST"], url_path="parse")
    def parse(self, request):
        """
        @api {POST} /plugin/parse/ 解析插件包
        @apiName plugin_parse
        @apiGroup backend_plugin
        @apiParam {String} file_name 文件名
        @apiParam {String} [is_update] 是否为更新校验，默认为`False`
        @apiParamExample {Json} 请求参数
        {
            "file_name": "basereport-10.1.12.tgz"
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "result": True,
                "message": "新增插件",
                "pkg_abs_path": "basereport_linux_x86_64/basereport",
                "pkg_name": "basereport-10.1.12",
                "project": "basereport",
                "version": "10.1.12",
                "category": "官方插件",
                "config_templates": [
                    {"name": "child1.conf", "version": "1.0", "is_main": false},
                    {"name": "child2.conf", "version": "1.1", "is_main": false},
                    {"name": "basereport-main.config", "version": "0.1", "is_main": true}
                ],
                "os": "x86_64",
                "cpu_arch": "linux",
                "description": "高性能日志采集"
            },
            {
                "result": False,
                "message": "缺少project.yaml文件",
                "pkg_abs_path": "external_bkmonitorbeat_windows_x32/bkmonitorbeat",
                "pkg_name": None,
                "project": None,
                "version": None,
                "category": None,
                "config_templates": [],
                "os": "x32",
                "cpu_arch": "windows",
                "description": None
            },
        ]
        """
        params = self.get_validated_data()
        upload_package_obj = (
            models.UploadPackage.objects.filter(file_name=params["file_name"]).order_by("-upload_time").first()
        )
        if upload_package_obj is None:
            raise exceptions.UploadPackageNotExistError(_("找不到请求发布的文件，请确认后重试"))

        # 获取插件中各个插件包的路径信息
        package_infos = tools.list_package_infos(file_path=upload_package_obj.file_path)
        # 解析插件包
        pkg_parse_results = []
        for package_info in package_infos:
            pkg_parse_result = tools.parse_package(
                pkg_absolute_path=package_info["pkg_absolute_path"],
                package_os=package_info["package_os"],
                cpu_arch=package_info["cpu_arch"],
                is_update=params["is_update"],
            )
            pkg_parse_result.update(
                {
                    "pkg_abs_path": package_info["pkg_relative_path"],
                    # parse_package 对 category 执行校验并返回错误信息，此处category不一定是合法值，所以使用get填充释义
                    "category": const.CATEGORY_DICT.get(pkg_parse_result["category"]),
                }
            )
            pkg_parse_results.append(pkg_parse_result)

        # 清理临时解压目录
        plugin_tmp_dirs = set([package_info["plugin_tmp_dir"] for package_info in package_infos])
        for plugin_tmp_dir in plugin_tmp_dirs:
            shutil.rmtree(plugin_tmp_dir)
        return Response(pkg_parse_results)

    def list(self, request, *args, **kwargs):
        """
        @api {GET} /plugin/ 插件列表
        @apiName list_plugin
        @apiGroup backend_plugin
        @apiParam {String} [search] 插件别名&名称模糊搜索
        @apiParam {Boolean} [simple_all] 返回全部数据（概要信息，`id`, `description`, `name`），默认`False`
        @apiParam {Int} [page] 当前页数，默认`1`
        @apiParam {Int} [pagesize] 分页大小，默认`10`
        @apiParam {object} [sort] 排序
        @apiParam {String=["name", "category", "creator", "scenario", "description"]} [sort.head] 排序字段
        @apiParam {String=["ASC", "DEC"]} [sort.sort_type] 排序类型
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 成功返回:
        {
            "total": 2,
            "list": [
                {
                    "id": 1,
                    "description": "系统基础信息采集",
                    "name": "basereport",
                    "category": "官方插件",
                    "source_app_code": "bk_nodeman",
                    "scenario": "CMDB上的实时数据，蓝鲸监控里的主机监控，包含CPU，内存，磁盘等",
                    "deploy_type": "整包部署"
                },
                {
                    "id": 2,
                    "description": "监控采集器",
                    "name": "bkmonitorbeat",
                    "category": "第三方插件",
                    "source_app_code": "bk_monitor",
                    "scenario": "蓝鲸监控采集器，支持多种协议及多任务的采集，提供多种运行模式和热加载机制",
                    "deploy_type": "Agent自动部署"
                }
            ]
        }
        """
        query_params = self.get_validated_data()
        gse_plugin_desc_qs = models.GsePluginDesc.objects.filter(category=const.CategoryType.official).order_by(
            "-is_ready"
        )
        if "search" in query_params:
            gse_plugin_desc_qs = gse_plugin_desc_qs.filter(
                Q(description__contains=query_params["search"]) | Q(name__contains=query_params["search"])
            )

        if "sort" in query_params:
            sort_head = query_params["sort"]["head"]
            if query_params["sort"]["sort_type"] == const.SortType.DEC:
                gse_plugin_desc_qs = gse_plugin_desc_qs.order_by(f"-{sort_head}")
            else:
                gse_plugin_desc_qs = gse_plugin_desc_qs.order_by(sort_head)

        # 返回插件概要信息
        if query_params["simple_all"]:
            ret_plugins = list(gse_plugin_desc_qs.values("id", "description", "name", "is_ready"))
            return Response({"total": len(ret_plugins), "list": ret_plugins})

        plugins = list(
            gse_plugin_desc_qs.values(
                "id", "description", "name", "category", "source_app_code", "scenario", "deploy_type", "is_ready"
            )
        )

        try:
            # 分页
            paginator = Paginator(plugins, query_params["pagesize"])
            ret_plugins = paginator.page(query_params["page"]).object_list
        except EmptyPage:
            return Response({"total": len(plugins), "list": []})

        return Response({"total": len(plugins), "list": ret_plugins})

    def retrieve(self, request, *args, **kwargs):
        """
        @api {GET} /plugin/{{pk}}/ 插件详情
        @apiName retrieve_plugin
        @apiGroup backend_plugin
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 成功返回:
        {
            "id": 1,
            "description": "系统基础信息采集",
            "name": "basereport",
            "category": "官方插件",
            "source_app_code": "bk_nodeman",
            "scenario": "CMDB上的实时数据，蓝鲸监控里的主机监控，包含CPU，内存，磁盘等",
            "deploy_type": "整包部署",
            "plugin_packages": [
                {
                    "id": 1,
                    "pkg_name": "basereport-10.1.12.tgz",
                    "module": "gse_plugin",
                    "project": "basereport",
                    "version": "10.1.12",
                    "config_templates": [
                        {"id": 1, "name": "basereport.conf", "version": "10.1", "is_main": true}
                    ],
                    "os": "linux",
                    "cpu_arch": "x86_64",
                    "support_os_cpu": "linux_x86_64",
                    "pkg_mtime": "2019-11-25 21:58:30",
                    "creator": "test_person",
                    "is_ready": True
                },
                {
                    "id": 2,
                    "pkg_name": "bkmonitorbeat-1.7.1.tgz",
                    "module": "gse_plugin",
                    "project": "bkmonitorbeat",
                    "version": "1.7.1",
                    "config_templates": [
                        {"id": 1, "name": "child1.conf", "version": "1.0", "is_main": false},
                        {"id": 2, "name": "child2.conf", "version": "1.1", "is_main": false},
                        {"id": 3, "name": "bkmonitorbeat.conf", "version": "0.1", "is_main": true}
                    ],
                    "os": "windows",
                    "cpu_arch": "x86",
                    "support_os_cpu": "windows_x86",
                    "pkg_mtime": "2019-11-25 21:58:30",
                    "creator": "test_person",
                    "is_ready": True
                }
            ]
        }
        """
        gse_plugin_desc = (
            models.GsePluginDesc.objects.filter(id=kwargs["pk"])
            .values(
                "id",
                "description",
                "name",
                "category",
                "source_app_code",
                "scenario",
                "deploy_type",
                "node_manage_control",
                "is_ready",
            )
            .first()
        )
        if gse_plugin_desc is None:
            raise exceptions.PluginNotExistError(_("不存在ID为: {id} 的插件").format(id=kwargs["pk"]))
        # 字段翻译
        gse_plugin_desc.update(
            {
                "category": const.CATEGORY_DICT[gse_plugin_desc["category"]],
                "deploy_type": const.DEPLOY_TYPE_DICT[gse_plugin_desc["deploy_type"]]
                if gse_plugin_desc["deploy_type"]
                else gse_plugin_desc["deploy_type"],
            }
        )
        # 筛选可用包，规则：启用，版本降序
        packages = (
            models.Packages.objects.filter(project=gse_plugin_desc["name"])
            .order_by("-is_ready")
            .values(
                "id", "pkg_name", "module", "project", "version", "os", "cpu_arch", "pkg_mtime", "creator", "is_ready"
            )
        )
        packages = sorted(packages, key=lambda x: version.parse(x["version"]), reverse=True)
        plugin_packages = []
        # 按支持的cpu, os对包进行分类
        packages_group_by_os_cpu = defaultdict(list)
        for package in packages:
            os_cpu = "{os}_{cpu}".format(os=package["os"], cpu=package["cpu_arch"])
            packages_group_by_os_cpu[os_cpu].append(package)
        # 取每个支持系统的最新版本插件包
        for os_cpu, package_group in packages_group_by_os_cpu.items():
            # 取启用版本的最新插件包，如无启用，取未启用的最新版本插件包
            release_package = package_group[0]
            release_package["support_os_cpu"] = os_cpu
            plugin_packages.append(release_package)

        # 获取各个系统最新插件包的配置文件
        configs = list(
            models.PluginConfigTemplate.objects.filter(
                plugin_name=gse_plugin_desc["name"],
                plugin_version__in=[pkg["version"] for pkg in plugin_packages] + ["*"],
                is_main=True,  # 目前只支持主配置
            )
            .order_by("plugin_version")
            .values("id", "name", "version", "is_main", "plugin_version")
        )
        configs_group_by_pkg_v = {
            pkg_version: list(config_group)
            for pkg_version, config_group in groupby(configs, key=itemgetter("plugin_version"))
        }
        for pkg in plugin_packages:
            pkg["config_templates"] = list(configs_group_by_pkg_v.get(pkg["version"], [])) + list(
                configs_group_by_pkg_v.get("*", [])
            )
        gse_plugin_desc["plugin_packages"] = plugin_packages
        return Response(dict(gse_plugin_desc))

    @action(detail=False, methods=["POST"], url_path="plugin_status_operation")
    def plugin_status_operation(self, request):
        """
        @api {POST} /plugin/plugin_status_operation/ 插件状态类操作
        @apiName plugin_status_operation
        @apiGroup backend_plugin
        @apiParam {String} operation 状态操作 `ready`-`启用`，`stop`-`停用`
        @apiParam {Int[]} id 插件id列表
        @apiParamExample {Json} 请求参数
        {
            "operation": "stop",
            "id": [1, 2]
        }
        @apiSuccessExample {json} 返回操作成功的插件id列表:
        [1, 2]
        """
        params = self.get_validated_data()
        status_field_map = {
            const.PluginStatusOpType.ready: {"is_ready": True},
            const.PluginStatusOpType.stop: {"is_ready": False},
        }
        update_plugins = models.GsePluginDesc.objects.filter(id__in=params["id"])
        update_plugins.update(**status_field_map[params["operation"]])
        return Response([plugin.id for plugin in update_plugins])

    @action(detail=True, methods=["GET", "POST"])
    def history(self, request, pk):
        """
        @api {GET} /plugin/{{pk}}/history/ 插件包历史
        @apiName plugin_history
        @apiGroup backend_plugin
        @apiParam {String} [os] 系统类型，`windows` `linux` `aix`
        @apiParam {String} [cpu_arch] cpu位数，`x86` `x86_64` `powerpc`
        @apiParam {Int[]} [pkg_ids] 插件包id列表
        @apiParamExample {Json} 请求参数
        {
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "id": 1,
                "pkg_name": "basereport-1.0.tgz",
                "project": "basereport",
                "version": "1.0",
                "pkg_size": 4391830,
                "md5": "35bf230be9f3c1b878ef7665be34e14e",
                "config_templates": [
                    {"name": "bkunifylogbeat.conf", "version": "1.0", "is_main": false},
                    {"name": "bkunifylogbeat1.conf", "version": "1.1", "is_main": false},
                    {"name": "bkunifylogbeat-main.config", "version": "0.1", "is_main": true}
                ],
                "pkg_mtime": "2019-11-25 21:58:30",
                "creator": "test_person",
                "is_ready": True,
                "is_release_version": True
            },
            {
                "id": 2,
                "pkg_name": "basereport-1.1.tgz",
                "module": "gse_plugin"
                "project": "basereport",
                "version": "1.1",
                "os": "linux",
                "cpu_arch": "x86"
                "md5": "35bf230be9f3c1b878ef7665be34e14e",
                "pkg_size": 4391830,
                "config_templates": [
                    {"id": 1, "name": "child1.conf", "version": "1.0", "is_main": false},
                    {"id": 2, "name": "child2.conf", "version": "2.0", "is_main": false},
                    {"id": 3, "name": "bkunifylogbeat-main.config", "version": "0.2", "is_main": true}
                ],
                "pkg_mtime": "2019-11-25 22:01:30",
                "creator": "test_person",
                "is_ready": True,
                // 最新上传的包
                "is_newest": True,
                "is_release_version": True
            },
        ]
        """
        params = self.get_validated_data()
        params.pop("bk_username")
        params.pop("bk_app_code")

        if "pkg_ids" in params:
            params["id__in"] = params.pop("pkg_ids")

        gse_plugin_desc_obj = models.GsePluginDesc.objects.filter(id=pk).first()
        if gse_plugin_desc_obj is None:
            raise exceptions.PluginNotExistError(_("不存在ID为: {id} 的插件").format(id=pk))
        plugin_name = gse_plugin_desc_obj.name

        packages = list(
            models.Packages.objects.filter(project=plugin_name, **params)
            .order_by("-pkg_ctime")
            .values(
                "id",
                "pkg_name",
                "module",
                "project",
                "version",
                "os",
                "cpu_arch",
                "pkg_size",
                "md5",
                "pkg_mtime",
                "creator",
                "is_ready",
                "is_release_version",
            )
        )
        # 找出启用且发布的最新上传包
        newest_pkg = next((pkg for pkg in packages if pkg["is_ready"] and pkg["is_release_version"]), None)
        if newest_pkg:
            newest_pkg["is_newest"] = True

        config_files = models.PluginConfigTemplate.objects.filter(plugin_name=plugin_name).values()
        # 根据版本号对配置文件归类
        config_group_by_name_version = defaultdict(list)
        for config_file in config_files:
            name_version_str = config_file["plugin_name"] + config_file["plugin_version"]
            config_group_by_name_version[name_version_str].append(
                {
                    "id": config_file["id"],
                    "version": config_file["version"],
                    "name": config_file["name"],
                    "is_main": config_file["is_main"],
                }
            )

        # 通用版本通配符
        plugin_name_version_passcode = f"{plugin_name}*"
        for package in packages:
            # 配置模板 = 通用版本配置模板 + 该版本的配置文件
            package["config_templates"] = (
                config_group_by_name_version[plugin_name_version_passcode]
                + config_group_by_name_version[package["project"] + package["version"]]
            )
            # 如果存在多个版本的同名配置，仅展示最新版本
            package["config_templates"] = tools.fetch_latest_config_templates(package["config_templates"])
        return Response(sorted(packages, key=lambda x: version.parse(x["version"]), reverse=True))


@csrf_exempt
@login_exempt
def upload_package(request):
    """
    @api {POST} /package/upload/ 上传文件接口
    @apiName upload_file
    @apiGroup backend_plugin
    @apiParam {String} module 模块名称
    @apiParam {String} md5 前端计算的MD5
    @apiParam {String} file_name 文件名称
    @apiParam {String} file_local_path Nginx上传路径
    @apiParam {String} file_local_md5 Nginx上传MD5
    @apiParamExample {Json} 请求参数
    {
        "module": "gse_plugin",
        "md5": "354659a3d1d40d380db314ed53355fe5",
        "file_name": "bkunifylogbeat-7.1.20.tgz",
        "file_local_path": "/tmp/0/9/"
        "file_local_md5": "354659a3d1d40d380db314ed53355fe5",
    }
    @apiSuccessExample {json} 成功返回:
    {
        "result": True,
        "message": "",
        "code": "00",
        "data": {
            "id": 21,  # 包上传记录ID
            "name": "test-0.01.tgz",  # 包名
            "pkg_size": "23412434",  # 单位byte
        },
    }
    """
    # 1. 获取上传的参数 & nginx的上传信息
    ser = serializers.UploadInfoSerializer(data=request.POST)
    if not ser.is_valid():
        logger.error("failed to valid request data for->[%s] maybe something go wrong?" % ser.errors)
        raise ValidationError(_("请求参数异常 [{err}]，请确认后重试").format(err=ser.errors))

    # 2. 判断哈希及参数是否符合预期
    file_local_md5 = ser.data["file_local_md5"]
    file_name = ser.data["file_name"]
    md5 = ser.data["md5"]

    if file_local_md5 != md5:
        logger.error("failed to valid file md5 local->[{}] user->[{}] maybe network error".format(file_local_md5, md5))
        raise ValidationError(_("上传文件MD5校验失败，请确认重试"))

    # 3. 创建上传的记录
    record = models.UploadPackage.create_record(
        module=ser.data["module"],
        file_path=ser.data["file_local_path"],
        md5=md5,
        operator=ser.data["bk_username"],
        source_app_code=ser.data["bk_app_code"],
        file_name=file_name,
    )
    logger.info(
        "user->[%s] from app->[%s] upload file->[%s] success."
        % (record.creator, record.source_app_code, record.file_path)
    )
    return JsonResponse(
        {
            "result": True,
            "message": "",
            "code": "00",
            "data": {
                "id": record.id,  # 包文件的ID
                "name": record.file_name,  # 包名
                "pkg_size": record.file_size,  # 单位byte
            },
        }
    )


@csrf_exempt
@login_exempt
def upload_package_by_cos(request):
    ser = serializers.CosUploadInfoSerializer(data=request.POST)
    if not ser.is_valid():
        logger.error("failed to valid request data for->[%s] maybe something go wrong?" % ser.errors)
        raise ValidationError(_("请求参数异常 [{err}]，请确认后重试").format(err=ser.errors))

    md5 = ser.data["md5"]
    origin_file_name = ser.data["file_name"]
    file_path = ser.data.get("file_path")
    download_url: str = ser.data.get("download_url")

    storage = get_storage()

    # TODO 此处的md5校验放到文件实际读取使用的地方更合理?
    # file_path 不为空表示文件已在项目管理的对象存储上，此时仅需校验md5，减少文件IO
    if file_path:
        if not storage.exists(name=file_path):
            raise ValidationError(_("文件不存在：file_path -> {file_path}").format(file_path=file_path))
        if files.md5sum(file_obj=storage.open(name=file_path)) != md5:
            raise ValidationError(_("上传文件MD5校验失败，请确认重试"))
    else:
        # 创建临时存放下载插件的目录
        tmp_dir = files.mk_and_return_tmpdir()
        with open(file=os.path.join(tmp_dir, origin_file_name), mode="wb+") as fs:
            # 下载文件并写入fs
            files.download_file(url=download_url, file_obj=fs, closed=False)
            # 计算下载文件的md5
            local_md5 = files.md5sum(file_obj=fs, closed=False)
            if local_md5 != md5:
                logger.error(
                    "failed to valid file md5 local->[{}] user->[{}] maybe network error".format(local_md5, md5)
                )
                raise ValidationError(_("上传文件MD5校验失败，请确认重试"))

            # 使用上传端提供的期望保存文件名，保存文件到项目所管控的存储
            file_path = storage.save(name=os.path.join(settings.UPLOAD_PATH, origin_file_name), content=fs)

        # 移除临时目录
        shutil.rmtree(tmp_dir)

    record = models.UploadPackage.create_record(
        module=ser.data["module"],
        file_path=file_path,
        md5=md5,
        operator=ser.data["bk_username"],
        source_app_code=ser.data["bk_app_code"],
        # 此处使用落地到文件系统的文件名，对象存储情况下文件已经写到仓库，使用接口传入的file_name会在后续判断中再转移一次文件
        file_name=os.path.basename(file_path),
    )
    logger.info(
        "user->[%s] from app->[%s] upload file->[%s] success."
        % (record.creator, record.source_app_code, record.file_path)
    )

    return JsonResponse(
        {
            "result": True,
            "message": "",
            "code": "00",
            "data": {
                "id": record.id,  # 包文件的ID
                "name": record.file_name,  # 包名
                "pkg_size": record.file_size,  # 单位byte
            },
        }
    )


@csrf_exempt
@login_exempt
def export_download(request):
    """
    @api {GET} /export/download/ 下载导出的内容,此处不做实际的文件读取，将由nginx负责处理
    @apiName download_content
    @apiGroup backend_plugin
    """

    # 及时如果拿到None的job_id，也可以通过DB查询进行防御
    job_id = request.GET.get("job_id")
    key = request.GET.get("key")

    try:
        record = models.DownloadRecord.objects.get(id=job_id)

    except models.DownloadRecord.DoesNotExist:
        logger.error("record->[%s] not exists, something go wrong?" % job_id)
        raise ValueError(_("请求任务不存在，请确认后重试"))

    if not record.download_key == key:
        logger.error(
            "try to download record->[%s] but request_key->[%s] is not match target_key->[%s]"
            % (job_id, key, record.download_key)
        )
        return HttpResponseForbidden(_("下载安全校验失败"))

    filename = os.path.basename(record.file_path)
    response = JsonResponse({"result": True, "message": "", "code": "00", "data": None})
    # 增加实际的下载文件名字准备
    request_str = six.moves.urllib.parse.urlencode({"real_name": os.path.basename(record.file_path).encode("utf8")})
    uri = os.path.join("/protect_download", filename)

    redirect_url = "?".join([uri, request_str])
    response["X-Accel-Redirect"] = redirect_url

    return response
