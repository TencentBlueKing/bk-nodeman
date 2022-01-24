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

import inspect

from django.contrib import admin

from . import models

# 自动导入所有model
for name, obj in inspect.getmembers(models):
    try:
        if inspect.isclass(obj) and name not in [
            "HostStatus",
            "Job",
            "Host",
            "IdentityData",
            "Profile",
            "IP",
            "SshKey",
            "JobTask",
            "Cloud",
            "ProcessStatus",
            "TaskLog",
            "CMDBHosts",
            "AccessPoint",
            "GlobalSettings",
            "Packages",
            "ProcControl",
            "GsePluginDesc",
        ]:
            admin.site.register(getattr(models, name))
    except Exception:
        pass


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("bk_username",)
    search_fields = ["bk_username"]
    list_filter = []


@admin.register(models.GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    list_display = ("key",)
    search_fields = ["key"]
    list_filter = []


@admin.register(models.Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "created_by", "job_type", "status")
    search_fields = ["job_type"]
    list_filter = ["job_type", "status"]


@admin.register(models.Host)
class HostAdmin(admin.ModelAdmin):
    list_display = ["bk_host_id", "inner_ip", "bk_biz_id", "bk_cloud_id", "os_type", "node_from", "node_type"]
    search_fields = ["inner_ip"]
    list_filter = ["os_type", "node_type", "node_from"]


@admin.register(models.IdentityData)
class IdentityDataAdmin(admin.ModelAdmin):
    def inner_ip(self):
        try:
            return models.Host.objects.get(bk_host_id=self.bk_host_id).inner_ip
        except models.IdentityData.DoesNotExist:
            return "--"

    list_display = ["bk_host_id", inner_ip, "auth_type", "retention", "updated_at"]
    search_fields = ["bk_host_id"]
    list_filter = ["auth_type", "retention"]


@admin.register(models.Cloud)
class CloudAdmin(admin.ModelAdmin):
    list_display = ("bk_cloud_id", "bk_cloud_name", "isp", "ap_id", "creator", "is_visible", "is_deleted")
    search_fields = ["bk_cloud_id", "bk_cloud_name", "creator"]
    list_filter = ["creator", "isp", "ap_id", "is_visible", "is_deleted"]


@admin.register(models.ProcessStatus)
class ProcessStatusAdmin(admin.ModelAdmin):
    def inner_ip(self):
        try:
            return models.Host.objects.get(bk_host_id=self.bk_host_id).inner_ip
        except models.IdentityData.DoesNotExist:
            return "--"

    list_display = ("bk_host_id", inner_ip, "name", "status", "is_auto", "version", "proc_type")
    search_fields = ["bk_host_id", "name"]
    list_filter = ["name", "status", "proc_type", "version"]


@admin.register(models.AccessPoint)
class AccessPointAdmin(admin.ModelAdmin):
    list_display = ("name", "ap_type", "status", "is_enabled", "is_default")
    search_fields = ["name"]
    list_filter = ["ap_type", "status", "is_enabled", "is_default"]


@admin.register(models.JobTask)
class JobTaskAdmin(admin.ModelAdmin):
    def inner_ip(self):
        try:
            return models.Host.objects.get(bk_host_id=self.bk_host_id).inner_ip
        except models.IdentityData.DoesNotExist:
            return "--"

    list_display = ("job_id", "bk_host_id", inner_ip, "status", "current_step", "create_time")
    search_fields = ["bk_host_id", "job_id"]
    list_filter = ["status", "current_step"]


@admin.register(models.Packages)
class PackagesAdmin(admin.ModelAdmin):
    list_display = ("pkg_name", "version", "project", "module", "os", "cpu_arch")
    search_fields = ("pkg_name", "version", "module", "project", "md5")
    list_filter = ("cpu_arch", "os", "version")


@admin.register(models.ProcControl)
class ProcControlAdmin(admin.ModelAdmin):
    list_display = ("project", "module", "install_path", "plugin_package_id", "os", "need_delegate")
    search_fields = ("project", "module")
    list_filter = ("project", "os")


@admin.register(models.GsePluginDesc)
class GsePluginDescAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "launch_node", "config_file", "config_format", "auto_launch", "use_db")
    search_fields = ("name", "description", "description_en", "scenario", "scenario_en", "config_format")
    list_filter = ("name", "category", "auto_launch")
