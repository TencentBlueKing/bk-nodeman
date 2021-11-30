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
import abc
import base64
import ntpath
import os
import posixpath
import time
from typing import List, Set, Union

import ujson as json
from django.conf import settings
from django.db.models import Max, Subquery
from django.utils.translation import ugettext_lazy as _

from apps.backend.api.constants import POLLING_INTERVAL, POLLING_TIMEOUT
from apps.backend.api.gse import GseClient
from apps.backend.components.collections.base import BaseService, CommonData
from apps.backend.components.collections.gse import GseBaseService
from apps.backend.components.collections.job import (
    JobFastExecuteScriptService,
    JobFastPushFileService,
    JobPushMultipleConfigFileService,
)
from apps.backend.subscription import tools
from apps.backend.views import generate_gse_config
from apps.component.esbclient import client_v2
from apps.node_man import constants
from apps.node_man.models import Host, Packages, ProcessStatus
from apps.utils import basic
from pipeline.component_framework.component import Component
from pipeline.core.flow import Service, StaticIntervalGenerator


class AgentBaseService(BaseService, metaclass=abc.ABCMeta):
    """
    AGENT安装基类
    """

    def sub_inst_failed_handler(self, sub_inst_ids: Union[List[int], Set[int]]):
        """
        订阅实例失败处理器
        :param sub_inst_ids: 订阅实例ID列表/集合
        """
        pass


class AgentCommonData(CommonData):
    pass


class PushUpgradePackageService(JobFastPushFileService):
    name = _("下发升级包")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        inputs = super().inputs_format()
        inputs.append(Service.InputItem(name="host_info", key="host_info", type="object", required=True))
        return inputs

    def outputs_format(self):
        outputs = super().outputs_format()
        outputs.append(Service.OutputItem(name="package_name", key="package_name", type="str", required=True))
        return outputs

    def execute(self, data, parent_data):
        self.logger.info(_("开始下发升级包"))
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info(host_info)
        nginx_path = host.ap.nginx_path or settings.DOWNLOAD_PATH
        data.inputs.file_target_path = host.agent_config["temp_path"]

        os_type = host.os_type.lower()

        # 根据节点类型、位数、系统等组装包名
        gse_type = "proxy" if host.node_type == constants.NodeType.PROXY else "client"
        package_name = f"gse_{gse_type}-{os_type}-{host.cpu_arch}_upgrade.tgz"
        files = [package_name]

        # windows机器需要添加解压文件
        if os_type == constants.OsType.WINDOWS:
            files.extend(["7z.dll", "7z.exe"])
        file_source = [{"files": [f"{nginx_path}/{file}" for file in files]}]

        data.inputs.file_source = file_source

        data.outputs.package_name = package_name
        return super().execute(data, parent_data)


class RunUpgradeCommandService(JobFastExecuteScriptService):
    name = _("下发升级脚本命令")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        inputs = super().inputs_format()
        inputs.append(Service.InputItem(name="host_info", key="host_info", type="object", required=True))
        return inputs

    def execute(self, data, parent_data):
        self.logger.info(_("开始执行升级脚本"))
        host_info = data.get_one_of_inputs("host_info")
        package_name = data.get_one_of_inputs("package_name")
        host = Host.get_by_host_info(host_info)
        agent_config = host.agent_config
        temp_path = agent_config["temp_path"]
        setup_path = agent_config["setup_path"]
        if host.os_type.lower() == "windows":
            # 1. 停止agent，此时无法从Job获取任务结果
            # 2. 解压升级包到目标路径，使用 -aot 参数把已存在的二进制文件重命名
            # 3. 启动agent
            scripts = (
                'reg add "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" '
                '/v gse_agent /t reg_sz /d "{setup_path}\\agent\\bin\\gsectl.bat start" /f 1>nul 2>&1'
                " && start gsectl.bat stop && ping -n 20 127.0.0.1 >> c:\\ping_ip.txt && {temp_path}\\7z.exe x"
                " {temp_path}\\{package_name} -o{temp_path} -y 1>nul 2>&1 && {temp_path}\\7z.exe x "
                "{temp_path}\\{package_name_tar} -aot -o{setup_path} -y 1>nul 2>&1 && gsectl.bat start"
            )
            data.inputs.script_content = scripts.format(
                setup_path=setup_path,
                temp_path=temp_path,
                package_name=package_name,
                package_name_tar=package_name.replace("tgz", "tar"),
            )
        else:
            path = os.path.join(settings.PROJECT_ROOT, "script_tools", "upgrade_agent.sh.tpl")
            with open(path, encoding="utf-8") as fh:
                script = fh.read()
            if host.node_type == constants.NodeType.PROXY:
                node_type = "proxy"
                reload_cmd = """
result=0
count=0
for proc in gse_agent gse_transit gse_btsvr gse_data; do
     [ -f {setup_path}/{node_type}/bin/$proc ] && cd {setup_path}/{node_type}/bin && ./$proc --reload && \
     count=$((count + 1))
     sleep 1
     result=$((result + $?))
done
if [[ $result -gt 0 || $count -lt 3 ]]; then
   cd {setup_path}/{node_type}/bin && ./gsectl restart all
fi
                """.format(
                    setup_path=setup_path, node_type=node_type
                )
            else:
                node_type = "agent"
                reload_cmd = "cd {setup_path}/{node_type}/bin && ./gse_agent --reload || ./gsectl restart all".format(
                    setup_path=setup_path, node_type=node_type
                )
            data.inputs.script_content = script.format(
                setup_path=setup_path,
                temp_path=temp_path,
                package_name=package_name,
                node_type=node_type,
                reload_cmd=reload_cmd,
            )
        return super().execute(data, parent_data)

    def schedule(self, data, parent_data, callback_data=None):
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info(host_info)
        if host.os_type.lower() == "windows":
            self.finish_schedule()
            return True
        else:
            return super().schedule(data, parent_data, callback_data=callback_data)


class RestartService(AgentBaseService):
    name = _("重启")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="bk_username", key="bk_username", type="str", required=True),
        ]

    def _execute(self, data, parent_data):
        self.logger.info(_("调用作业平台重启Agent"))
        host_info = data.get_one_of_inputs("host_info")
        bk_username = data.get_one_of_inputs("bk_username")
        host = Host.get_by_host_info({"bk_host_id": host_info["bk_host_id"]})
        if host.node_type == constants.NodeType.PROXY and not host.os_type:
            host.os_type = constants.OsType.LINUX
            host.save()
        install_path = host.agent_config["setup_path"]
        install_path = basic.suffix_slash(host.os_type, install_path)
        if host.node_type == constants.NodeType.PROXY:
            sub_path = "proxy"
        else:
            sub_path = "agent"

        if host.os_type.lower() == "windows":
            accounts = ["system", "Administrator"]
            script_type_num = 2
            script_content = base64.b64encode(f"{install_path}agent\\bin\\gsectl.bat restart".encode()).decode()
        else:
            accounts = ["root"]
            script_type_num = 1
            script_content = base64.b64encode(
                f"{install_path}{sub_path}/bin/gsectl restart >/dev/null 2>&1".encode()
            ).decode()

        for index, account in enumerate(accounts, 1):
            bk_biz_id = host.bk_biz_id
            kwargs = {
                "bk_biz_id": bk_biz_id,
                "ip_list": [{"ip": host.inner_ip, "bk_cloud_id": host.bk_cloud_id}],
                "script_timeout": 300,
                "script_type": script_type_num,
                "account": account,
            }
            kwargs.update({"script_content": script_content})
            self.logger.info("job parameter is：\n{}\n".format(json.dumps(kwargs, indent=2)))
            try:
                data = client_v2.job.fast_execute_script(kwargs, bk_username=bk_username)
            except Exception as err:
                if index != len(accounts):
                    self.logger.info("start job failed: {} ({}/{})".format(err, index, len(accounts)))
                    continue
                self.logger.error(f"start job failed: {err}")
                return False
            else:
                task_inst_id = data.get("job_instance_id")
                time.sleep(5)
                job_status_kwargs = {
                    "bk_biz_id": bk_biz_id,
                    "job_instance_id": task_inst_id,
                }
                job_status_data = client_v2.job.get_job_instance_status(job_status_kwargs, bk_username=bk_username)
                # 判断任务是否在执行中
                if job_status_data.get("job_instance", {}).get("status", "") != 2:
                    self.logger.info(
                        f"[{task_inst_id}]Job execution failed, please go to the Job"
                        " platform to check the task execution details."
                    )
                    return False
                self.logger.info(f"[{task_inst_id}]start job success，begin poll agent status")
                break

        # 下发job作业后等待5秒后再开始查状态,
        time.sleep(5)
        return True


class UpdateProcessStatusService(AgentBaseService):
    name = _("更新主机进程状态")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="status", key="status", type="str", required=True),
        ]

    def _execute(self, data, parent_data):
        status = data.get_one_of_inputs("status")
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host_info = data.get_one_of_inputs("host_info")
        if status == constants.ProcStateType.NOT_INSTALLED:
            host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)
            host.node_from = "CMDB"
            host.save()
            process = ProcessStatus.objects.get(bk_host_id=host.bk_host_id, name="gseagent")
            process.status = constants.ProcStateType.NOT_INSTALLED
            process.save()

        self.logger.info(_("更新主机状态为{status}").format(status=status))
        return True


class UpdateJobStatusService(AgentBaseService):
    name = _("更新任务状态")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="expect_status", key="expect_status", type="int", required=True),
        ]

    def _execute(self, data, parent_data):
        tools.update_job_status(self.root_pipeline_id, result=True)
        return True


class OperatePluginService(AgentBaseService, GseBaseService):
    """
    操作插件基类
    """

    name = _("操作插件")
    __need_schedule__ = True
    interval = StaticIntervalGenerator(POLLING_INTERVAL)

    def __init__(self):
        super().__init__(name=self.name)

    def _execute(self, data, parent_data):
        bk_username = data.get_one_of_inputs("bk_username")
        plugin_name = data.get_one_of_inputs("plugin_name")
        action = data.get_one_of_inputs("action")
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)

        newest = (
            Packages.objects.filter(project=plugin_name, cpu_arch=constants.CpuType.x86_64)
            .values("os")
            .annotate(max_id=Max("id"))
        )

        packages = Packages.objects.filter(id__in=Subquery(newest.values("max_id")))
        os_type = host.os_type.lower()
        package_by_os = {package.os: package for package in packages}
        if os_type not in package_by_os:
            self.logger.info(f"{plugin_name} dose not support {os_type}!")
            return True
        package = package_by_os[os_type]
        control = package.proc_control
        control = {
            "start_cmd": control.start_cmd,
            "stop_cmd": control.stop_cmd,
            "restart_cmd": control.restart_cmd,
            "reload_cmd": control.reload_cmd or control.restart_cmd,
            "kill_cmd": control.kill_cmd,
            "version_cmd": control.version_cmd,
            "health_cmd": control.health_cmd,
        }

        gse_client = GseClient(username=bk_username, os_type=os_type, _logger=self.logger)

        hosts = [
            {"bk_cloud_id": host.bk_cloud_id, "ip": host.inner_ip, "bk_supplier_id": constants.DEFAULT_SUPPLIER_ID}
        ]
        if package.os == constants.PluginOsType.windows:
            path_handler = ntpath
        else:
            path_handler = posixpath

        setup_path = path_handler.join(
            package.proc_control.install_path, constants.PluginChildDir.OFFICIAL.value, "bin"
        )
        pid_path = package.proc_control.pid_path

        result = gse_client.register_process(hosts, control, setup_path, pid_path, plugin_name, plugin_name)
        if result["failed"]:
            data.outputs.result = result  # result字段存注册结果
            self.logger.error("GSE register process failed. result:\n[{}]".format(json.dumps(result, indent=2)))
            data.outputs.ex_data = "以下主机注册进程失败：{}".format(
                ",".join(["[{}] {}".format(host["ip"], host.get("error_msg")) for host in result["failed"]])
            )
            return False
        # self.logger.info('GSE register process success. result->[{}]'.format(json.dumps(result, indent=2)))
        self.logger.info("GSE register process success.")
        # 从 GSE Client 获取相应的动作
        operate_method = getattr(gse_client, "{}_process".format(action))
        task_id = operate_method(hosts, plugin_name)
        self.logger.info("GSE {} Process and get task_id: [{}]".format(action.upper(), task_id))
        data.outputs.task_id = task_id
        data.outputs.polling_time = 0
        return True

    def schedule(self, data, parent_data, callback_data=None):
        task_id = data.get_one_of_outputs("task_id")
        if not task_id:
            self.finish_schedule()
            return True

        bk_username = data.get_one_of_inputs("bk_username")
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info({"bk_host_id": bk_host_id} if bk_host_id else host_info)
        polling_time = data.get_one_of_outputs("polling_time")
        gse_client = GseClient(username=bk_username, os_type=host.os_type.lower(), _logger=self.logger)

        is_finished, task_result = gse_client.get_task_result(task_id)
        self.logger.info(
            "GSE(task_id: [{}]) get schedule task result:\n[{}].".format(task_id, json.dumps(task_result, indent=2))
        )
        if is_finished:
            data.outputs.task_result = task_result  # task_result字段保存轮询结果
            if task_result["failed"]:
                self.logger.error(
                    "gse task(task_id: [{}]) failed. task_result:\n[{}]".format(
                        task_id, json.dumps(task_result, indent=2)
                    ),
                )
                data.outputs.ex_data = "以下主机操作进程失败：{}".format(self.format_error_msg(task_result))
                return False
            self.logger.info("GSE(task_id: [{}]) get schedule finished].".format(task_id))
            self.finish_schedule()
        elif polling_time + POLLING_INTERVAL > POLLING_TIMEOUT:
            data.outputs.ex_data = "任务轮询超时"
            self.logger.error("GSE(task_id: [{}]) schedule timeout.".format(task_id))
            return False

        data.outputs.polling_time = polling_time + POLLING_INTERVAL
        return True

    def inputs_format(self):
        return [
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
            Service.InputItem(name="bk_username", key="bk_username", type="str", required=True),
            Service.InputItem(name="plugin_name", key="plugin_name", type="str", required=True),
            Service.InputItem(name="action", key="action", type="str", required=True),
        ]


class WaitService(AgentBaseService):
    name = _("等待")

    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="sleep_time", key="sleep_time", type="int", required=True),
        ]

    def _execute(self, data, parent_data):
        return True

    def schedule(self, data, parent_data, callback_data=None):
        # 等待一段时间，用于重启Agent、安装Proxy等场景
        sleep_time = data.get_one_of_inputs("sleep_time", 5)
        time.sleep(sleep_time)
        self.finish_schedule()
        return True


class CheckAgentStatusService(AgentBaseService):
    name = _("检查Agent状态")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="bk_host_id", key="bk_host_id", type="int", required=True),
        ]

    def _execute(self, data, parent_data):
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        process_status = ProcessStatus.objects.filter(bk_host_id=bk_host_id, name=ProcessStatus.GSE_AGENT_PROCESS_NAME)
        running_status = process_status.filter(status=constants.ProcStateType.RUNNING)
        process_status_count = process_status.count()

        if running_status:
            if process_status_count > 1:
                # 如果状态记录重复进行清理
                process_status.exclude(id=running_status.first().id).delete()
            self.logger.info(_("Agent 状态【正常】"))
            return True
        else:
            if process_status_count > 1:
                # 如果状态记录重复进行清理
                process_status.exclude(id=process_status.first().id).delete()
            self.logger.error(_("Agent 状态【异常】"))
            return False


class RenderAndPushGseConfigService(JobPushMultipleConfigFileService):
    name = _("渲染并下发Agent配置")

    def __init__(self):
        super().__init__(name=self.name)

    def inputs_format(self):
        return [
            Service.InputItem(name="bk_host_id", key="bk_host_id", type="int", required=True),
            Service.InputItem(name="host_info", key="host_info", type="object", required=True),
        ]

    def execute(self, data, parent_data):
        file_name = "agent.conf"
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info(host_info)

        # 路径处理器
        path_handler = ntpath if host.os_type == constants.OsType.WINDOWS else posixpath

        setup_path = host.agent_config["setup_path"]

        # 新配置写入数据库
        extra_data = {
            "peer_exchange_switch_for_agent": host_info.get("peer_exchange_switch_for_agent", True),
            "bt_speed_limit": host_info.get("bt_speed_limit", 0),
        }
        if host_info.get("data_path"):
            extra_data.update({"data_path": host_info["data_path"]})
        host.extra_data = extra_data
        host.ap_id = host_info["ap_id"]
        host.save()

        # 生成配置
        config = generate_gse_config(
            host_info["bk_cloud_id"], file_name, host_info["host_node_type"].lower(), host_info["bk_host_innerip"]
        )
        node_type = "proxy" if host.node_type == constants.NodeType.PROXY else "agent"

        file_params = [
            {
                "file_target_path": path_handler.join(setup_path, node_type, "etc"),
                "file_list": [{"name": file_name, "content": config}],
            }
        ]

        data.inputs.file_params = file_params
        return super(RenderAndPushGseConfigService, self).execute(data, parent_data)


class ReloadAgentConfigService(JobFastExecuteScriptService):
    """
    重载Agent配置
    """

    def execute(self, data, parent_data):
        host_info = data.get_one_of_inputs("host_info")
        host = Host.get_by_host_info(host_info)

        # 路径处理器
        path_handler = ntpath if host.os_type == constants.OsType.WINDOWS else posixpath
        node_type = "proxy" if host.node_type == constants.NodeType.PROXY else "agent"
        setup_path = host.agent_config["setup_path"]
        agent_path = path_handler.join(setup_path, node_type, "bin")
        script_content = f"cd {agent_path} && ./gse_agent --reload"
        data.inputs.script_content = script_content
        return super(ReloadAgentConfigService, self).execute(data, parent_data)


class CheckPolicyGseToProxyService(JobFastExecuteScriptService):
    """
    检测GSE svr到proxy的策略
    """

    def inputs_format(self):
        return [
            Service.InputItem(name="bk_host_id", key="bk_host_id", type="int", required=True),
        ]

    @staticmethod
    def query_gse_svr_biz(gse_svr_list):
        # 查询GSE SVR所在业务
        if settings.JOB_VERSION == "V3":
            bk_biz_id = settings.BLUEKING_BIZ_ID
        else:
            # 查询bk_host_id
            bk_host_ids = (
                client_v2.cc.list_hosts_without_biz(
                    {
                        "page": {"start": 0, "limit": 500, "sort": "bk_host_id"},
                        "fields": ["bk_host_id"],
                        "host_property_filter": {
                            "condition": "AND",
                            "rules": [
                                {
                                    "field": "bk_host_innerip",
                                    "operator": "in",
                                    "value": [svr["inner_ip"] for svr in gse_svr_list],
                                },
                                {"field": "bk_cloud_id", "operator": "equal", "value": constants.DEFAULT_CLOUD},
                            ],
                        },
                    }
                ).get("info")
                or []
            )
            host_data = (
                client_v2.cc.find_host_biz_relations({"bk_host_id": [_host["bk_host_id"] for _host in bk_host_ids]})
                or []
            )

            if not host_data:
                return None

            bk_biz_id = host_data[0]["bk_biz_id"]
        return bk_biz_id

    def execute(self, data, parent_data):
        bk_host_id = data.get_one_of_inputs("bk_host_id")
        host = Host.get_by_host_info({"bk_host_id": bk_host_id})
        port_config = host.ap.port_config
        script_content = """
#!/bin/bash
is_target_reachable () {
    local ip=${1}
    local target_port=$2
    local _port err ret

    if [[ $target_port =~ [0-9]+-[0-9]+ ]]; then
        target_port=$(seq ${target_port//-/ })
    fi
    for _port in $target_port; do
        timeout 5 bash -c ">/dev/tcp/$ip/$_port" 2>/dev/null
        case $? in
            0) return 0 ;;
            1) ret=1 && echo "GSE server connect to proxy($ip:$_port) connection refused" ;;
            ## 超时的情况，只有要一个端口是超时的情况，认定为网络不通，不继续监测
            124) echo "GSE server connect to proxy($ip:$target_port) failed: NETWORK TIMEOUT %(msg)s" && return 124;;
        esac
    done

    return $ret;
}
ret=0
is_target_reachable %(proxy_ip)s %(btsvr_thrift_port)s || ret=$?
is_target_reachable %(proxy_ip)s %(bt_port)s-%(tracker_port)s || ret=$?
exit $ret
""" % {
            "proxy_ip": host.outer_ip,
            "btsvr_thrift_port": port_config.get("btsvr_thrift_port"),
            "bt_port": port_config.get("bt_port"),
            "tracker_port": port_config.get("tracker_port"),
            "msg": _("请检查数据传输IP是否正确或策略是否开通"),
        }

        gse_svr_biz = self.query_gse_svr_biz(host.ap.btfileserver)
        if not gse_svr_biz:
            self.logger.error(_("查询GSE Svr业务失败，请确认GSE Svr是否存在CMDB中"))
            return False

        data.inputs.job_client = {
            "bk_biz_id": gse_svr_biz,
            "username": settings.SYSTEM_USE_API_ACCOUNT,
            "os_type": "linux",
        }
        data.inputs.ip_list = [
            {"ip": svr["inner_ip"], "bk_cloud_id": constants.DEFAULT_CLOUD} for svr in host.ap.btfileserver
        ]
        data.inputs.script_content = script_content
        return super(CheckPolicyGseToProxyService, self).execute(data, parent_data)


class PushUpgradePackageComponent(Component):
    name = _("升级")
    code = "push_upgrade_package"
    bound_service = PushUpgradePackageService


class RunUpgradeCommandComponent(Component):
    name = _("升级")
    code = "run_upgrade_command"
    bound_service = RunUpgradeCommandService


class RestartComponent(Component):
    name = _("重启")
    code = "restart"
    bound_service = RestartService


class UpdateProcessStatusComponent(Component):
    name = _("更新主机进程状态")
    code = "update_process_status"
    bound_service = UpdateProcessStatusService


class UpdateJobStatusComponent(Component):
    name = _("更新任务状态")
    code = "update_job_status"
    bound_service = UpdateJobStatusService


class OperatePluginComponent(Component):
    name = _("操作插件")
    code = "operate_plugin"
    bound_service = OperatePluginService


class WaitComponent(Component):
    name = _("等待")
    code = "wait"
    bound_service = WaitService


class CheckAgentStatusComponent(Component):
    name = _("检查Agent状态")
    code = "agent_check_agent_status"
    bound_service = CheckAgentStatusService


class RenderAndPushGseConfigComponent(Component):
    name = _("渲染并下发Agent配置")
    code = "render_and_push_gse_config"
    bound_service = RenderAndPushGseConfigService


class ReloadAgentConfigComponent(Component):
    name = _("重载Agent配置")
    code = "reload_agent_config"
    bound_service = ReloadAgentConfigService


class CheckPolicyGseToProxyComponent(Component):
    name = _("检测GSE Server到Proxy策略")
    code = "check_policy_gse_to_proxy"
    bound_service = CheckPolicyGseToProxyService
