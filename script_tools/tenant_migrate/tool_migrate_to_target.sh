#!/bin/bash

# ##########################################
# 说明：迁移数据
# 功能：
# 1. 创建dump的数据到目标数据库
# 2. 从 SQL 文件导入表结构和数据到目标数据库
# 
# 前置条件：
# - 必须先执行 tool_dump_source_db.sh 生成 SQL 文件
# ##########################################

source 0_config_common.sh

# 临时数据库前缀
prefix="new_"

# SQL 文件保存目录
sourceDumpDir="source_dump"

echo "========================================="
echo "准备迁移数据库..."
echo "临时数据库: ${targetMysqlHost}:${targetMysqlPort}"
echo "SQL 文件目录: ${sourceDumpDir}/"
echo "========================================="

# 检查 SQL 文件是否存在
echo ""
echo "检查 SQL 文件..."
missingFiles=0

if [[ ! -f "${sourceDumpDir}/${sourceNodemanDb}.sql" ]]; then
  echo "  ✗ 缺少文件: ${sourceDumpDir}/${sourceNodemanDb}.sql"
  missingFiles=1
fi

if [[ ${missingFiles} -eq 1 ]]; then
  echo ""
  echo "✗ 缺少必要的 SQL 文件！"
  echo ""
  echo "请先执行以下命令生成 SQL 文件："
  echo "  bash tool_dump_source_db.sh"
  echo ""
  exit 1
fi

echo "  ✓ 所有 SQL 文件已就绪"

echo ""
echo "步骤1: 从 SQL 文件导入表结构和数据到目标数据库..."

# 函数：从 SQL 文件导入到临时数据库
function importSqlFileTotargetDb() {
  sourceDb=$1
  targetDb=$2
  sqlFile="${sourceDumpDir}/${sourceDb}.sql"
  
  echo ""
  echo "  [${sourceDb}] 开始导入..."
  echo "    - SQL 文件: ${sqlFile}"
  echo "    - 目标库: ${targetDb} "

  NODEMAN_TABLES=(
    "node_man_accesspoint"
    "node_man_cloud"
    "node_man_globalsettings"
    "node_man_gseconfigenv"
    "node_man_gseconfigextraenv"
    "node_man_gseconfigtemplate"
    "node_man_gseplugindesc"
    "node_man_host"
    "node_man_installchannel"
    "node_man_packages"
    "node_man_pipelinetree"
    "node_man_pluginconfiginstance"
    "node_man_pluginconfigtemplate"
    "node_man_pluginresourcepolicy"
    "node_man_proccontrol"
    "node_man_processstatus"
    "node_man_subscription"
    "node_man_subscriptioninstancerecord"
    "node_man_subscriptionstep"
    "node_man_subscriptiontask"
    "tag_tag"
  )
  
  # 1. 检查并删除已存在的表
  echo "    - 检查并清理已存在的表..."
  
  # 构建 DROP TABLE 语句
  dropTableSql="DROP TABLE IF EXISTS "
  for tableName in "${NODEMAN_TABLES[@]}"; do
    dropTableSql="${dropTableSql}\`${targetDb}\`.\`${tableName}\`, "
  done
  # 移除最后的逗号和空格
  dropTableSql="${dropTableSql%, }"
  dropTableSql="${dropTableSql};"
  
  # 一条命令删除所有表
  echo "    - 执行批量删除表命令..."
  mysql -h${targetMysqlHost} -P${targetMysqlPort} -u${targetMysqlUser} -p${targetMysqlPassword} --default-character-set=utf8mb4 -e "${dropTableSql}" 2>/dev/null
  
  if [[ $? -eq 0 ]]; then
    echo "        ✓ 所有表已删除或不存在"
  else
    echo "        ✗ 删除表失败"
    return 1
  fi
  
  # 2. 准备导入文件（添加 USE 语句）
  targetFile="${sourceDumpDir}/${sourceDb}_import.sql"
  echo "USE \`${targetDb}\`;" > ${targetFile}
  cat ${sqlFile} >> ${targetFile}
  
  # 3. 导入到临时数据库
  echo "    - 正在导入数据..."
  mysql -h${targetMysqlHost} -P${targetMysqlPort} -u${targetMysqlUser} -p${targetMysqlPassword} --default-character-set=utf8mb4 < ${targetFile}
  
  if [[ $? -ne 0 ]]; then
    echo "    ✗ 导入失败！"
    rm -f ${targetFile}
    return 1
  fi
  
  # 4. 清理临时文件
  rm -f ${targetFile}
  
  echo "    ✓ [${sourceDb}] 导入完成"
  
  return 0
}

# 导入 nodeman
importSqlFileTotargetDb "${sourceNodemanDb}" "${targetNodemanDb}"
if [[ $? -ne 0 ]]; then
  echo ""
  echo "✗ nodeman 数据库导入失败"
  exit 1
fi

echo ""
echo "步骤2: 验证目标数据库..."

# 验证目标数据库中的表数量
function verifytargetDb() {
  targetDb=$1
  tableCount=$(executeSqlInTargetDb "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${targetDb}';" 2>/dev/null | grep -E '^[0-9]+$')
  echo "  - ${targetDb}: ${tableCount} 张表"
}

verifytargetDb "${targetNodemanDb}"

echo ""
echo "步骤3: 调整目标数据库偏移量..."

# 执行偏移量调整 SQL 文件

if [[ -f "${sqlFile}" ]]; then
  echo "  - 执行偏移量调整 SQL 文件: ${sqlFile}"
  sqlFile="sql/alter_auto_increment.sql"
  targetFile="sql/alter_auto_increment_import.sql"
  echo "USE \`${targetNodemanDb}\`;" > ${targetFile}
  cat ${sqlFile} >> ${targetFile}
  mysql -h${targetMysqlHost} -P${targetMysqlPort} -u${targetMysqlUser} -p${targetMysqlPassword} --default-character-set=utf8mb4 < ${targetFile}
  rm -rf ${targetFile}
  echo "  - 执行偏移量调整完成"
else
  echo "  - 偏移量调整 SQL 文件不存在: ${sqlFile}"
fi

echo ""
echo "========================================="
echo "数据库准备完成！"
echo "迁移的数据库："
echo "  - ${targetNodemanDb} (已从 ${sourceDumpDir}/${sourceNodemanDb}.sql 导入)"
echo "========================================="