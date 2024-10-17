get_cpu_arch () {
    local cmd=$1
    CPU_ARCH=$($cmd)
    CPU_ARCH=$(echo ${CPU_ARCH} | tr 'A-Z' 'a-z')
    if [[ "${CPU_ARCH}" =~ "x86_64" ]]; then
        return 0
    elif [[ "${CPU_ARCH}" =~ "x86" || "${CPU_ARCH}" =~ ^i[3456]86 ]]; then
        return 1
    elif [[ "${CPU_ARCH}" =~ "aarch" ]]; then
        return 0
    else
        return 1
    fi
}
get_cpu_arch "uname -p" || get_cpu_arch "uname -m" || fail get_cpu_arch "Failed to get CPU arch or unsupported CPU arch, please contact the developer."

/opt/nginx-portable/nginx-portable stop || :;
rm -rf /opt/nginx-portable/;
rm -rf /opt/py36/;

tar xvf %(nginx_path)s/py36-${CPU_ARCH}.tgz -C /opt;
tar xvf %(nginx_path)s/nginx-portable-${CPU_ARCH}.tgz -C /opt;

timeout 120 chmod -R 755 %(nginx_path)s || echo "chmod directory %(nginx_path)s failed"
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

ipv6_valid_ip () {
    local ip=$1
    regex='^([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}$'
    awk '$0 !~ /'"$regex"'/{print "not an ipv6=>"$0;exit 1}' <<< "$1"
}

nginx_dns_list=()
for dns_ip in ${DNS_LIST[@]}; do
    if ipv6_valid_ip $dns_ip; then
        nginx_dns_list+=(["$dns_ip"])
    else
        nginx_dns_list+=("$dns_ip")
    fi
done

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
        listen [::]:%(bk_nodeman_nginx_download_port)s;
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
        listen [::]:%(bk_nodeman_nginx_proxy_pass_port)s;
        server_name localhost;
        resolver ${nginx_dns_list[@]};
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
            /proc/net/tcp*) || ((ret+=1))
        done
    done
    return "$ret"
}
pid=$(cat /opt/nginx-portable/logs/nginx.pid);
is_port_listen_by_pid "$pid" %(bk_nodeman_nginx_download_port)s %(bk_nodeman_nginx_proxy_pass_port)s
exit $?
