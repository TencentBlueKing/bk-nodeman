### Function Description

Query the topology path of multiple nodes

### Request Parameters

#### Interface Parameters

| Field              | Type     | <div style="width: 50pt">Required</div> | Description                                                              |
|--------------------|----------|-----------------------------------------|--------------------------------------------------------------------------|
| node_list          | array    | Yes                                     | List of topology nodes, see node_list definition                         |
| action             | string   | No                                      | Permission type. Default: agent_view. See action definition              |

##### node_list

| Field         | Type     | <div style="width: 50pt">Required</div> | Description                        |
|---------------|----------|-----------------------------------------|------------------------------------|
| object_id     | string   | Yes                                     | Node type ID                       |
| instance_id   | string   | Yes                                     | Node instance ID                   |
| meta          | object   | Yes                                     | Metadata, see meta definition      |

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

###### meta

| Field         | Type     | <div style="width: 50pt">Required</div> | Description         |
|---------------|----------|-----------------------------------------|---------------------|
| bk_biz_id     | int      | No                                      | Business ID         |
| scope_type    | string   | Yes                                     | Resource scope type |
| scope_id      | string   | Yes                                     | Resource scope ID   |


### Request Example

```json
{
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
            "instance_id": 1,
            "meta": {
                "scope_type": "biz",
                "scope_id": "2",
                "bk_biz_id": 2
            }
        }
    ]
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        [
            {
                "meta": {
                    "scope_type": "biz",
                    "scope_id": "1",
                    "bk_biz_id": 1
                },
                "object_id": "biz",
                "object_name": "业务",
                "instance_id": 1,
                "instance_name": "蓝鲸"
            }
        ],
        [
            {
                "meta": {
                    "scope_type": "biz",
                    "scope_id": "2",
                    "bk_biz_id": 2
                },
                "object_id": "biz",
                "object_name": "业务",
                "instance_id": 2,
                "instance_name": "蓝鲸运营"
            }
        ]
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field     | Type   | Description                                                            |
|-----------|--------|------------------------------------------------------------------------|
| result    | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code      | int    | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string | Error message returned when the request fails                          |
| data      | array  | Data returned by the request, see definition below                     |
 
#### data

| Field          | Type     | Description                   |
|----------------|----------|-------------------------------|
| meta           | object   | Metadata, see meta definition |
| object_id      | string   | Node type ID                  |
| object_name    | string   | Node type name                |
| instance_id    | int      | Node instance ID              |
| instance_name  | string   | Node instance name            |

#### meta

| Field        | Type    | Description           |
|--------------|---------|-----------------------|
| bk_biz_id    | int     | Business ID           |
| scope_type   | string  | Resource scope type   |
| scope_id     | string  | Resource scope type   |