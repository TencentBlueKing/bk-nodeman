/opt/nginx-portable/nginx-portable stop || :;
rm -rf /opt/nginx-portable/;
rm -rf /opt/py36/;
tar xvf %(nginx_path)s/py36.tgz -C /opt;
tar xvf %(nginx_path)s/nginx-portable.tgz -C /opt;
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
        listen %(bk_nodeman_nginx_download_port)s;
        server_name localhost;
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
        listen %(bk_nodeman_nginx_proxy_pass_port)s;
        server_name localhost;
        resolver ${DNS_LIST[@]};
        proxy_connect;
        proxy_connect_allow 443 563;
        location / {
            proxy_pass http://\$http_host\$request_uri;
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
            /proc/net/tcp) || ((ret+=1))
        done
    done
    return "$ret"
}
pid=$(cat /opt/nginx-portable/logs/nginx.pid);
is_port_listen_by_pid "$pid" %(bk_nodeman_nginx_download_port)s %(bk_nodeman_nginx_proxy_pass_port)s
exit $?