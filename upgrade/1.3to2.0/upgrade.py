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
import json
import logging
import os
import time
import traceback
from datetime import datetime

import pymysql
import requests

"""
SCRIPT_VERSION: 1.2
本文件用于节点管理V1.3 升级到节点管理V2.0
"""
try:
    import sys

    reload(sys)
    sys.setdefaultencoding("utf-8")
except Exception:
    pass


logger = logging.getLogger()
logger.setLevel(logging.INFO)
rq = time.strftime("%Y%m%d%H%M", time.localtime(time.time()))
logfile = "./" + rq + ".log"
fh = logging.FileHandler(logfile, mode="w")
formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)

DB_HOST = os.environ.get("BK_MYSQL_IP0", "localhost")
DB_PORT = int(os.environ.get("BK_MYSQL_PORT", 3306))
DB_USERNAME = os.environ.get("BK_MYSQL_ADMIN_USER", "root")
DB_PASSWORD = os.environ.get("BK_MYSQL_ADMIN_PASSWORD", "")
DB_NAME = "bk_nodeman"

try:
    APP_CODE = sys.argv[1]
    APP_SECRET = sys.argv[2]
    RUN_ENV = sys.argv[3]
except Exception as e:
    print("[Error---->Usage example]: python upgrade.py $APP_CODE $APP_SECRET $RUN_ENV[ee|ce] [$PAAS_FQDN]")
    exit(1)

PAAS_HOST = os.environ.get("BK_PAAS_PRIVATE_ADDR", "")
SEARCH_BIZ_URL = "http://{}/api/c/compapi/v2/cc/search_business/".format(PAAS_HOST or sys.argv[4])
LIST_BIZ_HOSTS_URL = "http://{}/api/c/compapi/v2/cc/list_biz_hosts/".format(PAAS_HOST or sys.argv[4])


def get_biz_bk_host_id(bk_biz_id, hosts):
    ret = {}

    def query_cc(start=0):
        # 查询业务主机ID
        kwargs = {
            "bk_app_code": APP_CODE,
            "bk_app_secret": APP_SECRET,
            "bk_username": "admin",
            "bk_biz_id": bk_biz_id,
            "bk_supplier_account": "0",
            "page": {"start": start, "limit": 500, "sort": "bk_host_id"},
            "host_property_filter": {
                "condition": "AND",
                "rules": [{"field": "bk_host_innerip", "operator": "in", "value": hosts}],
            },
        }

        logger.info("业务[%s]的查询参数为：%s" % (bk_biz_id, kwargs))
        req = json.loads(requests.post(LIST_BIZ_HOSTS_URL, json=kwargs, verify=False).content)

        logger.info("业务[%s]CMDB返回数据为：%s" % (bk_biz_id, req))
        for host in req["data"]["info"]:
            ret["{}_{}".format(host["bk_cloud_id"], host["bk_host_innerip"])] = host["bk_host_id"]
        if req["data"]["count"] > start + 500:
            query_cc(start + 500)

    query_cc()
    return ret


def backup_proxy_host():
    """
    备份PROXY主机
    :return:
    """
    cursor.execute("select * from node_man_host where node_type = 'PROXY' AND is_deleted = 0;")

    hosts = cursor.fetchall()
    logger.info("全部PROXY数据: %s" % str(hosts))

    # 生成cc查询参数
    hosts_kwargs = {}
    for host in hosts:
        if host["bk_biz_id"] in hosts_kwargs:
            hosts_kwargs[host["bk_biz_id"]].append(host)
        else:
            hosts_kwargs[host["bk_biz_id"]] = [host]

    host_data = []
    identity_data = []
    process_status_data = []

    for biz_id, biz_hosts in hosts_kwargs.items():
        biz_bk_host_ids = get_biz_bk_host_id(biz_id, [_host["inner_ip"] for _host in biz_hosts])
        for biz_host in biz_hosts:
            bk_host_id = biz_bk_host_ids.get("{}_{}".format(biz_host["bk_cloud_id"], biz_host["inner_ip"]))
            if not bk_host_id:
                logger.info("查询[bk_host_id]失败主机：%s" % biz_host)
                continue

            host_data.append(
                '({bk_host_id}, {bk_biz_id}, {bk_cloud_id}, "{inner_ip}", "{outer_ip}", '
                '"{login_ip}", "{data_ip}", "{os_type}", "{node_type}", {ap_id}, "[]", '
                '"{created_at}", "{updated_at}", "{node_from}")'.format(
                    bk_host_id=bk_host_id,
                    bk_biz_id=biz_host["bk_biz_id"],
                    bk_cloud_id=biz_host["bk_cloud_id"],
                    inner_ip=biz_host["inner_ip"],
                    outer_ip=biz_host["outer_ip"],
                    login_ip=biz_host["login_ip"],
                    data_ip=biz_host["data_ip"],
                    os_type="LINUX",
                    node_type=biz_host["node_type"],
                    ap_id=1,
                    updated_at=datetime.strftime(biz_host["update_time"], "%Y-%m-%d %H:%M:%S"),
                    created_at=datetime.strftime(biz_host["create_time"], "%Y-%m-%d %H:%M:%S"),
                    node_from="nodeman",
                )
            )
            identity_data.append(
                '({bk_host_id}, "{auth_type}", "{account}", {password}, {port}, {key},'
                ' "{retention}", "{updated_at}")'.format(
                    bk_host_id=bk_host_id,
                    auth_type=biz_host["auth_type"],
                    account=biz_host["account"],
                    password="null",
                    port=biz_host["port"],
                    key="null",
                    retention=1,
                    updated_at=datetime.strftime(biz_host["update_time"], "%Y-%m-%d %H:%M:%S"),
                )
            )

            process_status_data.append(
                '({bk_host_id}, "{name}", "{status}", "{is_auto}", "{proc_type}", '
                '"[]", "", "", "", "", "", "default")'.format(
                    bk_host_id=bk_host_id, name="gseagent", status="UNKNOWN", is_auto="AUTO", proc_type="AGENT"
                )
            )

    logger.info("生成的插入host数据： %s" % host_data)
    logger.info("生成的插入host_identity_data数据： %s" % identity_data)
    logger.info("生成的插入process_status_data数据： %s" % process_status_data)

    return host_data, identity_data, process_status_data


def migrate_proxy(host_data, identity_data, process_status_data):
    insert_sql = (
        "INSERT INTO node_man_host (bk_host_id, bk_biz_id ,bk_cloud_id, inner_ip,"
        " outer_ip, login_ip, data_ip, os_type, node_type, ap_id, upstream_nodes, "
        "created_at, updated_at, node_from) VALUES %s;" % ",".join(host_data)
    )
    logger.info("插入PROXY语句为： %s" % insert_sql)

    insert_identity_data_sql = (
        "INSERT INTO node_man_identitydata (bk_host_id, auth_type, account,"
        " `password`, `port`, `key`, retention, updated_at) VALUES %s;" % ",".join(identity_data)
    )
    logger.info("插入PROXY认证数据语句为： %s" % insert_identity_data_sql)

    process_status_sql = (
        "INSERT INTO node_man_processstatus (bk_host_id, `name`, status, is_auto,"
        "proc_type, configs, setup_path, log_path, data_path, "
        "pid_path, group_id, source_type) VALUES %s;" % ",".join(process_status_data or [])
    )
    logger.info("插入PROXY Agent状态语句为： %s" % process_status_sql)

    if host_data:
        logger.info("run insert_sql: {}".format(insert_sql))
        cursor.execute(insert_sql)
    if identity_data:
        logger.info("run insert_identity_data_sql: {}".format(insert_identity_data_sql))
        cursor.execute(insert_identity_data_sql)
    if process_status_data:
        logger.info("run process_status_sql: {}".format(process_status_sql))
        cursor.execute(process_status_sql)

    db.commit()


def backup_host_status():
    cursor.execute(
        "select name,status,version,proc_type,is_auto,configs,data_path,group_id,listen_ip,listen_port,"
        "log_path,pid_path,setup_path,source_id,source_type,bk_biz_id,bk_cloud_id,inner_ip from "
        "node_man_hoststatus inner join node_man_host on node_man_host.id=node_man_hoststatus.host_id"
        " where source_type != 'default';"
    )

    hosts_status = cursor.fetchall()
    logger.info("process_status需要迁移的数据为： %s" % str(hosts_status))
    hosts_status_kwargs = {}
    for host in hosts_status:
        if host["bk_biz_id"] in hosts_status_kwargs:
            hosts_status_kwargs[host["bk_biz_id"]].append(host)
        else:
            hosts_status_kwargs[host["bk_biz_id"]] = [host]

    process_status_data = []
    process_status_data_no_listen_port = []
    for biz_id, hosts_status_data in hosts_status_kwargs.items():
        # 需要返回业务内全部数据
        biz_bk_host_ids = get_biz_bk_host_id(biz_id, list(set([_host["inner_ip"] for _host in hosts_status_data])))
        for biz_host in hosts_status_data:
            bk_host_id = biz_bk_host_ids.get("{}_{}".format(biz_host["bk_cloud_id"], biz_host["inner_ip"]))
            if not bk_host_id:
                logger.info("process_status查询[bk_host_id]失败主机：%s" % str(biz_host))
                continue
            configs = biz_host["configs"].replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
            if biz_host["listen_port"]:
                process_status_data.append(
                    "({bk_host_id}, '{name}', '{status}', '{is_auto}', '{version}',"
                    "'{proc_type}', '{configs}', '{listen_ip}', '{listen_port}', '{setup_path}', "
                    "'{log_path}', '{data_path}', '{pid_path}', '{group_id}', '{source_type}', "
                    "'{source_id}')".format(
                        bk_host_id=bk_host_id,
                        name=biz_host["name"],
                        status=biz_host["status"],
                        is_auto=biz_host["is_auto"],
                        version=biz_host["version"],
                        proc_type=biz_host["proc_type"],
                        configs=configs,
                        listen_ip=biz_host["listen_ip"],
                        listen_port=biz_host["listen_port"],
                        setup_path=biz_host["setup_path"],
                        log_path=biz_host["log_path"],
                        data_path=biz_host["data_path"],
                        pid_path=biz_host["pid_path"],
                        group_id=biz_host["group_id"],
                        source_type=biz_host["source_type"],
                        source_id=biz_host["source_id"],
                    )
                )
            else:
                process_status_data_no_listen_port.append(
                    "({bk_host_id}, '{name}', '{status}', '{is_auto}', '{version}',"
                    "'{proc_type}', '{configs}', '{listen_ip}', '{setup_path}', "
                    "'{log_path}', '{data_path}', '{pid_path}', '{group_id}', '{source_type}', "
                    "'{source_id}')".format(
                        bk_host_id=bk_host_id,
                        name=biz_host["name"],
                        status=biz_host["status"],
                        is_auto=biz_host["is_auto"],
                        version=biz_host["version"],
                        proc_type=biz_host["proc_type"],
                        configs=configs,
                        listen_ip=biz_host["listen_ip"],
                        setup_path=biz_host["setup_path"],
                        log_path=biz_host["log_path"],
                        data_path=biz_host["data_path"],
                        pid_path=biz_host["pid_path"],
                        group_id=biz_host["group_id"],
                        source_type=biz_host["source_type"],
                        source_id=biz_host["source_id"],
                    )
                )

    logger.info("process_status 需要插入的数据为： %s" % process_status_data)
    return process_status_data, process_status_data_no_listen_port


def migrate_process_status(process_status_data, process_status_data_no_listen_port):
    if process_status_data:
        for status in process_status_data:
            process_status_sql = (
                "INSERT INTO node_man_processstatus (bk_host_id, `name`, status, is_auto, version, "
                "proc_type, configs,listen_ip, listen_port, setup_path, log_path, data_path, "
                "pid_path, group_id, source_type, source_id) VALUES %s;" % status
            )
            logger.info(u"插入process_status语句为： %s" % process_status_sql)
            cursor.execute(process_status_sql)
    if process_status_data_no_listen_port:
        for status in process_status_data_no_listen_port:
            sql_no_listen_port = (
                "INSERT INTO node_man_processstatus (bk_host_id, `name`, status, is_auto, version, "
                "proc_type, configs,listen_ip, setup_path, log_path, data_path, "
                "pid_path, group_id, source_type, source_id)"
                " VALUES %s;" % status
            )
            logger.info(u"插入process_status_data_no_listen_port语句为： %s" % sql_no_listen_port)
            cursor.execute(sql_no_listen_port)
    db.commit()


def migrate_cloud_creator(clouds):
    for cloud in clouds:
        if not cloud["bk_biz_id"] or cloud["bk_biz_id"] in [-1, "-1"]:
            continue

        bk_biz_maintainer = []
        try:
            for bk_biz_id in cloud["bk_biz_id"].split(","):
                bk_biz_maintainer.extend(
                    json.loads(
                        requests.post(
                            SEARCH_BIZ_URL,
                            json={
                                "bk_app_code": APP_CODE,
                                "bk_app_secret": APP_SECRET,
                                "bk_username": "admin",
                                "fields": ["bk_biz_id", "bk_biz_name", "bk_biz_maintainer"],
                                "condition": {"bk_biz_id": int(bk_biz_id)},
                            },
                        ).content
                    )["data"]["info"][0]
                    .get("bk_biz_maintainer", "")
                    .split(",")
                )
            creator = json.dumps(list(set(bk_biz_maintainer)))
            cursor.execute(
                "insert into node_man_cloud(bk_cloud_id, bk_cloud_name, isp, ap_id, creator, is_visible, is_deleted) "
                "values ({}, '{}', 'PrivateCloud', 1, '{}', {}, {})".format(
                    cloud["bk_cloud_id"], cloud["bk_cloud_name"], creator, cloud["is_visible"], cloud["is_deleted"]
                )
            )
            db.commit()
        except Exception as err:
            print(traceback.format_exc())


def backup_pipeline_trees():
    cursor.execute("select * from node_man_pipelinetree")
    trees = cursor.fetchall()
    return trees


def migrate_pipeline_tree(pipeline_trees):
    for tree in pipeline_trees:
        sql = "insert into node_man_pipelinetree(id, tree) values ('{}', '{}')".format(
            tree["id"], tree["tree"].replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
        )
        logger.info("running pipeline tree: {}".format(sql))
        cursor.execute(sql)
    db.commit()


def escape_value(value):
    if type(value) is int:
        return str(value)
    elif type(value) is str:
        value = value.replace("'", "''")
        if (value.startswith("[") and value.endswith("]")) or (value.startswith("{") and value.endswith("}")):
            value = json.dumps(value)
            value = value[1 : len(value) - 1]
        return "'{}'".format(value)
    elif value is None:
        return "null"
    else:
        return "'{}'".format(value)


def upgrade_ee():
    # 删除V1的表
    drop_v1_tables = [
        "DROP TABLE node_man_agentversion;",
        "DROP TABLE node_man_cloud;",
        "DROP TABLE node_man_cmdbeventrecord;",
        "DROP TABLE node_man_cmdbhosts;",
        "DROP TABLE node_man_cpuload;",
        "DROP TABLE node_man_downloadrecord;",
        "DROP TABLE node_man_gseplugindesc;",
        "DROP TABLE node_man_host;",
        "DROP TABLE node_man_hoststatus;",
        "DROP TABLE node_man_job;",
        "DROP TABLE node_man_jobtask;",
        "DROP TABLE node_man_kv;",
        "DROP TABLE node_man_packages;",
        "DROP TABLE node_man_pipelinetree;",
        "DROP TABLE node_man_pluginconfiginstance;",
        "DROP TABLE node_man_pluginconfigtemplate;",
        "DROP TABLE node_man_proccontrol;",
        "DROP TABLE node_man_profile;",
        "DROP TABLE node_man_subscription;",
        "DROP TABLE node_man_subscriptioninstancerecord;",
        "DROP TABLE node_man_subscriptionstep;",
        "DROP TABLE node_man_subscriptiontask;",
        "DROP TABLE node_man_tasklog;",
        "DROP TABLE node_man_uploadpackage;",
        "DELETE FROM django_migrations where app='node_man';",
        "DELETE FROM django_migrations where app='requests_tracker';",
    ]

    # # 删除pipeline表
    # drop_pipeline_tables = [
    #     "DROP TABLE node_man_agentversion;",
    #     "DELETE FROM django_migrations where app='pipeline';"
    # ]
    # 直接迁移数据的表
    direct_migrate_tables = [
        "node_man_packages",
        "node_man_gseplugindesc",
        "node_man_pluginconfiginstance",
        "node_man_pluginconfigtemplate",
        "node_man_proccontrol",
        "node_man_subscription",
        "node_man_subscriptioninstancerecord",
        "node_man_subscriptionstep",
        "node_man_subscriptiontask",
        "node_man_uploadpackage",
        "Excludes",
        "Records",
    ]

    # 新增字段的表需配上默认值
    table_values_map = {
        "node_man_subscriptioninstancerecord": {
            "default_keys": ["need_clean"],
            "default_values": ['"0"'],
            "where": "where is_latest=1",
        }
    }

    insert_sqls = []
    for table_name in direct_migrate_tables:
        logger.info("migrating {}".format(table_name))
        cursor.execute("select * from {} {};".format(table_name, table_values_map.get(table_name, {}).get("where", "")))
        table_values = cursor.fetchall()
        if table_values:
            default_keys = table_values_map.get(table_name, {}).get("default_keys", [])
            default_values = table_values_map.get(table_name, {}).get("default_values", [])

            table_key_lists = default_keys + list(table_values[0].keys())
            table_keys = ",".join("`{}`".format(key) for key in table_key_lists)
            insert_values = []
            for table_value in table_values:
                single_value = ",".join(
                    default_values + ["{}".format(escape_value(value)) for value in table_value.values()]
                )
                insert_sqls.append("INSERT INTO {} ({}) VALUES ({});".format(table_name, table_keys, single_value))
    # 生成proxy插入语句
    hosts, id_data, proxy_process_data = backup_proxy_host()
    # 生成process_status插入语句
    process_data, process_data_no_listen_port = backup_host_status()

    pipeline_trees = backup_pipeline_trees()

    cursor.execute("select * from node_man_cloud;")
    clouds = cursor.fetchall()
    try:
        # 执行sql语句
        cursor.execute("SET foreign_key_checks=0;")
        for sql in drop_v1_tables:
            logger.info("running drop sql: {}".format(sql))
            cursor.execute(sql)
        db.commit()

        # migrate数据库
        create_tables = [
            "CREATE TABLE `node_man_accesspoint` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(255) NOT NULL, `ap_type` varchar(255) NOT NULL, `region_id` varchar(255) NOT NULL, `city_id` varchar(255) NOT NULL, `servers` json NOT NULL, `zk_hosts` json NOT NULL, `zk_account` varchar(255) NOT NULL, `zk_password` longtext NULL, `package_inner_url` longtext NOT NULL, `package_outer_url` longtext NOT NULL, `agent_config` json NOT NULL, `status` varchar(255) NOT NULL, `description` longtext NOT NULL, `is_enabled` bool NOT NULL, `is_default` bool NOT NULL);",
            "CREATE TABLE `node_man_cloud` (`bk_cloud_id` integer NOT NULL PRIMARY KEY, `bk_cloud_name` varchar(45) NOT NULL, `isp` varchar(45) NULL, `ap_id` integer NULL, `creator` json NOT NULL, `is_visible` bool NOT NULL, `is_deleted` bool NOT NULL);",
            "CREATE TABLE `node_man_cmdbeventrecord` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `bk_biz_id` integer NOT NULL, `subscription_id` varchar(50) NOT NULL, `event_type` varchar(20) NOT NULL, `action` varchar(20) NOT NULL, `obj_type` varchar(32) NOT NULL, `data` json NOT NULL, `create_time` datetime(6) NOT NULL);",
            "CREATE TABLE `node_man_downloadrecord` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `category` varchar(32) NOT NULL, `query_params` varchar(256) NOT NULL, `file_path` varchar(256) NOT NULL, `task_status` integer NOT NULL, `error_message` longtext NOT NULL, `creator` varchar(64) NOT NULL, `create_time` datetime(6) NOT NULL, `finish_time` datetime(6) NOT NULL, `source_app_code` varchar(64) NOT NULL);",
            "CREATE TABLE `node_man_globalsettings` (`key` varchar(255) NOT NULL PRIMARY KEY, `v_json` json NOT NULL);",
            "CREATE TABLE `node_man_gseplugindesc` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(32) NOT NULL UNIQUE, `description` longtext NOT NULL, `scenario` longtext NOT NULL, `description_en` longtext NULL, `scenario_en` longtext NULL, `category` varchar(32) NOT NULL, `launch_node` varchar(32) NOT NULL, `config_file` varchar(128) NULL, `config_format` varchar(32) NULL, `use_db` bool NOT NULL, `auto_launch` bool NOT NULL, `is_binary` bool NOT NULL);",
            "CREATE TABLE `node_man_host` (`bk_host_id` integer NOT NULL PRIMARY KEY, `bk_biz_id` integer NOT NULL, `bk_cloud_id` integer NOT NULL, `inner_ip` varchar(45) NOT NULL, `outer_ip` varchar(45) NULL, `login_ip` varchar(45) NULL, `data_ip` varchar(45) NULL, `os_type` varchar(45) NOT NULL, `node_type` varchar(45) NOT NULL, `node_from` varchar(45) NOT NULL, `ap_id` integer NULL, `upstream_nodes` json NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NULL);",
            "CREATE TABLE `node_man_identitydata` (`bk_host_id` integer NOT NULL PRIMARY KEY, `auth_type` varchar(45) NOT NULL, `account` varchar(45) NOT NULL, `password` longtext NULL, `port` integer NULL, `key` longtext NULL, `extra_data` json NULL, `retention` integer NOT NULL, `updated_at` datetime(6) NULL);",
            "CREATE TABLE `node_man_job` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_by` varchar(45) NOT NULL, `job_type` varchar(45) NOT NULL, `subscription_id` integer NOT NULL, `task_id_list` json NOT NULL, `start_time` datetime(6) NOT NULL, `end_time` datetime(6) NULL, `status` varchar(45) NOT NULL, `global_params` json NULL, `statistics` json NULL, `bk_biz_scope` json NOT NULL, `error_hosts` json NOT NULL);",
            "CREATE TABLE `node_man_jobtask` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `job_id` integer NOT NULL, `bk_host_id` integer NOT NULL, `instance_id` varchar(45) NOT NULL, `pipeline_id` varchar(50) NOT NULL, `status` varchar(45) NOT NULL, `current_step` varchar(45) NOT NULL, `create_time` datetime(6) NOT NULL, `update_time` datetime(6) NOT NULL, `end_time` datetime(6) NULL);",
            "CREATE TABLE `node_man_packages` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `pkg_name` varchar(128) NOT NULL, `version` varchar(128) NOT NULL, `module` varchar(32) NOT NULL, `project` varchar(32) NOT NULL, `pkg_size` integer NOT NULL, `pkg_path` varchar(128) NOT NULL, `md5` varchar(32) NOT NULL, `pkg_mtime` varchar(48) NOT NULL, `pkg_ctime` varchar(48) NOT NULL, `location` varchar(512) NOT NULL, `os` varchar(32) NOT NULL, `cpu_arch` varchar(32) NOT NULL, `is_release_version` bool NOT NULL, `is_ready` bool NOT NULL);",
            "CREATE TABLE `node_man_pipelinetree` (`id` varchar(32) NOT NULL PRIMARY KEY, `tree` json NOT NULL);",
            "CREATE TABLE `node_man_pluginconfiginstance` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `plugin_config_template` integer NOT NULL, `render_data` longtext NOT NULL, `data_md5` varchar(50) NOT NULL, `creator` varchar(64) NOT NULL, `create_time` datetime(6) NOT NULL, `source_app_code` varchar(64) NOT NULL);",
            "CREATE TABLE `node_man_proccontrol` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `module` varchar(32) NOT NULL, `project` varchar(32) NOT NULL, `plugin_package_id` integer NOT NULL, `install_path` longtext NOT NULL, `log_path` longtext NOT NULL, `data_path` longtext NOT NULL, `pid_path` longtext NOT NULL, `start_cmd` longtext NOT NULL, `stop_cmd` longtext NOT NULL, `restart_cmd` longtext NOT NULL, `reload_cmd` longtext NOT NULL, `kill_cmd` longtext NOT NULL, `version_cmd` longtext NOT NULL, `health_cmd` longtext NOT NULL, `debug_cmd` longtext NOT NULL, `os` varchar(32) NOT NULL, `process_name` varchar(128) NULL, `port_range` longtext NULL, `need_delegate` bool NOT NULL);",
            "CREATE TABLE `node_man_processstatus` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `bk_host_id` integer NOT NULL, `name` varchar(45) NOT NULL, `status` varchar(45) NOT NULL, `is_auto` varchar(45) NOT NULL, `version` varchar(45) NULL, `proc_type` varchar(45) NOT NULL, `configs` json NOT NULL, `listen_ip` varchar(45) NULL, `listen_port` integer NULL, `setup_path` longtext NOT NULL, `log_path` longtext NOT NULL, `data_path` longtext NOT NULL, `pid_path` longtext NOT NULL, `group_id` varchar(50) NOT NULL, `source_type` varchar(128) NOT NULL, `source_id` varchar(128) NULL);",
            "CREATE TABLE `node_man_profile` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `bk_username` varchar(45) NOT NULL, `favorite` json NOT NULL, `update_time` datetime(6) NOT NULL);",
            "CREATE TABLE `node_man_subscription` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `bk_biz_id` integer NULL, `object_type` varchar(20) NOT NULL, `node_type` varchar(20) NOT NULL, `nodes` json NOT NULL, `target_hosts` json NULL, `from_system` varchar(30) NOT NULL, `update_time` datetime(6) NOT NULL, `create_time` datetime(6) NOT NULL, `creator` varchar(64) NOT NULL, `enable` bool NOT NULL, `is_deleted` bool NOT NULL);",
            "CREATE TABLE `node_man_subscriptioninstancerecord` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `task_id` integer NOT NULL, `subscription_id` integer NOT NULL, `instance_id` varchar(50) NOT NULL, `instance_info` json NOT NULL, `steps` json NOT NULL, `pipeline_id` varchar(50) NOT NULL, `update_time` datetime(6) NOT NULL, `create_time` datetime(6) NOT NULL, `need_clean` bool NOT NULL, `is_latest` bool NOT NULL);",
            "CREATE TABLE `node_man_subscriptiontask` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `subscription_id` integer NOT NULL, `scope` json NOT NULL, `actions` json NOT NULL, `create_time` datetime(6) NOT NULL, `is_auto_trigger` bool NOT NULL);",
            "CREATE TABLE `node_man_uploadpackage` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `file_name` varchar(64) NOT NULL, `module` varchar(32) NOT NULL, `file_path` varchar(128) NOT NULL, `file_size` integer NOT NULL, `md5` varchar(32) NOT NULL, `upload_time` datetime(6) NOT NULL, `creator` varchar(64) NOT NULL, `source_app_code` varchar(64) NOT NULL);",
            "CREATE TABLE `node_man_subscriptionstep` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `subscription_id` integer NOT NULL, `index` integer NOT NULL, `step_id` varchar(64) NOT NULL, `type` varchar(20) NOT NULL, `config` json NOT NULL, `params` json NOT NULL);",
            "CREATE TABLE `node_man_pluginconfigtemplate` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `plugin_name` varchar(32) NOT NULL, `plugin_version` varchar(128) NOT NULL, `name` varchar(128) NOT NULL, `version` varchar(128) NOT NULL, `format` varchar(16) NOT NULL, `file_path` varchar(128) NOT NULL, `content` longtext NOT NULL, `is_release_version` bool NOT NULL, `creator` varchar(64) NOT NULL, `create_time` datetime(6) NOT NULL, `source_app_code` varchar(64) NOT NULL);",
            "CREATE INDEX `node_man_cmdbeventrecord_bk_biz_id_ceef7b40` ON `node_man_cmdbeventrecord` (`bk_biz_id`);",
            "CREATE INDEX `node_man_cmdbeventrecord_subscription_id_40f64e79` ON `node_man_cmdbeventrecord` (`subscription_id`);",
            "CREATE INDEX `node_man_job_subscription_id_66d5dd8f` ON `node_man_job` (`subscription_id`);",
            "CREATE INDEX `node_man_packages_project_599c6474` ON `node_man_packages` (`project`);",
            "CREATE INDEX `node_man_packages_os_4c08c4de` ON `node_man_packages` (`os`);",
            "CREATE INDEX `node_man_packages_cpu_arch_bdefbd6c` ON `node_man_packages` (`cpu_arch`);",
            "CREATE INDEX `node_man_packages_is_release_version_5839e52e` ON `node_man_packages` (`is_release_version`);",
            "CREATE INDEX `node_man_pluginconfiginstance_plugin_config_template_532138e3` ON `node_man_pluginconfiginstance` (`plugin_config_template`);",
            "CREATE INDEX `node_man_processstatus_bk_host_id_3bcd512d` ON `node_man_processstatus` (`bk_host_id`);",
            "CREATE INDEX `node_man_processstatus_name_e9030502` ON `node_man_processstatus` (`name`);",
            "CREATE INDEX `node_man_processstatus_status_51dc1f80` ON `node_man_processstatus` (`status`);",
            "CREATE INDEX `node_man_processstatus_group_id_e049f18d` ON `node_man_processstatus` (`group_id`);",
            "CREATE INDEX `node_man_subscription_bk_biz_id_4ee72393` ON `node_man_subscription` (`bk_biz_id`);",
            "CREATE INDEX `node_man_subscription_enable_adb38208` ON `node_man_subscription` (`enable`);",
            "CREATE INDEX `node_man_subscriptioninstancerecord_task_id_60347e2e` ON `node_man_subscriptioninstancerecord` (`task_id`);",
            "CREATE INDEX `node_man_subscriptioninstancerecord_subscription_id_7f191490` ON `node_man_subscriptioninstancerecord` (`subscription_id`);",
            "CREATE INDEX `node_man_subscriptioninstancerecord_instance_id_387f11f5` ON `node_man_subscriptioninstancerecord` (`instance_id`);",
            "CREATE INDEX `node_man_subscriptiontask_subscription_id_d9370f40` ON `node_man_subscriptiontask` (`subscription_id`);",
            "CREATE INDEX `node_man_uploadpackage_file_name_c64aa93d` ON `node_man_uploadpackage` (`file_name`);",
            "ALTER TABLE `node_man_subscriptionstep` ADD CONSTRAINT `node_man_subscriptionstep_subscription_id_index_7a8cc815_uniq` UNIQUE (`subscription_id`, `index`);",
            "ALTER TABLE `node_man_subscriptionstep` ADD CONSTRAINT `node_man_subscriptionstep_subscription_id_step_id_238ea3a4_uniq` UNIQUE (`subscription_id`, `step_id`);",
            "CREATE INDEX `node_man_subscriptionstep_subscription_id_a54b7b75` ON `node_man_subscriptionstep` (`subscription_id`);",
            "ALTER TABLE `node_man_pluginconfigtemplate` ADD CONSTRAINT `node_man_pluginconfigtem_plugin_name_plugin_versi_2c31949f_uniq` UNIQUE (`plugin_name`, `plugin_version`, `name`, `version`);",
            "CREATE INDEX `node_man_pluginconfigtemplate_plugin_name_49d483c6` ON `node_man_pluginconfigtemplate` (`plugin_name`);",
        ]
        for sql in create_tables:
            logger.info("running create sql: {}".format(sql))
            cursor.execute(sql)

        cursor.execute(
            "INSERT INTO django_migrations(app, name, applied) VALUES ('node_man', '0001_initial', now());",
        )

        for sql in insert_sqls:
            logger.info("running insert sql: {}".format(sql))
            try:
                cursor.execute(sql)
            except Exception as error:
                logger.error("insert_sql_failed: {}".format(sql))
        db.commit()

        migrate_proxy(hosts, id_data, proxy_process_data)
        migrate_process_status(process_data, process_data_no_listen_port)
        migrate_cloud_creator(clouds)
        migrate_pipeline_tree(pipeline_trees)

    except Exception as e:
        print("upgrade error: %s" % traceback.format_exc())
        # 发生错误时回滚
        print("Start Rolling Back...")
        db.rollback()
        print("Rolling Back End")


def upgrade_ce():
    # 删除V1的表
    drop_v1_tables = [
        "DROP TABLE node_man_agentversion;",
        "DROP TABLE node_man_cloud;",
        "DROP TABLE node_man_cmdbhosts;",
        "DROP TABLE node_man_cpuload;",
        "DROP TABLE node_man_downloadrecord;",
        "DROP TABLE node_man_gseplugindesc;",
        "DROP TABLE node_man_host;",
        "DROP TABLE node_man_hoststatus;",
        "DROP TABLE node_man_job;",
        "DROP TABLE node_man_jobtask;",
        "DROP TABLE node_man_kv;",
        "DROP TABLE node_man_packages;",
        "DROP TABLE node_man_pluginconfiginstance;",
        "DROP TABLE node_man_pluginconfigtemplate;",
        "DROP TABLE node_man_proccontrol;",
        "DROP TABLE node_man_profile;",
        "DROP TABLE node_man_tasklog;",
        "DROP TABLE node_man_uploadpackage;",
        "DROP TABLE Records",
        "DROP TABLE Excludes",
        "DROP TABLE Filters",
        "DELETE FROM django_migrations where app='node_man';",
        "DELETE FROM django_migrations where app='requests_tracker';",
    ]

    # 直接迁移数据的表
    direct_migrate_tables = [
        "node_man_packages",
        "node_man_gseplugindesc",
        "node_man_pluginconfiginstance",
        "node_man_pluginconfigtemplate",
        "node_man_proccontrol",
        "node_man_uploadpackage",
    ]

    # 新增字段的表需配上默认值
    table_values_map = {
        "node_man_subscriptioninstancerecord": {
            "default_keys": ["need_clean"],
            "default_values": ['"0"'],
            "where": "where is_latest=1",
        }
    }

    insert_sqls = []
    for table_name in direct_migrate_tables:
        logger.info("migrating {}".format(table_name))
        cursor.execute("select * from {} {};".format(table_name, table_values_map.get(table_name, {}).get("where", "")))
        table_values = cursor.fetchall()
        if table_values:
            default_keys = table_values_map.get(table_name, {}).get("default_keys", [])
            default_values = table_values_map.get(table_name, {}).get("default_values", [])

            table_key_lists = default_keys + list(table_values[0].keys())
            table_keys = ",".join("`{}`".format(key) for key in table_key_lists)
            insert_values = []
            for table_value in table_values:
                single_value = ",".join(
                    default_values + ["{}".format(escape_value(value)) for value in table_value.values()]
                )
                insert_sqls.append("INSERT INTO {} ({}) VALUES ({});".format(table_name, table_keys, single_value))
    # 生成proxy插入语句
    hosts, id_data, proxy_process_data = backup_proxy_host()

    cursor.execute("select * from node_man_cloud;")
    clouds = cursor.fetchall()
    try:
        # 执行sql语句
        cursor.execute("SET foreign_key_checks=0;")
        for sql in drop_v1_tables:
            logger.info("running drop sql: {}".format(sql))
            cursor.execute(sql)
        db.commit()

        # migrate数据库
        create_tables = [
            "CREATE TABLE `node_man_accesspoint` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(255) NOT NULL, `ap_type` varchar(255) NOT NULL, `region_id` varchar(255) NOT NULL, `city_id` varchar(255) NOT NULL, `servers` json NOT NULL, `zk_hosts` json NOT NULL, `zk_account` varchar(255) NOT NULL, `zk_password` longtext NULL, `package_inner_url` longtext NOT NULL, `package_outer_url` longtext NOT NULL, `agent_config` json NOT NULL, `status` varchar(255) NOT NULL, `description` longtext NOT NULL, `is_enabled` bool NOT NULL, `is_default` bool NOT NULL);",
            "CREATE TABLE `node_man_cloud` (`bk_cloud_id` integer NOT NULL PRIMARY KEY, `bk_cloud_name` varchar(45) NOT NULL, `isp` varchar(45) NULL, `ap_id` integer NULL, `creator` json NOT NULL, `is_visible` bool NOT NULL, `is_deleted` bool NOT NULL);",
            "CREATE TABLE `node_man_cmdbeventrecord` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `bk_biz_id` integer NOT NULL, `subscription_id` varchar(50) NOT NULL, `event_type` varchar(20) NOT NULL, `action` varchar(20) NOT NULL, `obj_type` varchar(32) NOT NULL, `data` json NOT NULL, `create_time` datetime(6) NOT NULL);",
            "CREATE TABLE `node_man_downloadrecord` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `category` varchar(32) NOT NULL, `query_params` varchar(256) NOT NULL, `file_path` varchar(256) NOT NULL, `task_status` integer NOT NULL, `error_message` longtext NOT NULL, `creator` varchar(64) NOT NULL, `create_time` datetime(6) NOT NULL, `finish_time` datetime(6) NOT NULL, `source_app_code` varchar(64) NOT NULL);",
            "CREATE TABLE `node_man_globalsettings` (`key` varchar(255) NOT NULL PRIMARY KEY, `v_json` json NOT NULL);",
            "CREATE TABLE `node_man_gseplugindesc` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `name` varchar(32) NOT NULL UNIQUE, `description` longtext NOT NULL, `scenario` longtext NOT NULL, `description_en` longtext NULL, `scenario_en` longtext NULL, `category` varchar(32) NOT NULL, `launch_node` varchar(32) NOT NULL, `config_file` varchar(128) NULL, `config_format` varchar(32) NULL, `use_db` bool NOT NULL, `auto_launch` bool NOT NULL, `is_binary` bool NOT NULL);",
            "CREATE TABLE `node_man_host` (`bk_host_id` integer NOT NULL PRIMARY KEY, `bk_biz_id` integer NOT NULL, `bk_cloud_id` integer NOT NULL, `inner_ip` varchar(45) NOT NULL, `outer_ip` varchar(45) NULL, `login_ip` varchar(45) NULL, `data_ip` varchar(45) NULL, `os_type` varchar(45) NOT NULL, `node_type` varchar(45) NOT NULL, `node_from` varchar(45) NOT NULL, `ap_id` integer NULL, `upstream_nodes` json NOT NULL, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NULL);",
            "CREATE TABLE `node_man_identitydata` (`bk_host_id` integer NOT NULL PRIMARY KEY, `auth_type` varchar(45) NOT NULL, `account` varchar(45) NOT NULL, `password` longtext NULL, `port` integer NULL, `key` longtext NULL, `extra_data` json NULL, `retention` integer NOT NULL, `updated_at` datetime(6) NULL);",
            "CREATE TABLE `node_man_job` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_by` varchar(45) NOT NULL, `job_type` varchar(45) NOT NULL, `subscription_id` integer NOT NULL, `task_id_list` json NOT NULL, `start_time` datetime(6) NOT NULL, `end_time` datetime(6) NULL, `status` varchar(45) NOT NULL, `global_params` json NULL, `statistics` json NULL, `bk_biz_scope` json NOT NULL, `error_hosts` json NOT NULL);",
            "CREATE TABLE `node_man_jobtask` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `job_id` integer NOT NULL, `bk_host_id` integer NOT NULL, `instance_id` varchar(45) NOT NULL, `pipeline_id` varchar(50) NOT NULL, `status` varchar(45) NOT NULL, `current_step` varchar(45) NOT NULL, `create_time` datetime(6) NOT NULL, `update_time` datetime(6) NOT NULL, `end_time` datetime(6) NULL);",
            "CREATE TABLE `node_man_packages` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `pkg_name` varchar(128) NOT NULL, `version` varchar(128) NOT NULL, `module` varchar(32) NOT NULL, `project` varchar(32) NOT NULL, `pkg_size` integer NOT NULL, `pkg_path` varchar(128) NOT NULL, `md5` varchar(32) NOT NULL, `pkg_mtime` varchar(48) NOT NULL, `pkg_ctime` varchar(48) NOT NULL, `location` varchar(512) NOT NULL, `os` varchar(32) NOT NULL, `cpu_arch` varchar(32) NOT NULL, `is_release_version` bool NOT NULL, `is_ready` bool NOT NULL);",
            "CREATE TABLE `node_man_pipelinetree` (`id` varchar(32) NOT NULL PRIMARY KEY, `tree` json NOT NULL);",
            "CREATE TABLE `node_man_pluginconfiginstance` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `plugin_config_template` integer NOT NULL, `render_data` longtext NOT NULL, `data_md5` varchar(50) NOT NULL, `creator` varchar(64) NOT NULL, `create_time` datetime(6) NOT NULL, `source_app_code` varchar(64) NOT NULL);",
            "CREATE TABLE `node_man_proccontrol` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `module` varchar(32) NOT NULL, `project` varchar(32) NOT NULL, `plugin_package_id` integer NOT NULL, `install_path` longtext NOT NULL, `log_path` longtext NOT NULL, `data_path` longtext NOT NULL, `pid_path` longtext NOT NULL, `start_cmd` longtext NOT NULL, `stop_cmd` longtext NOT NULL, `restart_cmd` longtext NOT NULL, `reload_cmd` longtext NOT NULL, `kill_cmd` longtext NOT NULL, `version_cmd` longtext NOT NULL, `health_cmd` longtext NOT NULL, `debug_cmd` longtext NOT NULL, `os` varchar(32) NOT NULL, `process_name` varchar(128) NULL, `port_range` longtext NULL, `need_delegate` bool NOT NULL);",
            "CREATE TABLE `node_man_processstatus` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `bk_host_id` integer NOT NULL, `name` varchar(45) NOT NULL, `status` varchar(45) NOT NULL, `is_auto` varchar(45) NOT NULL, `version` varchar(45) NULL, `proc_type` varchar(45) NOT NULL, `configs` json NOT NULL, `listen_ip` varchar(45) NULL, `listen_port` integer NULL, `setup_path` longtext NOT NULL, `log_path` longtext NOT NULL, `data_path` longtext NOT NULL, `pid_path` longtext NOT NULL, `group_id` varchar(50) NOT NULL, `source_type` varchar(128) NOT NULL, `source_id` varchar(128) NULL);",
            "CREATE TABLE `node_man_profile` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `bk_username` varchar(45) NOT NULL, `favorite` json NOT NULL, `update_time` datetime(6) NOT NULL);",
            "CREATE TABLE `node_man_subscription` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `bk_biz_id` integer NULL, `object_type` varchar(20) NOT NULL, `node_type` varchar(20) NOT NULL, `nodes` json NOT NULL, `target_hosts` json NULL, `from_system` varchar(30) NOT NULL, `update_time` datetime(6) NOT NULL, `create_time` datetime(6) NOT NULL, `creator` varchar(64) NOT NULL, `enable` bool NOT NULL, `is_deleted` bool NOT NULL);",
            "CREATE TABLE `node_man_subscriptioninstancerecord` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `task_id` integer NOT NULL, `subscription_id` integer NOT NULL, `instance_id` varchar(50) NOT NULL, `instance_info` json NOT NULL, `steps` json NOT NULL, `pipeline_id` varchar(50) NOT NULL, `update_time` datetime(6) NOT NULL, `create_time` datetime(6) NOT NULL, `need_clean` bool NOT NULL, `is_latest` bool NOT NULL);",
            "CREATE TABLE `node_man_subscriptiontask` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `subscription_id` integer NOT NULL, `scope` json NOT NULL, `actions` json NOT NULL, `create_time` datetime(6) NOT NULL, `is_auto_trigger` bool NOT NULL);",
            "CREATE TABLE `node_man_uploadpackage` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `file_name` varchar(64) NOT NULL, `module` varchar(32) NOT NULL, `file_path` varchar(128) NOT NULL, `file_size` integer NOT NULL, `md5` varchar(32) NOT NULL, `upload_time` datetime(6) NOT NULL, `creator` varchar(64) NOT NULL, `source_app_code` varchar(64) NOT NULL);",
            "CREATE TABLE `node_man_subscriptionstep` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `subscription_id` integer NOT NULL, `index` integer NOT NULL, `step_id` varchar(64) NOT NULL, `type` varchar(20) NOT NULL, `config` json NOT NULL, `params` json NOT NULL);",
            "CREATE TABLE `node_man_pluginconfigtemplate` (`id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY, `plugin_name` varchar(32) NOT NULL, `plugin_version` varchar(128) NOT NULL, `name` varchar(128) NOT NULL, `version` varchar(128) NOT NULL, `format` varchar(16) NOT NULL, `file_path` varchar(128) NOT NULL, `content` longtext NOT NULL, `is_release_version` bool NOT NULL, `creator` varchar(64) NOT NULL, `create_time` datetime(6) NOT NULL, `source_app_code` varchar(64) NOT NULL);",
            "CREATE INDEX `node_man_cmdbeventrecord_bk_biz_id_ceef7b40` ON `node_man_cmdbeventrecord` (`bk_biz_id`);",
            "CREATE INDEX `node_man_cmdbeventrecord_subscription_id_40f64e79` ON `node_man_cmdbeventrecord` (`subscription_id`);",
            "CREATE INDEX `node_man_job_subscription_id_66d5dd8f` ON `node_man_job` (`subscription_id`);",
            "CREATE INDEX `node_man_packages_project_599c6474` ON `node_man_packages` (`project`);",
            "CREATE INDEX `node_man_packages_os_4c08c4de` ON `node_man_packages` (`os`);",
            "CREATE INDEX `node_man_packages_cpu_arch_bdefbd6c` ON `node_man_packages` (`cpu_arch`);",
            "CREATE INDEX `node_man_packages_is_release_version_5839e52e` ON `node_man_packages` (`is_release_version`);",
            "CREATE INDEX `node_man_pluginconfiginstance_plugin_config_template_532138e3` ON `node_man_pluginconfiginstance` (`plugin_config_template`);",
            "CREATE INDEX `node_man_processstatus_bk_host_id_3bcd512d` ON `node_man_processstatus` (`bk_host_id`);",
            "CREATE INDEX `node_man_processstatus_name_e9030502` ON `node_man_processstatus` (`name`);",
            "CREATE INDEX `node_man_processstatus_status_51dc1f80` ON `node_man_processstatus` (`status`);",
            "CREATE INDEX `node_man_processstatus_group_id_e049f18d` ON `node_man_processstatus` (`group_id`);",
            "CREATE INDEX `node_man_subscription_bk_biz_id_4ee72393` ON `node_man_subscription` (`bk_biz_id`);",
            "CREATE INDEX `node_man_subscription_enable_adb38208` ON `node_man_subscription` (`enable`);",
            "CREATE INDEX `node_man_subscriptioninstancerecord_task_id_60347e2e` ON `node_man_subscriptioninstancerecord` (`task_id`);",
            "CREATE INDEX `node_man_subscriptioninstancerecord_subscription_id_7f191490` ON `node_man_subscriptioninstancerecord` (`subscription_id`);",
            "CREATE INDEX `node_man_subscriptioninstancerecord_instance_id_387f11f5` ON `node_man_subscriptioninstancerecord` (`instance_id`);",
            "CREATE INDEX `node_man_subscriptiontask_subscription_id_d9370f40` ON `node_man_subscriptiontask` (`subscription_id`);",
            "CREATE INDEX `node_man_uploadpackage_file_name_c64aa93d` ON `node_man_uploadpackage` (`file_name`);",
            "ALTER TABLE `node_man_subscriptionstep` ADD CONSTRAINT `node_man_subscriptionstep_subscription_id_index_7a8cc815_uniq` UNIQUE (`subscription_id`, `index`);",
            "ALTER TABLE `node_man_subscriptionstep` ADD CONSTRAINT `node_man_subscriptionstep_subscription_id_step_id_238ea3a4_uniq` UNIQUE (`subscription_id`, `step_id`);",
            "CREATE INDEX `node_man_subscriptionstep_subscription_id_a54b7b75` ON `node_man_subscriptionstep` (`subscription_id`);",
            "ALTER TABLE `node_man_pluginconfigtemplate` ADD CONSTRAINT `node_man_pluginconfigtem_plugin_name_plugin_versi_2c31949f_uniq` UNIQUE (`plugin_name`, `plugin_version`, `name`, `version`);",
            "CREATE INDEX `node_man_pluginconfigtemplate_plugin_name_49d483c6` ON `node_man_pluginconfigtemplate` (`plugin_name`);",
        ]
        for sql in create_tables:
            logger.info("running create sql: {}".format(sql))
            cursor.execute(sql)

        cursor.execute(
            "INSERT INTO django_migrations(app, name, applied) VALUES ('node_man', '0001_initial', now());",
        )

        for sql in insert_sqls:
            logger.info("running insert sql: {}".format(sql))
            try:
                cursor.execute(sql)
            except Exception as error:
                logger.error("insert_sql_failed: {}".format(sql))
        db.commit()

        migrate_proxy(hosts, id_data, proxy_process_data)
        migrate_cloud_creator(clouds)

    except Exception as e:
        print("upgrade error: %s" % traceback.format_exc())
        # 发生错误时回滚
        print("Start Rolling Back...")
        db.rollback()
        print("Rolling Back End")


if __name__ == "__main__":

    # 打开数据库连接
    db = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USERNAME, passwd=DB_PASSWORD, db=DB_NAME, charset="utf8")

    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = db.cursor(pymysql.cursors.DictCursor)
    current_path = os.path.abspath(os.path.dirname(__file__))

    if RUN_ENV == "ee":
        upgrade_ee()
    elif RUN_ENV == "ce":
        upgrade_ce()
    else:
        print("not supported~")

    # 关闭数据库连接
    db.close()
