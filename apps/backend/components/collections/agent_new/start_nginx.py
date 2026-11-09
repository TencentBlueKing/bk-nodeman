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
import os

from django.conf import settings

from .base import AgentCommonData, AgentExecuteScriptService

# 脚本模板中存在 {print $2} 等和 format 关键字冲突的片段，故采用 % 方式进行字符串渲染
SCRIPT_TMPL_PATH = os.path.join(settings.BK_SCRIPTS_PATH, "start_nginx.sh.tpl")


class StartNginxService(AgentExecuteScriptService):
    @property
    def script_name(self):
        return "start_nginx"

    def get_script_content(self, data, common_data: AgentCommonData, host) -> str:
        """
        获取脚本内容，按每台主机的内网 IP 分别渲染，避免批次内多台机器共用同一份配置导致监听 IP 拿错
        :param data:
        :param common_data:
        :param host: 主机对象（models.Host），使用 inner_ip 作为监听地址
        :return: 脚本内容
        """
        with open(SCRIPT_TMPL_PATH, encoding="utf-8") as fh:
            script = fh.read()

        # 使用主机的内网 IP 进行监听，与作业平台投递/查询保持一致（避免 CMDB 与本地数据多 IP 不一致）
        listen_ip = host.inner_ip

        server_tpl = """
    server {
        listen %(listen_ip)s:%(bk_nodeman_nginx_download_port)s;
        server_name %(listen_ip)s;
        root %(nginx_path)s;

        location / {
            index index.html;
        }
        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }
    }
    server {
        listen %(listen_ip)s:%(bk_nodeman_nginx_proxy_pass_port)s;
        server_name %(listen_ip)s;
        resolver ${nginx_dns_list[@]};
        proxy_connect;
        proxy_connect_allow 443 563;
        location / {
            proxy_pass http://\\$http_host\\$request_uri;
        }
    }
        """

        server_tpl = server_tpl % {
            "nginx_path": settings.DOWNLOAD_PATH,
            "listen_ip": listen_ip,
            "bk_nodeman_nginx_download_port": settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT,
            "bk_nodeman_nginx_proxy_pass_port": settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT,
        }
        script_content = script % {
            "nginx_server": server_tpl,
            "nginx_path": settings.DOWNLOAD_PATH,
            "bk_nodeman_nginx_download_port": settings.BK_NODEMAN_NGINX_DOWNLOAD_PORT,
            "bk_nodeman_nginx_proxy_pass_port": settings.BK_NODEMAN_NGINX_PROXY_PASS_PORT,
        }
        return script_content
