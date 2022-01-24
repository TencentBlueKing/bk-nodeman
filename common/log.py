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

import logging

from apps.utils.local import get_request_id

"""
Usage:

    from common.log import logger

    logger.info("test")
    logger.error("wrong1")
    logger.exception("wrong2")

    # with traceback
    try:
        1 / 0
    except Exception:
        logger.exception("wrong3")
"""
logger_detail = logging.getLogger("root")


# ===============================================================================
# 自定义添加打印内容
# ===============================================================================
# traceback--打印详细错误日志
class logger_traceback:
    """
    详细异常信息追踪
    """

    def __init__(self):
        pass

    def error(self, message=""):
        """
        打印 error 日志方法
        """
        message = self.build_message(message)
        logger_detail.error(message)

    def info(self, message=""):
        """
        info 日志
        """
        message = self.build_message(message)
        logger_detail.info(message)

    def warning(self, message=""):
        """
        warning 日志
        """
        message = self.build_message(message)
        logger_detail.warning(message)

    def debug(self, message=""):
        """
        debug 日志
        """
        message = self.build_message(message)
        logger_detail.debug(message)

    def critical(self, message=""):
        """
        critical 日志
        """
        message = self.build_message(message)
        logger_detail.critical(message)

    def exception(self, message="", *args):
        message = self.build_message(message)
        logger_detail.exception(message, *args)

    @staticmethod
    def build_message(message):
        request_id = get_request_id()
        return "%s | %s" % (request_id, message)


# traceback--打印详细错误日志
logger = logger_traceback()
