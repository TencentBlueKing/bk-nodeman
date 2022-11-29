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
setup_path="$@"
cd $setup_path
for file in $(ls); do
    if echo $file | grep '.*sh$'; then
        chmod +x $setup_path/${file}
    fi
done
"""

START_NGINX_TEMPLATE = """
/opt/nginx-portable/nginx-portable stop || :;
rm -rf /opt/nginx-portable/;
rm -rf /opt/py36/;
tar xvf {{ nginx_path }}/py36.tgz -C /opt;
tar xvf {{ nginx_path }}/nginx-portable.tgz -C /opt;
chmod -R 755 /data
user=root
group=root
#create group if not exists
egrep "^$group" /etc/group >& /dev/null
if [ $? -ne 0 ]
then
    groupadd $group
fi

#create user if not exists
egrep "^$user" /etc/passwd >& /dev/null
if [ $? -ne 0 ]
then
    useradd -g $group $user
fi
DNS_LIST=$(awk 'BEGIN{ORS=" "} $1=="nameserver" {print $2}' /etc/resolv.conf)
if ! grep -q "nameserver.*127.0.0.1" /etc/resolv.conf; then
    DNS_LIST+=(127.0.0.1)
fi
echo -e "
user $user;
events {
    worker_connections  65535;
}
http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    server {
        listen {{ bk_nodeman_nginx_download_port }};
        server_name localhost;
        root {{ nginx_path }}

        location / {
            index index.html;
        }
        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }
    }
    server {
        listen {{ bk_nodeman_nginx_proxy_pass_port }};
        {% if is_v6_host %}
        listen [::]:{{ bk_nodeman_nginx_proxy_pass_port }};
        {% endif %}
        server_name localhost;
        {% if is_v6_host %}
        resolver [{{ inner_ipv6 }}] ${DNS_LIST[@]};
        {% else %}
        resolver ${DNS_LIST[@]};
        {% endif %}
        proxy_connect;
        proxy_connect_allow 443 563;
        location / {
            proxy_pass http://$http_host$request_uri;
        }
    }
}" > /opt/nginx-portable/conf/nginx.conf;
/opt/nginx-portable/nginx-portable start;
sleep 5
is_port_listen_by_pid () {
    local pid regex ret
    pid=$1
    shift 1
    ret=0

    for i in {0..10}; do
        sleep 1
        for port in "$@"; do
            stat -L -c %%i /proc/"$pid"/fd/* 2>/dev/null | grep -qwFf - \
            <( awk -v p="$port" 'BEGIN{ check=sprintf(":%%04X0A$", p)} $2$4 ~ check {print $10}' \
            /proc/net/tcp*) || ((ret+=1))
        done
    done
    return "$ret"
}
pid=$(cat /opt/nginx-portable/logs/nginx.pid);
is_port_listen_by_pid "$pid" {{ bk_nodeman_nginx_download_port }}  {{ bk_nodeman_nginx_proxy_pass_port}}
exit $?
"""
