### 功能描述

触发插件打包导出

### 请求参数

#### 接口参数

| 字段                | 类型     | <div style="width: 50pt">必选</div> | 描述                   |
|-------------------|--------| --------------------------------- |----------------------|
| category          | string | 是                                 | 插件名类型                |
| query_params      | object | 是                                 | 查询参数，见query_params定义 |
| creator           | string | 是                                 | 任务创建者                |
| bk_app_code       | string | 是                                 | 系统app_code           |

#### query_params

| 字段        | 类型     | <div style="width: 50pt">必选</div> | 描述    |
|-----------| ------ |-----------------------------------|-------|
| project   | string | 是                                 | 插件名称  |
| version   | string | 是                                 | 插件版本  |
| os        | string | 否                                 | 系统类型  |
| cpu_arch  | string | 否                                 | cpu架构 |

### 请求参数示例

```json
{
    "category": "gse_plugin",
    "query_params": {
        "project": "test_plugin",
        "version": "1.0.0"
    },
    "creator": "test_person",
    "bk_app_code": "bk_test_app"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
       "job_id": 1
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

| 字段             | 类型   | 描述     |
|----------------|------|--------|
| job_id         | int  | 任务id   |

