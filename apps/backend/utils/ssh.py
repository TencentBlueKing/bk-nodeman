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

import re
import socket
import time
import traceback
from typing import Any, Callable, Dict, Optional, Tuple

import paramiko
import wrapt
from django.utils.translation import ugettext_lazy as _
from six import StringIO

from apps.backend.constants import (
    MAX_WAIT_OUTPUT,
    RECV_BUFLEN,
    RECV_TIMEOUT,
    SLEEP_INTERVAL,
    SSH_CON_TIMEOUT,
)
from apps.exceptions import AuthOverdueException
from apps.node_man import constants
from apps.node_man.constants import AuthType
from apps.node_man.models import Host, IdentityData
from common.log import logger

"""
ssh登录与命令交互功能单元
"""

# public symbols
__all__ = ["ssh_login", "SshMan"]

# 去掉回车、空格、颜色码
CLEAR_CONSOLE_RE = re.compile(r"\\u001b\[\D|\[\d{1,2}\D?|\\u001b\[\d{1,2}\D?~?|\r|\n|\s+", re.I | re.U)
# 去掉其他杂项
CLEAR_MISC_RE = re.compile(r"\$.?\[\D", re.I | re.U)
# 换行转换
LINE_BREAK_RE = re.compile(r"\r\n|\r|\n", re.I | re.U)


class NotExceptSSHException(Exception):
    """
    未捕获的SSH异常
    """


def get_logger(_logger=None):
    if not _logger:
        return logger
    return _logger


def ssh_login(
    ip,
    port,
    auth_type,
    account="root",
    password=None,
    key=None,
    timeout=SSH_CON_TIMEOUT,
    _logger=None,
) -> paramiko.SSHClient:
    """
    使用ssh登录
    :param _logger:
    :param ip: IP地址
    :param port: 端口
    :param auth_type: 认证方式
    :param account: 账号
    :param password: 密码
    :param key: 密钥
    :param timeout: 超时时间
    :return: ssh
    """
    _logger = get_logger(_logger)

    ssh = None

    try:
        _logger.info("[%s]create ssh client" % ip)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 密钥认证
        if auth_type == AuthType.KEY:

            key_file = StringIO(key)

            # 尝试rsa登录
            key_type = "r"
            try:
                pkey = paramiko.RSAKey.from_private_key(key_file)
            except paramiko.PasswordRequiredException:
                _logger.error("【%s】RSAKey need password!" % ip)
                pkey = paramiko.RSAKey.from_private_key(key_file, password)

            # 尝试dsa登录
            except paramiko.SSHException:
                key_type = "d"
                try:
                    pkey = paramiko.DSSKey.from_private_key(key_file)
                except paramiko.PasswordRequiredException:
                    _logger.info("【%s】DSAKey need password!" % ip)
                    pkey = paramiko.DSSKey.from_private_key(key_file, password)

            _logger.info(
                "【{}】: login by {}sa key, hostname={}, username={}, port={}".format(ip, key_type, ip, account, port)
            )
            ssh.connect(
                hostname=ip,
                username=account,
                port=port,
                pkey=pkey,
                timeout=timeout,
                allow_agent=False,
                look_for_keys=False,
                banner_timeout=timeout,
            )

        # 密码认证
        elif auth_type in [AuthType.PASSWORD, AuthType.TJJ_PASSWORD]:
            ssh.connect(
                ip,
                port,
                account,
                password,
                timeout=timeout,
                allow_agent=False,
                look_for_keys=False,
                banner_timeout=timeout,
            )
        else:
            msg = "SSH authentication method not supported. {}:({})".format(ip, auth_type)
            _logger.error(msg)
            raise Exception(msg)  # 不支持的认证方式

    except paramiko.BadAuthenticationType:
        try:
            #  SSH AUTH WITH PAM
            def handler(title, instructions, fields):
                resp = []

                if len(fields) > 1:
                    raise paramiko.SSHException("Fallback authentication failed.")

                if len(fields) == 0:
                    # for some reason, at least on os x, a 2nd request will
                    # be made with zero fields requested.  maybe it's just
                    # to try to fake out automated scripting of the exact
                    # type we're doing here.  *shrug* :)
                    return resp

                for pr in fields:
                    if pr[0].strip() == "Username:":
                        resp.append(account)
                    elif pr[0].strip() == "Password:":
                        resp.append(password)

                _logger.error("SSH auth with interactive: %s" % resp)

                return resp

            ssh_transport = ssh.get_transport()
            if ssh_transport is None:
                _logger.error("get_transport is None")
                ssh_transport = paramiko.Transport((ip, port))

            try:
                ssh_transport = paramiko.Transport((ip, port))
                ssh._transport = ssh_transport
                ssh_transport.start_client()
            except Exception as e:
                _logger.error(e)

            ssh_transport.auth_interactive(account, handler)

            return ssh

        except paramiko.BadAuthenticationType as e:
            SshMan.safe_close(ssh)
            msg = "{}, {}".format(e, _("认证方式错误或不支持，请确认。"))
            _logger.error(msg)
            raise e  # 认证方式错误或不支持

        except paramiko.SSHException as e:
            _logger.error("attempt failed; just raise the original exception")
            raise e

    except paramiko.BadHostKeyException as e:
        SshMan.safe_close(ssh)
        msg = "SSH authentication key could not be verified.- {}@{}:{} - exception: {}".format(account, ip, port, e)
        msg = "{}, {}".format(msg, _("HostKey校验失败，请尝试删除 /root/.ssh/known_hosts 再重试"))
        _logger.error(msg)
        raise e  # Host Key 验证错误
    except paramiko.AuthenticationException as e:
        SshMan.safe_close(ssh)
        msg = "SSH authentication failed.- {}@{}:{} - exception: {}".format(
            account,
            ip,
            port,
            e,
        )
        msg = "{}, {}".format(msg, _("登录认证失败，请确认账号，密码，密钥或IP是否正确。"))
        _logger.error(msg)
        raise e  # 密码错或者用户错(Authentication failed)
    except paramiko.SSHException as e:
        SshMan.safe_close(ssh)
        msg = "SSH connect failed.- {}@{}:{} - exception: {}".format(account, ip, port, e)
        msg = "{}, {}".format(msg, _("ssh登录，请确认IP是否正确或目标机器是否可被正常登录。"))
        _logger.error(msg)
        raise NotExceptSSHException  # 登录失败，原因可能有not a valid RSA private key file
    except socket.error as e:
        SshMan.safe_close(ssh)
        msg = "TCP connect failed, timeout({}) - {}@{}:{}".format(e, account, ip, port)
        msg = "{}, {}".format(msg, _("ssh登录连接超时，请确认IP是否正确或ssh端口号是否正确或网络策略是否正确开通。"))
        _logger.error(msg)
        raise e  # 超时
    else:
        return ssh


class Inspector(object):
    """
    关键字处理，捕捉ssh及脚本相关输出并判定
    """

    @staticmethod
    def clear(s):
        """
        过滤console输出，回车、空格、颜色码等
        """

        try:
            # 尝试clear，出现异常（编码错误）则返回原始字符串
            _s = CLEAR_CONSOLE_RE.sub("", s)
            _s = CLEAR_MISC_RE.sub("$", _s)
        except Exception as e:
            _s = s
            logger.error("clear(Exception):%s" % e)
        if isinstance(_s, bytes):
            _s = str(_s, encoding="utf-8")
        return _s

    @staticmethod
    def clear_cmd_and_prompt(output, cmd, prompt):
        """
        过滤输出中带的原始输入命令和终端提示符
        """
        for clear_char in [" \r", "\r", cmd, prompt, "\n"]:
            output = output.replace(clear_char, "")
        return output

    @staticmethod
    def clear_yes_or_no(s):
        return s.replace("yes/no", "").replace("'yes'or'no':", "")

    def is_wait_password_input(self, buff):
        buff = self.clear(buff)
        return buff.endswith("assword:") or buff.endswith("Password:")

    def is_too_open(self, buff):
        buff = self.clear(buff)
        return buff.find("tooopen") != -1 or buff.find("ignorekey") != -1

    def is_permission_denied(self, buff):
        buff = self.clear(buff)
        return buff.find("Permissiondenied") != -1

    def is_public_key_denied(self, buff):
        buff = self.clear(buff)
        return buff.find("Permissiondenied(publickey") != -1

    def is_invalid_key(self, buff):
        buff = self.clear(buff)
        return buff.find("passphraseforkey") != -1

    def is_timeout(self, buff):
        buff = self.clear(buff)
        return (
            buff.find("lostconnectinfo") != -1
            or buff.find("Noroutetohost") != -1
            or buff.find("Connectiontimedout") != -1
            or buff.find("Connectiontimeout") != -1
        )

    def is_key_login_required(self, buff):
        buff = self.clear(buff)
        return not buff.find("publickey,gssapi-keyex,gssapi-with-mic") == -1

    def is_refused(self, buff):
        buff = self.clear(buff)
        return not buff.find("Connectionrefused") == -1

    def is_fingerprint(self, buff):
        buff = self.clear(buff)
        return not buff.find("fingerprint:") == -1

    def is_wait_known_hosts_add(self, buff):
        buff = self.clear(buff)
        return not buff.find("tothelistofknownhosts") == -1

    def is_yes_input(self, buff):
        buff = self.clear(buff)
        return not buff.find("yes/no") == -1 or not buff.find("'yes'or'no':") == -1

    def is_console_ready(self, buff):
        buff = self.clear(buff)
        return buff.endswith("#") or buff.endswith("$") or buff.endswith(">")

    def has_lastlogin(self, buff):
        buff = self.clear(buff)
        return buff.find("Lastlogin") != -1

    def is_no_such_file(self, buff):
        buff = self.clear(buff)
        return not buff.find("Nosuchfileordirectory") == -1

    def is_cmd_not_found(self, buff):
        buff = self.clear(buff)
        return not buff.find("Commandnotfound") == -1

    def is_transported_ok(self, buff):
        buff = self.clear(buff)
        return buff.find("100%") != -1

    def is_curl_failed(self, buff):
        _buff = buff.lower()
        return (
            _buff.find("failedconnectto") != -1
            or _buff.find("connectiontimedout") != -1
            or _buff.find("couldnotreso") != -1
            or _buff.find("connectionrefused") != -1
            or _buff.find("couldn'tconnect") != -1
            or _buff.find("sockettimeout") != -1
            or _buff.find("notinstalled") != -1
            or _buff.find("error") != -1
            or _buff.find("resolvehost") != -1
        )

    # 脚本输出解析方式
    def is_setup_done(self, buff):
        return buff.find("setup done") != -1 and buff.find("install_success") != -1

    def is_setup_failed(self, buff):
        return buff.find("setup failed") != -1

    def parse_err_msg(self, buff):
        return re.split(":|--", buff)[1]
        # return buff.split('--')[1]

    def is_cmd_started_on_aix(self, cmd, output):
        """
        在aix机器上，输出命令的显示返回的下划线会包含特殊字符在下划线前。此方法用字母类子串来判断。
        :param cmd:
        :param output:
        :return:
        """
        cmd_chars = "".join(c for c in cmd if c.isalpha())
        output_chars = "".join(c for c in output if c.isalpha())
        is_common_substring = re.search(r"\w*".join(list(cmd_chars)), output_chars)
        return is_common_substring or (cmd_chars in output_chars) or (cmd_chars.startswith(output_chars))


# 状态检测
inspector = Inspector()


@wrapt.decorator
def ssh_man_exception_handler(wrapped: Callable, instance: Optional[object], args: Tuple[Any], kwargs: Dict[str, Any]):
    """
    捕获 SshMan 类方法的异常，尝试释放连接，减少占用IO资源
    :param wrapped: 被装饰的函数或类方法
    :param instance:
        - 如果被装饰者为普通类方法，该值为类实例
        - 如果被装饰者为 classmethod / 类方法，该值为类
        - 如果被装饰者为类/函数/静态方法，该值为 None
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return:
    """
    try:
        return wrapped(*args, **kwargs)
    except Exception:
        if instance:
            instance.safe_close(getattr(instance, "ssh"))
        raise


class SshMan(object):
    """
    SshMan，负责SSH终端命令交互
    """

    def __init__(self, host: Host, log, identity_data: Optional[IdentityData] = None):
        self.set_proxy_prompt = r'export PS1="[\u@\h_BKproxy \W]\$"'

        # 初始化ssh会话
        if host.node_type == constants.NodeType.PROXY:
            ip = host.login_ip or host.outer_ip
        else:
            ip = host.login_ip or host.inner_ip
        identity_data = identity_data or host.identity
        if (identity_data.auth_type == AuthType.PASSWORD and not identity_data.password) or (
            identity_data.auth_type == AuthType.KEY and not identity_data.key
        ):
            log.info(_("认证信息已过期, 请重装并填入认证信息"))
            raise AuthOverdueException

        # 重试解决 No existing session 问题
        retry_times = 5
        for try_time in range(retry_times):
            try:
                self.ssh = ssh_login(
                    ip,
                    identity_data.port,
                    identity_data.auth_type,
                    identity_data.account,
                    identity_data.password,
                    identity_data.key,
                    _logger=log,
                )
            except (NotExceptSSHException, EOFError) as e:
                if try_time < retry_times:
                    time.sleep(1)
                    continue
                else:
                    log.error(str(e))
                    raise e
            else:
                break
        self.account = identity_data.account
        self.password = identity_data.password
        self.chan = self.ssh.invoke_shell()
        self.log = log
        self.setup_channel()

    def setup_channel(self, blocking=0, timeout=-1):
        """
        # settimeout(0) -> setblocking(0)
        # settimeout(None) -> setblocking(1)
        """
        # set socket read time out
        self.chan.setblocking(blocking=bool(blocking))
        timeout = RECV_TIMEOUT if timeout < 0 else timeout
        self.chan.settimeout(timeout=timeout)

    @ssh_man_exception_handler
    def send_cmd(
        self,
        cmd,
        wait_console_ready=True,
        is_adding_output=False,
        is_clear_cmd_and_prompt=True,
        check_output=True,
    ):
        """
        用指定账户user发送命令cmd
        check_output: 是否需要从output中分析异常
        """
        # 根据用户名判断是否采用sudo
        is_root = True
        if self.account not in ["root", "Administrator"]:
            is_root = False
            cmd = "sudo %s" % cmd
            self.log.info("current account is {}, please confirm your [sudo] privileges".format(self.account))

        # 增加回车符
        cmd = cmd if cmd.endswith("\n") else "%s\n" % cmd

        # 发送命令并等待结束
        cmd_cleared = inspector.clear(cmd)
        self.chan.sendall(cmd)
        self.wait_for_output()
        # self.log.info('start cmd: %s' % cmd)
        # self.log.info('waiting for cmd finished.')

        cmd_sent = False
        recv_output = ""
        while True:
            # self.log.info(time.time())
            time.sleep(SLEEP_INTERVAL)
            try:
                try:
                    chan_recv = str(self.chan.recv(RECV_BUFLEN), encoding="utf-8")
                except UnicodeDecodeError:
                    chan_recv = str(self.chan.recv(RECV_BUFLEN))
                if is_adding_output:
                    # Windows collect log can not get the command running if using the clear_cmd_and_prompt method
                    recv_output += chan_recv
                    output = recv_output
                else:
                    recv_output = chan_recv
                    if is_clear_cmd_and_prompt:
                        if not is_root and inspector.clear(recv_output).endswith(f"passwordfor{self.account}:"):
                            output = recv_output
                        else:
                            output = inspector.clear_cmd_and_prompt(recv_output, cmd, self.get_prompt(origin=True))
                    else:
                        # Linux pagent collect log will hang in this loop if use the inspector.clear_cmd_and_prompt
                        output = recv_output
                # 剔除空格、回车和换行
                _output = inspector.clear(recv_output)
                self.log.info(output)

            except socket.timeout:
                raise socket.timeout(f"recv socket timeout after {RECV_TIMEOUT} seconds")
            except Exception as e:
                raise Exception(f"recv exception: {e}")

            if _output.find("sudo:notfound") != -1:
                cmd = cmd[len("sudo ") :]
                self.log.info("do not support sudo, run cmd [%s]" % cmd, "info")
                self.chan.sendall(cmd)

            # [sudo] password for vagrant:
            if check_output and _output.endswith(f"passwordfor{self.account}:"):
                if not cmd_sent:
                    cmd_sent = True
                    self.chan.sendall(self.password + "\n")
                    time.sleep(SLEEP_INTERVAL)
                else:
                    raise Exception(f"password error，sudo failed: {output}")
            elif check_output and (_output.find("tryagain") != -1 or _output.find("incorrectpassword") != -1):
                if cmd_sent:
                    raise Exception(f"password error，sudo failed: {output}")
            elif not wait_console_ready:
                # self.log.info('no need to wait cmd run over.')
                return output
            elif check_output and inspector.is_curl_failed(_output):
                self.log.error("curl failed")
                raise Exception(f"curl failed: {output}")
            elif check_output and inspector.is_no_such_file(_output):
                raise Exception(f"no such file: {output}")
            elif inspector.is_console_ready(_output):
                return output
            elif _output.find(cmd_cleared) != -1 or cmd_cleared.startswith(_output):
                continue
            # elif inspector.is_cmd_started_on_aix(cmd_cleared, _output):
            #     continue

    def get_and_set_prompt(self):
        """
        尝试设置并获取终端提示符
        """

        prompt = ""
        try:
            self.set_prompt(self.set_proxy_prompt)

            prompt = self.get_prompt()
            is_prompt_set = True
        except Exception as e:
            stack_info = "".join(traceback.format_stack())
            self.log.error("get_and_set_prompt: error={}, stack={}".format(e, stack_info))
            is_prompt_set = False

        return is_prompt_set, prompt

    def wait_for_output(self):
        """
        等待通道标准输出可读，重试32次
        """

        cnt = 0
        while not self.chan.recv_ready():
            time.sleep(SLEEP_INTERVAL)
            cnt += 1
            if cnt > MAX_WAIT_OUTPUT:  # 32
                break

    def get_prompt(self, origin=False):
        """
        尝试获取终端提示符
        """

        self.chan.sendall("\n")

        while True:
            time.sleep(SLEEP_INTERVAL)
            res = str(self.chan.recv(RECV_BUFLEN), encoding="utf-8")
            if origin:
                buff = res
            else:
                buff = inspector.clear(res)
            if inspector.is_console_ready(buff):
                prompt = LINE_BREAK_RE.split(buff)[-1]
                break
        return prompt

    def set_prompt(self, cmd=None):
        """
        尝试设置新的终端提示符
        """
        if cmd is None:
            cmd = self.set_proxy_prompt

        self.chan.sendall(cmd + "\n")
        while True:
            time.sleep(0.3)
            res = self.chan.recv(RECV_BUFLEN)
            buff = inspector.clear(res)
            # self.log.info(buff)
            if buff.find("BKproxy") != -1:
                break

    @staticmethod
    def safe_close(ssh_or_chan):
        """
        安全关闭ssh连接或会话
        """

        try:
            if ssh_or_chan:
                ssh_or_chan.close()
        except Exception:
            pass
