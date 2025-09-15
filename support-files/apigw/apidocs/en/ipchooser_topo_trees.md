### Function Description

Batch get topology trees containing the number of hosts for each node

### Request Parameters

#### Interface Parameters

| Field        | Type   | <div style="width: 50pt">Required</div> | Description                                                             |
|--------------|--------|-----------------------------------------|-------------------------------------------------------------------------|
| all_scope    | bool   | No                                      | Whether to retrieve topology across all resource scopes. Default: false |
| scope_list   | array  | No                                      | Resource scope list for the topology，see scope_list definition          |
| action       | string | No                                      | Permission type. Default: agent_view. See action definition             |

###### scope_list

| Field          | Type     | <div style="width: 50pt">Required</div> | Description         |
|----------------|----------|-----------------------------------------|---------------------|
| scope_type     | string   | Yes                                     | Resource scope type |
| scope_id       | string   | No                                      | Resource scope ID   |
| bk_biz_id      | int      | No                                      | Business ID         |

###### action

| Field             | Type     | Description             |
|-------------------|----------|-------------------------|
| agent_view        | string   | View Agent information  |
| agent_operate     | string   | Operate on Agent        |
| proxy_operate     | string   | Operate on Proxy        |
| plugin_view       | string   | View plugin information |
| plugin_operate    | string   | Operate on plugin       |
| strategy_view     | string   | View strategy           |
| strategy_create   | string   | Create strategy         |

### Request Example

```json
{
    "all_scope": false,
    "scope_list": [
        {
            "scope_type": "biz",
            "scope_id": "10003"
        }
    ]
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "instance_id": 5000445,
            "instance_name": "EIAM政务认证",
            "object_id": "biz",
            "object_name": "业务",
            "meta": {
                "scope_type": "biz",
                "scope_id": "5000445",
                "bk_biz_id": 5000445
            },
            "count": 1,
            "child": [
                {
                    "instance_id": 5026009,
                    "instance_name": "空闲机池",
                    "object_id": "set",
                    "object_name": "集群",
                    "meta": {
                        "scope_type": "biz",
                        "scope_id": "5000445",
                        "bk_biz_id": 5000445
                    },
                    "count": 1,
                    "child": [
                        {
                            "instance_id": 5067855,
                            "instance_name": "故障机",
                            "object_id": "module",
                            "object_name": "模块",
                            "meta": {
                                "scope_type": "biz",
                                "scope_id": "5000445",
                                "bk_biz_id": 5000445
                            },
                            "count": 0,
                            "child": [],
                            "lazy": false
                        },
                        {
                            "instance_id": 5067854,
                            "instance_name": "空闲机",
                            "object_id": "module",
                            "object_name": "模块",
                            "meta": {
                                "scope_type": "biz",
                                "scope_id": "5000445",
                                "bk_biz_id": 5000445
                            },
                            "count": 1,
                            "child": [],
                            "lazy": false
                        },
                        {
                            "instance_id": 5067856,
                            "instance_name": "待回收",
                            "object_id": "module",
                            "object_name": "模块",
                            "meta": {
                                "scope_type": "biz",
                                "scope_id": "5000445",
                                "bk_biz_id": 5000445
                            },
                            "count": 0,
                            "child": [],
                            "lazy": false
                        }
                    ],
                    "lazy": false
                }
            ],
            "lazy": false
        }
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field       | Type    | Description                                                            |
|-------------|---------|------------------------------------------------------------------------|
| result      | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code        | int     | Error code. 0 indicates success; values greater than 0 indicate errors |
| message     | string  | Error message returned when the request fails                          |
| data        | array   | Data returned by the request, see definition below                     |
 
#### data

| Field          | Type    | Description                                                                      |
|----------------|---------|----------------------------------------------------------------------------------|
| meta           | object  | Metadata, see meta definition                                                    |
| object_id      | string  | Node type ID                                                                     |
| object_name    | string  | Node type name                                                                   |
| instance_id    | int     | Node instance ID                                                                 |
| instance_name  | string  | Node instance name                                                               |
| count          | int     | Number of node                                                                   |
| child          | array   | List of child nodes. see child definition                                        |
| lazy           | bool    | Indicates whether children are lazily loaded (true = only placeholder returned)  |

#### child

| Field          | Type    | Description                                                                      |
|----------------|---------|----------------------------------------------------------------------------------|
| meta           | object  | Metadata, see meta definition                                                    |
| object_id      | string  | Node type ID                                                                     |
| object_name    | string  | Node type name                                                                   |
| instance_id    | int     | Node instance ID                                                                 |
| instance_name  | string  | Node instance name                                                               |
| count          | int     | Number of node                                                                   |
| child          | array   | List of child nodes. see child definition                                        |
| lazy           | bool    | Indicates whether children are lazily loaded (true = only placeholder returned)  |

#### meta

| Field        | Type    | Description           |
|--------------|---------|-----------------------|
| bk_biz_id    | int     | Business ID           |
| scope_type   | string  | Resource scope type   |
| scope_id     | string  | Resource scope type   |