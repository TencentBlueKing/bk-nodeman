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
import os
import sys
import typing

from blueapps.conf.log import get_logging_config_dict

from env import constants


def add_iam_log_conf(logging_conf: typing.Dict):
    root_logging_config = logging_conf["handlers"]["root"]
    log_dir = os.path.sep.join(root_logging_config["filename"].split(os.path.sep)[:-1])
    logging_conf["handlers"]["iam"] = {
        "class": root_logging_config["class"],
        "formatter": root_logging_config["formatter"],
        "filename": os.path.sep.join([log_dir, "iam.log"]),
        "maxBytes": root_logging_config["maxBytes"],
        "backupCount": root_logging_config["backupCount"],
    }
    logging_conf["loggers"]["iam"] = {
        "handlers": ["iam"],
        "level": logging_conf["loggers"]["root"]["level"],
        "propagate": True,
    }
    return logging_conf


def get_paas_logging_conf(settings_module: typing.Dict):
    logging_conf = get_logging_config_dict(settings_module)
    logging_conf["handlers"]["root"]["encoding"] = "utf-8"
    logging_conf["handlers"]["component"]["encoding"] = "utf-8"
    logging_conf["handlers"]["mysql"]["encoding"] = "utf-8"
    logging_conf["handlers"]["blueapps"]["encoding"] = "utf-8"
    return add_iam_log_conf(logging_conf)


def get_backend_logging_conf(log_level: str, bk_log_dir: str, is_local: bool):
    from blueapps.patch.log import get_paas_v2_logging_config_dict

    logging_conf = get_paas_v2_logging_config_dict(is_local=False, bk_log_dir=bk_log_dir, log_level=log_level)
    return add_iam_log_conf(logging_conf)


def get_stdout_logging_conf(log_level: str):
    return {
        "version": 1,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "fmt": (
                    "%(levelname)s | %(asctime)s | %(pathname)s | %(lineno)d "
                    "%(funcName)s | %(process)d | %(thread)d | %(message)s "
                ),
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "django": {"handlers": ["stdout"], "level": "INFO", "propagate": True},
            "django.server": {
                "handlers": ["stdout"],
                "level": log_level,
                "propagate": True,
            },
            "django.request": {
                "handlers": ["stdout"],
                "level": "ERROR",
                "propagate": True,
            },
            "django.db.backends": {
                "handlers": ["stdout"],
                "level": log_level,
                "propagate": True,
            },
            # the root logger ,用于整个project的logger
            "root": {"handlers": ["stdout"], "level": log_level, "propagate": True},
            # 组件调用日志
            "component": {
                "handlers": ["stdout"],
                "level": log_level,
                "propagate": True,
            },
            "celery": {"handlers": ["stdout"], "level": log_level, "propagate": True},
            # other loggers...
            # blueapps
            "blueapps": {
                "handlers": ["stdout"],
                "level": log_level,
                "propagate": True,
            },
            # 普通app日志
            "app": {"handlers": ["stdout"], "level": log_level, "propagate": True},
            # 权限中心
            "iam": {"handlers": ["stdout"], "level": log_level, "propagate": True},
        },
    }


def get_logging(
    log_type: str,
    log_level: str,
    bk_log_dir: str,
    is_local: bool,
    bk_backend_config: bool,
    bkapp_is_paas_deploy: bool,
    settings_module: typing.Dict,
) -> typing.Dict:
    if log_type == constants.LogType.STDOUT.value:
        return get_stdout_logging_conf(log_level)

    if bk_backend_config:
        if bkapp_is_paas_deploy:
            return get_paas_logging_conf(settings_module)
        else:
            return get_backend_logging_conf(log_level, bk_log_dir, is_local)
    else:
        return get_paas_logging_conf(settings_module)
