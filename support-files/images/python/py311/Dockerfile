FROM centos:7

ARG ROOT_PATH=/root/python
ARG OPENSSL_VERSION=1.1.1v
ARG PYTHON_VERSION=3.11.10
ARG PYTHON_DIR=/opt/py311
ARG PKG_PATH=/tmp/py311.tgz

RUN mkdir -p ${ROOT_PATH} ${PYTHON_DIR}
WORKDIR ${ROOT_PATH}

RUN sed -e 's|^mirrorlist=|#mirrorlist=|g' \
         -e 's|^#baseurl=http://mirror.centos.org|baseurl=https://mirrors.cloud.tencent.com|g' \
         -i.bak \
         /etc/yum.repos.d/CentOS-*.repo  && yum makecache

RUN yum install -y gcc automake autoconf libtool make glibc-static centos-release-scl

RUN sed -e 's|^mirrorlist=|#mirrorlist=|g' \
         -e 's|^#baseurl=http://mirror.centos.org|baseurl=https://mirrors.cloud.tencent.com|g' \
         -i.bak \
         /etc/yum.repos.d/CentOS-SCLo-scl-rh.repo  && sed -e 's|^mirrorlist=|#mirrorlist=|g' \
         -e 's|^# baseurl=http://mirror.centos.org|baseurl=https://mirrors.cloud.tencent.com|g' \
         -i.bak \
         /etc/yum.repos.d/CentOS-SCLo-scl.repo  && yum makecache

RUN yum install -y devtoolset-7 wget perl perl-devel zlib-devel bzip2-devel readline-devel sqlite-devel snappy-devel xz-devel libffi-devel ncurses-devel gdbm-devel tk-devel xz-devel

RUN echo "source /opt/rh/devtoolset-7/enable" >> /etc/bashrc && source /opt/rh/devtoolset-7/enable

RUN wget --no-check-certificate https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz

RUN wget --no-check-certificate https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz

RUN tar -zxvf openssl-${OPENSSL_VERSION}.tar.gz

RUN cd openssl-${OPENSSL_VERSION} && ./config -fPIC no-shared --prefix=/usr/local/ssl --openssldir=/usr/local/ssl

RUN cd openssl-${OPENSSL_VERSION} && make -j4 && make install

RUN tar xvf Python-${PYTHON_VERSION}.tgz
RUN cd Python-${PYTHON_VERSION} && printf 'SSL=/usr/local/ssl\n_ssl _ssl.c \\\n  -DUSE_SSL -I$(SSL)/include -I$(SSL)/include/openssl \\\n  -L$(SSL)/lib -l:libssl.a -l:libcrypto.a\n' > Modules/Setup.local

RUN cd Python-${PYTHON_VERSION} && ./configure --prefix=${PYTHON_DIR} --disable-shared --enable-optimizations --enable-option-checking=fatal
RUN cd Python-${PYTHON_VERSION} && make build_all -j4 && make install
RUN mkdir /root/.pip/ && touch /root/.pip/pip.conf
RUN sed '4d' /root/.pip/pip.conf > /root/.pip/pip.conf

COPY requirements.txt ${ROOT_PATH}/requirements.txt

RUN  ${PYTHON_DIR}/bin/pip3 install --upgrade pip==24.3.1 -i https://mirrors.tencent.com/pypi/simple/ --trusted-host mirrors.tencent.com
RUN  ${PYTHON_DIR}/bin/pip3 install -i https://mirrors.tencent.com/pypi/simple/ --trusted-host mirrors.tencent.com pbr==6.1.0
RUN  ${PYTHON_DIR}/bin/pip3 install -i https://mirrors.tencent.com/pypi/simple/ --trusted-host mirrors.tencent.com -r requirements.txt

RUN cd ${PYTHON_DIR}/bin && ln -sf python3 python && ln -sf pip3 pip
RUN cd ${PYTHON_DIR} && find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete
RUN rm -rf ${PYTHON_DIR}/lib/python3.11/site-packages/impacket/examples
RUN tar czvf ${PKG_PATH} -C /opt py311