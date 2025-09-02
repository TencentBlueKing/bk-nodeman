### 功能描述

获取多个拓扑节点的主机 Agent 状态统计信息

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段               | 类型     | <div style="width: 50pt">必选</div> | 描述                        |
|------------------|--------| --------------------------------- |---------------------------|
| node_list        | array  | 是                                 | 主机列表，见 node_list 定义       | 
| search_limit     | object | 否                                 | 检索范围限制，见search_limit定义 |
| search_condition | object | 否                                 | 搜索条件，见search_condition定义  |
| search_content   | string | 否                                 | 模糊搜索内容                    |
| conditions       | array  | 否                                 | 搜索条件                      |
| start            | int    | 否                                 | 数据起始位置，默认为0               |
| page_size        | int    | 否                                 | 拉取数据数量，不传或传 `-1` 表示拉取所有   |
| action           | string | 否                                 | 权限类型，见 action 定义          |

##### node_list

| 字段          | 类型       | <div style="width: 50pt">必选</div> | 描述                                         |
|-------------|----------|-----------------------------------|--------------------------------------------|
| object_id   | string   | 是                                 | 节点类型ID |
| instance_id | string   | 是                                 | 节点实例ID                              |
| meta        | object   | 是                                 | 元数据，见 meta 定义                              |

###### search_limit

| 字段              | 类型     | <div style="width: 50pt">必选</div> | 描述   |
|-----------------|--------|-----------------------------------|------|
| host_ids        | array | 否                                 |主机 ID 列表                        |
| node_list       | array | 否                                 |节点列表                            |
| limit_host_ids  | array | 否                                 |限制检索的主机 ID 列表                            |

###### search_condition

| 字段         | 类型     | <div style="width: 50pt">必选</div> | 描述                                             |
|------------|--------|-----------------------------------|------------------------------------------------|
| ip         | string | 否                                 | 内网IP                                           |
| ipv6       | string | 否                                 | 内网IPv6                                         |
| os_type    | string | 否                                 | 操作系统类型                                         |
| host_name  | string | 否                                 | 主机名称                                           |
| cloud_name | string | 否                                 | 管控区域名称                                         |
| alive      | int    | 否                                 | Agent 存活状态，1表示存活，0表示未存活                        |
| content    | string | 否                                 | 模糊搜索内容（支持同时对`主机IP`/`主机名`/`操作系统`/`管控区域名称`进行模糊搜索 |

###### action

| 字段              | 类型     | 描述        |
|-----------------| ------ |-----------|
| agent_view      | string | agent查询   |
| agent_operate   | string | agent操作   |
| proxy_operate   | string | proxy操作   |
| plugin_view     | string | 插件查看      |
| plugin_operate  | string | 插件操作      |
| strategy_view   | string | 策略查看   |
| strategy_create | string | 策略创建 |

###### meta

| 字段          | 类型     | <div style="width: 50pt">必选</div> | 描述 |
|-------------|--------|-----------------------------------|----|
| bk_biz_id   | int    | 否                                 |业务 ID |
| scope_type  | string | 是                                 |资源范围类型 |
| scope_id    | string | 是                                 |资源范围ID |


### 请求参数示例

```json
{
    "start": 0,
    "page_size": -1,
    "action": "strategy_create",
    "node_list": [
        {
            "object_id": "biz",
            "instance_id": 1,
            "meta": {
                "scope_type": "biz",
                "scope_id": "1",
                "bk_biz_id": 1
            }
        },
        {
            "object_id": "biz",
            "instance_id": 61,
            "meta": {
                "scope_type": "biz",
                "scope_id": "61",
                "bk_biz_id": 61
            }
        }
    ],
    "conditions": []
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "agent_statistics": {
                "total_count": 0,
                "alive_count": 0,
                "not_alive_count": 0
            },
            "node": {
                "object_id": "biz",
                "instance_id": 1,
                "meta": {
                    "scope_type": "biz",
                    "scope_id": "1",
                    "bk_biz_id": 1
                }
            }
        },
        {
            "agent_statistics": {
                "total_count": 143,
                "alive_count": 136,
                "not_alive_count": 7
            },
            "node": {
                "object_id": "biz",
                "instance_id": 61,
                "meta": {
                    "scope_type": "biz",
                    "scope_id": "61",
                    "bk_biz_id": 61
                }
            }
        }
    ],
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
