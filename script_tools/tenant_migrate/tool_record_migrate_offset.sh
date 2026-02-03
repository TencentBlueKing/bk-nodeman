#!/bin/bash
# -*- coding: utf-8 -*-
# 记录迁移数据的最大 ID 到 GlobalSettings 表

# 源文件目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 导入配置文件
source "${SCRIPT_DIR}/0_config_common.sh"

# 检查配置
if [ -z "$targetMysqlHost" ] || [ -z "$targetMysqlPort" ] || [ -z "$targetMysqlUser" ] || [ -z "$targetNodemanDb" ]; then
    echo "错误：请先在 0_config_common.sh 中配置目标数据库信息"
    exit 1
fi

echo "=================="
echo "开始记录迁移偏移量..."
echo "=================="
echo "目标数据库: ${targetMysqlHost}:${targetMysqlPort}/${targetNodemanDb}"
echo ""

# 构建 MySQL 连接命令
MYSQL_CMD="mysql -h ${targetMysqlHost} -P ${targetMysqlPort} -u ${targetMysqlUser} -p${targetMysqlPassword} ${targetNodemanDb}"

# 查询各表的最大 ID（合并为一个 SQL 查询，只连接一次）
echo "查询各表最大 ID..."

QUERY_RESULT=$(${MYSQL_CMD} -N << 'SQLEOF'
SELECT 
    COALESCE(MAX(id), 0) AS gse_plugin_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_packages) AS packages_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_pluginconfiginstance) AS plugin_config_instance_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_pluginconfigtemplate) AS plugin_config_template_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_pluginresourcepolicy) AS plugin_resource_policy_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_proccontrol) AS proc_control_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_processstatus) AS process_status_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_subscription) AS subscription_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_subscriptioninstancerecord) AS subscription_instance_record_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_subscriptionstep) AS subscription_step_max_id,
    (SELECT COALESCE(MAX(id), 0) FROM node_man_subscriptiontask) AS subscription_task_max_id
FROM node_man_gseplugindesc;
SQLEOF
)

# 解析查询结果
GSE_PLUGIN_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $1}')
PACKAGES_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $2}')
PLUGIN_CONFIG_INSTANCE_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $3}')
PLUGIN_CONFIG_TEMPLATE_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $4}')
PLUGIN_RESOURCE_POLICY_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $5}')
PROC_CONTROL_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $6}')
PROCESS_STATUS_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $7}')
SUBSCRIPTION_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $8}')
SUBSCRIPTION_INSTANCE_RECORD_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $9}')
SUBSCRIPTION_STEP_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $10}')
SUBSCRIPTION_TASK_MAX_ID=$(echo "$QUERY_RESULT" | awk '{print $11}')

echo "node_man_gseplugindesc 最大 ID: $GSE_PLUGIN_MAX_ID"
echo "node_man_packages 最大 ID: $PACKAGES_MAX_ID"
echo "node_man_pluginconfiginstance 最大 ID: $PLUGIN_CONFIG_INSTANCE_MAX_ID"
echo "node_man_pluginconfigtemplate 最大 ID: $PLUGIN_CONFIG_TEMPLATE_MAX_ID"
echo "node_man_pluginresourcepolicy 最大 ID: $PLUGIN_RESOURCE_POLICY_MAX_ID"
echo "node_man_proccontrol 最大 ID: $PROC_CONTROL_MAX_ID"
echo "node_man_processstatus 最大 ID: $PROCESS_STATUS_MAX_ID"
echo "node_man_subscription 最大 ID: $SUBSCRIPTION_MAX_ID"
echo "node_man_subscriptioninstancerecord 最大 ID: $SUBSCRIPTION_INSTANCE_RECORD_MAX_ID"
echo "node_man_subscriptionstep 最大 ID: $SUBSCRIPTION_STEP_MAX_ID"
echo "node_man_subscriptiontask 最大 ID: $SUBSCRIPTION_TASK_MAX_ID"
echo ""

# 记录到 GlobalSettings 表
echo "记录迁移偏移量到 GlobalSettings..."

${MYSQL_CMD} << EOF
INSERT INTO node_man_globalsettings (\`key\`, v_json) VALUES (
    'MIGRATE_OFFSET',
    JSON_OBJECT(
        'gse_plugin_desc', ${GSE_PLUGIN_MAX_ID},
        'packages', ${PACKAGES_MAX_ID},
        'plugin_config_instance', ${PLUGIN_CONFIG_INSTANCE_MAX_ID},
        'plugin_config_template', ${PLUGIN_CONFIG_TEMPLATE_MAX_ID},
        'plugin_resource_policy', ${PLUGIN_RESOURCE_POLICY_MAX_ID},
        'proc_control', ${PROC_CONTROL_MAX_ID},
        'process_status', ${PROCESS_STATUS_MAX_ID},
        'subscription', ${SUBSCRIPTION_MAX_ID},
        'subscription_instance_record', ${SUBSCRIPTION_INSTANCE_RECORD_MAX_ID},
        'subscription_step', ${SUBSCRIPTION_STEP_MAX_ID},
        'subscription_task', ${SUBSCRIPTION_TASK_MAX_ID}
    )
)
ON DUPLICATE KEY UPDATE v_json = VALUES(v_json);
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=================="
    echo "✓ 迁移偏移量记录成功！"
    echo "=================="
    echo ""
    
    # 验证记录
    echo "验证记录内容："
    ${MYSQL_CMD} -e "SELECT \`key\`, v_json FROM node_man_globalsettings WHERE \`key\`='MIGRATE_OFFSET';"
else
    echo ""
    echo "=================="
    echo "✗ 记录迁移偏移量失败！"
    echo "=================="
    exit 1
fi
