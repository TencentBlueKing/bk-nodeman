### 功能描述

创建同步任务

### 请求参数

#### 接口参数

| 字段            | 类型     | <div style="width: 50pt">必选</div> | 描述    |
|---------------|--------| --------------------------------- |-------|
| task_name     | string | 是                                 | 任务名称   |
| task_params   | object | 否                                 | 任务调用参数  |

### 请求参数示例

```json
{
    "task_name": "sync_cmdb_host"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "task_id": "0ffdb6ef-95ab-46dc-a37a-3443db7608a2"
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

| 字段                  | 类型     | 描述   |
|---------------------|--------|------|
| task_id             | int    | 任务id |

