## bk-nodeman升级django3记录

这个文档用来记录节点管理由django2升级为django3的问题和措施，方便后续追溯

### 1. 去掉npath, upath

错误：

```
can't import upath() and npath()
```

解决:

django.utils._os.upath() and npath() - These functions do nothing on Python 3.

参考: 

 https://stackoverflow.com/questions/67287298/importerror-cannot-import-name-upath-django-3



### 2. 修改AppIAMConfig的name

错误：

```
django.core.exceptions.ImproperlyConfigured: Cannot import 'apps.iam'. Check that 'apps.iam_migration.apps.AppIAMConfig.name' is correct.
```

解决：

修改AppIAMConfig的name，具体代码如下

```python
class AppIAMConfig(AppConfig):
    name = "apps.iam_migration"
    verbose_name = "AppIAM"
```

参考：

https://stackoverflow.com/questions/67358268/django-python-django-core-exceptions-improperlyconfigured-cannot-import-conta



### 3. 升级celery相关安装包

错误：

```
File "E:\pythonProj\bk-nodeman\bk-nodeman\venv\lib\site-packages\djcelery\admin.py", line 11, in <module>
    from django.shortcuts import render_to_response
ImportError: cannot import name 'render_to_response'
```

解决：

在django3中，djcelery可以用celery4.0以上代替，然后升级相关安装包即可

参考：

https://www.cnblogs.com/wuyan717/p/15108341.html



### 4. 升级django3的相关依赖包，或者安装django-utils-six

错误:

在rest_framework中报错:

```
ImportError: cannot import name 'six'
```

解决:

理论上说需要把相关的报都升级为最高版本，但是升级以后依然报错，无奈只能安装这个包临时抢救一下了：

```shell
pip install django-utils-six
```

参考:

https://stackoverflow.com/questions/59193514/importerror-cannot-import-name-six-from-django-utils



### 5. Django 3.2 use HttpResponse.headers in place of ._headers

错误：

```
response.\_headers["x-content-type-options"] = ("X-Content-Type-Options", "nosniff")
AttributeError: 'Response' object has no attribute '_headers'
```

解决：

```python
response.headers["x-content-type-options"] = ("X-Content-Type-Options", "nosniff")
```

参考：

[Django 3.2 use HttpResponse.headers in place of ._headers · Issue #7015 · django-cms/django-cms (github.com)](https://github.com/django-cms/django-cms/issues/7015)



### 6. from_db_value()中的'context'设置为None

错误：

```
TypeError: from_db_value() missing 1 required positional argument: 'context'
```

解决

在apps/node_man/models.py中修改from_db_value代码如下

```python
def from_db_value(self, value, expression, connection, context=None):
```

参考：

https://github.com/nesdis/djongo/issues/414



### 7. worker启动出错 将StrictRedisCluster替换为RedisCluster

错误：

```
from rediscluster import StrictRedisCluster
ImportError: cannot import name 'StrictRedisCluster'
```

解决：

因为新版本的redis-py-cluster已经不支持StrictRedisCluster，因此我们需要把代码里面的StrictRedisCluster替换成RedisCluster

参考：

https://blog.csdn.net/zhang_xiaoqiang/article/details/112644805



### 8. 禁用掉djcelery使用

错误:

```
AttributeError: 'DatabaseFeatures' object has no attribute 'autocommits_when_autocommit_is_off'
```

解决：

禁用掉djcelery的使用，具体来说在default.py里面将IS_USE_CELERY设为Fasle

参考：

无

