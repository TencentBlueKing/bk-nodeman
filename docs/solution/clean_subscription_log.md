# 数据膨胀后日志表清理

## 问题描述

#### 问题现象
当节点管理相关记录日志表膨胀到一定量级后，会产生明显慢查询问题，需要清理相关的表数据

#### 解决方案

1. 手动清理
	1. `TRUNCATE`相关表数据
	2. 根据条件删除不同级别的日志、不同时间点的日志
2. 通过配置周期任务定期清理日志表，具体表现为   
	1. 保留xx天的日志
	2. 保留什么级别的日志
	3. 由于存量日志过多，每次最多删除xx条，防止因批量操作而导致的数据库`io`问题

#### 清理日志表说明
> 相关订阅任务的重试和查询结果不受影响，巡检任务不受影响

1. 清理日志表可以保留 `任务历史` 下的任务详情执行状态，并且保留`实例主机`执行状态
2. 如果选择保留`ERROR`级别的日志详情，可以查询到对应的执行失败详情
3. 如果选择保留 xx 天前的日志并且不清除 xx 天内的任意级别的日志，可以查询到 xx 天内所有的日志，xx 天前的日志只保留执行状态不保留执行日志详情

## 手动清理相关表数据
> 数据无价，请在具体删除操作前确认已经完成了节点管理数据库的全量备份

###  方案一: 全量删除相关表数据
> 通过 `Truncate`  表方案，优点是速度快，数据库`IO`负载低, 缺点是无法删选保留数据。如果不考虑历史执行记录查询详情可以选择

```bash
#!/usr/bin/env bash 
MYSQL_USER=root
MYSQL_PASSWD=123456
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DBNAME=bk_nodeman


t_tables=(node_man_subscriptioninstancestatusdetail engine_data engine_status engine_noderelationship engine_history engine_historydata engine_processsnapshot engine_pipelineprocess engine_processcelerytask engine_nodecelerytask engine_scheduleservice engine_pipelinemodel)

for t in "${t_tables[@]}"; do
    echo "truncate table $t"
    mysql -u"${MYSQL_USER}" -p"${MYSQL_PASSWD}" -h"${MYSQL_HOST}" -P"${MYSQL_PORT}" -e "SET FOREIGN_KEY_CHECKS = 0;use $MYSQL_DBNAME; TRUNCATE table $t;SET FOREIGN_KEY_CHECKS = 1;"
done

```

###  方案二:  定量删除相关表数据
> Pipeline 相关表数据可以全量删除，可以删除后再根据条件清理相关日志数据
```bash
#!/usr/bin/env bash 
MYSQL_USER=root
MYSQL_PASSWD=123456
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DBNAME=bk_nodeman


t_tables=(engine_data engine_status engine_noderelationship engine_history engine_historydata engine_processsnapshot engine_pipelineprocess engine_processcelerytask engine_nodecelerytask engine_scheduleservice engine_pipelinemodel)

for t in "${t_tables[@]}"; do
    echo "truncate table $t"
    mysql -u"${MYSQL_USER}" -p"${MYSQL_PASSWD}" -h"${MYSQL_HOST}" -P"${MYSQL_PORT}" -e "SET FOREIGN_KEY_CHECKS = 0;use $MYSQL_DBNAME; TRUNCATE table $t;SET FOREIGN_KEY_CHECKS = 1;"
done
```

#### 保留失败级别的执行日志

```sql
# limit 1000 指每次删除的记录数，防止同时删除记录数量过多，可以根据场景自行调整
delete from node_man_subscriptioninstancestatusdetail WHERE status NOT IN ('FAILED', 'RUNNING') limit 1000;
```

#### 保留指定天数之前的执行日志
```sql
# 其中 30 是指30天，可根据需求自行调整
# limit 1000 指每次删除的记录数，防止同时删除记录数量过多，可以根据场景自行调整
DELETE FROM node_man_subscriptioninstancestatusdetail WHERE create_time < DATE_SUB(NOW(), INTERVAL 30 DAY) limit 1000;
```

### 配置周期任务定期清理

TODO：