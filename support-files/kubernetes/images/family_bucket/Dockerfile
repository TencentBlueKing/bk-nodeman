ARG BKAPP_RUN_ENV=ee


FROM node:16.15.0-buster-slim AS static-builder

ENV NPM_VERSION 6.14.4

WORKDIR /frontend
COPY frontend ./
RUN npm install
RUN npm run build


FROM tencentos/tencentos4-minimal AS base

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH"

RUN set -ex && \
    chmod 1777 /tmp && \
    dnf -y install python3.11 python3-devel gawk && \
    python3 -m ensurepip && \
    pip3 install --upgrade pip && \
    mkdir ~/.pip && printf '[global]\nindex-url = https://mirrors.tencent.com/pypi/simple/' > ~/.pip/pip.conf


FROM base AS builder

WORKDIR /

# Install OS package dependencies
RUN set -ex && \
    dnf install -y gcc mariadb-devel && \
    dnf clean all

COPY requirements.txt /

# 创建 Python 虚拟环境并安装依赖
RUN set -ex && python3 -m venv /venv && \
    pip3 install setuptools_rust && \
    pip3 install --no-cache-dir -r requirements.txt


FROM base AS base-app

# 安装运行时依赖
RUN set -ex && \
    dnf install -y gettext curl vim mariadb-devel && \
    dnf clean all

WORKDIR /app
USER root

ADD ./ ./

# 换行符兼容转换
RUN support-files/kubernetes/images/family_bucket/docs2unix.sh script_tools

# 拷贝构件
COPY --from=builder /venv /venv
COPY --from=static-builder /static/ /app/static/


FROM base-app AS ieod-app

RUN set -ex && \
    rm -rf bkoauth && \
    pip install --no-cache-dir python-crontab==2.6.0 && \
    pip install --no-cache-dir bkoauth==0.0.22

# 移除 upstreams 检查
RUN set -ex && sed -i '/check_polices_\${node_type}_to_upstream/s/^/#/' script_tools/setup_agent.sh


FROM base-app AS backend-ieod-app

# 移除 upstreams 检查
RUN set -ex && sed -i '/check_polices_\${node_type}_to_upstream/s/^/#/' script_tools/setup_agent.sh


FROM base-app AS ee-app


FROM base-app AS ce-app


FROM ${BKAPP_RUN_ENV}-app AS app
ENTRYPOINT ["support-files/kubernetes/images/family_bucket/entrypoint.sh"]
