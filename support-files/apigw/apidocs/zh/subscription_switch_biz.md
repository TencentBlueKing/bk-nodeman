### 功能描述

启用/禁用业务订阅巡检

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段         | 类型        | <div style="width: 50pt">必选</div> | 描述                          |
|------------|-----------| --------------------------------- |-----------------------------|
| bk_biz_ids | int array | 是                                 | 业务ID列表                      |
| action     | string    | 是                                 | 启停动作，可选["enable","disable"] |


### 请求参数示例

```json
{
    "bk_biz_ids": [78],
    "action": "enable"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "bk_biz_ids": [
            78
        ],
        "action": "enable"
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

| 字段             | 类型            | 描述           |
|----------------|---------------|--------------|
| bk_biz_ids     | int array     | 业务ID列表        |
| action         | string        | 启停动作       |

