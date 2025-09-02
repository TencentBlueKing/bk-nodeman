### 功能描述

插件包状态类操作

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段       | 类型       | <div style="width: 50pt">必选</div> | 描述    |
|----------|----------| --------------------------------- |-------|
| name     | string   | 是                                 | 插件名   |
| version  | string   | 否                                 | 插件版本  |
| cpu_arch | string   | 否                                 | cpu架构 |
| os       | string   | 否                                 | 操作系统  |

### 请求参数示例

```json
{
    "name": "bkmonitorbeat",
    "version": "2.9.1.209",
    "os": "linex"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "id": 9,
            "module": "gse_plugin",
            "project": "bkmonitorbeat",
            "version": "2.9.1.209",
            "os": "windows",
            "cpu_arch": "x86",
            "pkg_name": "bkmonitorbeat-2.9.1.209.tgz",
            "pkg_size": 13759268,
            "pkg_mtime": "2023-05-24 04:31:33.868368+00:00",
            "md5": "350d6f165b291f8e51a98a193e9d05b6",
            "creator": "admin",
            "location": "http://127.0.0.1/download/windows/x86",
            "is_ready": false,
            "is_release_version": true,
            "name": "bkmonitorbeat",
            "source_app_code": "bk_nodeman"
        },
        {
            "id": 12,
            "module": "gse_plugin",
            "project": "bkmonitorbeat",
            "version": "2.9.1.209",
            "os": "windows",
            "cpu_arch": "x86_64",
            "pkg_name": "bkmonitorbeat-2.9.1.209.tgz",
            "pkg_size": 13890930,
            "pkg_mtime": "2023-05-24 04:31:49.547280+00:00",
            "md5": "7f8473812eee909bd2f8879916a10261",
            "creator": "admin",
            "location": "http://127.0.0.1/download/windows/x86_64",
            "is_ready": false,
            "is_release_version": true,
            "name": "bkmonitorbeat",
            "source_app_code": "bk_nodeman"
        }
    ],
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

| 字段                  | 类型     | 描述           |
|---------------------|--------|--------------|
| id                  | int    | 插件包id        |
| module              | string | 订阅任务名称       |
| project             | string | 工程名          |
| version             | string | 插件版本         |
| os                  | string | 操作系统         |
| cpu_arch            | string | cpu架构        |
| pkg_name            | string | 压缩包名         |
| pkg_size            | string | 插件包大小        |
| pkg_mtime           | string | 包更新时间        |
| md5                 | string | md5值         |
| creator             | string | 操作人          |
| location            | string | 安装包链接        |
| is_ready            | bool   | 插件是否可用       |
| is_release_version  | bool   | 是否已经发布版本     |
| name                | string | 插件名          |
| source_app_code     | string | 来源系统app_code |
