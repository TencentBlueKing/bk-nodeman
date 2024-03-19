#!/bin/sh


# 节点管理公网回调地址
if [ "__BK_NODEMAN_PUBLIC_CALLBACK_URL__" == "" ]; then
    bkapp_nodeman_outer_callback_url="http://__WAN_IP__/backend"
else
    bkapp_nodeman_outer_callback_url="__BK_NODEMAN_PUBLIC_CALLBACK_URL__"
fi

# 节点管理内网回调地址
if [ "__BK_NODEMAN_PRIVATE_CALLBACK_URL__" == "" ]; then
    bkapp_nodeman_callback_url="http://__LAN_IP__:__BK_NODEMAN_API_PORT__/backend"
else
    bkapp_nodeman_callback_url="__BK_NODEMAN_PRIVATE_CALLBACK_URL__"
fi


export PATH=__BK_HOME__/.envs/bknodeman-nodeman/bin:$PATH
export BK_ENV="production"
export BK_BACKEND_CONFIG="True"
export LAN_IP="__LAN_IP__"
export BK_PAAS_HOST="__BK_PAAS_PUBLIC_URL__"
export BK_PAAS_INNER_HOST="__BK_PAAS_PRIVATE_URL__"
export APP_ID="__BK_NODEMAN_APP_CODE__"
export APP_TOKEN="__BK_NODEMAN_APP_SECRET__"
export BKAPP_NODEMAN_CALLBACK_URL="${bkapp_nodeman_callback_url}"
export BKAPP_NODEMAN_OUTER_CALLBACK_URL="${bkapp_nodeman_outer_callback_url}"
export BK_LOG_DIR=__BK_HOME__/logs/bknodeman
export BKAPP_RUN_ENV="__BK_NODEMAN_RUN_ENV__"
export BKAPP_BACKEND_HOST="__BK_NODEMAN_PUBLIC_DOWNLOAD_URL__"
export BKAPP_PUBLIC_PATH="__BK_NODEMAN_PUBLIC_PATH__"
export BK_FILE_PATH="__BK_HOME__/bknodeman/cert/saas_priv.txt"
export BK_NODEMAN_API_ADDR="__BK_NODEMAN_API_ADDR__"
export BKPAAS_BK_CRYPTO_TYPE="__BK_CRYPTO_TYPE__"

# CMDB
# 资源池业务ID
export BK_CMDB_RESOURCE_POOL_BIZ_ID="__BK_CMDB_RESOURCE_POOL_BIZ_ID__"
export CONCURRENT_NUMBER="__BK_NODEMAN_REQUEST_CMDB_CONCURRENT_NUMBER__"
export DEFAULT_SUPPLIER_ACCOUNT="__BK_CMDB_SUPPLIER_ACCOUNT__"
export BK_CC_HOST='__BK_CMDB_PUBLIC_URL__'

# 作业平台
# 蓝鲸业务集ID，默认值为 9991001
export BLUEKING_BIZ_ID="__BK_SPECIAL_BIZ_ID__"
# 作业平台版本，取值为 V2 或 V3
export JOB_VERSION="__BK_JOB_VERSION__"
export BK_JOB_HOST="__BK_JOB_PUBLIC_URL__"

# 权限中心
export BKAPP_USE_IAM="__BK_NODEMAN_USE_IAM__"
export BK_IAM_V3_INNER_HOST="__BK_IAM_PRIVATE_URL__"

# 数据库
export MYSQL_NAME="__BK_NODEMAN_MYSQL_NAME__"
export MYSQL_USER="__BK_NODEMAN_MYSQL_USER__"
export MYSQL_PASSWORD="__BK_NODEMAN_MYSQL_PASSWORD__"
export MYSQL_HOST="__BK_NODEMAN_MYSQL_HOST__"
export MYSQL_PORT="__BK_NODEMAN_MYSQL_PORT__"

# 缓存
export CACHE_BACKEND="__BK_NODEMAN_CACHE_BACKEND__"
export CACHE_ENABLE_PREHEAT="__BK_NODEMAN_CACHE_ENABLE_PREHEAT__"
export CACHE_PIECE_DB_LENGTH="__BK_NODEMAN_CACHE_PIECE_DB_LENGTH__"
export CACHE_PIECE_REDIS_LENGTH="__BK_NODEMAN_CACHE_PIECE_REDIS_LENGTH__"

# Redis
# standalone: 单实例
# sentinel： 哨兵
export REDIS_MODE="__BK_NODEMAN_REDIS_MODE__"
export REDIS_SENTINEL_HOST="__BK_NODEMAN_REDIS_SENTINEL_HOST__"
export REDIS_SENTINEL_PORT=__BK_NODEMAN_REDIS_SENTINEL_PORT__
export REDIS_SENTINEL_PASSWORD="__BK_NODEMAN_REDIS_SENTINEL_PASSWORD__"
export REDIS_PASSWORD="__BK_NODEMAN_REDIS_PASSWORD__"
export REDIS_MASTER_NAME="__BK_NODEMAN_REDIS_SENTINEL_MASTER_NAME__"
# 单实例需要配置下面的变量
export REDIS_HOST="__BK_NODEMAN_REDIS_HOST__"
export REDIS_PORT=__BK_NODEMAN_REDIS_PORT__

# RabbitMQ
export RABBITMQ_USER="__BK_NODEMAN_RABBITMQ_USERNAME__"
export RABBITMQ_PASSWORD="__BK_NODEMAN_RABBITMQ_PASSWORD__"
export RABBITMQ_HOST="__BK_NODEMAN_RABBITMQ_HOST__"
export RABBITMQ_PORT=__BK_NODEMAN_RABBITMQ_PORT__
export RABBITMQ_VHOST="__BK_NODEMAN_RABBITMQ_VHOST__"

# GSE
export BKAPP_GSE_AGENT_HOME="__BK_GSE_AGENT_HOME__"
export BKAPP_GSE_AGENT_LOG_DIR="__BK_GSE_AGENT_LOG_DIR__"
export BKAPP_GSE_AGENT_RUN_DIR="__BK_GSE_AGENT_RUN_DIR__"
export BKAPP_GSE_AGENT_DATA_DIR="__BK_GSE_AGENT_DATA_DIR__"

export BKAPP_GSE_WIN_AGENT_HOME="__BK_GSE_WIN_AGENT_HOME__"
export BKAPP_GSE_WIN_AGENT_LOG_DIR="__BK_GSE_WIN_AGENT_LOG_DIR__"
export BKAPP_GSE_WIN_AGENT_RUN_DIR="__BK_GSE_WIN_AGENT_RUN_DIR__"
export BKAPP_GSE_WIN_AGENT_DATA_DIR="__BK_GSE_WIN_AGENT_DATA_DIR__"
export BKAPP_GSE_USE_ENCRYPTION="__BK_NODEMAN_GSE_ENCRYPTION__"

export GSE_VERSION="__BK_GSE_AGENT_VERSION__"
export GSE_CERT_PATH="__BK_GSE_CERT_PATH__"
export GSE_ENABLE_PUSH_ENVIRON_FILE="__BK_NODEMAN_ENABLE_PUSH_ENVIRON_FILE__"
export GSE_ENVIRON_DIR="__BK_GSE_ENVIRON_DIR__"
export GSE_ENVIRON_WIN_DIR="__BK_GSE_ENVIRON_WIN_DIR__"

export BKAPP_ENABLE_DHCP="__BK_NODEMAN_ENABLE_DHCP__"
export BKAPP_BK_GSE_APIGATEWAY="__BK_API_GATEWAY_GSE_URL__"