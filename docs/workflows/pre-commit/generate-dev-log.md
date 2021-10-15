
# generate-dev-log
> 提交自动生成 dev-log


## 背景

为了精确维护版本日志，我们要求开发者在提交代码时，需要在 `dev_log/${pre-version}` 目录新建 `${username}_{datetime}.yaml` 的开发日志

* datetime格式：`%Y%m%d%H%M`

```text
dev_log
├── 2.1.341
│   ├── crayon_202107301142.yaml
│   ├── crayon_202108251730.yaml
│   └── durant_202108191135.yaml

```

### yaml 文件格式

####  commit_type: 提交类型
  * feature - 新特性
  * bugfix - 线上功能bug
  * minor - 不重要的修改（换行，拼写错误等）
  * optimization - 功能优化
  * refactor - 功能重构
  * test - 增加测试代码
  * docs - 编写文档

#### commit_msg: 提交信息
一般情况下，提交都是关联 Github Issue，非常建议在 `commit-msg` 中显式的声明或关闭 issue

声明或关闭 `issue` `(${action} #${issue_id})`
* action:
  * 可为空，表示该 `issue` 还未完结
  * 对于不同的 `commit_type`，做如下约束：
    * `commit_type != bugfix` - `close` `closes` `closed` 
    * `commit_type == bugfix` - `fix` `fixes` `fixed` `resolve` `resolves` `resolved`
  * action 不为空的情况下，当该 `commit` 合入主分支时，`GitHub` 会关闭相应的 `issue`，你可以参考：https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue

* issue_id: 在提交代码前，应该先在 `Github` 创建 `issue`，简要记录背景和解决方案

下面简单给一个样例子

```yaml
# dev_log/2.1.348/crayon_202108141110.yaml
feature:
  - "插件包管理支持对象存储模式 (closed #2)"
```

## 使用

通过在 `commit message` 加入 `(wf -l)` 关键字，`hook` 会匹配给关键字并根据 `commit message` 自动生成 yaml 文件 

无需担心 `(wf -l)` 会污染 `commit message`，`hook` 会从 `commit message` 中自动移除该关键字

```shell
git commit -m "feature: 插件包管理支持对象存储模式 (closed #2)(wf -l)"

# git log
# feature: 插件包管理支持对象存储模式 (closed #2)
```


## 自定义
> 如果有拓展或修改yaml格式的需求，可以通过修改 scripts/workflows/pre-commit/generate_dev_log.py 来实现

### 修改关键字

`WF_CMD_PATTERN`: 默认值为 `(wf -l)`

### 修改 `dev_log` 生成路径

`DEV_LOG_ROOT`: 默认值为 `dev_log`，即位于项目目录下

### 查重

生成 yaml 文件后，`pre-commit` 会失败，需要重新再提交一次，为了保证不重复生成 yaml 文件，需要进行查重

方法 `check_is_record` 用于实现该查重功能，通过修改传入的文件列表 `dev_log_yaml_paths: List[str]` 来确定扫描范围，同时你也可以修改该函数的逻辑，更精确地进行扫描

### 修改 yaml 文件格式

重写 `generate_dev_log` 方法


## 已知问题

### PyCharm Git 可视化提交，生成的yaml文件未能及时展示

* PyCharm 仅监听应用主进程的文件变更，并且使用 `git commit only` 进行提交，新增文件没有触发 `File Watch`
* 解决方法：`File -> Reload All from Disk` 或对应的快捷键进行刷新
