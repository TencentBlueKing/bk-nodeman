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
import json
import operator
from functools import reduce

from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.db.models import Q

from . import models


class MultiSearchResultAdmin(admin.ModelAdmin):
    """支持按逗号分割进行多对象多模糊搜索"""

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(MultiSearchResultAdmin, self).get_search_results(request, queryset, search_term)

        search_words = search_term.split(",")
        if search_words:
            q_objects = []
            for word in search_words:
                for field in self.search_fields:
                    q_objects.append(Q(**{f"{field}__icontains": word}))
            if q_objects:
                queryset |= self.model.objects.filter(reduce(operator.or_, q_objects))
        return queryset, use_distinct


@admin.register(models.GlobalSettings)
class GlobalSettingsAdmin(MultiSearchResultAdmin):
    list_display = ("key", "value")
    search_fields = ["key"]

    def value(self, settings_obj):
        return json.dumps(settings_obj.v_json)[:100]


@admin.register(models.Job)
class JobAdmin(MultiSearchResultAdmin):
    list_display = ("id", "subscription_id", "created_by", "start_time", "job_type", "status", "is_auto_trigger")
    search_fields = ["job_type", "subscription_id"]
    list_filter = ["job_type", "status", "is_auto_trigger"]


@admin.register(models.Host)
class HostAdmin(MultiSearchResultAdmin):
    list_display = [
        "bk_host_id",
        "inner_ip",
        "outer_ip",
        "bk_biz_id",
        "bk_cloud_id",
        "os_type",
        "cpu_arch",
        "node_type",
        "node_from",
    ]
    search_fields = ["bk_host_id", "inner_ip", "outer_ip"]
    list_editable = ["os_type", "cpu_arch", "node_type"]
    list_filter = ["os_type", "cpu_arch", "node_type", "node_from", "install_channel_id"]


@admin.register(models.IdentityData)
class IdentityDataAdmin(MultiSearchResultAdmin):
    def inner_ip(self):
        try:
            return models.Host.objects.get(bk_host_id=self.bk_host_id).inner_ip
        except models.Host.DoesNotExist:
            return "--"

    list_display = ["bk_host_id", inner_ip, "account", "port", "auth_type", "retention", "updated_at"]
    search_fields = ["bk_host_id"]
    list_filter = ["auth_type", "retention", "port"]


@admin.register(models.Cloud)
class CloudAdmin(MultiSearchResultAdmin):
    list_display = ("bk_cloud_id", "bk_cloud_name", "isp", "ap_id", "creator", "is_visible", "is_deleted")
    search_fields = ["bk_cloud_id", "bk_cloud_name"]
    list_filter = ["creator", "isp", "ap_id", "is_visible", "is_deleted"]


@admin.register(models.ProcessStatus)
class ProcessStatusAdmin(MultiSearchResultAdmin):
    def inner_ip(self):
        try:
            return models.Host.objects.get(bk_host_id=self.bk_host_id).inner_ip
        except models.Host.DoesNotExist:
            return "--"

    list_display = ("bk_host_id", inner_ip, "name", "status", "is_auto", "version", "proc_type")
    search_fields = ["bk_host_id", "name"]
    list_filter = ["name", "status", "proc_type", "version"]


@admin.register(models.AccessPoint)
class AccessPointAdmin(MultiSearchResultAdmin):
    list_display = ("name", "ap_type", "status", "is_enabled", "is_default")
    search_fields = ["name"]
    list_filter = ["ap_type", "status", "is_enabled", "is_default"]


@admin.register(models.JobTask)
class JobTaskAdmin(MultiSearchResultAdmin):
    def inner_ip(self):
        try:
            return models.Host.objects.get(bk_host_id=self.bk_host_id).inner_ip
        except models.IdentityData.DoesNotExist:
            return "--"

    list_display = ("job_id", "bk_host_id", inner_ip, "status", "current_step", "create_time")
    search_fields = ["bk_host_id", "job_id"]
    list_filter = ["status", "current_step"]


@admin.register(models.Packages)
class PackagesAdmin(MultiSearchResultAdmin):
    list_display = ("pkg_name", "version", "project", "module", "os", "cpu_arch")
    search_fields = ("pkg_name", "version", "module", "project", "md5")
    list_filter = ("cpu_arch", "os", "version")


@admin.register(models.ProcControl)
class ProcControlAdmin(MultiSearchResultAdmin):
    list_display = ("project", "module", "install_path", "plugin_package_id", "os", "need_delegate")
    search_fields = ("project", "module")
    list_filter = ("project", "os")


@admin.register(models.GsePluginDesc)
class GsePluginDescAdmin(MultiSearchResultAdmin):
    list_display = ("name", "category", "launch_node", "config_file", "config_format", "auto_launch", "use_db")
    search_fields = ("name", "description", "description_en", "scenario", "scenario_en", "config_format")
    list_filter = ("name", "category", "auto_launch")


@admin.register(models.Subscription)
class SubscriptionAdmin(MultiSearchResultAdmin):
    list_display = (
        "id",
        "name",
        "bk_biz_id",
        "bk_biz_scope",
        "object_type",
        "node_type",
        "create_time",
        "creator",
        "enable",
        "is_main",
        "category",
        "plugin_name",
    )
    search_fields = ("name",)
    list_filter = (
        "object_type",
        "node_type",
        "category",
        "enable",
        "is_main",
    )


@admin.register(models.PluginConfigTemplate)
class PluginConfigTemplateAdmin(MultiSearchResultAdmin):
    list_display = (
        "plugin_name",
        "plugin_version",
        "name",
        "version",
        "os",
        "cpu_arch",
        "is_main",
        "file_path",
        "creator",
        "create_time",
        "source_app_code",
        "is_release_version",
    )
    search_fields = ("plugin_name", "plugin_version", "name", "version")
    list_filter = ("os", "cpu_arch", "is_main", "is_release_version", "source_app_code")


@admin.register(models.PluginResourcePolicy)
class PluginResourcePolicyAdmin(MultiSearchResultAdmin):
    list_display = ("plugin_name", "cpu", "mem", "bk_biz_id", "bk_obj_id", "created_at")
    search_fields = ("plugin_name",)


# 自动导入所有未注册的model
for name, obj in inspect.getmembers(models):
    if inspect.isclass(obj) and issubclass(obj, models.models.Model):
        try:
            admin.site.register(getattr(models, name))
        except AlreadyRegistered:
            continue
