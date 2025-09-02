### 功能描述

渲染配置模板

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段             | 类型        | <div style="width: 50pt">必选</div> | 描述       |
|----------------|-----------|-----------------------------------|----------|
| plugin_name    | string    | 否                                 | 插件名      |
| plugin_version | string    | 否                                 | 版本号      |
| name           | string    | 否                                 | 配置模板名    |
| version        | string    | 否                                 | 配置模板版本   |
| id             | int array | 否                                 | 配置模板版本id |
| data           | object    | 是                                 | 采集配置     |

### 请求参数示例

```json
{
    "plugin_name": "poe_prometheus_exporter",
    "plugin_version": "*",
    "name": "bkmonitorbeat_debug.yaml",
    "version": "1",
    "data": {
        "host": "127.0.0.1",
        "port": "9090",
        "period": "10",
        "metric_url": "127.0.0.1:9090/metrics"
    }
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "id": 9,
        "md5": "dab43f1b255a78e1d288783c62fcf1b",
        "creator": "admin",
        "source_app_code": "bk_nodeman"
    },
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型     | 描述                         |
| ------- | ------ | -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | object | 请求返回的数据，见data定义            |

#### data

| 字段              | 类型     | 描述           |
|-----------------|--------|--------------|
| id              | int    | 插件配置文件实例id   |
| md5             | string | md5值         |
| creator         | string | 创建者          |
| source_app_code | string | 来源系统app_code |
