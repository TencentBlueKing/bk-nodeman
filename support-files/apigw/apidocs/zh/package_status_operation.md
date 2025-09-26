### 功能描述

插件包状态类操作

### 请求参数

#### 接口参数

| 字段            | 类型        | <div style="width: 50pt">必选</div> | 描述                                                          |
|---------------|-----------|-----------------------------------|-------------------------------------------------------------|
| operation     | string    | 是                                 | 状态操作，`release`-`上线`，`offline`-`下线` `ready`-`启用`，`stop`-`停用` |
| id            | array     | 否                                 | 插件包id列表，`id`和（`name`, `version`）至少有一个                       |
| name          | string    | 否                                 | 插件名，`id`和（`name`, `version`）至少有一个                           |
| version       | string    | 否                                 | 插件版本                                                        |
| cpu_arch      | string    | 否                                 | cpu架构                                                       |
| os            | string    | 否                                 | 操作系统                                                        |
| md5_list      | array     | 是                                 | md5列表                                                       |

### 请求参数示例

```json
{
    "operation": "stop",
    "name": "bkmonitorbeat",
    "version": "3.63.3482",
    "os": "linux",
    "cpu_arch": "x86",
    "md5_list": ["8329838ebbbfba3a72ef5e6011d740af"]
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        55
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
| data    | array  | 请求返回的数据，返回操作成功的插件包id列表           |


