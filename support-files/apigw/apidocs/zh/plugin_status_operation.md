### 功能描述

插件状态类操作

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段           | 类型        | <div style="width: 50pt">必选</div> | 描述    |
|--------------|-----------| --------------------------------- |-------|
| operation    | string    | 是                                 | 状态操作 `ready`-`启用`，`stop`-`停用`   |
| id           | int array | 是                                 |  插件id列表  |


### 请求参数示例

```json
{
    "operation": "stop",
    "id": [1, 2]
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [1, 2],
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

