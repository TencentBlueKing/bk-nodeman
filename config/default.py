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
import sys
from distutils.util import strtobool
from enum import Enum

from blueapps.conf.default_settings import *  # noqa

from apps.utils.env import get_type_env
from config import ENVIRONMENT

# pipeline 配置
from pipeline.celery.settings import CELERY_QUEUES as PIPELINE_CELERY_QUEUES
from pipeline.celery.settings import CELERY_ROUTES as PIPELINE_CELERY_ROUTES

# SaaS运行环境用于区分环境差异
BKAPP_RUN_ENV = os.getenv("BKAPP_RUN_ENV")
REDIRECT_FIELD_NAME = "c_url"
IS_AJAX_PLAIN_MODE = True

# 请在这里加入你的自定义 APP
INSTALLED_APPS += (
    "django_mysql",
    "rest_framework",
    "common.api",
    "version_log",
    "apps.node_man",
    "apps.backend",
    "apps.core.files",
    "requests_tracker",
    # pipeline
    "pipeline",
    "pipeline.log",
    "pipeline.engine",
    "pipeline.component_framework",
    "pipeline.django_signal_valve",
    "apps.iam_migration",
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
    # 'blueapps.account.middlewares.BkJwtLoginRequiredMiddleware',
    # 'blueapps.account.middlewares.WeixinLoginRequiredMiddleware',
    "blueapps.account.middlewares.LoginRequiredMiddleware",
    # exception middleware
    "blueapps.core.exceptions.middleware.AppExceptionMiddleware",
    # 自定义中间件
    "django.middleware.locale.LocaleMiddleware",
    "apps.middlewares.CommonMid",
    "apps.middlewares.UserLocalMiddleware",
)

# 单元测试豁免登录
if "test" in sys.argv:
    index = MIDDLEWARE.index("blueapps.account.middlewares.LoginRequiredMiddleware")
    MIDDLEWARE = MIDDLEWARE[:index] + MIDDLEWARE[index + 1 :]

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

# 所有环境的日志级别可以在这里配置
# LOG_LEVEL = 'INFO'

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
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # Redis 结果后端

# CELERY 配置，申明任务的文件路径，即包含有 @task 装饰器的函数文件
CELERY_IMPORTS = (
    "apps.backend.periodic_tasks",
    "apps.backend.subscription.tasks",
    "apps.backend.healthz.tasks",
    "pipeline.engine.tasks",
    "apps.node_man.periodic_tasks",
)

# ===============================================================================
# 项目配置
# ===============================================================================
BK_PAAS_HOST = os.getenv("BK_PAAS_HOST", "") or BK_URL
BK_PAAS_INNER_HOST = os.getenv("BK_PAAS_INNER_HOST") or BK_PAAS_HOST

BK_NODEMAN_URL = os.getenv("BK_NODEMAN_URL", f"{BK_PAAS_INNER_HOST}/o/bk_nodeman")
BK_CMDB_HOST = os.environ.get("BK_CMDB_HOST", BK_PAAS_HOST.replace("paas", "cmdb"))
BK_JOB_HOST = os.environ.get("BK_JOB_HOST", BK_PAAS_HOST.replace("paas", "job"))

BK_IAM_ESB_PAAS_HOST = os.getenv("BK_IAM_ESB_PAAS_HOST") or BK_PAAS_INNER_HOST
BK_IAM_HOST = os.getenv("BK_IAM_V3_INNER_HOST", "http://bkiam.service.consul:9081")
BK_IAM_SYSTEM_ID = os.getenv("BK_IAM_SYSTEM_ID", "bk_nodeman")
BK_IAM_CMDB_SYSTEM_ID = os.getenv("BK_IAM_CMDB_SYSTEM_ID", "bk_cmdb")
BK_IAM_URL = os.getenv("BK_IAM_URL", f"{BK_PAAS_HOST}/o/bk_iam/apply-custom-perm")

BK_IAM_MIGRATION_APP_NAME = "iam_migrations"
BK_IAM_SKIP = False

CONF_PATH = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CONF_PATH))
PYTHON_BIN = os.path.dirname(sys.executable)

BK_DOCS_CENTER_HOST = os.getenv("BK_DOCS_CENTER_HOST")

INIT_SUPERUSER = ["admin"]
DEBUG = False
SHOW_EXCEPTION_DETAIL = False

# 使用权限中心
USE_IAM = bool(os.getenv("BKAPP_USE_IAM", False))

# 并发数
CONCURRENT_NUMBER = int(os.getenv("CONCURRENT_NUMBER", 50) or 50)

# 敏感参数
SENSITIVE_PARAMS = ["app_code", "app_secret", "bk_app_code", "bk_app_secret", "auth_info"]

# rest_framework
REST_FRAMEWORK = {
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "EXCEPTION_HANDLER": "apps.generic.custom_exception_handler",
    "SEARCH_PARAM": "keyword",
    "DEFAULT_RENDERER_CLASSES": ("apps.utils.drf.GeneralJSONRenderer",),
}


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

VUE_INDEX = f"{ENVIRONMENT}/index.html"

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

CACHES["default"] = CACHES["db"]


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

# 节点管理后台外网域名，用于构造文件导入导出的API URL
BACKEND_HOST = os.getenv("BKAPP_BACKEND_HOST", "")

BKREPO_USERNAME = os.getenv("BKREPO_USERNAME")
BKREPO_PASSWORD = os.getenv("BKREPO_PASSWORD")
BKREPO_PROJECT = os.getenv("BKREPO_PROJECT")
# 默认文件存放仓库
BKREPO_BUCKET = os.getenv("BKREPO_BUCKET")
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
FILE_SYSTEM_UPLOAD_API = f"{BACKEND_HOST}/backend/package/upload/"

# 对象存储上传文件后台API
COS_UPLOAD_API = f"{BACKEND_HOST}/backend/package/upload_cos/"

# 暂时存在多个上传API的原因：原有文件上传接口被Nginx转发
STORAGE_TYPE_UPLOAD_API_MAP = {
    StorageType.FILE_SYSTEM.value: FILE_SYSTEM_UPLOAD_API,
    StorageType.BLUEKING_ARTIFACTORY.value: COS_UPLOAD_API,
}

DEFAULT_FILE_UPLOAD_API = STORAGE_TYPE_UPLOAD_API_MAP[STORAGE_TYPE]

BKAPP_NODEMAN_DOWNLOAD_API = f"{BACKEND_HOST}/backend/export/download/"

PUBLIC_PATH = os.getenv("BKAPP_PUBLIC_PATH") or "/data/bkee/public/bknodeman/"

# NGINX miniweb路径
DOWNLOAD_PATH = os.path.join(PUBLIC_PATH, "download")

# 上传文件的保存位置
UPLOAD_PATH = os.path.join(PUBLIC_PATH, "upload")

# 下载文件路径
EXPORT_PATH = os.path.join(PUBLIC_PATH, "export")

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

"""
以下为框架代码 请勿修改
"""
# celery settings
if IS_USE_CELERY:
    INSTALLED_APPS = locals().get("INSTALLED_APPS", [])
    import djcelery

    INSTALLED_APPS += ("djcelery",)
    djcelery.setup_loader()
    CELERY_ENABLE_UTC = True
    CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
    CELERY_RESULT_BACKEND = "amqp"
    CELERY_TASK_RESULT_EXPIRES = 60 * 30  # 30分钟丢弃结果

# 后台配置
BK_BACKEND_CONFIG = bool(os.getenv("BK_BACKEND_CONFIG", None))

if BK_BACKEND_CONFIG:
    IS_LOCAL = False
    # 后台不需要version log
    DISABLED_APPS = ["version_log"]

    # 后台根路径与SaaS
    BASE_DIR = os.path.dirname(PROJECT_ROOT)

    # 在登录中间件前面加上JWT中间件认证
    JWT_MIDDLEWARE = "blueapps.account.middlewares.BkJwtLoginRequiredMiddleware"
    LOGIN_MIDDLEWARE = "blueapps.account.middlewares.LoginRequiredMiddleware"
    if LOGIN_MIDDLEWARE in MIDDLEWARE:
        MIDDLEWARE = (
            MIDDLEWARE[0 : MIDDLEWARE.index(LOGIN_MIDDLEWARE)]
            + (JWT_MIDDLEWARE,)
            + MIDDLEWARE[MIDDLEWARE.index(LOGIN_MIDDLEWARE) :]
        )

    # SESSION 引擎
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
    FORCE_SCRIPT_NAME = ""
    # 其他后台配置，都可以增加到这里
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",  # 默认用mysql
            "NAME": os.getenv("BK_NODEMAN_MYSQL_NAME", "bk_nodeman"),  # 数据库名
            "USER": os.getenv("BK_NODEMAN_MYSQL_USER"),
            "PASSWORD": os.getenv("BK_NODEMAN_MYSQL_PASSWORD"),
            "HOST": os.getenv("BK_NODEMAN_MYSQL_HOST"),
            "PORT": os.getenv("BK_NODEMAN_MYSQL_PORT"),
            "OPTIONS": {"isolation_level": "repeatable read"},
        }
    }
    BK_OFFICIAL_PLUGINS_INIT_PATH = os.path.join(PROJECT_ROOT, "official_plugin")
    BK_SCRIPTS_PATH = os.path.join(PROJECT_ROOT, "script_tools")
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
        "apps.utils.drf.CsrfExemptSessionAuthentication",
    ]
    # redis 集群sentinel模式
    REDIS_HOST = os.getenv("BK_NODEMAN_REDIS_SENTINEL_HOST")
    REDIS_PORT = os.getenv("BK_NODEMAN_REDIS_SENTINEL_PORT")
    REDIS_PASSWD = os.getenv("BK_NODEMAN_REDIS_PASSWORD")
    REDIS_MASTER_NAME = os.getenv("BK_NODEMAN_REDIS_MASTER_NAME")

    REDIS = {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "password": REDIS_PASSWD,
        "service_name": REDIS_MASTER_NAME,
        "mode": "replication",  # 哨兵模式，可选 single, cluster, replication
    }
    # BROKER_URL
    BROKER_URL = "amqp://{user}:{passwd}@{host}:{port}/{vhost}".format(
        user=os.getenv("BK_NODEMAN_RABBITMQ_USERNAME"),
        passwd=os.getenv("BK_NODEMAN_RABBITMQ_PASSWORD"),
        host=os.getenv("BK_NODEMAN_RABBITMQ_HOST"),
        port=os.getenv("BK_NODEMAN_RABBITMQ_PORT"),
        vhost=os.getenv("BK_NODEMAN_RABBITMQ_VHOST") or "bk_bknodeman",
    )

    # celery redbeat config
    if BKAPP_RUN_ENV == "ce":
        REDBEAT_REDIS_URL = "redis://:{passwd}@{host}:{port}/0".format(
            passwd=REDIS_PASSWD, host=REDIS_HOST, port=REDIS_PORT or 6379
        )
        REDIS["mode"] = "single"
    else:
        REDBEAT_REDIS_URL = "redis-sentinel://redis-sentinel:{port}/0".format(port=REDIS_PORT or 26379)
    REDBEAT_REDIS_OPTIONS = {
        "sentinels": [(REDIS_HOST, REDIS_PORT)],
        "password": REDIS_PASSWD,
        "service_name": REDIS_MASTER_NAME or "mymaster",
        "socket_timeout": 0.1,
        "retry_period": 60,
    }
    REDBEAT_KEY_PREFIX = "nodeman"

    # 使用标准运维开通策略相关变量
    BKAPP_REQUEST_EE_SOPS_APP_CODE = os.getenv("BKAPP_REQUEST_EE_SOPS_APP_CODE")
    BKAPP_REQUEST_EE_SOPS_APP_SECRET = os.getenv("BKAPP_REQUEST_EE_SOPS_APP_SECRET")
    BKAPP_EE_SOPS_API_HOST = os.getenv("BKAPP_EE_SOPS_API_HOST")
    BKAPP_REQUEST_EE_SOPS_OPERATOR = os.getenv("BKAPP_REQUEST_EE_SOPS_OPERATOR", "admin")
    BKAPP_EE_SOPS_TEMPLATE_ID = os.getenv("BKAPP_EE_SOPS_TEMPLATE_ID")
    BKAPP_REQUEST_EE_SOPS_BK_BIZ_ID = os.getenv("BKAPP_REQUEST_EE_SOPS_BK_BIZ_ID")

    from blueapps.patch.log import get_paas_v2_logging_config_dict

    # 日志
    BK_LOG_DIR = os.getenv("BK_LOG_DIR", "./../bk_nodeman/logs")
    LOGGING = get_paas_v2_logging_config_dict(
        is_local=IS_LOCAL, bk_log_dir=BK_LOG_DIR, log_level=locals().get("LOG_LEVEL", "INFO")
    )
else:
    from blueapps.conf.log import get_logging_config_dict

    LOGGING = get_logging_config_dict(locals())
    LOGGING["handlers"]["root"]["encoding"] = "utf-8"
    LOGGING["handlers"]["component"]["encoding"] = "utf-8"
    LOGGING["handlers"]["mysql"]["encoding"] = "utf-8"
    LOGGING["handlers"]["blueapps"]["encoding"] = "utf-8"

ROOT_LOGGING_CONFIG = LOGGING["handlers"]["root"]
LOG_DIR = os.path.sep.join(ROOT_LOGGING_CONFIG["filename"].split(os.path.sep)[:-1])
LOGGING["handlers"]["iam"] = {
    "class": ROOT_LOGGING_CONFIG["class"],
    "formatter": ROOT_LOGGING_CONFIG["formatter"],
    "filename": os.path.sep.join([LOG_DIR, "iam.log"]),
    "maxBytes": ROOT_LOGGING_CONFIG["maxBytes"],
    "backupCount": ROOT_LOGGING_CONFIG["backupCount"],
}
LOGGING["loggers"]["iam"] = {"handlers": ["iam"], "level": LOGGING["loggers"]["root"]["level"], "propagate": True}


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

# 是否使用CMDB订阅机制去主动触发插件下发
USE_CMDB_SUBSCRIPTION_TRIGGER = get_type_env(key="BKAPP_USE_CMDB_SUBSCRIPTION_TRIGGER", default=True, _type=bool)

VERSION_LOG = {"MD_FILES_DIR": os.path.join(PROJECT_ROOT, "release")}


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
