### 功能描述

获取GSE 2.0灰度信息

### 请求参数

{{ common_args_desc }}

#### 接口参数

### 请求参数示例

```json
{}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "bk_biz_ids": [
            2,
            5
        ]
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

| 字段        | 类型       | <div style="width: 50pt">必选</div> | 描述     |
|-----------|----------| --------------------------------- |--------|
| bk_biz_ids    | string   | 是                                 | 业务ID列表 |
