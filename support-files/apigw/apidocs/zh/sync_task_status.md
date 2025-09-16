### 功能描述

查询同步任务状态

### 请求参数

#### 接口参数

| 字段          | 类型     | <div style="width: 50pt">必选</div> | 描述     |
|-------------|--------| --------------------------------- |--------|
| task_id     | string | 是                                 | 任务ID   |

### 请求参数示例

```json
{
    "task_id": "0ffdb6ef-95ab-46dc-a37a-3443db7608a2"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "task_id": "0ffdb6ef-95ab-46dc-a37a-3443db7608a2",
        "status": "PENDING"
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

| 字段                  | 类型     | 描述               |
|---------------------|--------|------------------|
| task_id             | int    | 任务ID             |
| status              | int    | 同步任务状态，见status定义 |

##### status

| 状态类型     | 类型     | 描述   |
|----------| ------ |------|
| PENDING  | string | 运行中  |
| STARTED  | string | 已经开始 |
| RETRY    | string | 重试   |
| FAILURE  | string | 失败   |
| SUCCESS  | string | 成功   |

