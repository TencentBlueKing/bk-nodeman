### 功能描述

查询策略列表

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段         | 类型        | <div style="width: 50pt">必选</div> | 描述       |
|------------|-----------| --------------------------------- |----------|
| bk_biz_ids | int array | 否                                 | 业务ID李彪   |
| only_root  | bool      | 否                                 | 仅搜索父策略   |
| conditions | array     | 否                                 | 搜索条件     |
| page       | int       | 否                                 | 当前页数，默认为1 |
| pagesize   | int       | 否                                 | 分页大小，默认为10 |
| ordering   | object    | 否                                 | 返回全部简要信息 |

### 请求参数示例

```json
{
    "bk_biz_ids": [
        555,
        100791
    ],
    "only_root": true,
    "conditions": [
        {
            "key": "plugin_name",
            "value": "bkmonitorbeat"
        }
    ],
    "page": 1,
    "pagesize": 20
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "total": 10,
        "list": [
            {
                "id": 1,
                "name": "日志采集",
                "plugin_name": "basereport",
                "nodes_scope": {
                    "host_count": 99,
                    "node_count": 123
                },
                "bk_biz_scope": [1, 2, 3],
                "operator": "admin",
                "updated_at": "2020-07-26 19:17:56"
            },
            {
                "id": 2,
                "name": "日志采集2",
                "plugin_name": "basereport",
                "nodes_scope": {
                    "host_count": 80,
                    "node_count": 123
                },
                "bk_biz_scope": [1, 2],
                "operator": "admin",
                "updated_at": "2020-07-26 19:17:56"
            }
        ]
    },
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

| 字段             | 类型        | <div style="width: 50pt">必选</div> | 描述       |
|----------------|-----------|-----------------------------------|----------|
| id             | int       | 是                                 | 策略ID     |
| name           | string    | 是                                 | 策略名      |
| plugin_name    | string    | 是                                 | 插件名      |
| nodes_scope    | object    | 是                                 | 节点范围     |
| bk_biz_scope   | int array | 是                                 | 订阅监听业务范围 |
| operator       | string    | 是                                 | 操作人      |
| updated_at     | string    | 是                                 | 更新时间     |
