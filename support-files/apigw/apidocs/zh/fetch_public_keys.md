### 功能描述

获取公钥列表

### 请求参数

#### 接口参数

| 字段                | 类型  | <div style="width: 50pt">必选</div> | 描述     |
|-------------------|-----|-----------------------------------|--------|
| names             | int | 是                                 | 密钥名称列表   |

### 请求参数示例

```json
{
    "names": ["DEFAULT"]
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
      {
        "name": "DEFAULT",
        "description": "默认RSA密钥",
        "content": "-----BEGIN PUBLIC KEY-----\n xxx\n-----END PUBLIC KEY-----"
      }
    ],
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型     | 描述                         |
| ------- |--------| -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | array  | 请求返回的数据，见data定义            |

#### data

| 字段           | 类型      | 描述   |
|--------------|-----------| ------|
| name         | string    | 密钥名称 |
| description  | string    | 密钥描述 |
| content      | string    | 密钥内容 |
