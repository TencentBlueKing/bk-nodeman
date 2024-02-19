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
from django.utils.translation import ugettext_lazy as _

from apps.utils.enum import EnhanceEnum


class SyncTaskType(EnhanceEnum):
    """同步任务类型"""

    SYNC_CMDB_HOST = "sync_cmdb_host"
    REGISTER_GSE_PACKAGE = "register_gse_package"

    @classmethod
    def _get_member__alias_map(cls):
        return {
            cls.SYNC_CMDB_HOST: _("同步 CMDB 主机数据"),
            cls.REGISTER_GSE_PACKAGE: _("注册gse package任务"),
        }

    @classmethod
    def get_member__cache_key_map(cls):
        """获取缓存键名"""
        cache_key_map = {
            cls.SYNC_CMDB_HOST: f"{settings.APP_CODE}:backend:sync_task:sync_cmdb_host:" + "biz:{bk_biz_id}",
            cls.REGISTER_GSE_PACKAGE: f"{settings.APP_CODE}:backend:sync_task:register_gse_package:"
            + "file_name={file_name}:tags={tags}",
        }
        return cache_key_map

    @classmethod
    def get_member__import_path_map(cls):
        import_path_map = {
            cls.SYNC_CMDB_HOST: "apps.node_man.periodic_tasks.sync_cmdb_host.sync_cmdb_host_task",
            cls.REGISTER_GSE_PACKAGE: "apps.node_man.periodic_tasks.register_gse_package.register_gse_package_task",
        }
        return import_path_map
