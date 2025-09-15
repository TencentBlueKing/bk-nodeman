### 功能描述

查询插件包历史

### 请求参数

#### 接口参数

| 字段   | 类型   | <div style="width: 50pt">必选</div> | 描述    |
|------|------|-----------------------------------|-------|
| id   | int  | 是                                 | 插件包id |

### 请求参数示例

```json
{
  "id": 1
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
      {
        "id": 1,
        "pkg_name": "basereport-1.0.tgz",
        "project": "basereport",
        "version": "1.0",
        "pkg_size": 4391830,
        "md5": "35bf230be9f3c1b878ef7665be34e14e",
        "config_templates": [
            {"name": "bkunifylogbeat.conf", "version": "1.0", "is_main": false},
            {"name": "bkunifylogbeat1.conf", "version": "1.1", "is_main": false},
            {"name": "bkunifylogbeat-main.config", "version": "0.1", "is_main": true}
        ],
        "pkg_mtime": "2019-11-25 21:58:30",
        "creator": "test_person",
        "is_ready": true,
        "is_release_version": true
      },
      {
        "id": 2,
        "pkg_name": "basereport-1.1.tgz",
        "module": "gse_plugin",
        "project": "basereport",
        "version": "1.1",
        "os": "linux",
        "cpu_arch": "x86",
        "md5": "35bf230be9f3c1b878ef7665be34e14e",
        "pkg_size": 4391830,
        "config_templates": [
            {"id": 1, "name": "child1.conf", "version": "1.0", "is_main": false},
            {"id": 2, "name": "child2.conf", "version": "2.0", "is_main": false},
            {"id": 3, "name": "bkunifylogbeat-main.config", "version": "0.2", "is_main": true}
        ],
        "pkg_mtime": "2019-11-25 22:01:30",
        "creator": "test_person",
        "is_ready": true,
        "is_newest": true,
        "is_release_version": true
      }
    ],
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型      | 描述                         |
| ------- |---------| -------------------------- |
| result  | bool    | 请求成功与否。true:请求成功；false请求失败 |
| code    | int     | 错误编码。 0表示success，>0表示失败错误  |
| message | string  | 请求失败返回的错误信息                |
| data    | array   | 请求返回的数据，见data定义            |

#### data

| 字段                  | 类型     | 描述                   |
|---------------------|--------|----------------------|
| id                  | int    | 插件包ID                |
| pkg_name            | string | 压缩包名                 |
| module              | string | 所属服务                 |
| project             | string | 工程名                  |
| version             | string | 版本号                  |
| os                  | string | 系统类型                 |
| cpu_arch            | string | CPU类型                |
| md5                 | string | md5值                 |
| pkg_size            | int    | 包大小                  |
| config_templates    | object | 配置模板信息               |
| pkg_mtime           | string | 包更新时间                |
| creator             | string | 操作人                  |
| is_ready            | bool   | 插件是否可用               |
| is_newest           | bool   | 是否是最新版本包 |
| is_release_version  | bool   | 是否已经发布版本             |
