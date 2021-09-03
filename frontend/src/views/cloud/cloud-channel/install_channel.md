# 安装通道

由于安装通道需适配的网络场景比较复杂，暂只支持手动安装。



## 部署指引

0. 选择一台与目标区域网络相通的服务器作为安装通道（建议配置不少于 `2核4G`）

1. 请手动把这台服务器安装上proxy或者agent，保证这台服务器在蓝鲸作业平台中可以正常执行任务。

2. 从蓝鲸获取 `python36.tgz`和 `nginx-portable.tgz` 并上传到安装通道服务器，并解压到 `/opt/` 目录下。

3. 执行`vim /opt/nginx-portable/conf/nginx.conf`，编辑 nginx 配置，配置内容如下，注意 resolver 需填写正确的DNS

   ```
   events {
       worker_connections  65535;
   }
   http {
       include       mime.types;
       default_type  application/octet-stream;
       sendfile        on;
       server {
           listen 17980;
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

4. 执行 `/opt/nginx-portable/nginx-portable start` 启动 nginx 进程

5. 创建文件存放目录 `mkdir -p /data/bkee/public/bknodeman/download`

6. 登录蓝鲸节点管理后台所在的机器 ，将 nginx 下载目录（/data/bkee/public/bknodeman/download）下的文件拷贝到安装节点服务器的 `/data/bkee/public/bknodeman/download` 目录下（主要包括以下文件）

   ```
   -rw-r--r-- 1 blueking blueking 40323665 Aug 25 18:08 gse_client-windows-x86_64.tgz
   -rw-r--r-- 1 blueking blueking 66874459 Aug 25 18:08 gse_client-linux-x86_64.tgz
   -rwxr-xr-x 1 blueking blueking    18187 Aug 25 18:48 wmiexec.py
   -rwxr-xr-x 1 blueking blueking    39424 Aug 25 18:48 unixdate.exe
   -rw-r--r-- 1 blueking blueking   258560 Aug 25 18:48 tcping.exe
   -rw-r--r-- 1 blueking blueking    28274 Aug 25 18:48 setup_agent.sh
   -rw-r--r-- 1 blueking blueking  1089144 Aug 25 18:48 libcurl-x64.dll
   -rw-r--r-- 1 blueking blueking  1074224 Aug 25 18:48 handle.exe
   -rw-r--r-- 1 blueking blueking  4060792 Aug 25 18:48 curl.exe
   -rw-r--r-- 1 blueking blueking   223687 Aug 25 18:48 curl-ca-bundle.crt
   -rwxr-xr-x 1 blueking blueking   265216 Aug 25 18:48 7z.exe
   -rw-r--r-- 1 blueking blueking  1073664 Aug 25 18:48 7z.dll
   -rw-r--r-- 1 blueking blueking    39640 Aug 25 19:32 setup_agent.bat
   -rw-r--r-- 1 blueking blueking     5864 Aug 25 19:32 gsectl.bat
   ```

   