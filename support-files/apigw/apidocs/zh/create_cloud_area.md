### 功能描述

创建管控区域

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段                | 类型        | <div style="width: 50pt">必选</div> | 描述                                             |
|-------------------|-----------|-----------------------------------| ---------------------------------------------- |
| bk_cloud_na       | string    | 是                                 | 管控区域名称                                           |
| isp               | string    | 是                                 | 云服务商                            |
| ap_id             | int       | 是                                 | 接入点ID                                    |

### 请求参数示例

```json
{
    "bk_cloud_name": "xxx",
    "isp": "企业私有云",
    "ap_id": 3
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "bk_cloud_id": 81
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

| 字段            | 类型  | 描述     |
|---------------| --- |--------|
| bk_cloud_id   | int | 管控区域ID |

