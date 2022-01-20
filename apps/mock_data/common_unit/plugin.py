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
from apps.node_man import constants

# 插件名称
PLUGIN_NAME = "test_plugin"

# 插件包版本
PACKAGE_VERSION = "1.0.1"


GSE_PLUGIN_DESC_MODEL_DATA = {
    "name": PLUGIN_NAME,
    "description": "单元测试插件",
    "description_en": "plugin for unittest",
    "scenario": "单元测试插件",
    "scenario_en": "plugin for unittest",
    "category": constants.CategoryType.official,
    "launch_node": "all",
    "config_file": "test_plugin.conf",
    "config_format": "yaml",
    "use_db": 0,
    "is_binary": 1,
    "auto_launch": 0,
}

PACKAGES_MODEL_DATA = {
    "id": 1,
    "pkg_name": f"{PLUGIN_NAME}-{PACKAGE_VERSION}.tgz",
    "version": PACKAGE_VERSION,
    "module": "gse_plugin",
    "project": PLUGIN_NAME,
    "pkg_size": 0,
    "pkg_path": "",
    "md5": "",
    "pkg_mtime": "",
    "pkg_ctime": "",
    "location": "",
    "os": constants.OsType.LINUX.lower(),
    "cpu_arch": constants.CpuType.x86_64,
    "is_release_version": True,
    "is_ready": True,
}


PROC_CONTROL_MODEL_DATA = {
    "id": 1,
    "module": "gse_plugin",
    "project": PLUGIN_NAME,
    "plugin_package_id": PACKAGES_MODEL_DATA["id"],
    "os": PACKAGES_MODEL_DATA["os"],
    "process_name": PLUGIN_NAME,
    "port_range": "1-65535",
    "need_delegate": True,
    "install_path": "/usr/local/gse_test",
    "log_path": "/var/log/gse_test",
    "data_path": "/var/lib/gse_test",
    "pid_path": f"/var/run/gse_test/{PLUGIN_NAME}.pid",
    "start_cmd": f"./start.sh {PLUGIN_NAME}",
    "stop_cmd": f"./stop.sh {PLUGIN_NAME}",
    "restart_cmd": f"./restart.sh {PLUGIN_NAME}",
    "reload_cmd": f"./reload.sh {PLUGIN_NAME}",
    "kill_cmd": f"./kill.sh {PLUGIN_NAME}",
    "version_cmd": f"./{PLUGIN_NAME} -v",
    "health_cmd": f"./{PLUGIN_NAME} -z",
    "debug_cmd": f"./{PLUGIN_NAME} -d",
}
