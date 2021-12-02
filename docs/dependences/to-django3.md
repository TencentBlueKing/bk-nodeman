# bk-nodeman升级django3记录

这个文档用来记录节点管理由django2升级为django3的问题和措施，方便后续追溯

## 移除 npath, upath

错误： `can't import upath() and npath()`

原因：django.utils._os.upath() and npath() - These functions do nothing on Python 3.

参考: https://stackoverflow.com/questions/67287298/importerror-cannot-import-name-upath-django-3



## 修改 AppIAMConfig 

### 报错

```
django.core.exceptions.ImproperlyConfigured: Cannot import 'apps.iam'. Check that 'apps.iam_migration.apps.AppIAMConfig.name' is correct.
```

### 处理方案

修改AppIAMConfig的name，具体代码如下

```python
class AppIAMConfig(AppConfig):
    name = "apps.iam_migration"
    verbose_name = "AppIAM"
```

### 参考

https://stackoverflow.com/questions/67358268/django-python-django-core-exceptions-improperlyconfigured-cannot-import-conta


## Django 3.2 use HttpResponse.headers in place of ._headers

### 错误

```
response.\_headers["x-content-type-options"] = ("X-Content-Type-Options", "nosniff")
AttributeError: 'Response' object has no attribute '_headers'
```

### 处理方案

```python
response.headers["x-content-type-options"] = ("X-Content-Type-Options", "nosniff")
```

参考：[Django 3.2 use HttpResponse.headers in place of ._headers · Issue #7015 · django-cms/django-cms (github.com)](https://github.com/django-cms/django-cms/issues/7015)



## `from_db_value()` 中的 `context` 设置为 `None`

### 错误

`TypeError: from_db_value() missing 1 required positional argument: 'context'`

### 处理方案

在apps/node_man/models.py中修改from_db_value代码如下

```python
def from_db_value(self, value, expression, connection, context=None):
```

### 参考

https://github.com/nesdis/djongo/issues/414



### `worker` 启动出错

### 报错：

```
from rediscluster import StrictRedisCluster
ImportError: cannot import name 'StrictRedisCluster'
```


### 处理方案

* 新版本的 `redis-py-cluster` 已经不支持 `StrictRedisCluster`

* 需要把 `StrictRedisCluster` 替换成 `RedisCluster`

### 参考

https://blog.csdn.net/zhang_xiaoqiang/article/details/112644805


## 禁用 `djcelery`

### 报错

```
AttributeError: 'DatabaseFeatures' object has no attribute 'autocommits_when_autocommit_is_off'
```

### 处理方案

禁用掉djcelery的使用，具体来说在default.py里面将IS_USE_CELERY设为Fasle



## Table empty or key no longer exists.

### 报错

```text
kombu.exceptions.OperationalError: 
Cannot route message for exchange 'reply.celery.pidbox': Table empty or key no longer exists.
Probably the key ('_kombu.binding.reply.celery.pidbox') has been removed from the Redis database.
```

https://github.com/celery/kombu/issues/1063


## Celery eventlet

### 报错
```text
django.db.utils.DatabaseError: DatabaseWrapper objects created in a thread can only be used in that same thread. The object with alias 'default' was created in thread id 140032074089736 and this is thread id 140031737889904.
```

### 处理方案

* -P eventlet -> threads
* 该问题目前的解决方式是不使用 eventlet

### 参考
* https://github.com/celery/celery/issues/5924
* https://github.com/intelowlproject/IntelOwl/issues/379

## django-mysql 兼容

### 报错

```text
django.db.utils.OperationalError: (1101, "BLOB, TEXT, GEOMETRY or JSON column 'attrs' can't have a default value")
```

### 处理方案

```python
# cf https://github.com/adamchainz/django-mysql/issues/417
# this is supposed to be fixed in django 1.11 but in the meantime
# we need this patch to get the migration working
def skip_default(self, field):
    db_type = field.db_type(self.connection)
    return db_type is not None and db_type.lower() in {
        "tinyblob",
        "blob",
        "mediumblob",
        "longblob",
        "tinytext",
        "text",
        "mediumtext",
        "longtext",
        "json",
    }
```