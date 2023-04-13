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
import argparse
import csv
import logging
import os
import sys
import time

import pymysql

EXPORT_PATH = "node_man_export"
CLOUD_INFO_PATH = "cloud_info.csv"
PROXY_HOST_INFO_PATH = "proxy_host_info.csv"


class ExportHelper(object):
    def __init__(self, db, cursor):
        self.db = db
        self.cursor = cursor
        self.current_path = os.path.abspath(os.path.dirname(__file__))
        self.export_path = os.path.join(self.current_path, EXPORT_PATH)
        self.cloud_info_path = os.path.join(self.export_path, CLOUD_INFO_PATH)
        self.proxy_host_info_path = os.path.join(self.export_path, PROXY_HOST_INFO_PATH)

    def export_proxy_host_info(self, with_v6_field: bool):
        self.check_file_exists(self.proxy_host_info_path)
        logg.info("start to export proxy info")
        self.cursor.execute("select * from node_man_host where node_type='PROXY'")
        proxy_hosts = self.cursor.fetchall()
        if not proxy_hosts:
            logg.error("no proxy host info to export")
        v6_fields = ["inner_ipv6", "outer_ipv6"]
        proxy_export_field_list = [
            "bk_biz_id",
            "bk_cloud_id",
            "inner_ip",
            "outer_ip",
            "login_ip",
            "data_ip",
            "ap_id",
            "bk_host_id",
        ]
        if with_v6_field:
            for v6_field in v6_fields:
                proxy_export_field_list.append(v6_field)
        with open(self.proxy_host_info_path, "w+") as proxy_csv_file:
            writer = csv.writer(proxy_csv_file)
            writer.writerow(proxy_export_field_list)
            for proxy_host in proxy_hosts:
                proxy_export_info = [proxy_host[field] for field in proxy_export_field_list]
                proxy_debug_logg = ", ".join([f"{field}: {proxy_host[field]}" for field in proxy_export_field_list])
                logg.debug(f"export proxy host info: [{proxy_debug_logg}]")
                writer.writerow(proxy_export_info)
        logg.info("export proxy info success")

    def export_cloud_info(self):
        self.check_file_exists(self.cloud_info_path)
        logg.info("start to export cloud info")
        self.cursor.execute("select * from node_man_cloud")
        clouds = self.cursor.fetchall()
        if not clouds:
            logg.error("no cloud info to export")
        export_field_list = ["bk_cloud_id", "bk_cloud_name", "isp", "ap_id", "creator", "is_visible", "is_deleted"]
        with open(self.cloud_info_path, "w+") as cloud_csv_file:
            writer = csv.writer(cloud_csv_file)
            writer.writerow(export_field_list)
            for cloud in clouds:
                export_cloud_info = [cloud[field] for field in export_field_list]
                writer.writerow(export_cloud_info)
                cloud_debug_logg = ", ".join([f"{field}: {cloud[field]}" for field in export_field_list])
                logg.debug(f"export cloud info: [{cloud_debug_logg}]")

        logg.info("export cloud info success")

    @classmethod
    def check_file_exists(cls, file_path):
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if not os.path.exists(file_path):
            return
        else:
            user_input = input(f"File {file_path} already exists. Do you want to overwrite it? (yes/no)")
            if not user_input.lower() == "yes":
                logg.info(f"File {file_path} already exists. Skip it.")
                sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, help="MySQL Target Ip", default="127.0.0.1")
    parser.add_argument("--account", type=str, help="MySQL account", default="root")
    parser.add_argument("--password", type=str, help="MySQL password")
    parser.add_argument("--port", type=int, help="MySQL port", default="3306")
    parser.add_argument("--dbname", type=str, help="NodeMan Database Name", default="bk_nodeman")
    parser.add_argument("--only-cloud", help="Only export cloud info", action="store_true")
    parser.add_argument("--only-proxy", help="Only export proxy host info", action="store_true")
    parser.add_argument(
        "--with-v6-field", help="Export proxy host info with ipv6 fields", action="store_true", default=False
    )

    args = parser.parse_args()
    MYSQL_USER = args.account
    MYSQL_HOST = args.host
    MYSQL_PORT = args.port
    MYSQL_PASSWORD = args.password
    DB_NAME = args.dbname
    ONLY_CLOUD = args.only_cloud
    ONLY_PROXY = args.only_proxy
    WITH_V6_FIELD = args.with_v6_field

    logg = logging.getLogger("export")
    logg.setLevel(logging.DEBUG)
    rq = time.strftime("%Y%m%d%H%M", time.localtime(time.time()))
    script_path = os.path.dirname(os.path.abspath(__file__))
    logfile: str = os.path.join(script_path, EXPORT_PATH, rq + ".log")
    logfile_dir_path: str = os.path.dirname(logfile)
    if not os.path.exists(logfile_dir_path):
        os.makedirs(logfile_dir_path)
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    file_handler.setFormatter(formatter)
    logg.addHandler(file_handler)
    steam_handler = logging.StreamHandler()
    steam_handler.setLevel(logging.INFO)
    steam_handler.setFormatter(formatter)
    logg.addHandler(steam_handler)

    db = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=DB_NAME, charset="utf8"
    )
    cursor = db.cursor(pymysql.cursors.DictCursor)

    export_helper = ExportHelper(db, cursor)
    export_helper.export_cloud_info() if not ONLY_PROXY else None
    export_helper.export_proxy_host_info(with_v6_field=WITH_V6_FIELD) if not ONLY_CLOUD else None

    db.close()
