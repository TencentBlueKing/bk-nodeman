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
from django.conf import settings  # noqa

from .clean_expired_info import clean_expired_info_periodic_task  # noqa
from .clean_requests_tracker_records import (  # noqa
    clean_requests_tracker_records_periodic_task,
)
from .clean_subscription_record_info import (  # noqa
    clean_subscription_record_info_periodic_task,
)
from .sync_agent_status_task import sync_agent_status_periodic_task  # noqa
from .sync_cmdb_cloud_area import sync_cmdb_cloud_area_periodic_task  # noqa
from .sync_cmdb_host import sync_cmdb_host_periodic_task  # noqa
from .sync_proc_status_task import sync_proc_status_periodic_task  # noqa
from .update_proxy_file import update_proxy_files  # noqa

# 是否启用 gse svr 服务发现，启用后，默认接入点会通过zk的方式，自动更新gse svr信息
if getattr(settings, "GSE_ENABLE_SVR_DISCOVERY", False):
    from .gse_svr_discovery import gse_svr_discovery_periodic_task  # noqa

if getattr(settings, "CONFIG_POLICY_BY_TENCENT_VPC", False):
    from .configuration_policy import configuration_policy  # noqa
