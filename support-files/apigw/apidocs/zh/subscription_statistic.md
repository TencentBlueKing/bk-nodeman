### 功能描述

统计订阅任务数据

### 请求参数

#### 接口参数

| 字段                    | 类型        | <div style="width: 50pt">必选</div> | 描述     |
|-----------------------|-----------|-----------------------------------|--------|
| subscription_id_list  | int array | 是                                 | 订阅ID列表 |

### 请求参数示例

```json
{
    "subscription_id_list": [100, 101]
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "subscription_id": 100,
            "status": [
                {
                    "status": "SUCCESS",
                    "count": 3
                },
                {
                    "status": "PENDING",
                    "count": 0
                },
                {
                    "status": "FAILED",
                    "count": 0
                },
                {
                    "status": "RUNNING",
                    "count": 0
                }
            ],
            "versions": [
                {
                    "version": "7.7.2-rc.29",
                    "count": 3,
                    "name": "bkunifylogbeat"
                }
            ],
            "instances": 3
        },
        {
            "subscription_id": 101,
            "status": [
                {
                    "status": "SUCCESS",
                    "count": 2
                },
                {
                    "status": "PENDING",
                    "count": 0
                },
                {
                    "status": "FAILED",
                    "count": 0
                },
                {
                    "status": "RUNNING",
                    "count": 0
                }
            ],
            "versions": [
                {
                    "version": "7.7.2-rc.29",
                    "count": 3,
                    "name": "bkmonitorbeat"
                }
            ],
            "instances": 2
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

| 字段              | 类型    | 描述                 |
|-----------------|-------|--------------------|
| subscription_id | int   | 订阅ID               |
| status          | array | 状态列表，见status定义     |
| versions        | array | 版本列表，见versions定义   |
| instances       | int   | 实例数                |

##### status

| 字段       | 类型     | 描述                                 |
|----------|--------|------------------------------------|
| status   | string | 状态，为SUCCESS、PENDING、FAILED、RUNNING |
| count    | int    | 当前状态的数量                            |

##### versions

| 字段       | 类型        | 描述      |
|----------|-----------|---------|
| version  | string    | 插件版本    |
| count    | int       | 当前版本的数量 |
| name     | string    | 插件名     |