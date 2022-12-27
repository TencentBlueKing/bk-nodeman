# 安装通道

由于安装通道需适配的网络场景比较复杂，暂只支持手动安装。


## 部署指引

0. 选择一台与目标区域网络相通的服务器作为安装通道（建议配置不少于 `2核4G`）

1. 请手动把这台服务器安装上proxy或者agent，保证这台服务器在蓝鲸作业平台中可以正常执行任务。

2. 从蓝鲸获取 `python36.tgz`和 `nginx-portable.tgz` 并上传到安装通道服务器，并解压到 `/opt/` 目录下。

3. 执行`vim /opt/nginx-portable/conf/nginx.conf`，编辑 nginx 配置，配置内容如下，注意 resolver 需填写正确的DNS
   * 在服务器上执行以下脚本可以获取当前通道服务器的DNS, 请将以下`nginx`配置模板中的``resolver``配置项替换为当前获取的`DNS`列表
      ```bash
      ipv6_valid_ip () {
          local ip=$1
          regex='^([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}$'
          awk '$0 !~ /'"$regex"'/{print "not an ipv6=>"$0;exit 1}' <<< "$1"
      }
      DNS_LIST=$(awk 'BEGIN{ORS=" "} $1=="nameserver" {print $2}' /etc/resolv.conf)
      if ! grep -q "nameserver.*127.0.0.1" /etc/resolv.conf; then
          DNS_LIST+=(127.0.0.1)
      fi
      nginx_dns_list=()
      for dns_ip in ${DNS_LIST[@]}; do
          if ipv6_valid_ip $dns_ip; then
              nginx_dns_list+=(["$dns_ip"])
          else
              nginx_dns_list+=("$dns_ip")
          fi
      done
      echo ${nginx_dns_list[@]}
      ```
   * 根据不同的网络场景，酌情选择以下对应的配置模板
     * 请注意: `nginx` 对于 ``ipv4`` 与 ``ipv6`` 的端口监听配置是不同的，配置项 `listen` 需要根据实际情况进行配置 
     * 请注意: `nginx` 对于 ``ipv4`` 与 ``ipv6`` 的上游地址配置方式是不同的，配置项 `upstream` 中的上游地址 `proxy` 需要根据上游实际地址进行配置, 
如果上游地址为``ipv6``主机时，以下模板二中的``upstream proxy`` 配置项请调整为 `[::ip]:17981;`，其中`::ip` 代表实际的 `ipv6` 地址 
     * 模板一: 常规通道主机`nginx`配置模板
         ```nginx
         events {
             worker_connections  65535;
         }
         http {
             include       mime.types;
             default_type  application/octet-stream;
             sendfile        on;
             server {
                 listen 17980;
                 listen [::]:17980;
                 server_name localhost;
                 root /data/bkee/public/bknodeman/download;

                 location / {
                     index index.html;
                 }
                 error_page   500 502 503 504  /50x.html;
                 location = /50x.html {
                     root   html;
                 }
             }
             server {
                 listen 17981;
                 listen [::]:17981;
                 server_name localhost;
                 # 需根据实际情况填写正确的 DNS
                 resolver 183.60.83.19 183.60.82.98;
                 proxy_connect;
                 proxy_connect_allow 443 563;
                 location / {
                     proxy_pass http://$http_host$request_uri;
                 }
             }
         }
         ```
     * 模板二: 当安装通道并不能直连节点管理外网回调地址时，请手动配置上游节点proxy地址作为配置模板当upstream，实现回调请求多级转发
       ```nginx
       events {
           worker_connections  65535;
       }
       http {
           include       mime.types;
           default_type  application/octet-stream;
           sendfile        on;
           server {
               listen 17980;
               listen [::]:17980;
               server_name localhost;
               root /data/bkee/public/bknodeman/download;

               location / {
                   index index.html;
               }
               error_page   500 502 503 504  /50x.html;
               location = /50x.html {
                   root   html;
               }
           }
           upstream proxy {
               server 10.0.0.1:17981;         
               server 10.0.0.2:17981;         
           }
           server {
               listen 17981;
               listen [::]:17981;
               server_name localhost;
               # 需根据实际情况填写正确的 DNS
               resolver 183.60.83.19 183.60.82.98;
               proxy_connect;
               proxy_connect_allow 443 563;
               location / {
                   proxy_set_header X-Forwarded-For $remote_addr;
                   proxy_set_header X-Real-IP $remote_addr;
                   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                   proxy_set_header Host $host;
                   proxy_redirect off;
                   proxy_read_timeout 600;
                   proxy_connect_timeout 600;
                   proxy_headers_hash_max_size 51200;
                   proxy_headers_hash_bucket_size 6400;
                   proxy_pass http://proxy;
               }
           }
       }
       ```

4. 执行 `/opt/nginx-portable/nginx-portable start` 启动 nginx 进程

5. 创建文件存放目录 `mkdir -p /data/bkee/public/bknodeman/download`

6. 登录蓝鲸节点管理后台所在的机器 ，将 nginx 下载目录（/data/bkee/public/bknodeman/download）中的以下文件拷贝到安装节点服务器的 `/data/bkee/public/bknodeman/download` 目录下（主要包括以下文件）

   ```bash
    ├── 7z.dll
    ├── 7z.exe
    ├── agent_tools
    │   └── agent2
    │       ├── setup_agent.bat
    │       ├── setup_agent.sh
    │       └── setup_proxy.sh
    ├── base64.exe
    ├── curl-ca-bundle.crt
    ├── curl.exe
    ├── handle.exe
    ├── jq.exe
    ├── libcurl-x64.dll
    ├── nginx-portable.tgz
    ├── ntrights.exe
    ├── py36.tgz
    ├── setup_agent.bat
    ├── setup_agent.ksh
    ├── setup_agent.sh
    ├── setup_agent.zsh
    ├── setup_pagent.py
    ├── setup_proxy.sh
    ├── setup_solaris_agent.sh
    ├── tcping.exe
    └── unixdate.exe
   ```
   
7. 解压下载目录中的 ``py36.tgz`` 到 `/opt` 目录
    ```bash
    tar xvf /data/bkee/public/bknodeman/download/py36.tgz -C /opt
    ```