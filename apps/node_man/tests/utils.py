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
import random
import time
from collections import Counter, defaultdict
from itertools import chain
from unittest.mock import patch

from django.utils import timezone

from apps.exceptions import ComponentCallError
from apps.node_man import constants as const
from apps.node_man import tools
from apps.node_man.handlers.ap import APHandler
from apps.node_man.handlers.cloud import CloudHandler
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.host import HostHandler
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.models import (
    AccessPoint,
    Cloud,
    Host,
    IdentityData,
    InstallChannel,
    Job,
    ProcessStatus,
)
from apps.utils.basic import filter_values, get_chr_seq

CONST_IP_LEN = 2234
IP_REG = r"((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}"
DIGITS = get_chr_seq("0", "9") + get_chr_seq("a", "z") + get_chr_seq("A", "Z")
SEARCH_BUSINESS = [
    {"bk_biz_id": 27, "bk_biz_name": "12"},
    {"bk_biz_id": 28, "bk_biz_name": "t2"},
    {"bk_biz_id": 29, "bk_biz_name": "13"},
    {"bk_biz_id": 30, "bk_biz_name": "t3"},
    {"bk_biz_id": 31, "bk_biz_name": "14"},
    {"bk_biz_id": 32, "bk_biz_name": "t4"},
    {"bk_biz_id": 33, "bk_biz_name": "15"},
    {"bk_biz_id": 34, "bk_biz_name": "t5"},
    {"bk_biz_id": 35, "bk_biz_name": "34"},
    {"bk_biz_id": 36, "bk_biz_name": "t6"},
    {"bk_biz_id": 37, "bk_biz_name": "t7"},
    {"bk_biz_id": 38, "bk_biz_name": "t8"},
    {"bk_biz_id": 39, "bk_biz_name": "t9"},
]
TOPO_ORDER = ["biz", "syy2", "syy1", "set", "module", "host", "test"]


def create_host_from_a_to_b(
    start,
    end,
    bk_host_id=None,
    ip=None,
    auth_type=None,
    bk_cloud_id=None,
    node_type=None,
    upstream_nodes=None,
    outer_ip=None,
    login_ip=None,
    proc_type=None,
):
    # 若传了bk_host_id，number必须为1
    host_to_create = []
    process_to_create = []
    identity_to_create = []
    for i in range(start, end):
        host_to_create.append(
            Host(
                **{
                    "bk_host_id": bk_host_id or i,
                    "bk_cloud_id": bk_cloud_id if bk_cloud_id is not None else [0, 1][random.randint(0, 1)],
                    "bk_biz_id": SEARCH_BUSINESS[random.randint(0, len(SEARCH_BUSINESS) - 1)]["bk_biz_id"],
                    "inner_ip": (
                        ip or f"{random.randint(1, 250)}.{random.randint(1, 250)}." f"{random.randint(1, 250)}.1"
                    ),
                    "outer_ip": (
                        outer_ip or f"{random.randint(1, 250)}.{random.randint(1, 250)}." f"{random.randint(1, 250)}.1"
                    ),
                    "login_ip": (
                        login_ip or f"{random.randint(1, 250)}.{random.randint(1, 250)}." f"{random.randint(1, 250)}.1"
                    ),
                    "node_type": node_type or ["AGENT", "PAGENT", "PROXY"][random.randint(0, 2)],
                    "os_type": const.OS_TUPLE[random.randint(0, 1)],
                    "ap_id": 1,
                    "upstream_nodes": upstream_nodes if upstream_nodes else [i for i in range(100)],
                    "extra_data": {"bt_speed_limit": None, "peer_exchange_switch_for_agent": 1},
                }
            )
        )
        # ProcessStatus创建，准备bulk_create
        process_to_create.append(
            ProcessStatus(
                bk_host_id=bk_host_id or i, proc_type=const.ProcType.AGENT, version=i, status=proc_type or "RUNNING"
            )
        )
        # Identity Data创建，准备bulk_create
        identity_to_create.append(
            IdentityData(
                **{
                    "bk_host_id": bk_host_id or i,
                    "auth_type": auth_type or const.AUTH_TUPLE[random.randint(0, 2)],
                    "account": "".join(random.choice(DIGITS) for i in range(8)),
                    "password": "".join(random.choice(DIGITS) for i in range(8)),
                    "port": random.randint(0, 10000),
                    "key": "".join(random.choice(DIGITS) for i in range(8)),
                    "retention": 1,
                }
            )
        )

    # bulk_create创建Host
    Host.objects.bulk_create(host_to_create)
    # bulk_create创建进程状态
    ProcessStatus.objects.bulk_create(process_to_create)
    # bulk_create创建认证信息
    IdentityData.objects.bulk_create(identity_to_create)

    return host_to_create, process_to_create, identity_to_create


def create_host(
    number,
    bk_host_id=None,
    ip=None,
    auth_type=None,
    bk_cloud_id=None,
    node_type=None,
    upstream_nodes=None,
    outer_ip=None,
    login_ip=None,
    proc_type=None,
):
    # 若传了bk_host_id，number必须为1
    host_to_create = []
    process_to_create = []
    identity_to_create = []
    max_count = 50000
    for index in range(0, int(number / max_count) + 1):
        if number - index * max_count > max_count:
            # 若还要分批创建
            host, process, identity = create_host_from_a_to_b(
                index * max_count,
                (index + 1) * max_count,
                bk_host_id=bk_host_id,
                ip=ip,
                auth_type=auth_type,
                bk_cloud_id=bk_cloud_id,
                node_type=node_type,
                upstream_nodes=upstream_nodes,
                outer_ip=outer_ip,
                login_ip=login_ip,
                proc_type=proc_type,
            )
        else:
            host, process, identity = create_host_from_a_to_b(
                index * max_count,
                number,
                bk_host_id=bk_host_id,
                ip=ip,
                auth_type=auth_type,
                bk_cloud_id=bk_cloud_id,
                node_type=node_type,
                upstream_nodes=upstream_nodes,
                outer_ip=outer_ip,
                login_ip=login_ip,
                proc_type=proc_type,
            )
        host_to_create.extend(host)
        process_to_create.extend(process)
        identity_to_create.extend(identity)
    return host_to_create, process_to_create, identity_to_create


class Subscription:
    def create_subscription(self, job_type, nodes):

        rsa_util = tools.HostTools.get_rsa_util()
        subscription_id = random.randint(100, 1000)
        task_id = random.randint(10, 1000)
        if job_type in ["REINSTALL_AGENT", "REINSTALL_PROXY", "RESTART_PROXY", "RESTART_AGENT"]:
            return {"subscription_id": subscription_id, "task_id": task_id}
        for node in nodes:
            host_info = node["instance_info"]
            # 准备注册数据
            bk_host_id = host_info.get("bk_host_id", -1)
            inner_ip = host_info["bk_host_innerip"]
            outer_ip = host_info.get("bk_host_outerip", "")
            login_ip = host_info.get("login_ip", "")
            data_ip = host_info.get("data_ip", "")
            Host.objects.update_or_create(
                bk_host_id=bk_host_id,
                defaults={
                    "bk_biz_id": host_info["bk_biz_id"],
                    "bk_cloud_id": host_info["bk_cloud_id"],
                    "inner_ip": inner_ip,
                    "outer_ip": outer_ip,
                    "login_ip": login_ip,
                    "data_ip": data_ip,
                    "os_type": host_info["os_type"],
                    "node_type": host_info["host_node_type"],
                    "ap_id": host_info["ap_id"],
                    "upstream_nodes": host_info.get("upstream_nodes", []),
                },
            )
            IdentityData.objects.update_or_create(
                bk_host_id=bk_host_id,
                defaults={
                    "auth_type": host_info.get("auth_type"),
                    "account": host_info.get("account"),
                    "password": tools.HostTools.decrypt_with_friendly_exc_handle(
                        rsa_util=rsa_util, encrypt_message=host_info["password"], raise_exec=Exception
                    ),
                    "port": host_info.get("port"),
                    "key": tools.HostTools.decrypt_with_friendly_exc_handle(
                        rsa_util=rsa_util, encrypt_message=host_info["key"], raise_exec=Exception
                    ),
                    "retention": host_info.get("retention", 1),
                    "extra_data": host_info.get("extra_data"),
                    "updated_at": timezone.now(),
                },
            )
            ProcessStatus.objects.get_or_create(
                bk_host_id=bk_host_id, name="gseagent", source_type=ProcessStatus.SourceType.DEFAULT
            )

        return {"subscription_id": subscription_id, "task_id": task_id}


class GseApi:
    @staticmethod
    def get_agent_status(*args, **kwargs):
        return {"bk_host_id": 1, "agent_status": "RUNNING"}


class JobApi:
    @staticmethod
    def fast_execute_script(*args, **kwargs):
        job_id = random.randint(100, 1000)
        return {"job_id": job_id, "args": args, "kwargs": kwargs}

    @staticmethod
    def get_job_instance_log(*args, **kwargs):
        job_id = random.randint(100, 1000)
        return [{"job_id": job_id, "args": args, "kwargs": kwargs}]


class NodeApi:
    @staticmethod
    def create_subscription(param):
        subscription_id = random.randint(100, 1000)
        task_id = random.randint(10, 1000)
        return {"subscription_id": subscription_id, "task_id": task_id, "param": param}

    @staticmethod
    def retry_subscription_task(param):
        subscription_id = random.randint(100, 1000)
        task_id = random.randint(10, 1000)
        return {"subscription_id": subscription_id, "task_id": task_id}

    @staticmethod
    def revoke_subscription_task(param):
        subscription_id = random.randint(100, 1000)
        task_id = random.randint(10, 1000)
        return {"subscription_id": subscription_id, "task_id": task_id}

    @staticmethod
    def get_subscription_task_status(param):
        if param["subscription_id"] == 1:
            status = "SUCCESS"
        elif param["subscription_id"] == 2:
            status = "FAILED"
        elif param["subscription_id"] == 3:
            status = "RUNNING"
        elif param["subscription_id"] == 4:
            status = "PENDING"
        elif param["subscription_id"] == 5:
            status = "RUNNING"
        else:
            status = "SUCCESS"

        # 测异常分支
        if param["subscription_id"] == 0:
            target_hosts = []
            status = "FAILED"
        else:
            target_hosts = [
                {
                    "sub_steps": [
                        {
                            "status": status,
                            "index": 1,
                            "node_name": "手动安装" if param["subscription_id"] == 5 else "1",
                            "pipeline_id": 1,
                        }
                    ]
                }
            ]

        result = [
            {
                "status": status,
                "instance_id": random.randint(100, 1000),
                "create_time": "2021-05-17 15:54:13",
                "start_time": "2021-05-17 15:54:14",
                "finish_time": "2021-05-17 15:54:15",
                "instance_info": {
                    "host": {
                        "bk_host_innerip": f"{random.randint(1, 250)}.{random.randint(1, 250)}."
                        f"{random.randint(1, 250)}.{random.randint(1, 250)}",
                        "bk_cloud_id": 0 if param["subscription_id"] == 5 else random.randint(100, 1000),
                        "bk_cloud_name": random.randint(100, 1000),
                        "bk_biz_id": random.randint(100, 1000),
                        "bk_biz_name": random.randint(100, 1000),
                        "bk_host_id": 1 if param["subscription_id"] == 5 else random.randint(1, 1000),
                    }
                },
                "steps": [{"target_hosts": target_hosts}],
            }
        ]

        # 测试PART_FAILED
        if param["subscription_id"] == 6:
            result.append(
                {
                    "status": "FAILED",
                    "instance_id": random.randint(100, 1000),
                    "create_time": "2021-05-17 15:54:13",
                    "start_time": "2021-05-17 15:54:14",
                    "finish_time": "2021-05-17 15:54:15",
                    "instance_info": {
                        "host": {
                            "bk_host_innerip": f"{random.randint(1, 250)}.{random.randint(1, 250)}."
                            f"{random.randint(1, 250)}.{random.randint(1, 250)}",
                            "bk_cloud_id": random.randint(100, 1000),
                            "bk_cloud_name": random.randint(100, 1000),
                            "bk_biz_id": random.randint(100, 1000),
                            "bk_biz_name": random.randint(100, 1000),
                            "bk_host_id": 1,
                        }
                    },
                    "steps": [{"target_hosts": target_hosts}],
                }
            )

        # 该接口已分页优化，兼容原先逻辑，没有传pagesize则不分页，传return_all需要返回分页结构
        if not param.get("return_all") and param.get("pagesize", -1) == -1:
            return result
        # 状态统计
        status_counter = []
        for instance in result:
            status_counter.append(instance["status"])
        status_counter = dict(Counter(status_counter))

        total = sum(list(status_counter.values()))
        status_counter["total"] = total
        return {"list": result, "total": total, "status_counter": status_counter}

    @staticmethod
    def get_subscription_task_detail(param):
        return {
            "status": "SUCCESS",
            "instance_id": random.randint(100, 1000),
            "instance_info": {
                "host": {
                    "bk_host_innerip": f"{random.randint(1, 250)}.{random.randint(1, 250)}."
                    f"{random.randint(1, 250)}.{random.randint(1, 250)}",
                    "bk_cloud_id": random.randint(100, 1000),
                    "bk_cloud_name": random.randint(100, 1000),
                    "bk_biz_id": random.randint(100, 1000),
                    "bk_biz_name": random.randint(100, 1000),
                }
            },
            "steps": [
                {
                    "id": random.randint(1, 250),
                    "target_hosts": [{"sub_steps": [{"status": "SUCCESS", "node_name": "1", "log": "1"}]}],
                }
            ],
        }

    @staticmethod
    def collect_subscription_task_detail(param):
        return "SUCCESS"

    @staticmethod
    def fetch_commands(param):
        return {
            "ips_commands": [{"ip": "127.0.0.1", "command": "test", "os_type": "LINUX"}],
            "win_commands": "test",
            "pre_commands": "test",
            "run_cmd": "test",
            "total_commands": "test",
        }

    @staticmethod
    def subscription_search_policy(param):
        return {
            "total": 1,
            "list": [
                {
                    "update_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "name": "我觉得能行",
                    "creator": "admin",
                    "bk_biz_scope": [27],
                    "nodes_scope": {"host_count": 33, "node_count": 6},
                    "plugin_name": "basereport",
                    "id": 1,
                }
            ],
        }

    @staticmethod
    def subscription_update(param):
        return {"subscription_id": 1, "task_id": 1}

    @staticmethod
    def run_subscription_task(param):
        return {"subscription_id": 1, "task_id": 1, "param": param}

    @staticmethod
    def plugin_retrieve(param):
        return {
            "category": "官方插件",
            "plugin_packages": [
                {
                    "cpu_arch": "x86_64",
                    "creator": "admin",
                    "module": "gse_plugin",
                    "project": "myprocessbeat",
                    "config_templates": [{}],
                    "version": "1.11.36",
                    "pkg_name": "myprocessbeat-1.11.36.tgz",
                    "is_ready": True,
                    "os": "linux",
                    "id": 115,
                }
            ],
            "node_manage_control": "",
            "name": "myprocessbeat",
            "scenario": "蓝鲸监控",
            "source_app_code": None,
            "is_ready": True,
            "deploy_type": None,
            "id": 1,
            "description": "主机进程信息采集器",
        }

    @staticmethod
    def plugin_list(param):
        return {
            "total": 1,
            "list": [
                {
                    "id": 1,
                    "description": "系统基础信息采集",
                    "name": "basereport",
                    "category": "官方插件",
                    "source_app_code": "bk_nodeman",
                    "scenario": "CMDB上的实时数据，蓝鲸监控里的主机监控，包含CPU，内存，磁盘等",
                    "deploy_type": "整包部署",
                }
            ],
        }

    @staticmethod
    def plugin_history(param):
        return [
            {
                "id": 1,
                "pkg_name": "basereport-1.0.tgz",
                "project": "basereport",
                "version": "1.0",
                "os": "linux",
                "cpu_arch": "x86",
            },
            {
                "id": 2,
                "pkg_name": "basereport-1.1.tgz",
                "module": "gse_plugin",
                "project": "basereport",
                "version": "1.1",
                "os": "linux",
                "cpu_arch": "x86",
            },
        ]

    @staticmethod
    def metric_list():
        return []

    @staticmethod
    def plugin_info(*args, **kwargs):
        return {}


def create_cloud_area(number, creator="admin", begin=1):
    clouds = []
    for i in range(begin, number + begin):
        cloud = Cloud(
            bk_cloud_id=i,
            isp=["腾讯云", "阿里云", "AWS"][random.randint(0, 2)],
            ap_id=const.DEFAULT_AP_ID,
            bk_cloud_name="".join(random.choice(DIGITS) for x in range(8)),
            is_visible=1,
            is_deleted=0,
            creator=creator,
        )
        clouds.append(cloud)
    clouds = Cloud.objects.bulk_create(clouds)
    bk_cloud_ids = [cloud.bk_cloud_id for cloud in clouds]
    return bk_cloud_ids


def create_install_channel(number, begin=1):
    install_channels = []
    for install_channel_id in range(begin, number + begin):
        install_channel = InstallChannel(
            id=install_channel_id,
            name="".join(random.choice(DIGITS) for _ in range(8)),
            bk_cloud_id=random.randint(0, number),
            jump_servers=["127.0.0.1"],
            upstream_servers={"taskserver": ["127.0.0.1"], "btfileserver": ["127.0.0.1"], "dataserver": ["127.0.0.1"]},
        )
        install_channels.append(install_channel)
    install_channels = InstallChannel.objects.bulk_create(install_channels)
    bk_cloud_channel_map = defaultdict(list)
    for install_channel in install_channels:
        bk_cloud_channel_map[install_channel.bk_cloud_id].append(install_channel)
    return bk_cloud_channel_map


def mock_read_remote_file_content(url):
    return [
        {
            "gseplugindesc": {
                "id": 1,
                "name": "basereport",
                "description": "test",
                "description_en": "test",
                "scenario": "test",
                "scenario_en": "Data source for real-time data on CMDB and OS monitoring data in bk-monitor",
                "category": "official",
                "config_file": "basereport.conf",
                "config_format": "yaml",
                "use_db": False,
                "is_binary": True,
                "auto_launch": True,
            },
            "packages": {
                "id": 1,
                "module": "gse_plugin",
                "project": "basereport",
                "version": "latest",
                "os": "linux",
                "cpu_arch": "x86_64",
                "pkg_size": 2,
            },
            "proccontrol": {"id": 1, "module": "gse_plugin", "project": "basereport", "os": "linux"},
        },
        {"test": {"id": 444}},
    ]


def random_ip():
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"


def create_ap(number):
    ap_to_create = []
    for i in range(1, number):
        ap_to_create.append(
            AccessPoint(
                **{
                    "name": "默认接入点",
                    "zk_hosts": [
                        {"zk_ip": random_ip(), "zk_port": [random.randint(2220, 22222)]},
                        {"zk_ip": random_ip(), "zk_port": [random.randint(2220, 22222)]},
                        {"zk_ip": random_ip(), "zk_port": [random.randint(2220, 22222)]},
                    ],
                    "ap_type": "whatever",
                    "region_id": 0,
                    "city_id": 0,
                    "status": "test",
                    "is_enabled": 1,
                    "zk_account": "bkzk",
                    "zk_password": "bkzk",
                    "btfileserver": [{"inner_ip": random_ip(), "outer_ip": random_ip()}],
                    "dataserver": [{"inner_ip": random_ip(), "outer_ip": random_ip()}],
                    "taskserver": [{"inner_ip": random_ip(), "outer_ip": random_ip()}],
                    "package_inner_url": "http://127.0.0.1:80/download",
                    "package_outer_url": "http://127.0.0.1:80/download",
                    "nginx_path": "/data/bkee/public/bknodeman/download",
                    "agent_config": {
                        "linux": {
                            "setup_path": "/usr/local/gse",
                            "data_path": "/usr/local/gse/data",
                            "run_path": "/usr/local/gse/run",
                            "log_path": "/usr/local/gse/log",
                        },
                        "windows": {
                            "setup_path": "/usr/local/gse",
                            "data_path": "/usr/local/gse/data",
                            "log_path": "/usr/local/gse/log",
                        },
                    },
                    "description": "GSE默认接入点1",
                    "is_default": True,
                }
            )
        )

    # bulk_create创建接入点
    AccessPoint.objects.bulk_create(ap_to_create)


def create_job(number, id=None, end_time=None, bk_biz_scope=None):
    job_types = list(chain(*list(const.JOB_TYPE_MAP.values())))

    jobs = []
    for i in range(1, number + 1):
        job = Job(
            id=id or i,
            job_type=random.choice(job_types),
            start_time=time.strftime("%a %b %d %H:%M:%S", time.localtime()),
            status=list(dict(const.JobStatusType.get_choices()).keys())[
                random.randint(0, len(const.JobStatusType.get_choices()) - 1)
            ],
            statistics={"success_count": 0, "failed_count": 0, "running_count": 0, "total_count": 0},
            bk_biz_scope=bk_biz_scope
            if bk_biz_scope == {}
            else [[biz["bk_biz_id"] for biz in SEARCH_BUSINESS][random.randint(0, 10)]],
            subscription_id=random.randint(1, 100),
            task_id_list=[random.randint(1, 100)],
            created_by="admin",
            end_time=end_time,
        )
        jobs.append(job)
    jobs = Job.objects.bulk_create(jobs)
    job_ids = [job.id for job in jobs]
    return job_ids


def multiple_cond_sql(data):
    """
    用于生成多条件sql查询
    :param data: 条件数据
    :return: 根据条件查询的所有结果
    """
    wheres = [
        f"{Host._meta.db_table}.bk_host_id={ProcessStatus._meta.db_table}.bk_host_id",
        f'{ProcessStatus._meta.db_table}.proc_type="{const.ProcType.AGENT}"',
    ]

    # 如果有status请求参数
    status = data.get("status", "")
    if status != "":
        statuses = '"' + '","'.join(status) + '"'
        wheres.append(f"{ProcessStatus._meta.db_table}.status in ({statuses})")

    # 如果有version请求参数
    version = data.get("version", "")
    if version != "":
        versions = '"' + '","'.join(version) + '"'
        wheres.append(f"{ProcessStatus._meta.db_table}.version in ({versions})")

    sql = Host.objects.filter(node_type__in=[const.NodeType.AGENT, const.NodeType.PAGENT]).extra(
        select={
            "status": f"{ProcessStatus._meta.db_table}.status",
            "version": f"{ProcessStatus._meta.db_table}.version",
        },
        tables=[ProcessStatus._meta.db_table],
        where=wheres,
    )
    return sql


def host_search_return_value(*args, **kwargs):
    # 会返回云区域版本和非云区域版本的bk_host_id
    # 因此返回2倍数量的Host
    limit = args[0]["page"]["limit"]
    start = args[0]["page"]["start"]
    ips = args[0]["host_property_filter"]["rules"][0]["value"]
    ip_host_id = []
    if ips != []:
        number = len(ips)
        for i in range(number):
            ip_host_id.append({"ip": ips[i], "bk_host_id": i})
    else:
        number = CONST_IP_LEN
        for i in range(number):
            ip = (
                f"{random.randint(1, 255)}.{random.randint(1, 255)}."
                f"{random.randint(1, 255)}.{random.randint(1, 255)}"
            )
            ip_host_id.append({"ip": ip, "bk_host_id": i})

    def gen_data(i, bk_cloud_id):
        return {
            "bk_asset_id": "DKUXHBUH189",
            "bk_bak_operator": "admin",
            "bk_cloud_id": bk_cloud_id,
            "bk_comment": "",
            "bk_cpu": 8,
            "bk_cpu_mhz": 2609,
            "bk_cpu_module": "E5-2620",
            "bk_disk": 300000,
            "bk_host_id": i["bk_host_id"],
            "bk_host_innerip": i["ip"],
            "bk_host_name": "nginx-1",
            "bk_host_outerip": "",
            "bk_isp_name": "1",
            "bk_mac": "",
            "bk_mem": 32000,
            "bk_os_bit": "",
            "create_time": "2019-07-22T01:52:21.737Z",
            "last_time": "2019-07-22T01:52:21.737Z",
            "bk_os_version": "",
            "bk_os_type": "1",
            "bk_service_term": 5,
            "bk_sla": "1",
            "import_from": "1",
            "bk_province_name": "广东",
            "bk_supplier_account": "0",
            "bk_state_name": "CN",
            "bk_outer_mac": "",
            "operator": "admin",
            "bk_sn": "",
        }

    total_data = []
    for i in ip_host_id:
        # 云区域这个值在测不同类型主机时需要改
        total_data.append(gen_data(i, 0))
        # total_data.append(gen_data(i, 1))

    return {"count": number, "info": total_data[start : start + limit]}


def gen_install_accept_list(count, nodetype, ip=None, bk_cloud_id=None, ticket=None, auth_type=None, is_manual=False):
    accept_list = [
        {
            "bk_cloud_id": bk_cloud_id or 97 if nodetype == "PROXY" or nodetype == "PAGENT" else 0,
            "ap_id": [-1, 1][random.randint(0, 1)],
            "bk_biz_id": random.randint(1, 10),
            "os_type": "LINUX",
            "inner_ip": ip
            or f"{random.randint(1, 255)}.{random.randint(1, 255)}."
            f"{random.randint(1, 255)}.{random.randint(1, 255)}",
            "account": "root",
            "port": i,
            "auth_type": auth_type or "PASSWORD",
            "password": f"{i * i}",
            "ticket": ticket,
            "is_manual": is_manual,
        }
        for i in range(count)
    ]
    return accept_list


def gen_update_accept_list(host_to_create, identity_to_create, no_change=False):
    accept_list = [
        {
            "bk_host_id": host_to_create[i].bk_host_id,
            "bk_cloud_id": host_to_create[i].bk_cloud_id,
            "ap_id": host_to_create[i].ap_id if no_change else -host_to_create[i].ap_id,
            "bk_biz_id": host_to_create[i].bk_biz_id if no_change else random.randint(1, 10),
            "os_type": host_to_create[i].os_type if no_change else const.OS_TUPLE[random.randint(0, 2)],
            "inner_ip": host_to_create[i].inner_ip,
            "login_ip": host_to_create[i].login_ip,
            "account": identity_to_create[i].account if no_change else "".join(random.choice(DIGITS) for i in range(8)),
            "port": identity_to_create[i].port if no_change else random.randint(100, 40000),
            "auth_type": identity_to_create[i].auth_type,
            "key": None if no_change else identity_to_create[i].key,
            "password": None if no_change else "".join(random.choice(DIGITS) for i in range(8)),
            "peer_exchange_switch_for_agent": host_to_create[i].extra_data["peer_exchange_switch_for_agent"],
            "bt_speed_limit": host_to_create[i].extra_data["bt_speed_limit"],
        }
        for i in range(len(host_to_create))
    ]
    accept_list = [filter_values(accept) for accept in accept_list]
    return accept_list


def gen_job_data(
    job_type,
    count,
    host_to_create=None,
    identity_to_create=None,
    ip=None,
    login_ip=None,
    outer_ip=None,
    bk_cloud_id=None,
    ap_id=None,
    bk_host_id=None,
    bk_biz_id=None,
    is_manual=False,
):
    op_type = job_type.split("_")[0]
    node_type = job_type.split("_")[1]
    if op_type == "INSTALL" or op_type == "REPLACE":
        accept_list = {"job_type": job_type, "op_type": op_type, "node_type": node_type, "hosts": []}
        if node_type == "PROXY":
            bk_cloud_id = bk_cloud_id if bk_cloud_id is not None else 1
            bk_biz_scope = [random.randint(27, 39)]
        else:
            bk_cloud_id = bk_cloud_id if bk_cloud_id is not None else 0
            bk_biz_scope = []

        if op_type == "REPLACE":
            accept_list["replace_host_id"] = 0

        for i in range(count):
            accept_list["hosts"].append(
                {
                    "bk_cloud_id": bk_cloud_id,
                    "ap_id": ap_id or [-1, 1][random.randint(0, 1)],
                    "bk_biz_id": bk_biz_id or random.randint(27, 39),
                    "os_type": "LINUX",
                    "inner_ip": ip
                    or f"{random.randint(1, 255)}.{random.randint(1, 255)}." f"{random.randint(1, 254)}.1",
                    "outer_ip": outer_ip
                    or f"{random.randint(1, 250)}.{random.randint(1, 250)}." f"{random.randint(1, 250)}.1",
                    "login_ip": login_ip
                    or f"{random.randint(1, 250)}.{random.randint(1, 250)}." f"{random.randint(1, 250)}.1",
                    "account": "root",
                    "port": i,
                    "bk_biz_scope": bk_biz_scope,
                    "auth_type": "PASSWORD",
                    "password": f"{i * i}",
                    "is_manual": is_manual,
                }
            )
    else:
        accept_list = {"job_type": job_type, "op_type": op_type, "node_type": node_type, "hosts": []}
        if node_type == "PROXY":
            bk_cloud_id = 1
        else:
            bk_cloud_id = bk_cloud_id or 0
        for i in range(count):
            accept_list["hosts"].append(
                {
                    "bk_host_id": bk_host_id or host_to_create[i].bk_host_id,
                    "bk_cloud_id": bk_cloud_id,
                    "ap_id": ap_id or [-1, 1][random.randint(0, 1)],
                    "bk_biz_id": random.randint(27, 39),
                    "is_manual": is_manual,
                    "os_type": const.OS_TUPLE[random.randint(0, 2)],
                    "inner_ip": ip or host_to_create[i].inner_ip,
                    "outer_ip": outer_ip or host_to_create[i].outer_ip,
                    "login_ip": login_ip or host_to_create[i].login_ip,
                    "account": identity_to_create[i].account,
                    "port": random.randint(100, 40000),
                    "auth_type": identity_to_create[i].auth_type,
                    "password": "".join(random.choice(DIGITS) for i in range(8)),
                }
            )

    return accept_list


def cmdb_or_cache_biz(self, username=""):
    if username != "special_test":
        data = {"info": SEARCH_BUSINESS}
    else:
        data = {"info": []}
    return data


class MockClientRaise(object):
    class cc(object):
        @classmethod
        def search_business(cls, *args, **kwargs):
            raise ComponentCallError


class MockClient(object):
    @classmethod
    def set_username(cls, *args, **kwargs):
        return

    class cc(object):
        @classmethod
        def list_hosts_without_biz(cls, *args, **kwargs):
            return host_search_return_value(*args, **kwargs)

        @classmethod
        def add_host_to_resource(cls, *args, **kwargs):
            return

        @classmethod
        def batch_update_host(cls, *args, **kwargs):
            return

        @classmethod
        def update_host_cloud_area_field(cls, *args, **kwargs):
            return

        @classmethod
        def search_business(cls, *args, **kwargs):
            data = {"info": SEARCH_BUSINESS}
            return data

        @classmethod
        def search_cloud_area(cls, *args, **kwargs):
            if args[0]["condition"]["bk_cloud_name"][0] == "a":
                raise ComponentCallError
            elif args[0]["condition"]["bk_cloud_name"][0] == "b":
                return {"info": None}
            return {"info": [{"bk_cloud_id": random.randint(0, 1000)}]}

        @classmethod
        def create_cloud_area(cls, *args, **kwargs):
            if args[0]["bk_cloud_name"][0] == "a":
                raise ComponentCallError({"code": 1199048})
            if args[0]["bk_cloud_name"][0] == "b":
                raise ComponentCallError({"code": 1111111})
            return {"created": {"id": random.randint(1001, 10000)}}

        @classmethod
        def update_cloud_area(cls, *args, **kwargs):
            if args[0]["bk_cloud_id"] < 1000:
                raise ComponentCallError
            return

        @classmethod
        def update_inst(cls, *args, **kwargs):
            return

        @classmethod
        def delete_cloud_area(cls, *args, **kwargs):
            if args[0]["bk_cloud_id"] == 9999:
                raise ComponentCallError({"code": 1111111})
            if args[0]["bk_cloud_id"] == 8888:
                raise ComponentCallError({"code": 1101030})
            return {"deleted": {"id": args[0]["bk_cloud_id"]}}

        @classmethod
        def create_inst(cls, *args, **kwargs):
            return {"bk_cloud_id": random.randint(1, 1000)}

        @classmethod
        def delete_inst(cls, *args, **kwargs):
            return

        @classmethod
        def search_inst(cls, *args, **kwargs):
            return {"info": [{"bk_cloud_id": random.randint(0, 1000)}]}

        @classmethod
        def cmdb_update_host(cls, *args, **kwargs):
            return

        @classmethod
        def search_object_attribute(cls, *args, **kwargs):
            return

        @classmethod
        def cmdb_update_host_cloud(cls, *args, **kwargs):
            return

        @classmethod
        def list_biz_hosts_topo(cls, *args, **kwargs):
            data = {
                "info": [
                    {
                        "host": {"bk_host_id": 1},
                        "topo": [{"bk_set_name": "test", "module": [{"bk_module_name": "test_module"}]}],
                    }
                ]
            }
            return data

        @classmethod
        def list_biz_hosts(cls, *args, **kwargs):
            if args[0]["bk_biz_id"] == 1:
                return {
                    "count": 1,
                    "info": [
                        {
                            "bk_cpu": None,
                            "bk_isp_name": None,
                            "bk_os_name": "",
                            "bk_province_name": None,
                            "bk_host_id": 14110,
                            "import_from": "3",
                            "bk_os_version": "",
                            "bk_disk": None,
                            "operator": None,
                            "create_time": "2020-02-26T17:09:11.685+08:00",
                            "bk_mem": None,
                            "bk_host_name": "",
                            "last_time": "2020-02-26T17:09:11.685+08:00",
                            "bk_host_innerip": "2.1.2.52",
                            "bk_comment": "",
                            "bk_os_bit": "",
                            "bk_outer_mac": "",
                            "bk_asset_id": "",
                            "bk_service_term": None,
                            "bk_cloud_id": 0,
                            "bk_sla": None,
                            "bk_cpu_mhz": None,
                            "bk_host_outerip": "2.1.2.52",
                            "bk_state_name": None,
                            "bk_os_type": "1",
                            "bk_mac": "",
                            "bk_bak_operator": None,
                            "bk_supplier_account": "2",
                            "bk_sn": "",
                            "bk_cpu_module": "",
                        }
                    ],
                }
            elif args[0]["bk_biz_id"] == -1:
                # 测异步
                if args[0]["page"]["start"] == 0:
                    return {"count": 555, "info": [{"bk_host_id": random.randint(1000, 10000)} for _ in range(500)]}
                elif args[0]["page"]["start"] == 500:
                    return {"count": 555, "info": [{"bk_host_id": random.randint(1000, 10000)} for _ in range(55)]}
            else:
                raise ComponentCallError

        @classmethod
        def search_biz_inst_topo(cls, *args, **kwargs):
            if args[0]["bk_biz_id"] == 1:
                return [
                    {
                        "host_count": 0,
                        "default": 0,
                        "bk_obj_name": "业务",
                        "bk_obj_id": "biz",
                        "service_instance_count": 0,
                        "child": [
                            {
                                "host_count": 0,
                                "default": 0,
                                "bk_obj_name": "Yun测试",
                                "bk_obj_id": "yun",
                                "service_instance_count": 0,
                                "child": [],
                                "service_template_id": 0,
                                "bk_inst_id": 10166,
                                "bk_inst_name": "Yun测试",
                            }
                        ],
                        "service_template_id": 0,
                        "bk_inst_id": 1,
                        "bk_inst_name": "资源池",
                    }
                ]
            else:
                raise ComponentCallError

        @classmethod
        def get_biz_internal_module(cls, *args, **kwargs):
            if args[0]["bk_biz_id"] == 1:
                return {"bk_set_id": 10, "module": None, "bk_set_name": "空闲机池"}
            else:
                raise ComponentCallError

        @classmethod
        def get_host_by_topo_node(cls, bk_biz_id, *args, **kwargs):
            if bk_biz_id == 0:
                raise ComponentCallError
            return []


class MockIAM(object):
    def __init__(self, app_code, secret_key, bk_iam_inner_host, bk_component_api_url):
        self.app_code = app_code
        self.secret_key = secret_key
        self.bk_iam_inner_host = bk_iam_inner_host
        self.bk_component_api_url = bk_component_api_url

    class _client:
        @staticmethod
        def policy_query(request_data):
            """
            根据测试角色类型来返回不同的权限数据
            """
            user = request_data["subject"]["id"]
            instance_type, action_type, *args = request_data["action"]["id"].split("_")
            instance_type = IamHandler.get_instance_type(instance_type, action_type)

            if user == "creator":
                # 构造创建者的数据情况
                condition = {"field": f"{instance_type}.iam_resource_owner", "op": "eq", "value": user}
            elif user.startswith("normal"):
                # 构建普通角色的数据情况
                op = user.split("_")[1]
                if op == "any" and action_type == "view":
                    condition = {"field": f"{instance_type}.id", "op": op, "value": []}
                else:
                    user_value_map = {"eq": 1, "in": [1, 2], "null": []}
                    op = "null" if op == "any" else op
                    condition = {"field": f"{instance_type}.id", "op": op, "value": user_value_map[op]}
            else:
                # 模拟未注册或者不合法用户
                condition = {}

            code, message, data = (1, "ok", condition)
            return code, message, data

        @staticmethod
        def get_apply_url(bk_token, bk_username, data):
            related_resource_types = data["actions"][0].get("related_resource_types")
            if not related_resource_types:
                # 生成不带资源实例的url
                url = "127.0.0.1/without_resource"
            else:
                # 生成带资源实例的url
                url = "127.0.0.1/with_resource"

            code, message, data = (1, "ok", url)
            return code, message, data


@patch("apps.node_man.handlers.cmdb.CmdbHandler.cmdb_or_cache_biz", cmdb_or_cache_biz)
@patch("apps.node_man.handlers.cmdb.client_v2", MockClient)
def ret_to_validate_data(data):
    # 获取Hosts中的cloud_id列表、ap_id列表、内网、外网、登录IP列表、bk_biz_scope列表
    bk_cloud_ids = set()
    ap_ids = set()
    bk_biz_scope = set()
    inner_ips = set()
    outer_ips = set()
    login_ips = set()

    for host in data["hosts"]:
        bk_cloud_ids.add(host["bk_cloud_id"])
        bk_biz_scope.add(host["bk_biz_id"])
        inner_ips.add(host["inner_ip"])
        if host.get("ap_id"):
            ap_ids.add(host["ap_id"])
        if host.get("outer_ip"):
            outer_ips.add(host["outer_ip"])
        if host.get("login_ip"):
            login_ips.add(host["login_ip"])

    # 获得用户的业务列表
    # 格式 { bk_biz_id: bk_biz_name , ...}
    biz_info = CmdbHandler().biz_id_name({})

    # 获得相应云区域 id, name, ap_id, bk_biz_scope
    # 格式 { cloud_id: {'bk_cloud_name': name, 'ap_id': id, 'bk_biz_scope':bk_biz_scope}, ...}
    cloud_info = CloudHandler().list_cloud_info(bk_cloud_ids)

    # 获得接入点列表
    # 格式 { id: name, ...}
    ap_id_name = APHandler().ap_list(ap_ids)

    # 获得请求里所有在数据库中的IP的相关信息
    # 格式 { inner_ip: {'bk_biz_id': bk_biz_id, 'node_type': node_type, 'bk_cloud_id': bk_cloud_id}, ...}
    inner_ip_info = HostHandler().ip_list(inner_ips)
    outer_ip_info = HostHandler().ip_list(outer_ips)
    login_ip_info = HostHandler().ip_list(login_ips)

    return biz_info, data, cloud_info, ap_id_name, inner_ip_info, outer_ip_info, login_ip_info, bk_biz_scope
