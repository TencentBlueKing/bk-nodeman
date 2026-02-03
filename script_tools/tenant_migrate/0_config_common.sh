#
# Tencent is pleased to support the open source community by making BK-JOB蓝鲸智云作业平台 available.
#
# Copyright (C) 2021 Tencent.  All rights reserved.
#
# BK-JOB蓝鲸智云作业平台 is licensed under the MIT License.
#
# License for BK-JOB蓝鲸智云作业平台:
# --------------------------------------------------------------------
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
# to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

# ###### 新迁移工具配置信息 ######

# 源环境数据库配置（老环境）
sourceMysqlHost="127.0.0.1"
sourceMysqlPort="3306"
sourceMysqlUser="root"
sourceMysqlPassword=""
sourceNodemanDb="bk-nodeman-test"

# 目标环境数据库配置（新环境）
targetMysqlHost="127.0.0.1"
targetMysqlPort="3306"
targetMysqlUser="root"
targetMysqlPassword=""
targetNodemanDb="bk_node_man"

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

# 要填充的租户ID
defaultTenantId="tencent"

# ############   配置信息结束    #############

# 公共基础函数
dbResult=""
function showDbResult(){
  _tmp=""
  echo "dbResult=${dbResult}"
}


function executeSqlInSourceDb(){
  echo "execute sql: mysql -h${sourceMysqlHost} -P${sourceMysqlPort} -u${sourceMysqlUser} -p${sourceMysqlPassword} -e \"$1\""
  dbResult=$(mysql -h${sourceMysqlHost} -P${sourceMysqlPort} -u${sourceMysqlUser} -p${sourceMysqlPassword} -e "$1")
  showDbResult
}

function executeSqlInTargetDb(){
  echo "execute sql: mysql -h${targetMysqlHost} -P${targetMysqlPort} -u${targetMysqlUser} -p${targetMysqlPassword} -e \"$1\""
  dbResult=$(mysql -h${targetMysqlHost} -P${targetMysqlPort} -u${targetMysqlUser} -p${targetMysqlPassword} -e "$1")
  showDbResult
}

# 迁移工具名称
systemName=$(uname -s)
echo "systemName=${systemName}"
migratorName=""
if [[ "${systemName}" =~ "MINGW" ]];then
  migratorName="nodeman-migration.exe"
elif [[ "${systemName}" =~ "Linux" ]];then
  migratorName="nodeman-migration"
fi
echo "migratorName=${migratorName}"