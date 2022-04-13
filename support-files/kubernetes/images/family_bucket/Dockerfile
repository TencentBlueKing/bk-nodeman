FROM node:12.13.1-stretch-slim AS staticBuilder

ENV NPM_VERSION 6.14.4

WORKDIR /frontend
COPY frontend ./
RUN npm install
RUN npm run build


FROM python:3.6.12-slim-buster AS base

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

## PYTHON
# Seems to speed things up
ENV PYTHONUNBUFFERED=1
# Turns off writing .pyc files. Superfluous on an ephemeral container.
ENV PYTHONDONTWRITEBYTECODE=1

# Ensures that the python and pip executables used
# in the image will be those from our virtualenv.
ENV PATH="/venv/bin:$PATH"

RUN set -ex && \
    rm /etc/apt/sources.list && \
    echo "deb https://mirrors.cloud.tencent.com/debian buster main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.cloud.tencent.com/debian buster-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.cloud.tencent.com/debian buster main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.cloud.tencent.com/debian buster-updates main contrib non-free" >> /etc/apt/sources.list

RUN set -ex && mkdir ~/.pip && printf '[global]\nindex-url = https://mirrors.tencent.com/pypi/simple/' > ~/.pip/pip.conf


FROM base AS builder

WORKDIR /

# Install OS package dependencies.
# Do all of this in one RUN to limit final image size.
RUN set -ex &&  \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc gettext mariadb-client libmariadbclient-dev default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /

# 创建 Python 虚拟环境并安装依赖
RUN set -ex && python -m venv /venv && pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


FROM base AS app

# 安装运行时依赖
RUN set -ex &&  \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gettext curl vim default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
USER root

ADD ./ ./

# 换行符兼容转换
RUN awk 'sub("$","\r")' script_tools/setup_agent.bat > script_tools/setup_agent.bat_w && mv -f script_tools/setup_agent.bat_w script_tools/setup_agent.bat && \
    awk 'sub("$","\r")' script_tools/gsectl.bat > script_tools/gsectl.bat_w && mv -f script_tools/gsectl.bat_w script_tools/gsectl.bat && \
    awk 'sub("$","\r")' script_tools/plugin_scripts/start.bat > script_tools/plugin_scripts/start.bat_w && mv -f script_tools/plugin_scripts/start.bat_w script_tools/plugin_scripts/start.bat && \
    awk 'sub("$","\r")' script_tools/plugin_scripts/stop.bat > script_tools/plugin_scripts/stop.bat_w && mv -f script_tools/plugin_scripts/stop.bat_w script_tools/plugin_scripts/stop.bat && \
    awk 'sub("$","\r")' script_tools/plugin_scripts/restart.bat > script_tools/plugin_scripts/restart.bat_w && mv -f script_tools/plugin_scripts/restart.bat_w script_tools/plugin_scripts/restart.bat

# 拷贝构件
COPY --from=builder /venv /venv
COPY --from=staticBuilder /static/ /app/static/

ENTRYPOINT ["support-files/kubernetes/images/family_bucket/entrypoint.sh"]
