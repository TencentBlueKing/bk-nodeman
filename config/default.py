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
import sys
from enum import Enum
from typing import Dict, Optional

from bkcrypto import constants as bkcrypto_constants
from bkcrypto.asymmetric.options import RSAAsymmetricOptions
from bkcrypto.symmetric.options import AESSymmetricOptions, SM4SymmetricOptions
from blueapps.conf.default_settings import *  # noqa
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

import env
from apps.utils.encrypt.crypto import Interceptor
from apps.utils.enum import EnhanceEnum
from apps.utils.env import get_type_env

# pipeline 配置
from pipeline.celery.settings import CELERY_QUEUES as PIPELINE_CELERY_QUEUES
from pipeline.celery.settings import CELERY_ROUTES as PIPELINE_CELERY_ROUTES

from .patchers import logging
from .patchers.monitor_reporter import monitor_report_config

ENVIRONMENT = env.ENVIRONMENT

# ===============================================================================
# 运行时，用于区分环境差异
# ===============================================================================
BKAPP_RUN_ENV = env.BKAPP_RUN_ENV
BKAPP_IS_PAAS_DEPLOY = env.BKAPP_IS_PAAS_DEPLOY
BKAPP_ENABLE_DHCP = env.BKAPP_ENABLE_DHCP
BK_BACKEND_CONFIG = env.BK_BACKEND_CONFIG
BKPAAS_MAJOR_VERSION = env.BKPAAS_MAJOR_VERSION
BKPAAS_BK_CRYPTO_TYPE = env.BKPAAS_BK_CRYPTO_TYPE


# ===============================================================================
# 日志
# ===============================================================================
LOG_TYPE = env.LOG_TYPE
LOG_LEVEL = env.LOG_LEVEL


REDIRECT_FIELD_NAME = "c_url"
IS_AJAX_PLAIN_MODE = True

# 请在这里加入你的自定义 APP
INSTALLED_APPS += (
    "django_mysql",
    "drf_yasg",
    "rest_framework",
    "common.api",
    "version_log",
    "apps.node_man",
    "apps.backend",
    "apps.core.files",
    "apps.core.encrypt",
    "apps.core.tag",
    "apps.core.ipchooser",
    "apps.core.gray",
    # pipeline
    "pipeline",
    "pipeline.log",
    "pipeline.engine",
    "pipeline.component_framework",
    "pipeline.django_signal_valve",
    "apps.iam_migration",
    # DB重连
    "django_dbconn_retry",
    # django_prometheus
    "django_prometheus",
    "blueapps.opentelemetry.instrument_app",
    # apigw
    "apigw_manager.apigw",
    # bk-notice
    "bk_notice_sdk",
)

# 这里是默认的中间件，大部分情况下，不需要改动
# 如果你已经了解每个默认 MIDDLEWARE 的作用，确实需要去掉某些 MIDDLEWARE，或者改动先后顺序，请去掉下面的注释，然后修改
MIDDLEWARE = (
    # request instance provider
    "blueapps.middleware.request_provider.RequestProvider",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "blueapps.middleware.xss.middlewares.CheckXssMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # 蓝鲸静态资源服务
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Auth middleware
    # 'blueapps.account.middlewares.WeixinLoginRequiredMiddleware',
    # "blueapps.account.middlewares.BkJwtLoginRequiredMiddleware",
    "blueapps.account.middlewares.LoginRequiredMiddleware",
    "apps.middlewares.ApiGatewayForceVerifyMiddleware",
    "apigw_manager.apigw.authentication.ApiGatewayJWTGenericMiddleware",  # JWT 认证
    "apigw_manager.apigw.authentication.ApiGatewayJWTAppMiddleware",  # JWT 透传的应用信息
    "apps.middlewares.ApiGatewayJWTUserInjectAppMiddleware",  # JWT 透传的用户信息
    # exception middleware
    "blueapps.core.exceptions.middleware.AppExceptionMiddleware",
    # 自定义中间件
    "apps.middlewares.LocaleMiddleware",
    "apps.middlewares.CommonMid",
    "apps.middlewares.UserLocalMiddleware",
)

# 添加django_prometheus中间件
MIDDLEWARE = (
    ("blueapps.opentelemetry.metrics.middlewares.SaaSMetricsBeforeMiddleware",)
    + MIDDLEWARE
    + (
        "blueapps.opentelemetry.metrics.middlewares.SaaSMetricsAfterMiddleware",
        "apps.prometheus.middlewares.NodeManAfterMiddleware",
    )
)

# ===============================================================================
# 可观测
# ===============================================================================

ENABLE_OTEL_TRACE = env.BKAPP_ENABLE_OTEL_TRACE
BKAPP_OTEL_SAMPLER = env.BKAPP_OTEL_SAMPLER
BK_APP_OTEL_INSTRUMENT_DB_API = env.BKAPP_OTEL_INSTRUMENT_DB_API
BKAPP_OTEL_GRPC_HOST = env.BKAPP_OTEL_GRPC_URL
BKAPP_OTEL_BK_DATA_TOKEN = env.BKAPP_OTEL_BK_DATA_TOKEN

# 单元测试豁免登录
if "test" in sys.argv:

    IN_TEST = True

    index = MIDDLEWARE.index("blueapps.account.middlewares.LoginRequiredMiddleware")
    MIDDLEWARE = MIDDLEWARE[:index] + MIDDLEWARE[index + 1 :]

    # testcase 在两次test中会执行回滚，该行为被django_dbconn_retry误判，所以在单元测试禁用该中间件
    # 参考 -> https://github.com/jdelic/django-dbconn-retry/issues/3
    index = INSTALLED_APPS.index("django_dbconn_retry")
    INSTALLED_APPS = INSTALLED_APPS[:index] + INSTALLED_APPS[index + 1 :]

else:
    IN_TEST = False

# 供应商账户，默认为0，内部为tencent
DEFAULT_SUPPLIER_ACCOUNT = os.getenv("DEFAULT_SUPPLIER_ACCOUNT", "0")
# 云区域ID，默认为0
DEFAULT_CLOUD_ID = os.getenv("DEFAULT_CLOUD_ID", 0)
# 蓝鲸业务集ID
try:
    BLUEKING_BIZ_ID = int(os.getenv("BLUEKING_BIZ_ID", 9991001))
except (TypeError, ValueError):
    BLUEKING_BIZ_ID = 9991001
# 作业平台版本
JOB_VERSION = os.getenv("JOB_VERSION") or "V3"
# 资源池业务ID
BK_CMDB_RESOURCE_POOL_BIZ_ID = int(os.getenv("BK_CMDB_RESOURCE_POOL_BIZ_ID", 1)) or 1
BK_CMDB_RESOURCE_POOL_BIZ_NAME = "资源池"

BKAPP_DEFAULT_SSH_PORT = int(os.getenv("BKAPP_DEFAULT_SSH_PORT", 22))

try:
    NEED_TRACK_REQUEST = int(os.environ.get("BKAPP_NEED_TRACK_REQUEST", 1))
except ValueError:
    NEED_TRACK_REQUEST = 1

# SUPERVISOR 自监控配置
SUPERVISOR_PROCESS_UPTIME = 10
SUPERVISOR_PORT = 9001
SUPERVISOR_SERVER = "unix:///var/run/bknodeman/nodeman-supervisord.sock"
SUPERVISOR_USERNAME = ""
SUPERVISOR_PASSWORD = ""
SUPERVISOR_SOCK = "unix:///var/run/bknodeman/nodeman-supervisord.sock"
# 自监控rabbitmq队列最大长度配置
RABBITMQ_MAX_MESSAGE_COUNT = 10000

# ===============================================================================
# Django 基础配置
# ===============================================================================

LOGGING = logging.get_logging(
    log_type=LOG_TYPE,
    log_level=LOG_LEVEL,
    bk_log_dir=env.BK_LOG_DIR,
    is_local=False,
    bk_backend_config=BK_BACKEND_CONFIG,
    bkapp_is_paas_deploy=BKAPP_IS_PAAS_DEPLOY,
    settings_module=locals(),
)


# 默认DB主键字段
# https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# 请求最大存储占用，默认为 2.5 MB，仅能支持 4k 台主机信息的传入
# 调整为默认值的4倍，支持 Agent 安装一次性传入 2w 台
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 10

# ===============================================================================
# 静态资源配置
# ===============================================================================

# 静态资源文件(js,css等）在APP上线更新后, 由于浏览器有缓存,
# 可能会造成没更新的情况. 所以在引用静态资源的地方，都把这个加上
# Django 模板中：<script src="/a.js?v={{ STATIC_VERSION }}"></script>
# mako 模板中：<script src="/a.js?v=${ STATIC_VERSION }"></script>
# 如果静态资源修改了以后，上线前改这个版本号即可
#
STATIC_VERSION = "1.0"

STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

# ==============================================================================
# SENTRY相关配置
# ==============================================================================

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    RAVEN_CONFIG = {
        "dsn": SENTRY_DSN,
    }

# ==============================================================================
# CELERY相关配置
# 参考：https://docs.celeryproject.org/en/stable/userguide/configuration.html
# ==============================================================================

# CELERY 开关，使用时请改为 True，修改项目目录下的 Procfile 文件，添加以下两行命令：
# worker: python manage.py celery worker -l info
# beat: python manage.py celery beat -l info
# 不使用时，请修改为 False，并删除项目目录下的 Procfile 文件中 celery 配置
IS_USE_CELERY = True

BROKER_HEARTBEAT = 60
BROKER_HEARTBEAT_CHECKRATE = 6
CELERY_EVENT_QUEUE_TTL = 5
CELERY_EVENT_QUEUE_EXPIRES = 60

# CELERY 并发数，默认为 2，可以通过环境变量或者 Procfile 设置
CELERYD_CONCURRENCY = os.getenv("BK_CELERYD_CONCURRENCY", 2)

CELERY_ACCEPT_CONTENT = ["pickle", "json"]
CELERY_TASK_SERIALIZER = "pickle"
CELERY_RESULT_SERIALIZER = "pickle"

# CELERY 配置，申明任务的文件路径，即包含有 @task 装饰器的函数文件
CELERY_IMPORTS = (
    "apps.backend.periodic_tasks",
    "apps.backend.subscription.tasks",
    "apps.backend.healthz.tasks",
    "pipeline.engine.tasks",
    "apps.node_man.periodic_tasks",
    # 避免 subscription.tools 循环导入，故单独引入
    "apps.node_man.periodic_tasks.add_biz_to_gse2_gray_scope",
)

BK_NODEMAN_CELERY_RESULT_BACKEND_BROKER_URL = "amqp://{user}:{passwd}@{host}:{port}/{vhost}".format(
    user=os.getenv("RABBITMQ_USER"),
    passwd=os.getenv("RABBITMQ_PASSWORD"),
    host=os.getenv("RABBITMQ_HOST"),
    port=os.getenv("RABBITMQ_PORT"),
    vhost=os.getenv("RABBITMQ_VHOST") or "bk_bknodeman",
)

# celery settings
if IS_USE_CELERY:
    INSTALLED_APPS = locals().get("INSTALLED_APPS", [])
    INSTALLED_APPS += ("django_celery_beat", "django_celery_results")
    CELERY_ENABLE_UTC = False
    CELERYBEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"
    CELERY_RESULT_BACKEND = BK_NODEMAN_CELERY_RESULT_BACKEND_BROKER_URL
    CELERY_RESULT_PERSISTENT = True
    # celery3 的配置，升级后先行注释，待确认无用后废弃
    # CELERY_TASK_RESULT_EXPIRES = 60 * 30  # 30分钟丢弃结果

CELERY_ROUTES = {
    "apps.backend.subscription.tasks.*": {"queue": "backend"},
    "apps.backend.plugin.tasks.*": {"queue": "backend"},
    "apps.node_man.handler.policy.*": {"queue": "saas"},
}

CELERY_ROUTES.update(PIPELINE_CELERY_ROUTES)
CELERY_QUEUES = PIPELINE_CELERY_QUEUES

CELERY_DEFAULT_QUEUE = "default"
CELERY_DEFAULT_EXCHANGE = "default"
CELERY_DEFAULT_ROUTING_KEY = "default"

IS_CELERY = False
IS_CELERY_BEAT = False
if "celery" in sys.argv:
    IS_CELERY = True
    if "beat" in sys.argv:
        IS_CELERY_BEAT = True
# ===============================================================================
# 项目配置
# ===============================================================================

CONF_PATH = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CONF_PATH))
PYTHON_BIN = os.path.dirname(sys.executable)

BK_PAAS_HOST = os.getenv("BK_PAAS_HOST", "")
BK_PAAS_INNER_HOST = os.getenv("BK_PAAS_INNER_HOST") or BK_PAAS_HOST
# ESB、APIGW 的域名，新增于PaaSV3，如果取不到该值，则使用 BK_PAAS_INNER_HOST
# OVERWRITE 区分，BK_COMPONENT_API_URL 会被开发框架覆盖导致 PaaSV2 环境下为 None
BK_COMPONENT_API_OVERWRITE_URL = env.BK_COMPONENT_API_URL
BK_COMPONENT_API_OUTER_URL = env.BK_COMPONENT_API_OUTER_URL
BK_APIGW_NAME = "bk-nodeman"
BK_API_URL_TMPL = env.BK_API_URL_TMPL
BK_DOMAIN = env.BK_DOMAIN

SYNC_APIGATEWAY_ENABLED = env.SYNC_APIGATEWAY_ENABLED

BK_NODEMAN_HOST = env.BK_NODEMAN_HOST
# 节点管理后台外网域名，用于构造文件导入导出的API URL
BK_NODEMAN_BACKEND_HOST = env.BK_NODEMAN_BACKEND_HOST
BK_JOB_HOST = os.environ.get("BK_JOB_HOST", BK_PAAS_HOST.replace("paas", "job"))
BK_CC_HOST = env.BK_CC_HOST

# 是否使用权限中心
USE_IAM = bool(os.getenv("BKAPP_USE_IAM", False))

BK_IAM_APP_CODE = os.getenv("BK_IAM_V3_APP_CODE", "bk_iam")
BK_IAM_INNER_HOST = os.getenv("BK_IAM_V3_INNER_HOST", "http://bkiam.service.consul:9081")
BK_IAM_SAAS_HOST = env.BK_IAM_SAAS_HOST

BK_IAM_SYSTEM_ID = os.getenv("BKAPP_IAM_SYSTEM_ID", "bk_nodeman")
BK_IAM_SYSTEM_NAME = _("节点管理")
BK_IAM_CMDB_SYSTEM_ID = os.getenv("BKAPP_IAM_CMDB_SYSTEM_ID", "bk_cmdb")
BK_IAM_MIGRATION_JSON_PATH = os.path.join(PROJECT_ROOT, "support-files/bkiam")
BK_IAM_RESOURCE_API_HOST = env.BK_IAM_RESOURCE_API_HOST

BK_IAM_MIGRATION_APP_NAME = "iam_migrations"
BK_IAM_SKIP = False

BK_DOCS_CENTER_HOST = env.BK_DOCS_CENTER_HOST
# 导航栏技术支持地址
BKAPP_NAV_HELPER_URL = env.BKAPP_NAV_HELPER_URL
# 导航栏开源社区地址
BKAPP_NAV_OPEN_SOURCE_URL = env.BKAPP_NAV_OPEN_SOURCE_URL

INIT_SUPERUSER = ["admin"]
DEBUG = False
SHOW_EXCEPTION_DETAIL = False

# 并发数
CONCURRENT_NUMBER = int(os.getenv("CONCURRENT_NUMBER", 50) or 50)

# 插件进程状态同步周期
SYNC_PROC_STATUS_TASK_INTERVAL = env.BKAPP_SYNC_PROC_STATUS_TASK_INTERVAL

# Agent安装前置脚本
SCRIPT_HOOKS = env.BKAPP_SCRIPT_HOOKS

BKPAAS_SHARED_RES_URL = env.BKPAAS_SHARED_RES_URL
BKAPP_LEGACY_AUTH = env.BKAPP_LEGACY_AUTH
BK_NOTICE_ENABLED = env.BK_NOTICE_ENABLED

# 敏感参数
SENSITIVE_PARAMS = ["app_code", "app_secret", "bk_app_code", "bk_app_secret", "auth_info"]

SWAGGER_SETTINGS = {
    "DEFAULT_INFO": "urls.openapi_info",
}

# rest_framework
REST_FRAMEWORK = {
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "EXCEPTION_HANDLER": "apps.generic.custom_exception_handler",
    "SEARCH_PARAM": "keyword",
    "DEFAULT_RENDERER_CLASSES": ("apps.utils.drf.GeneralJSONRenderer",),
}


ESB_SDK_NAME = "blueking.component"

BKCRYPTO = {
    "SYMMETRIC_CIPHERS": {
        "default": {
            "get_key_config": "apps.utils.encrypt.key.get_key_config",
            "cipher_options": {
                bkcrypto_constants.SymmetricCipherType.AES.value: AESSymmetricOptions(
                    key_size=24,
                    iv=b"TencentBkNode-Iv",
                    mode=bkcrypto_constants.SymmetricMode.CFB,
                    interceptor=Interceptor,
                    encryption_metadata_combination_mode=bkcrypto_constants.EncryptionMetadataCombinationMode.STRING_SEP,
                ),
                bkcrypto_constants.SymmetricCipherType.SM4.value: SM4SymmetricOptions(
                    mode=bkcrypto_constants.SymmetricMode.CTR
                ),
            },
        },
    },
    "ASYMMETRIC_CIPHERS": {
        "gse": {
            "get_key_config": "apps.utils.encrypt.key.get_gse_asymmetric_key_config",
            "cipher_options": {
                bkcrypto_constants.AsymmetricCipherType.RSA.value: RSAAsymmetricOptions(
                    padding=bkcrypto_constants.RSACipherPadding.PKCS1_OAEP
                )
            },
        },
    },
}


# 启用框架内置数据加密
BLUEAPPS_ENABLE_DB_ENCRYPTION = True
# 复用已有的 default 对称加密实例
BKCRYPTO["SYMMETRIC_CIPHERS"]["blueapps"] = BKCRYPTO["SYMMETRIC_CIPHERS"]["default"]

# 加密
if BKPAAS_BK_CRYPTO_TYPE == env.constants.BkCryptoType.SHANGMI.value:
    BKCRYPTO.update(
        {
            "ASYMMETRIC_CIPHER_TYPE": bkcrypto_constants.AsymmetricCipherType.SM2.value,
            "SYMMETRIC_CIPHER_TYPE": bkcrypto_constants.SymmetricCipherType.SM4.value,
        }
    )
else:
    BKCRYPTO.update(
        {
            "ASYMMETRIC_CIPHER_TYPE": bkcrypto_constants.AsymmetricCipherType.RSA.value,
            "SYMMETRIC_CIPHER_TYPE": bkcrypto_constants.SymmetricCipherType.AES.value,
        }
    )

# ==============================================================================
# 国际化相关配置
# ==============================================================================

# 时区
USE_TZ = True
TIME_ZONE = "Etc/GMT-8"

DATAAPI_TIME_ZONE = "Etc/GMT-8"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"

# 翻译
USE_I18N = True
USE_L10N = True
LANGUAGE_CODE = "zh-cn"
LOCALEURL_USE_ACCEPT_LANGUAGE = True
LANGUAGE_SESSION_KEY = "blueking_language"
LANGUAGE_COOKIE_NAME = "blueking_language"
SUPPORT_LANGUAGE = ["en", "zh-cn"]
# 设定使用根目录的locale
LOCALE_PATHS = (os.path.join(PROJECT_ROOT, "locale"),)

# ===============================================================================
# Authentication
# ===============================================================================
AUTH_USER_MODEL = "account.User"
AUTHENTICATION_BACKENDS = (
    "apps.authentication.ApiGatewayJWTUserModelBackend",
    "blueapps.account.backends.BkJwtBackend",
    "blueapps.account.backends.UserBackend",
    "django.contrib.auth.backends.ModelBackend",
)
# 验证登录的cookie名
BK_COOKIE_NAME = "bk_token"

# 请求API用户名
SYSTEM_USE_API_ACCOUNT = "admin"

# ==============================================================================
# Templates
# ==============================================================================
# mako template dir

MAKO_TEMPLATE_DIR = [os.path.join(PROJECT_ROOT, directory) for directory in ["static/dist", "templates"]]

VUE_INDEX = f"{env.ENVIRONMENT}/index.html"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(PROJECT_ROOT, "templates"), os.path.join(PROJECT_ROOT, "static/")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "blueapps.template.context_processors.blue_settings",
                "common.context_processors.mysetting",  # 自定义模版context，可在页面中使用STATIC_URL等变量
            ],
            "debug": DEBUG,
        },
    },
]

# ==============================================================================
# 文件存储
# ==============================================================================


class StorageType(Enum):
    """文件存储类型"""

    # 本地文件系统
    FILE_SYSTEM = "FILE_SYSTEM"

    # 制品库
    BLUEKING_ARTIFACTORY = "BLUEKING_ARTIFACTORY"


# 用于控制默认的文件存储类型
# 更多类型参考 apps.node_man.constants.STORAGE_TYPE
STORAGE_TYPE = os.getenv("STORAGE_TYPE", StorageType.FILE_SYSTEM.value)

# 是否覆盖同名文件
FILE_OVERWRITE = get_type_env("FILE_OVERWRITE", _type=bool, default=False)

BKREPO_USERNAME = os.getenv("BKREPO_USERNAME")
BKREPO_PASSWORD = os.getenv("BKREPO_PASSWORD")
BKREPO_PROJECT = os.getenv("BKREPO_PROJECT")
# 默认文件存放仓库
BKREPO_BUCKET = os.getenv("BKREPO_PUBLIC_BUCKET")
# 对象存储平台域名
BKREPO_ENDPOINT_URL = os.getenv("BKREPO_ENDPOINT_URL")

# 存储类型 - storage class 映射关系
STORAGE_TYPE_IMPORT_PATH_MAP = {
    StorageType.FILE_SYSTEM.value: "apps.core.files.storage.AdminFileSystemStorage",
    StorageType.BLUEKING_ARTIFACTORY.value: "apps.core.files.storage.CustomBKRepoStorage",
}

# 默认的file storage
DEFAULT_FILE_STORAGE = STORAGE_TYPE_IMPORT_PATH_MAP[STORAGE_TYPE]

# 本地文件系统上传文件后台API
FILE_SYSTEM_UPLOAD_API = f"{BK_NODEMAN_BACKEND_HOST}/backend/package/upload/"

# 对象存储上传文件后台API
COS_UPLOAD_API = f"{BK_NODEMAN_BACKEND_HOST}/backend/api/plugin/upload/"

# 暂时存在多个上传API的原因：原有文件上传接口被Nginx转发
STORAGE_TYPE_UPLOAD_API_MAP = {
    StorageType.FILE_SYSTEM.value: FILE_SYSTEM_UPLOAD_API,
    StorageType.BLUEKING_ARTIFACTORY.value: COS_UPLOAD_API,
}

DEFAULT_FILE_UPLOAD_API = STORAGE_TYPE_UPLOAD_API_MAP[STORAGE_TYPE]

DEFAULT_FILE_DOWNLOAD_API = f"{BK_NODEMAN_BACKEND_HOST}/backend/tools/download/"

BKAPP_NODEMAN_DOWNLOAD_API = f"{BK_NODEMAN_BACKEND_HOST}/backend/export/download/"

PUBLIC_PATH = os.getenv("BKAPP_PUBLIC_PATH") or "/data/bkee/public/bknodeman/"

# NGINX miniweb路径
DOWNLOAD_PATH = os.path.join(PUBLIC_PATH, "download")

# 上传文件的保存位置
UPLOAD_PATH = os.path.join(PUBLIC_PATH, "upload")

# 下载文件路径
EXPORT_PATH = os.path.join(PUBLIC_PATH, "export")

# 脚本工具存放位置
BK_SCRIPTS_PATH = os.path.join(PROJECT_ROOT, "script_tools")

# ==============================================================================
# 后台配置
# ==============================================================================

PIPELINE_DATA_BACKEND = "pipeline.engine.core.data.mysql_backend.MySQLDataBackend"
PIPELINE_END_HANDLER = "apps.backend.agent.signals.pipeline_end_handler"
ENGINE_ZOMBIE_PROCESS_DOCTORS = [
    {
        "class": "pipeline.engine.health.zombie.doctors.RunningNodeZombieDoctor",
        "config": {"max_stuck_time": 1200, "detect_wait_callback_proc": True},
    }
]
ENGINE_ZOMBIE_PROCESS_HEAL_CRON = {"minute": "*/10"}

# API 执行者
BACKEND_JOB_OPERATOR = os.getenv("BKAPP_BACKEND_JOB_OPERATOR", "admin")
BACKEND_GSE_OPERATOR = os.getenv("BKAPP_BACKEND_GSE_OPERATOR", "admin")
BACKEND_SOPS_OPERATOR = os.getenv("BKAPP_BACKEND_SOPS_OPERATOR", "admin")

# Windows的作业执行账户
BACKEND_WINDOWS_ACCOUNT = os.getenv("BKAPP_BACKEND_WINDOWS_ACCOUNT", "system")
BACKEND_UNIX_ACCOUNT = os.getenv("BKAPP_BACKEND_UNIX_ACCOUNT", "root")

"""
以下为框架代码 请勿修改
"""


class ConfigRedisMode(EnhanceEnum):
    """
    后台配置的Redis模式
    背景：脱离PaaS的后台部署，运维提供的Redis模式切换控制变量
    """

    STANDALONE = "standalone"
    SENTINEL = "sentinel"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.STANDALONE: "单例模式", cls.SENTINEL: "哨兵模式"}


class RedisMode(EnhanceEnum):
    """标准Redis模式"""

    SINGLE = "single"
    REPLICATION = "replication"
    CLUSTER = "cluster"

    @classmethod
    def _get_member__alias_map(cls) -> Dict[Enum, str]:
        return {cls.SINGLE: "单例模式", cls.REPLICATION: "主从模式", cls.CLUSTER: "集群模式"}

    @classmethod
    def get_config_mode__redis_mode_map(cls):
        """获取配置Redis模式 - 标准Redis模式映射"""
        return {
            ConfigRedisMode.SENTINEL.value: cls.REPLICATION.value,
            ConfigRedisMode.STANDALONE.value: cls.SINGLE.value,
        }

    @classmethod
    def get_standard_redis_mode(cls, config_redis_mode: str, default: Optional[str] = None) -> Optional[str]:
        return cls.get_config_mode__redis_mode_map().get(config_redis_mode, default)


# ==============================================================================
# Cache
# ==============================================================================
CACHES.update(
    {
        "db": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "django_cache",
            "OPTIONS": {"MAX_ENTRIES": 10000, "CULL_FREQUENCY": 10},
        }
    }
)

CACHE_KEY_TMPL = APP_CODE + ":scope:{scope}:body:{body}"

CONFIG_REDIS_MODE = os.getenv("REDIS_MODE", ConfigRedisMode.SENTINEL.value)
REDIS_MODE = RedisMode.get_standard_redis_mode(CONFIG_REDIS_MODE, default=RedisMode.REPLICATION.value)

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_MASTER_NAME = os.getenv("REDIS_MASTER_NAME")
REDIS_SENTINEL_PASSWORD = os.getenv("REDIS_SENTINEL_PASSWORD")

DJANGO_REDIS_COMMON_OPTIONS = {
    "CLIENT_CLASS": "django_redis.client.DefaultClient",
    "REDIS_CLIENT_CLASS": "redis.client.StrictRedis",
    "SERIALIZER": "apps.utils.cache.JSONSerializer",
}

if REDIS_MODE == "replication":
    # redis 集群sentinel模式
    REDIS_HOST = os.getenv("REDIS_SENTINEL_HOST")
    REDIS_PORT = os.getenv("REDIS_SENTINEL_PORT")
    # # celery redbeat config
    REDBEAT_REDIS_URL = "redis-sentinel://redis-sentinel:{port}/0".format(port=REDIS_PORT or 26379)
    REDBEAT_REDIS_OPTIONS = {
        "sentinels": [(REDIS_HOST, REDIS_PORT)],
        "password": REDIS_PASSWORD,
        "service_name": REDIS_MASTER_NAME or "mymaster",
        "socket_timeout": 0.1,
        "retry_period": 60,
        "sentinel_kwargs": {"password": REDIS_SENTINEL_PASSWORD},
    }
    DJANGO_REDIS_CONNECTION_FACTORY = "apps.utils.cache.SentinelConnectionFactory"
    CACHES["redis"] = {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDBEAT_REDIS_OPTIONS['service_name']}:{REDIS_PORT}/0",
        "KEY_PREFIX": "nodeman",
        "KEY_FUNCTION": "apps.utils.cache.django_cache_key_maker",
        "OPTIONS": {
            "PASSWORD": REDIS_PASSWORD,
            "SENTINELS": REDBEAT_REDIS_OPTIONS["sentinels"],
            "SENTINEL_KWARGS": REDBEAT_REDIS_OPTIONS["sentinel_kwargs"],
            "CONNECTION_POOL_CLASS": "redis.sentinel.SentinelConnectionPool",
            **DJANGO_REDIS_COMMON_OPTIONS,
        },
    }
else:
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT")
    # # celery redbeat config
    REDBEAT_REDIS_URL = "redis://:{passwd}@{host}:{port}/0".format(
        passwd=REDIS_PASSWORD, host=REDIS_HOST, port=REDIS_PORT or 6379
    )
    DJANGO_REDIS_CONNECTION_FACTORY = "apps.utils.cache.ConnectionFactory"
    CACHES["redis"] = {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDBEAT_REDIS_URL,
        "KEY_PREFIX": "nodeman",
        "KEY_FUNCTION": "apps.utils.cache.django_cache_key_maker",
        "OPTIONS": {**DJANGO_REDIS_COMMON_OPTIONS},
    }

REDIS = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "password": REDIS_PASSWORD,
    "service_name": REDIS_MASTER_NAME,
    "sentinel_password": REDIS_SENTINEL_PASSWORD,
    "mode": REDIS_MODE,  # 哨兵模式，可选 single, cluster, replication
}

CACHE_BACKEND = env.CACHE_BACKEND
CACHE_ENABLE_PREHEAT = env.CACHE_ENABLE_PREHEAT
CACHES["default"] = CACHES[CACHE_BACKEND]


# ==============================================================================
# 后台配置
# ==============================================================================

if BK_BACKEND_CONFIG:
    DISABLED_APPS = []

    # 后台根路径与SaaS
    BASE_DIR = os.path.dirname(PROJECT_ROOT)

    # SESSION 引擎
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
    FORCE_SCRIPT_NAME = ""
    # 其他后台配置，都可以增加到这里
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",  # 默认用mysql
            "NAME": os.getenv("MYSQL_NAME", "bk_nodeman"),  # 数据库名
            "USER": os.getenv("MYSQL_USER"),
            "PASSWORD": os.getenv("MYSQL_PASSWORD"),
            "HOST": os.getenv("MYSQL_HOST"),
            "PORT": os.getenv("MYSQL_PORT"),
            "OPTIONS": {"isolation_level": "repeatable read"},
        }
    }
    BK_OFFICIAL_PLUGINS_INIT_PATH = os.path.join(PROJECT_ROOT, "official_plugin")
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
        "apps.utils.drf.CsrfExemptSessionAuthentication",
    ]

    # 移除用户认证中间件
    LOGIN_MIDDLEWARE = "blueapps.account.middlewares.LoginRequiredMiddleware"
    if LOGIN_MIDDLEWARE in MIDDLEWARE:
        MIDDLEWARE = (
            MIDDLEWARE[: MIDDLEWARE.index(LOGIN_MIDDLEWARE)] + MIDDLEWARE[MIDDLEWARE.index(LOGIN_MIDDLEWARE) + 1 :]
        )

    # BROKER_URL
    BROKER_URL = BK_NODEMAN_CELERY_RESULT_BACKEND_BROKER_URL

    REDBEAT_KEY_PREFIX = "nodeman"


# TODO 目前后台使用
# 节点管理后台 BKAPP_LAN_IP 或 BKAPP_NFS_IP 进行文件分发，是否能统一变量
BKAPP_LAN_IP = os.getenv("LAN_IP")

# 节点管理后台 NFS_IP
BKAPP_NFS_IP = os.getenv("NFS_IP") or BKAPP_LAN_IP

# 节点管理回调地址
BKAPP_NODEMAN_CALLBACK_URL = os.getenv("BKAPP_NODEMAN_CALLBACK_URL", "")
BKAPP_NODEMAN_OUTER_CALLBACK_URL = os.getenv("BKAPP_NODEMAN_OUTER_CALLBACK_URL", "")
BK_NODEMAN_API_ADDR = os.getenv("BK_NODEMAN_API_ADDR", "")
BK_NODEMAN_NGINX_DOWNLOAD_PORT = os.getenv("BK_NODEMAN_NGINX_DOWNLOAD_PORT") or 17980
BK_NODEMAN_NGINX_PROXY_PASS_PORT = os.getenv("BK_NODEMAN_NGINX_PROXY_PASS_PORT") or 17981

# 使用标准运维开通策略相关变量
BKAPP_REQUEST_EE_SOPS_APP_CODE = os.getenv("BKAPP_REQUEST_EE_SOPS_APP_CODE")
BKAPP_REQUEST_EE_SOPS_APP_SECRET = os.getenv("BKAPP_REQUEST_EE_SOPS_APP_SECRET")
BKAPP_EE_SOPS_API_HOST = os.getenv("BKAPP_EE_SOPS_API_HOST")
BKAPP_REQUEST_EE_SOPS_OPERATOR = os.getenv("BKAPP_REQUEST_EE_SOPS_OPERATOR", "admin")
BKAPP_EE_SOPS_TEMPLATE_ID = os.getenv("BKAPP_EE_SOPS_TEMPLATE_ID")
BKAPP_REQUEST_EE_SOPS_BK_BIZ_ID = os.getenv("BKAPP_REQUEST_EE_SOPS_BK_BIZ_ID")

# 使用云梯开通策略相关变量
BKAPP_REQUEST_YUNTI_APP_KEY = os.getenv("BKAPP_REQUEST_YUNTI_APP_KEY")
BKAPP_REQUEST_YUNTI_SECRET = os.getenv("BKAPP_REQUEST_YUNTI_SECRET")

# 管控平台平台版本
GSE_VERSION = env.GSE_VERSION
GSE_CERT_PATH = env.GSE_CERT_PATH

GSE_ENABLE_PUSH_ENVIRON_FILE = env.GSE_ENABLE_PUSH_ENVIRON_FILE
GSE_ENVIRON_DIR = env.GSE_ENVIRON_DIR
GSE_ENVIRON_WIN_DIR = env.GSE_ENVIRON_WIN_DIR

# agent 安装路径配置
GSE_AGENT_HOME = os.getenv("BKAPP_GSE_AGENT_HOME") or "/usr/local/gse"
GSE_AGENT_LOG_DIR = os.getenv("BKAPP_GSE_AGENT_LOG_DIR") or "/var/log/gse"
GSE_AGENT_RUN_DIR = os.getenv("BKAPP_GSE_AGENT_RUN_DIR") or "/var/run/gse"
GSE_AGENT_DATA_DIR = os.getenv("BKAPP_GSE_AGENT_DATA_DIR") or "/var/lib/gse"

GSE_WIN_AGENT_HOME = os.getenv("BKAPP_GSE_WIN_AGENT_HOME") or "C:\\gse"
GSE_WIN_AGENT_LOG_DIR = os.getenv("BKAPP_GSE_WIN_AGENT_LOG_DIR") or "C:\\gse\\logs"
GSE_WIN_AGENT_RUN_DIR = os.getenv("BKAPP_GSE_WIN_AGENT_RUN_DIR") or "C:\\gse\\logs"
GSE_WIN_AGENT_DATA_DIR = os.getenv("BKAPP_GSE_WIN_AGENT_DATA_DIR") or "C:\\gse\\data"

# 是否使用GSE加密敏感信息
GSE_USE_ENCRYPTION = get_type_env(key="BKAPP_GSE_USE_ENCRYPTION", default=False, _type=bool)

GSE_PROCESS_STATUS_DATAID = os.getenv("GSE_PROCESS_STATUS_DATAID") or 1200000
GSE_PROCESS_EVENT_DATAID = os.getenv("GSE_PROCESS_EVENT_DATAID") or 1100008

# 是否启用 gse svr 服务发现，启用后，默认接入点会通过zk的方式，自动更新gse svr信息
GSE_ENABLE_SVR_DISCOVERY = get_type_env(key="GSE_ENABLE_SVR_DISCOVERY", default=False, _type=bool)

# 是否使用CMDB订阅机制去主动触发插件下发
USE_CMDB_SUBSCRIPTION_TRIGGER = get_type_env(key="BKAPP_USE_CMDB_SUBSCRIPTION_TRIGGER", default=True, _type=bool)

VERSION_LOG = {"MD_FILES_DIR": os.path.join(PROJECT_ROOT, "release"), "LANGUAGE_MAPPINGS": {"en": "en"}}

# 腾讯云endpoint
TXY_ENDPOINT = env.TXY_ENDPOINT

# ==============================================================================
# 可观测
# ==============================================================================

# 自定义上报监控配置
if env.BKAPP_MONITOR_REPORTER_ENABLE:
    monitor_report_config()

# remove disabled apps
if locals().get("DISABLED_APPS"):
    INSTALLED_APPS = locals().get("INSTALLED_APPS", [])
    DISABLED_APPS = locals().get("DISABLED_APPS", [])

    INSTALLED_APPS = [_app for _app in INSTALLED_APPS if _app not in DISABLED_APPS]

    _keys = (
        "AUTHENTICATION_BACKENDS",
        "DATABASE_ROUTERS",
        "FILE_UPLOAD_HANDLERS",
        "MIDDLEWARE",
        "PASSWORD_HASHERS",
        "TEMPLATE_LOADERS",
        "STATICFILES_FINDERS",
        "TEMPLATE_CONTEXT_PROCESSORS",
    )

    import itertools

    for _app, _key in itertools.product(DISABLED_APPS, _keys):
        if locals().get(_key) is None:
            continue
        locals()[_key] = tuple([_item for _item in locals()[_key] if not _item.startswith(_app + ".")])
