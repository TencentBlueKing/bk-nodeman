# installation channel

Due to the complex network scenarios that need to be adapted to the installation channel, only manual installation is supported for now.

## Deployment Guidelines

0. Select a server that is connected to the network of target region as the installation channel (it is recommended to configure no less than `2 core 4G`)

1. Please manually install the proxy or agent on this server to ensure that this server can perform tasks normally in the BlueKing JOB.

2. Obtain `python36.tgz` and `nginx-portable.tgz` from Blueking, upload them to the installation channel server, and extract them to the `/opt/` directory.

3. Execute `vim /opt/nginx-portable/conf/nginx.conf`, edit the nginx configuration, the configuration content is as follows, note that the resolver needs to be filled with the correct DNS
    * Execute the following script on the server to obtain the DNS of the current channel server, please replace the ``resolver`` configuration item in the `nginx` configuration template below with the currently obtained `DNS` list
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
   * According to different network scenarios, select the following corresponding configuration templates as appropriate
      * Please note: `nginx` has different port monitoring configurations for ``ipv4`` and ``ipv6``, the configuration item `listen` needs to be configured according to the actual situation
      * Please note: `nginx` has different upstream address configuration methods for ``ipv4`` and ``ipv6``, the upstream address `proxy` in the configuration item `upstream` needs to be configured according to the actual upstream address,
If the upstream address is an ``ipv6`` host, please adjust the ``upstream proxy`` configuration item in the following template 2 to `[::ip]:17981;`, where `::ip` represents the actual `ipv6 ` address
      * Template 1: General channel host `nginx` configuration template
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
                 # The correct DNS should be filled in according to the actual situation
                 resolver 183.60.83.19 183.60.82.98;
                 proxy_connect;
                 proxy_connect_allow 443 563;
                 location / {
                     proxy_pass http://$http_host$request_uri;
                 }
             }
         }
         ```
      * Template 2: When the installation channel cannot be directly connected to the external network callback address of nodeman, please manually configure the proxy address of the upstream node as the configuration template as upstream to realize multi-level forwarding of callback requests
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
               # The correct DNS should be filled in according to the actual situation
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

4. Execute `/opt/nginx-portable/nginx-portable start` to start the nginx process

5. Create a file storage directory `mkdir -p /data/bkee/public/bknodeman/download`

6. Log in to the host where the Blueking nodeman backend is located, and copy the following files in the nginx download directory (/data/bkee/public/bknodeman/download) to directory `/data/bkee/public/bknodeman/download` on the node server (mainly including the following files)

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
   
7. Unzip ``py36.tgz`` in the download directory to the `/opt` directory
    ```bash
    tar xvf /data/bkee/public/bknodeman/download/py36.tgz -C /opt
    ```