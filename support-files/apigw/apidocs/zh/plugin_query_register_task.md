### 功能描述

查询插件注册任务

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段      | 类型  | <div style="width: 50pt">必选</div> | 描述   |
|---------| --- | --------------------------------- |------|
| job_id | int | 是                                 | 任务ID |

### 请求参数示例

```json
{
  "job_id": 123456
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "is_finish": false,
        "status": "RUNNING",
        "message": "~",
    },
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型      | 描述                         |
| ------- |---------|----------------------------|
| result  | bool    | 请求成功与否。true:请求成功；false请求失败 |
| code    | int     | 错误编码。 0表示success，>0表示失败错误  |
| message | string  | 请求失败返回的错误信息                |
| data    | array   |  请求返回的数据，见data定义           |

#### data

| 字段            | 类型     | <div style="width: 50pt">必选</div> | 描述   |
|---------------|--------|-----------------------------------|------|
| is_finish     | bool   | 是                                 | 是否完成 |
| status        | bool   | 是                                 | 执行状态 |
| message       | string | 是                                 | 日志内容 |
