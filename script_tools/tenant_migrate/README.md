# 数据库迁移说明文档
下面文档详细列出了每一步的执行命令和注意事项。

## 概述
本文档说明了如何进行租户数据库迁移的完整流程。请严格按照步骤执行，以确保迁移的正确性和数据的完整性。

## 前置条件
- CC已迁移完成
- 确保目标环境可访问
- 拥有足够的数据库权限
- 已备份源和目标环境的数据库

## 迁移步骤

## 第一阶段：存量数据迁移（概要）

第一阶段负责将历史（存量）数据从源库完整迁移到目标库，典型流程：

- 停掉目标环境的 Celery Beat，避免后台任务执行
- 禁用目标环境的订阅任务
- 在 `0_config_common.sh` 中配置源/目标数据库信息
- 备份源数据库并恢复到目标数据库，同时应用自增偏移（`alter_auto_increment.sql`）
- 在目标库为必要表添加 `tenant_id` 列（默认值 `tencent`）或提前创建列以避免大表在线变更
- 记录各表最大 ID 到 `GlobalSettings.MIGRATE_OFFSET` 以便后续增量迁移

### 第一步：停掉目标环境 Celery Beat
停止目标环境的 Celery Beat 服务，确保迁移期间不会有后台任务干扰：

```bash
kubectl scale deployment bk-nodeman-backend-celery-beat --replicas=0 -n blueking
```

### 第二步：禁用目标环境所有业务订阅任务
禁用目标环境中所有业务订阅任务，防止迁移过程中任务被执行：

```bash
python manage.py migrate_tools --action disable_subscription_task
```

### 第三步：存量数据库迁移
编辑 `0_config_common.sh` 文件，填写对应的源数据库和目标数据库信息：

```bash
vim 0_config_common.sh
```

需要配置的参数：
- **源数据库信息**：源环境的数据库连接信息（主机、端口、用户名、密码、数据库名等）
- **目标数据库信息**：目标环境的数据库连接信息（主机、端口、用户名、密码、数据库名等）

配置完成后保存文件。

### 第四步：备份源数据库
执行备份脚本，将源数据库数据导出：

```bash
./tool_dump_source_db.sh
```

此命令将根据 `0_config_common.sh` 中的配置信息备份源数据库，生成备份文件供后续使用。

### 第五步：迁移数据并设置偏移量
将源数据库迁移进入目标数据库，并同时设置自增字段的偏移量。偏移量配置已在 `tenant_migrate/sql/alter_auto_increment.sql` 文件中预设好：

```bash
./tool_restore_target_db.sh
```

此命令会：
1. 从备份文件中恢复数据到目标数据库
2. 执行 `alter_auto_increment.sql` 中的偏移量配置，确保新旧数据不会产生 ID 冲突

### 第六步：变更 tenant_id 字段
为目标数据库中的相关表添加 `tenant_id` 字段，并设置默认值为 `tencent`。执行迁移脚本：
(根据现网实际测试情况决定是否进行优化为先变量数据库，如果变更较快可不优化)
手动执行 SQL 语句：

```sql
ALTER TABLE node_man_cloud ADD COLUMN tenant_id VARCHAR(64) DEFAULT 'tencent' NULL;
ALTER TABLE node_man_gseplugindesc ADD COLUMN tenant_id VARCHAR(64) DEFAULT 'tencent' NULL;
ALTER TABLE node_man_host ADD COLUMN tenant_id VARCHAR(64) DEFAULT 'tencent' NULL;
ALTER TABLE node_man_packages ADD COLUMN tenant_id VARCHAR(64) DEFAULT 'tencent' NULL;
ALTER TABLE node_man_pluginresourcepolicy ADD COLUMN tenant_id VARCHAR(64) DEFAULT 'tencent' NULL;
ALTER TABLE node_man_processstatus ADD COLUMN tenant_id VARCHAR(64) DEFAULT 'tencent' NULL;
ALTER TABLE node_man_subscription ADD COLUMN tenant_id VARCHAR(64) DEFAULT 'tencent' NULL;
```

### 第七步：验证数据并开启周期任务
完成数据迁移后，验证数据的完整性，然后开启周期任务。

#### 1. 记录迁移数据的最大 ID
将迁移过来的数据的最大 ID 记录到 GlobalSettings 表的 `MIGRATE_OFFSET` key 中：

```bash
./tool_record_migrate_offset.sh
```

此脚本会自动：
1. 查询目标数据库中各表的最大 ID
2. 将查询结果记录到 GlobalSettings 表的 `MIGRATE_OFFSET` key 中
3. 验证记录内容

脚本依赖 `0_config_common.sh` 中的数据库配置信息，请确保已正确配置。

#### 2. 验证数据
检查迁移后的数据是否完整和正确：

```bash
# 验证各表数据行数
mysql target_db -e "SELECT table_name, TABLE_ROWS FROM information_schema.TABLES WHERE table_schema='target_db' AND table_name IN ('node_man_cloud', 'node_man_host', 'node_man_packages', 'node_man_subscription');"
```

#### 3. 开启周期任务
恢复 Celery Beat 服务和订阅任务：

```bash
# 重启 Celery Beat
kubectl scale deployment bk-nodeman-backend-celery-beat --replicas=1 -n blueking
```

## 注意事项
- 迁移过程中请勿进行其他数据库操作
- 迁移完成后验证数据完整性
- 迁移失败时应立即回滚

---

## 第二阶段：增量数据迁移

第一阶段完成后，源环境会继续产生新数据。第二阶段用于迁移这些增量数据到目标环境。

### 前置条件：执行 Django `migrate`

在执行第二阶段增量迁移前，请先在目标环境对主数据库（通常是 `default`）执行 Django 迁移，确保所有模型变更和 schema 更新已经应用完毕。示例命令：

```bash
# 在目标环境应用迁移，仅对主库执行
python manage.py migrate --database=default
```

**执行位置**：目标环境

### 前置准备：配置数据库连接信息

在目标环境的 Django 配置中（`config/prod.py`）添加源数据库和目标数据库的连接配置：

```python
DATABASES = {
    'default': {
        # 目标数据库配置（现有配置）
        ...
    },
    'target': {
        # 目标数据库配置（与 default 相同）
        ...
    },
    'source': {
        # 源数据库配置（旧环境的数据库）
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '127.0.0.1',  # 源环境数据库主机
        'PORT': 3306,
        'NAME': 'bk_nodeman_old',  # 源环境数据库名
        'USER': 'root',
        'PASSWORD': 'source_password',
        ...
    },
}
```


### 第一步：执行增量数据迁移

使用 Django 管理命令执行增量数据迁移。该命令会根据第一阶段记录的 `MIGRATE_OFFSET` 偏移量来确定增量数据范围：

```bash
python manage.py migrate_incremental_tables \
    --source-db source \
    --target-db target \
    --offset 100000
```
此命令会：
1. 从目标库的 GlobalSettings 表中读取 `MIGRATE_OFFSET` 偏移量
2. 根据偏移量从源库查询增量数据（id > offset）
3. 将增量数据插入到目标库
4. 更新目标库的 `MIGRATE_OFFSET` 为最新的最大 ID

### 第二步：指定全局偏移量（可选）

如果需要使用全局偏移量而不是表级别的偏移量：

```bash
python manage.py migrate_incremental_tables \
    --source-db source \
    --target-db target \
    --offset 100000
```

参数说明：
- `--source-db`: 源数据库别名（
- `--target-db`: 目标数据库别名
- `--offset`: 全局偏移量，迁移 id > offset 的记录，若不指定则从 `MIGRATE_OFFSET` 读取

### 第三步：只迁移特定表（可选）

如果只需要迁移某些表的增量数据：

```bash
python manage.py migrate_incremental_tables \
    --source-db source \
    --target-db target \
    --tables node_man_subscription node_man_subscriptiontask
```

支持的表列表：
- node_man_gseconfigenv
- node_man_gseconfigextraenv
- node_man_gseconfigtemplate
- node_man_gseplugindesc
- node_man_installchannel
- node_man_packages
- node_man_pluginconfiginstance
- node_man_pluginconfigtemplate
- node_man_pluginresourcepolicy
- node_man_proccontrol
- node_man_processstatus
- node_man_subscription
- node_man_subscriptioninstancerecord
- node_man_subscriptionstep
- node_man_subscriptiontask
- tag_tag

### 第四步：Dry-run 模式（测试迁移）

在实际迁移前，可以用 dry-run 模式先预览会迁移的数据量：

```bash
python manage.py migrate_incremental_tables \
    --source-db source \
    --target-db target \
    --dry-run
```

此模式不会对目标库做任何修改，只是打印会迁移的数据统计信息。

### 第五步：调整批量大小（可选）

如果数据量很大，可以调整批处理的大小以优化性能：

```bash
python manage.py migrate_incremental_tables \
    --source-db source \
    --target-db target \
    --batch-size 5000
```

参数说明：
- `--batch-size`: 每批次查询和插入的行数（默认为 1000）

### 增量迁移执行示例

**场景1：首次增量迁移（使用第一阶段记录的偏移量）**
```bash
python manage.py migrate_incremental_tables \
    --source-db source \
    --target-db target
```

**场景2：多次增量迁移（自动使用更新后的偏移量）**
```bash
# 第2次增量迁移，自动从 MIGRATE_OFFSET 读取上次的最大 ID
python manage.py migrate_incremental_tables \
    --source-db source \
    --target-db target

# 第3次增量迁移，依次类推
python manage.py migrate_incremental_tables \
    --source-db source \
    --target-db target
```

**场景3：指定特定偏移量（用于恢复或补齐）**
```bash
python manage.py migrate_incremental_tables \
    --source-db source \
    --target-db target \
    --offset 500000
```

### 增量迁移注意事项

- **防重机制**：目标库使用 `INSERT IGNORE`（MySQL）或 `ON CONFLICT DO NOTHING`（PostgreSQL）自动处理重复数据
- **偏移量更新**：每次成功迁移后，`MIGRATE_OFFSET` 会自动更新为该表的最大 ID
- **Pipeline Tree**：含有 `pipeline_id` 的表会自动触发相关 `node_man_pipelinetree` 数据的迁移
- **事务支持**：每批数据使用事务保证一致性
- **可重复执行**：由于有防重机制，即使重复运行命令也不会产生重复数据
- **建议频率**：根据业务需求定期执行，如每小时或每天一次
