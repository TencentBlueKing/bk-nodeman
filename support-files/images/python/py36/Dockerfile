FROM centos:7

ARG ROOT_PATH=/root/python
ARG OPENSSL_VERSION=1.1.1v
ARG PYTHON_VERSION=3.6.13
ARG PYTHON_DIR=/opt/py36
ARG PKG_PATH=/tmp/py36.tgz

RUN mkdir -p ${ROOT_PATH} ${PYTHON_DIR}
WORKDIR ${ROOT_PATH}

RUN sed -e 's|^mirrorlist=|#mirrorlist=|g' \
         -e 's|^#baseurl=http://mirror.centos.org|baseurl=https://mirrors.cloud.tencent.com|g' \
         -i.bak \
         /etc/yum.repos.d/CentOS-*.repo  && yum makecache

RUN yum -y install gcc automake autoconf libtool make

RUN yum install -y  wget perl perl-devel zlib-devel bzip2-devel readline-devel sqlite-devel snappy-devel xz-devel

RUN wget --no-check-certificate https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz

RUN wget --no-check-certificate https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz

RUN tar -zxvf openssl-${OPENSSL_VERSION}.tar.gz

RUN cd openssl-${OPENSSL_VERSION} && ./config shared --prefix=${PYTHON_DIR} --openssldir=${PYTHON_DIR}/openssl

RUN cd openssl-${OPENSSL_VERSION} && make && make install

ENV  LDFLAGS "-L${PYTHON_DIR}/lib/ -L${PYTHON_DIR}/lib64/ -Wl,-rpath=${PYTHON_DIR}/lib/:${PYTHON_DIR}/lib64/"
ENV LD_LIBRARY_PATH "${PYTHON_DIR}/lib/:${PYTHON_DIR}/lib64/"
ENV CPPFLAGS "-I${PYTHON_DIR}/include -I${PYTHON_DIR}/include/openssl"

RUN mkdir Modules
RUN echo ' SSL=/usr/local/ssl _ssl _ssl.c  -DUSE_SSL -I$(SSL)/include -I$(SSL)/include/openssl  -L$(SSL)/lib -lssl -lcrypto ' >> Modules/Setup.dist

RUN tar xvf Python-${PYTHON_VERSION}.tgz
RUN cd Python-${PYTHON_VERSION} && ./configure --prefix=${PYTHON_DIR} --enable-optimizations --enable-option-checking=fatal 
RUN cd Python-${PYTHON_VERSION} && make build_all && make install
RUN mkdir /root/.pip/ && touch /root/.pip/pip.conf
RUN sed '4d' /root/.pip/pip.conf > /root/.pip/pip.conf

RUN touch requirements.txt
RUN  echo paramiko==2.9.1 >> requirements.txt
RUN  echo requests==2.20.0 >> requirements.txt
RUN  echo impacket==0.9.22 >> requirements.txt
RUN  echo psutil==5.7.0 >> requirements.txt
RUN  echo PyMySQL==0.6.7 >> requirements.txt
RUN  echo supervisor==4.2.1 >> requirements.txt
RUN  echo setuptools==40.6.2 >> requirements.txt
RUN  echo six==1.15.0 >> requirements.txt
RUN  echo stevedore==3.2.2 >> requirements.txt
RUN  echo virtualenv==20.1.0 >> requirements.txt
RUN  echo virtualenv-clone==0.5.4 >> requirements.txt
RUN  echo virtualenvwrapper==4.8.4 >> requirements.txt
RUN  echo typing-extensions==3.7.4.3 >> requirements.txt
RUN  echo zipp==3.2.0 >> requirements.txt

RUN  ${PYTHON_DIR}/bin/pip3 install --upgrade pip==20.2.3 -i https://mirrors.tencent.com/pypi/simple/ --trusted-host mirrors.tencent.com 
RUN  ${PYTHON_DIR}/bin/pip3 install -i https://mirrors.tencent.com/pypi/simple/ --trusted-host mirrors.tencent.com pbr==5.5.1
RUN  ${PYTHON_DIR}/bin/pip3 install -i https://mirrors.tencent.com/pypi/simple/ --trusted-host mirrors.tencent.com -r requirements.txt 

RUN cd ${PYTHON_DIR}/bin && ln -sf python3 python && ln -sf pip3 pip
RUN tar czvf ${PKG_PATH} -C /opt py36