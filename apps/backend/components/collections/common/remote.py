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
import traceback
import typing
from abc import ABC
from collections import defaultdict
from enum import Enum

from asgiref.sync import sync_to_async
from django.utils.translation import ugettext_lazy as _

from apps.backend import constants as backend_constants
from apps.core.concurrent import controller
from apps.core.remote import conns, core_remote_exceptions
from apps.node_man import constants, models
from apps.utils import concurrent, enum, exc
from apps.utils.cache import class_member_cache

from .. import base, core


class SshCheckResultType(enum.EnhanceEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    AVAILABLE_BUT_RAISE_EXC = "AVAILABLE_BUT_RAISE_EXC"

    @classmethod
    def _get_member__alias_map(cls) -> typing.Dict[Enum, str]:
        return {
            cls.AVAILABLE: _("SSH通道可用"),
            cls.AVAILABLE_BUT_RAISE_EXC: _("SSH通道可用但登录信息有误"),
            cls.UNAVAILABLE: _("SSH通道不可用"),
        }


class RemoteConnHelper:
    """远程连接公共逻辑"""

    sub_inst_id: int = None
    host: models.Host = None
    identity_data: models.IdentityData = None

    def __init__(self, sub_inst_id: int, host: models.Host, identity_data: models.IdentityData):
        self.sub_inst_id = sub_inst_id
        self.host = host
        self.identity_data = identity_data

    @property
    @class_member_cache()
    def conns_init_params(self) -> typing.Dict:
        """
        构造连接初始化参数
        :return:
        """
        if self.host.node_type == constants.NodeType.PROXY:
            ip = self.host.login_ip or self.host.outer_ip
        else:
            ip = self.host.login_ip or self.host.inner_ip

        client_key_strings = []
        if self.identity_data.auth_type == constants.AuthType.KEY:
            client_key_strings.append(self.identity_data.key)

        return dict(
            host=ip,
            port=self.identity_data.port,
            username=self.identity_data.account,
            password=self.identity_data.password,
            client_key_strings=client_key_strings,
            connect_timeout=backend_constants.SSH_CON_TIMEOUT,
        )


RemoteConnHelperT = typing.TypeVar("RemoteConnHelperT", bound=RemoteConnHelper)


def sub_inst_task_exc_handler(
    wrapped: typing.Callable,
    instance: base.BaseService,
    args: typing.Tuple[typing.Any],
    kwargs: typing.Dict[str, typing.Any],
    exception: Exception,
) -> typing.Any:
    if args:
        remote_conn_helper: RemoteConnHelperT = args[0]
    else:
        remote_conn_helper: RemoteConnHelperT = kwargs["remote_conn_helper"]
    sub_inst_id = remote_conn_helper.sub_inst_id
    instance.move_insts_to_failed([sub_inst_id], str(exception))
    # 打印 DEBUG 日志
    instance.log_debug(sub_inst_id, log_content=traceback.format_exc(), fold=True)
    return None


class RemoteServiceMixin(base.BaseService, ABC):
    @exc.ExceptionHandler(exc_handler=sub_inst_task_exc_handler)
    async def check_ssh(
        self, remote_conn_helper: RemoteConnHelperT
    ) -> typing.Dict[str, typing.Union[str, RemoteConnHelperT]]:
        """
        检测 SSH 通道是否可用
        :param remote_conn_helper:
        :return:
        """
        check_result = {"remote_conn_helper": remote_conn_helper, "type": SshCheckResultType.AVAILABLE.value}
        try:
            async with conns.AsyncsshConn(**remote_conn_helper.conns_init_params):
                pass
        except (core_remote_exceptions.DisconnectError, core_remote_exceptions.ConnectionLostError):
            # 抛出以上异常表示 SSH 通道不可用
            check_result["type"] = SshCheckResultType.UNAVAILABLE.value
        except Exception as exception:
            # 其他异常表示 SSH 可用，但出现认证错误等问题
            check_result.update(type=SshCheckResultType.AVAILABLE_BUT_RAISE_EXC.value, exc=exception)
            await sync_to_async(self.move_insts_to_failed)(
                sub_inst_ids=remote_conn_helper.sub_inst_id, log_content=exception
            )
        return check_result

    async def sudo_prompt(self, remote_conn_helper: RemoteConnHelperT):
        log_warning = sync_to_async(self.log_warning)
        if remote_conn_helper.identity_data.account not in [constants.LINUX_ACCOUNT, constants.WINDOWS_ACCOUNT]:
            await log_warning(
                remote_conn_helper.sub_inst_id,
                log_content=_("当前登录用户为「{account}」，请确保该用户具有 sudo 权限").format(
                    account=remote_conn_helper.identity_data.account
                ),
            )

    @controller.ConcurrentController(
        data_list_name="remote_conn_helpers",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.SSH.value},
    )
    def _bulk_check_ssh(
        self, remote_conn_helpers: typing.List[RemoteConnHelperT]
    ) -> typing.List[typing.Dict[str, typing.Union[str, RemoteConnHelperT]]]:
        params_list = [{"remote_conn_helper": remote_conn_helper} for remote_conn_helper in remote_conn_helpers]
        return concurrent.batch_call_coroutine(func=self.check_ssh, params_list=params_list)

    def bulk_check_ssh(
        self, remote_conn_helpers: typing.List[RemoteConnHelperT]
    ) -> typing.Dict[str, typing.List[RemoteConnHelperT]]:
        check_results = self._bulk_check_ssh(remote_conn_helpers=remote_conn_helpers)
        remote_conn_helpers_gby_result_type: typing.Dict[str, typing.List[RemoteConnHelper]] = defaultdict(list)
        for check_result in check_results:
            if not check_result:
                continue
            remote_conn_helpers_gby_result_type[check_result["type"]].append(check_result["remote_conn_helper"])
        return remote_conn_helpers_gby_result_type
