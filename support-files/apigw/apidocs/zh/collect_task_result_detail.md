### 功能描述

采集任务执行详细结果

### 请求参数

#### 接口参数

| 字段                 | 类型  | <div style="width: 50pt">必选</div> | 描述     |
|--------------------|-----|-----------------------------------|--------|
| job_id             | int | 是                                 | 作业ID   |
| instance_id        | int | 是                                 | 实例ID   |

### 请求参数示例

```json
{
    "job_id": "6679052",
    "instance_id": "host|instance|host|127.0.0.1-633-0"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
       "celery_id": 123
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

| 字段           | 类型   | 描述         |
|--------------|------|------------|
| celery_id    | int  |  celery任务ID |
