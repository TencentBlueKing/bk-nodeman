FROM centos:7

ARG NGINX_VERSION=1.20.0
ARG OPENSSL_VERSION=1.1.1
ARG NGINX_PATH=/opt/nginx-portable

RUN mkdir -p ${NGINX_PATH}
WORKDIR ${NGINX_PATH}

RUN sed -e 's|^mirrorlist=|#mirrorlist=|g' \
         -e 's|^#baseurl=http://mirror.centos.org|baseurl=https://mirrors.cloud.tencent.com|g' \
         -i.bak \
         /etc/yum.repos.d/CentOS-*.repo  && yum makecache

RUN yum install -y  wget perl perl-devel perl-ExtUtils-Embed libxslt libxslt-devel libxml2 \
    libxml2-devel gd gd-devel GeoIP GeoIP-devel gcc gcc-c++ glibc-static  make patch unzip

RUN wget http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz && tar zxf nginx-${NGINX_VERSION}.tar.gz

RUN wget https://www.openssl.org/source/openssl-${OPENSSL_VERSION}q.tar.gz --no-check-certificate && tar xvf openssl-${OPENSSL_VERSION}q.tar.gz

RUN cd ${NGINX_PATH}/openssl-${OPENSSL_VERSION}q && ./config  && make && make install

RUN wget https://github.com/chobits/ngx_http_proxy_connect_module/archive/master.zip && unzip master.zip

RUN mkdir -p ${NGINX_PATH}/{bin,conf,html,logs,tmp} && cd nginx-${NGINX_VERSION} && \
    patch -p1 < ../ngx_http_proxy_connect_module-master/patch/proxy_connect_rewrite_1018.patch

RUN cd nginx-${NGINX_VERSION} && ./configure --prefix=${NGINX_PATH} --sbin-path=${NGINX_PATH}/bin/ \
    --with-cc-opt='-O2 -static -static-libgcc' --conf-path=${NGINX_PATH}/conf/nginx.conf \
    --error-log-path=${NGINX_PATH}/logs/error.log \
    --http-client-body-temp-path=${NGINX_PATH}/tmp/client_body_temp/ \
    --http-proxy-temp-path=${NGINX_PATH}/tmp/proxy_temp/ \
    --http-fastcgi-temp-path=${NGINX_PATH}/tmp/fastcgi_temp/ \
    --http-uwsgi-temp-path=${NGINX_PATH}/tmp/uwsgi_temp/ \
    --http-scgi-temp-path=${NGINX_PATH}/tmp/scgi_temp/ \
    --without-mail_pop3_module --without-mail_imap_module \
    --without-mail_smtp_module --without-http_fastcgi_module \
    --without-http_rewrite_module \
    --add-module=../ngx_http_proxy_connect_module-master \
    --with-openssl=../openssl-${OPENSSL_VERSION}q --with-cc-opt='-D NGX_HAVE_GNU_CRYPT_R=0' \
    && make && make install
