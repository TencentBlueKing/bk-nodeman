### 功能描述

发布配置模板

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段        | 类型        | <div style="width: 50pt">必选</div> | 描述                                    |
|-----------|-----------|-----------------------------------|---------------------------------------|
| id        | int array | 否                                 | 插件包id列表，`id`和（`name`, `version`）至少有一个 |
| name      | string    | 否                                 | 插件包名称                                 |
| version   | string    | 否                                 | 版本号                                   |
| cpu_arch  | string    | 否                                 | CPU类型                                 |
| os        | string    | 否                                 | 系统类型                                  |
| md5_list  | array     | 是                                 | md5列表                                 |

### 请求参数示例

```json
{
    "name": "tconnd",
    "version": "5.6",
    "md5_list": [
        "de3c381a8904e5349f62d907a8d8d60b"
    ]
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [1, 2, 4],
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


