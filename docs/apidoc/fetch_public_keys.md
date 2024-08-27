### 功能描述

获取公钥列表

### 请求参数

{{common_args_desc }}

#### 接口参数

| 字段  | 类型  | <div style="width: 50pt">必选</div> | 描述                              |
| ----- | ----- | ----------------------------------- | --------------------------------- |
| names | array | 是                                  | 密钥名称列表，仅支持传递"DEFAULT" |

### 请求参数示例

```json
{
    "bk_app_code": "esb_test",
    "bk_app_secret": "xxx",
    "bk_username": "admin",
    "names": [
        "DEFAULT"
    ]
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "name": "DEFAULT",
            "description": "默认密钥",
            "content": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0AQEA6JEvfRtvBeQQ7Pk81vR8\n-----END PUBLIC KEY-----",
            "cipher_type": "RSA",
            "block_size": 95
        }
    ],
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段    | 类型   | 描述                                       |
| ------- | ------ | ------------------------------------------ |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误    |
| message | string | 请求失败返回的错误信息                     |
| data    | object | 请求返回的数据，见data定义                 |

#### data

| 字段        | 类型   | 描述             |
| ----------- | ------ | ---------------- |
| name        | string | 密钥名称         |
| description | string | 密钥描述         |
| content     | string | 密钥内容         |
| cipher_type | string | 加密类型         |
| block_size  | int    | 加解密最大片长度 |
