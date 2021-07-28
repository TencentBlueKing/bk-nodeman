

[TOC]



# 节点管理升级

> V2.0 升级至 V2.1



## 前置操作

### 备份DB

### 停止后台、SaaS节点管理进程





## 后台

###  节点管理环境

```shell
LANG="zh_CN.UTF-8"
workon bknodeman-nodeman
```



### migrate

```shell
./bin/manage.sh migrate node_man
```



### 更新数据

> 大约需要10s，执行失败会cat日志

```shell
./bin/manage.sh upgrade_old_data &>> /tmp/nodeman_upgrade_old_data.log || cat /tmp/nodeman_upgrade_old_data.log
```



### 升级周边系统关联订阅

> 查询DB中订阅ID的最大值`$SUB_MAX`，并作为迁移脚本的输入参数

```shell
source bin/environ.sh
SUB_MAX=`mysql -u$BK_NODEMAN_MYSQL_USER -h$BK_NODEMAN_MYSQL_HOST -p$BK_NODEMAN_MYSQL_PASSWORD -D$BK_NODEMAN_MYSQL_NAME -P$BK_NODEMAN_MYSQL_PORT -N -s -e'select max(id) from node_man_subscription;'`
./upgrade/2.0to2.1/batch_transfer_old_sub.sh --help
./upgrade/2.0to2.1/batch_transfer_old_sub.sh -b 1 -e $SUB_MAX -E -s 3
```



#### 脚本输出解释

日志所在目录

```
transfer_old_sub's log save to /tmp/node_man_upgrade_1_1900_20210427-104241
```

分片执行任务预览

```
[1]   运行中               nohup ./bin/manage.sh transfer_old_sub 1 635 >> xxx 2>&1 &
[2]-  运行中               nohup ./bin/manage.sh transfer_old_sub 636 1270 >> xxx 2>&1 &
[3]+  运行中               nohup ./bin/manage.sh transfer_old_sub 1271 1905 >> xxx 2>&1 &
```



#### 查询数据升级进度

```shell
# 进入脚本输出的日志所在目录
cd /tmp/node_man_upgrade_1_1900_20210427-104241
# 查询执行进度
grep -E '.*([[:digit:]]+[[:space:]]/[[:space:]][[:digit:]]+|total_cost)' *
# 执行完成标志，该目录下的所有日志文件都匹配到total_cost
grep total_cost *
```





## 部署SaaS

该步骤完成后可以启用后台及SaaS服务





## 后台 - 继续升级一次性任务



脚本输出及结果查询同 [脚本输出解释](#脚本输出解释)

```shell
./upgrade/2.0to2.1/batch_transfer_old_sub.sh -b 1 -e $SUB_MAX -s 3
```


## DB 数据更新

```sql
update node_man_processstatus set is_latest=1 where source_type='default' and source_id is null and name="bkmonitorbeat";
update node_man_processstatus set is_latest=1 where source_type='default' and source_id is null and name="processbeat";
update node_man_processstatus set is_latest=1 where source_type='default' and source_id is null and name="basereport";
update node_man_processstatus set is_latest=1 where source_type='default' and source_id is null and name="exceptionbeat";
update node_man_processstatus set is_latest=1 where source_type='default' and source_id is null and name="bkunifylogbeat";
```
