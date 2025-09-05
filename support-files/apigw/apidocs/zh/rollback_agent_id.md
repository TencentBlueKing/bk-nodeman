### 功能描述

回滚Agent ID配置

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段             | 类型    | <div style="width: 50pt">必选</div> | 描述        |
|----------------|-------|-----------------------------------|-----------|
| bk_biz_ids     | array | 是                                 | 业务ID列表    |
| cloud_ips      | array | 否                                 | 管控区域:主机列表 |

### 请求参数示例

```json
{
    "bk_biz_ids": [123],
    "cloud_ips": ["0:10.0.0.6", "3:10.0.7.12", "27:7.8.6.1", "0:10.0.66.77"]
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "no_bk_agent_id_hosts": [],
        "success": [
            "0:10.0.0.6",
            "3:10.0.7.12",
            "27:7.8.6.1",
            "0:10.0.66.77"
        ],
        "failed": []
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

| 字段                   | 类型      | <div style="width: 50pt">必选</div> | 描述              |
|----------------------|---------| --------------------------------- |-----------------|
| no_bk_agent_id_hosts | array   | 是                                 | 没有agent-id的主机列表 |
| success              | array   | 是                                 | 回滚成功的主机列表       |
| failed               | array   | 是                                 | 回滚失败的主机列表          |
