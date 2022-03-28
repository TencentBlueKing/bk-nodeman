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

from django.conf.urls import include, url
from django.contrib import admin

from version_log import config

urlpatterns = [
    url(r"^admin_nodeman/", admin.site.urls),
    url(r"^account/", include("blueapps.account.urls")),
    url(r"^backend/", include("apps.backend.urls")),
    url(r"^core/", include("apps.core.urls")),
    url(r"^", include("apps.node_man.urls")),
    url(r"^{}".format(config.ENTRANCE_URL), include("version_log.urls")),
]

# handler404 = 'common.error_views.error_404'
# handler500 = 'common.error_views.error_500'
# handler403 = 'common.error_views.error_403'
# handler401 = 'common.error_views.error_401'
