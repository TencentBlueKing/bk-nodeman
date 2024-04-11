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

REACHABLE_SCRIPT_TEMPLATE = """
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
"""

INITIALIZE_SCRIPT = """
setup_path="$2"
subscription_tmp_dir="$1"

if [ ! -d "$subscription_tmp_dir" ]; then
  exit 0
fi

if [ ! -d "$setup_path" ]; then
  mkdir -p "$setup_path"
fi

cd "$subscription_tmp_dir"
for file in $(ls); do
    if echo $file | grep '.*sh$'; then
        chmod +x $subscription_tmp_dir/${file}
        cp -p $subscription_tmp_dir/${file} $setup_path/${file}
    fi
done

rm -rf $subscription_tmp_dir
"""

ENVIRON_SH_TEMPLATE = """
#!/bin/sh

# What: environ.sh provides environment variables with consistent names
# to shield the installation differences of multi-version GSE Agents
# QuickStart:
# 1. source environ.sh
# 2. echo ${BK_GSE_AGENT_SETUP_PATH}

# GSE Agent installation path
export BK_GSE_AGENT_SETUP_PATH="{{ setup_path }}"

# GSE Agent dataipc path
export BK_GSE_DATA_IPC="{{ dataipc }}"

# NodeMan Plugin installation path
export BK_NODEMAN_PLUGIN_SETUP_PATH="{{ plugin_setup_path }}"

"""

ENVIRON_BAT_TEMPLATE = """
@echo off

rem What: environ.bat provides environment variables with consistent names
rem to shield the installation differences of multi-version GSE Agents
rem QuickStart:
rem 1. call environ.bat in your terminal
rem 2. echo %BK_GSE_AGENT_SETUP_PATH%

rem GSE Agent installation path
set BK_GSE_AGENT_SETUP_PATH={{ setup_path }}

rem GSE Agent dataipc
set BK_GSE_DATA_IPC={{ dataipc }}

rem NodeMan Plugin installation path
set BK_NODEMAN_PLUGIN_SETUP_PATH={{ plugin_setup_path }}

"""
