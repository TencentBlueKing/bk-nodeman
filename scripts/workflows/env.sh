#!/bin/bash

# DJANGO配置
export DJANGO_SETTINGS_MODULE="settings"
export DEBUG=true


# 项目环境变量
# APP 设置
export BKPAAS_ENGINE_REGION="open"
export RUN_ENV="open"
export APP_CODE="bk_nodeman"
export BK_PAAS_HOST="http://127.0.0.1"
export SECRET_KEY=$APP_CODE
export APP_TOKEN=$APP_CODE

# 不开启后台配置
export BK_BACKEND_CONFIG=

# 权限中心
export BK_IAM_V3_INNER_HOST="127.0.0.1"

# Nginx 配置
export BKAPP_BKNODEMAN_NGINX_URL="127.0.0.1"
export BKAPP_BACKEND_HOST="http://127.0.0.1"

# 普通
export JOB_VERSION="V3"
export CONCURRENT_NUMBER="10"

# 消息队列
export BROKER_URL="redis://localhost:6379/0"

export BK_CELERYD_CONCURRENCY="8"

export BKAPP_BK_NODE_APIGATEWAY=http://127.0.0.1:8000/

export BKAPP_NODEMAN_CALLBACK_URL=http://127.0.0.1:10300/backend

export BKAPP_NODEMAN_OUTER_CALLBACK_URL=http://127.0.0.1:10300/backend


# CI自定义环境变量
# 数据库
export MYSQL_NAME=$APP_CODE
export MYSQL_USER="root"
export MYSQL_PASSWORD=
export MYSQL_HOST="localhost"
export MYSQL_PORT="3306"
export MYSQL_TEST_NAME="${BK_MYSQL_NAME}_test"

# CI脚本所在目录
export WORKFLOW_DIR="scripts/workflows"

# 该值非空时通过yum install 安装基础组件
export YUM_INSTALL_SERVICE=1

# 该值非空时自行创建虚拟环境
export CREATE_PYTHON_VENV=1

export INSTALL_FRAMEWORK=1
