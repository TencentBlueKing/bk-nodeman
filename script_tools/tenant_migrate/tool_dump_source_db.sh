#!/bin/bash
# ##########################################
# 说明：从源数据库 dump 需要迁移的表到 SQL 文件
# 功能：
# 1. 从源数据库 dump 需要迁移的表（表结构 + 数据）
# 2. 生成 SQL 文件保存到 source_dump/ 目录
# 3. 这个脚本在批次开始前手动执行一次即可
# 
# 使用场景：
# - 批次1（业务1-100）开始前执行一次
# - 批次2（业务101-150）开始前再执行一次
# ##########################################

source 0_config_common.sh

# SQL 文件保存目录
sourceDumpDir="source_dump"

echo "========================================="
echo "从源数据库 dump 需要迁移的表..."
echo "源数据库: ${sourceMysqlHost}:${sourceMysqlPort}"
echo "dump 文件保存目录: ${sourceDumpDir}/"
echo "========================================="

# 创建 dump 目录
if [[ ! -d "${sourceDumpDir}" ]]; then
  mkdir -p "${sourceDumpDir}"
  echo "  - 创建目录: ${sourceDumpDir}/"
else
  echo "  - 目录已存在: ${sourceDumpDir}/"
  echo "  ⚠️  警告：将覆盖已有的 dump 文件"
fi

echo ""
echo "开始 dump 需要迁移的表..."

# 定义需要迁移的表清单
# nodeman 库需要迁移的表
NODEMAN_TABLES=(
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


# 函数：dump 指定表到 SQL 文件
function dumpTablesToFile() {
  sourceDb=$1
  shift
  tables=("$@")
  
  echo ""
  echo "  [${sourceDb}] 开始 dump ${#tables[@]} 张表..."
  
  # 拼接表名列表
  tableList=""
  for table in "${tables[@]}"; do
    tableList="${tableList} ${table}"
  done
  
  dumpFile="${sourceDumpDir}/${sourceDb}.sql"
  
  # 从源数据库 dump 指定表的结构和数据
  echo "    - 正在从源数据库导出表..."
  echo "    - 表清单: ${tableList}"

  mysqldump -h${sourceMysqlHost} -P${sourceMysqlPort} -u${sourceMysqlUser} -p${sourceMysqlPassword} \
    --default-character-set=utf8mb4 \
    --single-transaction \
    --quick \
    --lock-tables=false \
    --skip-add-drop-table \
    --skip-comments \
    --set-gtid-purged=OFF \
    ${sourceDb} ${tableList} > ${dumpFile}
  
  if [[ $? -ne 0 ]]; then
    echo "    ✗ dump 失败！"
    return 1
  fi
  
  echo "    - dump 完成"
  echo "    - 文件: ${dumpFile}"
  echo "    - 大小: $(du -h ${dumpFile} | cut -f1)"
  echo "    ✓ [${sourceDb}] ${#tables[@]} 张表 dump 完成"
  
  return 0
}

# dump nodeman 需要迁移的表
dumpTablesToFile "${sourceNodemanDb}" "${NODEMAN_TABLES[@]}"
if [[ $? -ne 0 ]]; then
  echo ""
  echo "✗ nodeman 数据库表 dump 失败，请检查源数据库连接和权限"
  exit 1
fi

echo ""
echo "========================================="
echo "dump 完成！"
echo ""
echo "已生成的 SQL 文件："
echo "  - ${sourceDumpDir}/${sourceNodemanDb}.sql"
echo ""
echo "这些文件将在后续的迁移过程中使用。"
echo "下次需要重新 dump 时，再次执行本脚本即可。"
echo "========================================="