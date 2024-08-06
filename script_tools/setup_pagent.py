#!/opt/py36/bin/python
# -*- encoding:utf-8 -*-
# vim:ft=python sts=4 sw=4 expandtab nu

from __future__ import print_function

import abc
import argparse
import base64
import hashlib
import ipaddress
import json
import logging
import os
import re
import socket
import sys
import time
import traceback
import typing
from functools import partial
from io import StringIO
from pathlib import Path
from subprocess import Popen
from typing import Any, Callable, Dict, List, Optional, Union


def arg_parser() -> argparse.ArgumentParser:
    """Commandline argument parser"""
    parser = argparse.ArgumentParser(description="p-agent setup scripts")
    parser.add_argument("-f", "--config", type=str, help="a file contain p-agent hosts info")
    parser.add_argument(
        "-j",
        "--json",
        type=str,
        help="a file contain p-agent hosts info in json format",
    )
    parser.add_argument("-I", "--lan-eth-ip", type=str, help="local ip address of proxy")
    parser.add_argument(
        "-l",
        "--download-url",
        type=str,
        help="a url for downloading gse agent packages (without filename)",
    )
    parser.add_argument("-s", "--task-id", type=str, help="task id generated by nodeman, optional")
    parser.add_argument("-r", "--callback-url", type=str, help="api for report step and task status")
    parser.add_argument("-c", "--token", type=str, help="token for request callback api")
    parser.add_argument(
        "-T",
        "--temp-dir",
        action="store_true",
        default=False,
        help="directory to save downloaded scripts and temporary files",
    )
    parser.add_argument("-L", "--download-path", type=str, help="Tool kit storage path")

    # 主机信息
    parser.add_argument("-HLIP", "--host-login-ip", type=str, help="Host Login IP")
    parser.add_argument("-HIIP", "--host-inner-ip", type=str, help="Host Inner IP")
    parser.add_argument("-HA", "--host-account", type=str, help="Host Account")
    parser.add_argument("-HP", "--host-port", type=str, help="Host Port")
    parser.add_argument("-HI", "--host-identity", type=str, help="Host Identity")
    parser.add_argument("-HAT", "--host-auth-type", type=str, help="Host Auth Type")
    parser.add_argument("-HC", "--host-cloud", type=str, help="Host Cloud")
    parser.add_argument("-HNT", "--host-node-type", type=str, help="Host Node Type")
    parser.add_argument("-HOT", "--host-os-type", type=str, help="Host Os Type")
    parser.add_argument("-HDD", "--host-dest-dir", type=str, help="Host Dest Dir")
    parser.add_argument("-HPP", "--host-proxy-port", type=int, default=17981, help="Host Proxy Port")
    parser.add_argument("-CPA", "--channel-proxy-address", type=str, help="Channel Proxy Address", default=None)

    parser.add_argument("-HSJB", "--host-solutions-json-b64", type=str, help="Channel Proxy Address", default=None)
    return parser


args = arg_parser().parse_args(sys.argv[1:])

try:
    # import 3rd party libraries here, in case the python interpreter does not have them
    import paramiko  # noqa
    import requests  # noqa

    import impacket  # noqa

    # import psutil

except ImportError as err:
    from urllib import request

    _query_params = json.dumps(
        {
            "task_id": args.task_id,
            "token": args.token,
            "logs": [
                {
                    "timestamp": round(time.time()),
                    "level": "ERROR",
                    "step": "import_3rd_libs",
                    "log": str(err),
                    "status": "FAILED",
                    "prefix": "[proxy]",
                }
            ],
        }
    ).encode()

    req = request.Request(
        f"{args.callback_url}/report_log/",
        data=_query_params,
        headers={"Content-Type": "application/json"},
    )
    request.urlopen(req)
    exit()


# 自定义日志处理器
class ReportLogHandler(logging.Handler):
    def __init__(self, report_log_url):
        super().__init__()
        self._report_log_url = report_log_url

    def emit(self, record):

        is_report: bool = getattr(record, "is_report", False)

        if not is_report:
            return

        status: str = ("-", "FAILED")[record.levelname == "ERROR"]
        query_params = {
            "task_id": args.task_id,
            "token": args.token,
            "logs": [
                {
                    "timestamp": round(time.time()),
                    "level": record.levelname,
                    "step": record.step,
                    "metrics": record.metrics,
                    "log": f"({status}) {record.message}",
                    "status": status,
                    "prefix": "[proxy]",
                }
            ],
        }
        if args.channel_proxy_address:
            proxy_address = {
                "http": args.channel_proxy_address,
                "https": args.channel_proxy_address,
            }
            requests.post(self._report_log_url, json=query_params, proxies=proxy_address)
        else:
            requests.post(self._report_log_url, json=query_params)


class CustomLogger(logging.LoggerAdapter):
    def _log(self, level, msg, *args, extra=None, **kwargs):
        if extra is None:
            extra = {}

        step: str = extra.pop("step", "N/A")
        is_report: str = extra.pop("is_report", True)
        metrics: typing.Dict[str, typing.Any] = extra.pop("metrics", {})
        kwargs = {"step": step, "is_report": is_report, "metrics": metrics}
        kwargs.update(extra)

        super()._log(level, msg, args, extra=kwargs)

    def logging(
        self,
        step: str,
        msg: str,
        metrics: typing.Optional[typing.Dict[str, typing.Any]] = None,
        level: int = logging.INFO,
        is_report: bool = True,
    ):
        self._log(level, msg, extra={"step": step, "is_report": is_report, "metrics": metrics or {}})


console_handler = logging.StreamHandler()
console_handler.stream = os.fdopen(sys.stdout.fileno(), "w", 1)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[console_handler, ReportLogHandler(f"{args.callback_url}/report_log/")],
)

logger = CustomLogger(logging.getLogger(), {})


# 默认的连接最长等待时间
DEFAULT_CONNECT_TIMEOUT = 30

# 默认的命令执行最长等待时间
DEFAULT_CMD_RUN_TIMEOUT = 30

DEFAULT_HTTP_PROXY_SERVER_PORT = args.host_proxy_port

JOB_PRIVATE_KEY_RE = re.compile(r"^(-{5}BEGIN .*? PRIVATE KEY-{5})(.*?)(-{5}END .*? PRIVATE KEY-{5}.?)$")

POWERSHELL_SERVICE_CHECK_SSHD = "powershell -c Get-Service -Name sshd"


def is_ip(ip: str, _version: Optional[int] = None) -> bool:
    """
    判断是否为合法 IP
    :param ip:
    :param _version: 是否为合法版本，缺省表示 both
    :return:
    """
    try:
        ip_address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if _version is None:
        return True
    return ip_address.version == _version


# 判断是否为合法 IPv6
is_v6 = partial(is_ip, _version=6)

# 判断是否为合法 IPv4
is_v4 = partial(is_ip, _version=4)


class DownloadFileError(Exception):
    """文件"""

    pass


def json_b64_decode(json_b64: str) -> Any:
    """
    base64(json_str) to python type
    :param json_b64:
    :return:
    """
    return json.loads(base64.b64decode(json_b64.encode()).decode())


def execute_cmd(
    cmd_str,
    ipaddr,
    username,
    password,
    domain="",
    share="ADMIN$",
    is_no_output=False,
):
    """execute command"""
    try:
        from wmiexec import WMIEXEC
    except ImportError:
        # WMI 执行文件不存在，从下载源同步
        # wmiexec 是下载到脚本执行目录下，不属于回环
        download_file(f"{args.download_url}/wmiexec.py", str(Path(__file__).parent), skip_lo_check=True)
        from wmiexec import WMIEXEC

    executor = WMIEXEC(cmd_str, username, password, domain, share=share, noOutput=is_no_output)
    result_data = executor.run(ipaddr)
    return {"result": True, "data": result_data}


def execute_batch_solution(
    login_ip: str,
    account: str,
    identity: str,
    tmp_dir: str,
    execution_solution: Dict[str, Any],
):
    if os.path.isfile(identity):
        logger.logging(
            step="execute_batch_solution",
            msg="identity seems like a key file, which is not supported by windows authentication",
            level=logging.ERROR,
        )

        return False

    for step in execution_solution["steps"]:
        for content in step["contents"]:
            if step["type"] == "dependencies":
                download_path: str = args.download_path
                if content.get("child_dir"):
                    download_path = os.path.join(download_path, content["child_dir"])
                localpath = os.path.join(download_path, content["name"])
                # 文件不存在，从下载源同步
                if not os.path.exists(localpath) or content.get("always_download"):
                    logger.logging(
                        "execute_batch_solution", f"file -> {content['name']} not exists, sync from {content['text']}"
                    )
                    download_file(content["text"], download_path)

                # 构造文件推送命令
                cmd: str = "put {localpath} {tmp_dir}".format(localpath=localpath, tmp_dir=tmp_dir)
            elif step["type"] == "commands":
                cmd: str = content["text"]
            else:
                logger.logging("execute_batch_solution", f"unknown step type -> {step['type']}")
                continue

            logger.logging("send_cmd", cmd)

            try:
                res = execute_cmd(cmd, login_ip, account, identity, is_no_output=content["name"] == "run_cmd")
            except Exception:
                # 过程中只要有一条命令执行失败，视为执行方案失败
                logger.logging("execute_batch_solution", f"execute {cmd} failed", level=logging.WARNING)
                # 把异常抛给最外层
                raise

            print(res)


def convert_shell_to_powershell(shell_cmd):
    # Convert mkdir -p xxx to if not exist xxx mkdir xxx
    shell_cmd = re.sub(
        r"mkdir -p\s+(\S+)",
        r"if (-Not (Test-Path -Path \1)) { New-Item -ItemType Directory -Path \1 }",
        shell_cmd,
    )

    # Convert chmod +x xxx to ''
    shell_cmd = re.sub(r"chmod\s+\+x\s+\S+", r"", shell_cmd)

    # Convert curl to Invoke-WebRequest
    # shell_cmd = re.sub(
    #     r"curl\s+(http[s]?:\/\/[^\s]+)\s+-o\s+(\/?[^\s]+)\s+--connect-timeout\s+(\d+)\s+-sSfg",
    #     r"Invoke-WebRequest -Uri \1 -OutFile \2 -TimeoutSec \3 -UseBasicParsing",
    #     shell_cmd,
    # )
    shell_cmd = re.sub(r"(curl\s+\S+\s+-o\s+\S+\s+--connect-timeout\s+\d+\s+-sSfg)", r'cmd /c "\1"', shell_cmd)

    # Convert nohup xxx &> ... & to xxx (ignore nohup, output redirection and background execution)
    shell_cmd = re.sub(
        r"nohup\s+([^&>]+)(\s*&>\s*.*?&)?",
        r"Invoke-Command -Session (New-PSSession) -ScriptBlock { \1 } -AsJob",
        shell_cmd,
    )

    # Remove '&>' and everything after it
    shell_cmd = re.sub(r"\s*&>.*", "", shell_cmd)

    # Convert \\ to \
    shell_cmd = shell_cmd.replace("\\\\", "\\")

    shell_cmd = shell_cmd.replace(" & ", ";")

    return shell_cmd.strip()


def execute_shell_solution(
    login_ip: str,
    account: str,
    port: int,
    identity: str,
    auth_type: str,
    os_type: str,
    execution_solution: Dict[str, Any],
):
    client_key_strings: List[str] = []
    if auth_type == "KEY":
        client_key_strings.append(identity)

    with ParamikoConn(
        host=login_ip,
        port=port,
        username=account,
        password=identity,
        client_key_strings=client_key_strings,
        connect_timeout=15,
    ) as conn:
        command_converter = {}
        if os_type == "windows":
            run_output: RunOutput = conn.run(POWERSHELL_SERVICE_CHECK_SSHD, check=True, timeout=30)
            if run_output.exit_status == 0 and "cygwin" not in run_output.stdout.lower():
                for step in execution_solution["steps"]:
                    if step["type"] != "commands":
                        continue
                    for content in step["contents"]:
                        cmd: str = content["text"]
                        command_converter[cmd] = convert_shell_to_powershell(cmd)

        for step in execution_solution["steps"]:
            # 暂不支持 dependencies 等其他步骤类型
            if step["type"] != "commands":
                continue
            for content in step["contents"]:
                cmd: str = command_converter.get(content["text"], content["text"])
                if not cmd:
                    continue

                # 根据用户名判断是否采用sudo
                if account not in ["root", "Administrator", "administrator"] and not cmd.startswith("sudo"):
                    cmd = "sudo %s" % cmd

                if content["name"] == "run_cmd":
                    logger.logging("send_cmd", cmd, is_report=True)
                else:
                    logger.logging("send_cmd", cmd, is_report=False)
                run_output: RunOutput = conn.run(cmd, check=True, timeout=30)
                if run_output.exit_status != 0:
                    raise ProcessError(f"Command returned non-zero: {run_output}")
                logger.logging("send_cmd", str(run_output), is_report=False)


def is_port_listen(ip: str, port: int) -> bool:
    s = socket.socket((socket.AF_INET, socket.AF_INET6)[is_v6(ip)], socket.SOCK_STREAM)
    r = s.connect_ex((ip, port))

    if r == 0:
        return True
    else:
        return False


def start_http_proxy(ip: str, port: int) -> Any:
    if is_port_listen(ip, port):
        logger.logging("start_http_proxy", "http proxy exists", is_report=False)
    else:
        Popen("/opt/nginx-portable/nginx-portable restart", shell=True)

        time.sleep(5)
        if is_port_listen(ip, port):
            logger.logging("start_http_proxy", "http proxy started")
        else:
            logger.logging("start_http_proxy", "http proxy start failed", level=logging.ERROR)
            raise Exception("http proxy start failed.")


def json_parser(json_file: str) -> List:
    """Resolve formatted lines to object from config file"""

    configs = []

    with open(json_file, "r", encoding="utf-8") as f:
        hosts = json.loads(f.read())
        for host in hosts:
            configs.append(tuple(host))
    return configs


def download_file(url: str, dest_dir: str, skip_lo_check: bool = False):
    """get files via http"""
    try:
        # 创建下载目录
        os.makedirs(dest_dir, exist_ok=True)
        local_filename = url.split("/")[-1]
        # NOTE the stream=True parameter below
        local_file = os.path.join(dest_dir, local_filename)

        if os.path.exists(local_file):
            # 如果修改时间临近，跳过下载，避免多个 setup 脚本文件互相覆盖
            mtimestamp: float = os.path.getmtime(local_file)
            if time.time() - mtimestamp < 10:
                logger.logging(
                    "download_file", f"File download skipped due to sync time approaching, mtimestamp -> {mtimestamp}"
                )
                return

        if args.lan_eth_ip in url and not skip_lo_check:
            logger.logging("download_file", "File download skipped due to lo ip")
            return

        r = requests.get(url, stream=True)
        r.raise_for_status()

        # 先下载到临时文件夹，再通过 os.replace 命名到目标文件路径，通过该方式防止同一时间多同步任务相互干扰，确保文件操作原子性
        # Refer: https://stackoverflow.com/questions/2333872/
        local_tmp_file = os.path.join(
            dest_dir, local_filename + "." + hashlib.md5(args.token.encode("utf-8")).hexdigest()
        )
        with open(str(local_tmp_file), "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                # filter out keep-alive new chunks
                if chunk:
                    f.write(chunk)

        os.replace(local_tmp_file, local_file)

    except Exception as exc:
        err_msg: str = f"download file from {url} to {dest_dir} failed: {str(exc)}"
        logger.logging("download_file", err_msg, level=logging.WARNING)
        raise DownloadFileError(err_msg) from exc


def use_shell() -> bool:
    os_type: str = args.host_os_type
    port = int(args.host_port)
    if os_type not in ["windows"] or (os_type in ["windows"] and port != 445):
        return True
    else:
        return False


def get_common_labels() -> typing.Dict[str, typing.Any]:
    os_type: str = args.host_os_type or "unknown"
    return {
        "method": ("proxy_wmiexe", "proxy_ssh")[use_shell()],
        "username": args.host_account,
        "port": int(args.host_port),
        "auth_type": args.host_auth_type,
        "os_type": os_type.upper(),
    }


def main() -> None:

    login_ip = args.host_login_ip
    user = args.host_account
    port = int(args.host_port)
    identity = args.host_identity
    auth_type = args.host_auth_type
    os_type = args.host_os_type
    tmp_dir = args.host_dest_dir
    host_solutions_json_b64 = args.host_solutions_json_b64

    host_solutions = json_b64_decode(host_solutions_json_b64)
    type__host_solution_map = {host_solution["type"]: host_solution for host_solution in host_solutions}

    # 启动proxy
    start_http_proxy(args.lan_eth_ip, DEFAULT_HTTP_PROXY_SERVER_PORT)

    if os_type not in ["windows"] or (os_type in ["windows"] and port != 445):
        host_solution = type__host_solution_map["shell"]
        execute_shell_solution(
            login_ip=login_ip,
            account=user,
            port=port,
            auth_type=auth_type,
            identity=identity,
            os_type=os_type,
            execution_solution=host_solution,
        )
    else:
        host_solution = type__host_solution_map["batch"]
        execute_batch_solution(
            login_ip=login_ip,
            account=user,
            identity=identity,
            tmp_dir=tmp_dir,
            execution_solution=host_solution,
        )

    app_core_remote_connects_total_labels = {**get_common_labels(), "status": "success"}
    logger.logging(
        "metrics",
        f"app_core_remote_connects_total_labels -> {app_core_remote_connects_total_labels}",
        metrics={"name": "app_core_remote_connects_total", "labels": app_core_remote_connects_total_labels},
    )


BytesOrStr = Union[str, bytes]


class RemoteBaseException(Exception):
    code = 0


class RunCmdError(RemoteBaseException):
    code = 1


class PermissionDeniedError(RemoteBaseException):
    code = 2


class DisconnectError(RemoteBaseException):
    code = 3


class RemoteTimeoutError(RemoteBaseException):
    code = 4


class ProcessError(RemoteBaseException):
    code = 5


class RunOutput:
    command: str = None
    exit_status: int = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None

    def __init__(self, command: BytesOrStr, exit_status: int, stdout: BytesOrStr, stderr: BytesOrStr):
        self.exit_status = exit_status
        self.command = self.bytes2str(command)
        self.stdout = self.bytes2str(stdout)
        self.stderr = self.bytes2str(stderr)

    @staticmethod
    def bytes2str(val: BytesOrStr) -> str:
        if isinstance(val, bytes):
            try:
                return val.decode(encoding="utf-8")
            except UnicodeDecodeError:
                return val.decode(encoding="gbk")
        return val

    def __str__(self):
        outputs = [
            f"exit_status -> {self.exit_status}",
            f"stdout -> {self.stdout}",
            f"stderr -> {self.stderr}",
        ]
        return "|".join(outputs)


class BaseConn(abc.ABC):
    """连接基类"""

    # 连接地址或域名
    host: str = None
    # 连接端口
    port: int = None
    # 登录用户名
    username: str = None
    # 登录密码
    password: Optional[str] = None
    # 登录密钥
    client_key_strings: Optional[List[str]] = None
    # 连接超时时间
    connect_timeout: Union[int, float] = None
    # 检查器列表，用于输出预处理
    inspectors: List[Callable[["BaseConn", RunOutput], None]] = None
    # 连接参数
    options: Dict[str, Any] = None
    # 连接对象
    _conn: Any = None

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        client_key_strings: Optional[List[str]] = None,
        connect_timeout: Optional[Union[int, float]] = None,
        inspectors: List[Callable[["BaseConn", RunOutput], bool]] = None,
        **options,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client_key_strings = client_key_strings or []
        self.connect_timeout = (connect_timeout, DEFAULT_CONNECT_TIMEOUT)[connect_timeout is None]
        self.inspectors = inspectors or []
        self.options = options

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError

    @abc.abstractmethod
    def connect(self):
        """
        创建一个连接
        :return:
        :raises:
            KeyExchangeError
            PermissionDeniedError 认证失败
            ConnectionLostError 连接丢失
            RemoteTimeoutError 连接超时
            DisconnectError 远程连接失败
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _run(
        self, command: str, check: bool = False, timeout: Optional[Union[int, float]] = None, **kwargs
    ) -> RunOutput:
        """命令执行"""
        raise NotImplementedError

    def run(
        self, command: str, check: bool = False, timeout: Optional[Union[int, float]] = None, **kwargs
    ) -> RunOutput:
        """
        命令执行
        :param command: 命令
        :param check: 返回码非0抛出 ProcessError 异常
        :param timeout: 命令执行最大等待时间，超时抛出 RemoteTimeoutError 异常
        :param kwargs:
        :return:
        :raises:
            SessionError 回话异常，连接被重置等
            ProcessError 命令执行异常
            RemoteTimeoutError 执行超时
        """
        run_output = self._run(command, check, timeout, **kwargs)
        # 输出预处理
        for inspector in self.inspectors:
            inspector(self, run_output)
        return run_output

    def __enter__(self) -> "BaseConn":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self._conn = None


class ParamikoConn(BaseConn):
    """
    基于 paramiko 实现的同步 SSH 连接
    paramiko
        仓库：https://github.com/paramiko/paramiko
        文档：https://www.paramiko.org/
    """

    _conn: Optional[paramiko.SSHClient] = None

    @staticmethod
    def get_key_instance(key_content: str):

        matched_private_key = JOB_PRIVATE_KEY_RE.match(key_content)
        if matched_private_key:
            start, content, end = matched_private_key.groups()
            # 作业平台传参后key的换行符被转义为【空格】，需重新替换为换行符
            content = content.replace(" ", "\n")
            # 手动安装命令key的换行符被转义为 \n 字符串，需重新替换为换行符
            content = content.replace("\\n", "\n")
            key_content = f"{start}{content}{end}"

        key_instance = None
        with StringIO(key_content) as key_file:
            for cls in [paramiko.RSAKey, paramiko.DSSKey, paramiko.ECDSAKey, paramiko.Ed25519Key]:
                try:
                    key_instance = cls.from_private_key(key_file)
                    logger.logging("[get_key_instance]", f"match {cls.__name__}", is_report=False)
                    break
                except paramiko.ssh_exception.PasswordRequiredException:
                    raise PermissionDeniedError("Password is required for the private key")
                except paramiko.ssh_exception.SSHException:
                    logger.logging("[get_key_instance]", f"not match {cls.__name__}, skipped", is_report=False)
                    key_file.seek(0)
                    continue

        if not key_instance:
            raise PermissionDeniedError("Unsupported key type")

        return key_instance

    def close(self):
        self._conn.close()

    def connect(self) -> paramiko.SSHClient:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 仅支持单个密钥
        if self.client_key_strings:
            pkey = self.get_key_instance(self.client_key_strings[0])
        else:
            pkey = None

        # API 文档：https://docs.paramiko.org/en/stable/api/client.html#paramiko.client.SSHClient.connect
        # 认证顺序：
        #  - pkey or key_filename
        #  - Any “id_rsa”, “id_dsa” or “id_ecdsa” key discoverable in ~/.ssh/ (look_for_keys=True)
        #  - username/password auth, if a password was given
        try:
            ssh.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                pkey=pkey,
                password=self.password,
                timeout=self.connect_timeout,
                allow_agent=False,
                # 从安全上考虑，禁用本地RSA私钥扫描
                look_for_keys=False,
                **self.options,
            )
        except paramiko.BadHostKeyException as e:
            raise PermissionDeniedError(f"Key verification failed：{e}") from e
        except paramiko.AuthenticationException as e:
            raise PermissionDeniedError(
                f"Authentication failed, please check the authentication information for errors: {e}"
            ) from e
        except (paramiko.SSHException, socket.error, Exception) as e:
            raise DisconnectError(f"Remote connection failed: {e}") from e
        self._conn = ssh
        return ssh

    def _run(
        self, command: str, check: bool = False, timeout: Optional[Union[int, float]] = None, **kwargs
    ) -> RunOutput:

        begin_time = time.time()
        try:
            __, stdout, stderr = self._conn.exec_command(command=command, timeout=timeout)
            # 获取 exit_status 方式参考：https://stackoverflow.com/questions/3562403/
            exit_status = stdout.channel.recv_exit_status()
        except paramiko.SSHException as e:
            if check:
                raise ProcessError(f"Command returned non-zero: {e}")
            # exec_command 方法没有明确抛出 timeout 异常，需要记录调用前后时间差进行抛出
            cost_time = time.time() - begin_time
            if cost_time > timeout:
                raise RemoteTimeoutError(f"Connect timeout：{e}") from e
            exit_status, stdout, stderr = 1, StringIO(""), StringIO(str(e))
        return RunOutput(command=command, exit_status=exit_status, stdout=stdout.read(), stderr=stderr.read())


if __name__ == "__main__":

    _paramiko_version: str = "-"
    try:
        _paramiko_version = str(paramiko.__version__)
    except Exception:
        logger.logging("proxy", "Failed to get paramiko version", is_report=False, level=logging.WARNING)

    _app_core_remote_proxy_info_labels = {
        "proxy_name": socket.gethostname(),
        "proxy_ip": args.lan_eth_ip,
        "bk_cloud_id": args.host_cloud,
        "paramiko_version": _paramiko_version,
    }
    logger.logging(
        "metrics",
        f"app_core_remote_proxy_info_labels -> {_app_core_remote_proxy_info_labels}",
        metrics={"name": "app_core_remote_proxy_info", "labels": _app_core_remote_proxy_info_labels},
    )

    logger.logging("proxy", "setup_pagent2 will start running now.", is_report=False)
    _start = time.perf_counter()

    try:
        main()
    except Exception as _e:
        _app_core_remote_connects_total_labels = {**get_common_labels(), "status": "failed"}
        logger.logging(
            "metrics",
            f"app_core_remote_connects_total_labels -> {_app_core_remote_connects_total_labels}",
            metrics={"name": "app_core_remote_connects_total", "labels": _app_core_remote_connects_total_labels},
        )

        if isinstance(_e, RemoteBaseException):
            exc_type = "app"
            exc_code = str(_e.code)
        else:
            exc_type = "unknown"
            exc_code = _e.__class__.__name__

        _app_core_remote_connect_exceptions_total_labels = {
            **get_common_labels(),
            "exc_type": exc_type,
            "exc_code": exc_code,
        }
        logger.logging(
            "metrics",
            f"app_core_remote_connect_exceptions_total_labels -> {_app_core_remote_connect_exceptions_total_labels}",
            metrics={
                "name": "app_core_remote_connect_exceptions_total",
                "labels": _app_core_remote_connect_exceptions_total_labels,
            },
        )
        logger.logging("proxy_fail", str(_e), level=logging.ERROR)
        logger.logging("proxy_fail", traceback.format_exc(), level=logging.ERROR, is_report=False)
    else:
        _app_core_remote_execute_duration_seconds_labels = {"method": ("proxy_wmiexe", "proxy_ssh")[use_shell()]}
        cost_time = time.perf_counter() - _start
        logger.logging(
            "metrics",
            f"app_core_remote_execute_duration_seconds_labels -> {_app_core_remote_execute_duration_seconds_labels}",
            metrics={
                "name": "app_core_remote_execute_duration_seconds",
                "labels": _app_core_remote_execute_duration_seconds_labels,
                "data": {"cost_time": cost_time},
            },
        )
        logger.logging("proxy", f"setup_pagent2 succeeded: cost_time -> {cost_time}", is_report=False)
