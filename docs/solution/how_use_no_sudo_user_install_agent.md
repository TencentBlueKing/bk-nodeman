# 使用无免密sudo账户安装agent注意事项

*请确保使用无免密sudo权限账户安装agent的机器未曾使用过非该账户安装过agent*

*或在使用无免密sudo权限账户安装agent前将原agent卸载并清理痕迹*

```shell
# 基于默认接入点包括但不限于
/tmp/nm*
/tmp/xuoasefasd.err
/tmp/bkjob
/usr/local/gse
/var/run/ipc.stat
/var/log/gse
/var/run/gse
/var/run/ipc.state.report
/var/lib/gse
```

*请在配置接入点时确认agent的安装账户拥有hostid文件路径的读写操作权限*

hostid文件的路径默认为`Linux: /var/lib/gse/host Windows: c:/gse/data/host`

> 二进制部署版本中默认位于cmdb的/data/bkee/cmdb/server/conf/common.yaml文件eventServer-hostIdentifier中配置
>
> 容器化版本中默认位于cmdb的/data/bkhelmfile/blueking/environments/default/bkcmdb-values.yaml.gotmpl文件中的common-eventServer-hostIdentifier中配置

*请确保所用账户拥有一下系统程序操作权限*

```shell
/usr/bin/curl,
/usr/bin/mkdir,
/usr/bin/ls,
/usr/bin/cat,
/usr/bin/which,
/usr/bin/ping,
/usr/bin/echo,
/usr/bin/chmod,
/usr/bin/nohup,
/usr/bin/tail,
/usr/bin/ps,
/usr/bin/date,
/usr/bin/tee,
/usr/bin/uname,
/usr/bin/rm,
/usr/bin/awk,
/usr/bin/lsof,
/usr/bin/stat,
/usr/bin/readlink,
/usr/bin/grep,
/usr/bin/read,
/usr/bin/hash,
/usr/bin/timeout,
/usr/bin/bash,
/usr/bin/sed,
/usr/bin/chattr,
/usr/bin/cd,
/usr/bin/cp,
/usr/bin/wait,
/usr/bin/tr,
/usr/bin/wc,
/usr/bin/mktemp,
/usr/bin/seq,
/usr/bin/sleep,
/usr/bin/df,
/usr/bin/pidof,
/usr/bin/tar,
/usr/bin/gzip,
/usr/bin/pgrep,
/usr/bin/xargs,
```

## 接入点配置

接入点配置中 `hostid路径` 必须与上述 cmdb 的配置文件中指定的路径一致

创建接入点后根据接入点页面中显示的接入点id到节点管理数据库中执行下述语句

```sql
use bk_nodeman;
update node_man_accesspoint set is_use_sudo=0 where id={接入点页面中显示的id};
```

## 作业平台

作业平台需要新建该无免密sudo权限的账户的执行账户