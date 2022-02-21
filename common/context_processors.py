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
import datetime
import os

from blueapps.account.conf import ConfFixture
from django.conf import settings
from django.utils.translation import ugettext as _

from apps.node_man import constants
from apps.node_man.handlers.iam import IamHandler
from apps.utils.local import get_request_username
from version_log.utils import get_latest_version

"""
context_processor for common(setting)

除setting外的其他context_processor内容，均采用组件的方式(string)
"""


def get_docs_center_url():
    docs_suffix = "markdown/节点管理/产品白皮书/Introduce/Overview.md"
    if settings.BK_DOCS_CENTER_HOST:
        docs_prefix = settings.BK_DOCS_CENTER_HOST
        return f"{docs_prefix}/{docs_suffix}"

    if settings.BKAPP_RUN_ENV == constants.BkappRunEnvType.CE.value:
        docs_prefix = "https://bk.tencent.com/docs"
    else:
        docs_prefix = f"{settings.BK_PAAS_HOST}/o/bk_docs_center"
    return f"{docs_prefix}/{docs_suffix}"


def get_title():
    return _("节点管理 | 腾讯蓝鲸智云")


def mysetting(request):
    return {
        "gettext": _,
        "_": _,
        "LANGUAGES": settings.LANGUAGES,
        # 基础信息
        "RUN_MODE": settings.RUN_MODE,
        "ENVIRONMENT": settings.ENVIRONMENT,
        "APP_CODE": settings.APP_CODE,
        "SITE_URL": settings.SITE_URL,
        # 远程静态资源url
        "REMOTE_STATIC_URL": settings.REMOTE_STATIC_URL,
        # 静态资源
        "STATIC_URL": settings.STATIC_URL,
        "BK_STATIC_URL": settings.STATIC_URL[: len(settings.STATIC_URL) - 1],
        "STATIC_VERSION": settings.STATIC_VERSION,
        # 登录跳转链接
        "LOGIN_URL": ConfFixture.LOGIN_URL,
        "LOGIN_SERVICE_URL": ConfFixture.LOGIN_URL,
        # PAAS域名
        "BK_PAAS_HOST": settings.BK_PAAS_HOST,
        # 当前页面，主要为了login_required做跳转用
        "APP_PATH": request.get_full_path(),
        "NOW": datetime.datetime.now(),
        "RUN_VER": settings.RUN_VER,
        "WEB_TITLE": get_title(),
        "VERSION": get_latest_version(),
        "DEFAULT_CLOUD": constants.DEFAULT_CLOUD,
        "USERNAME": request.user.username,
        # 是否使用权限中心
        "USE_IAM": settings.USE_IAM,
        # 如果是权限中心，使用权限中心的全局配置权限
        # 如果不是权限中心，使用超管权限
        "GLOBAL_SETTING_PERMISSION": IamHandler.iam_global_settings_permission(get_request_username()),
        # 任务配置权限
        "GLOBAL_TASK_CONFIG_PERMISSION": IamHandler.globe_task_config(get_request_username()),
        "GSE_LISTEN_PORT": "48668,58625,58925,10020-10030",
        "PROXY_LISTEN_PORT": "58930,10020-10030",
        "WXWORK_UIN": os.getenv("BKAPP_WXWORK_UIN"),
        "DESTOP_URL": os.getenv("BKAPP_DESTOP_URL"),
        # 默认端口
        "DEFAULT_SSH_PORT": getattr(settings, "BKAPP_DEFAULT_SSH_PORT", 22),
        "USE_TJJ": getattr(settings, "USE_TJJ", False),
        "BK_DOCS_CENTER_URL": get_docs_center_url(),
        "BKAPP_RUN_ENV": settings.BKAPP_RUN_ENV,
        # TAM前端监控
        "TAM_ID": os.getenv("BKAPP_TAM_ID"),
        "TAM_URL": os.getenv("BKAPP_TAM_URL"),
    }
