### Function Description

Get the statistics of the host Agent status for multiple topology nodes

### Request Parameters

#### Interface Parameters

| Field              | Type     | <div style="width: 50pt">Required</div> | Description                                                              |
|--------------------|----------|-----------------------------------------|--------------------------------------------------------------------------|
| node_list          | array    | Yes                                     | List of topology nodes, see node_list definition                         | 
| search_limit       | object   | No                                      | Search scope limits, see search_limit definition                         |
| search_condition   | object   | No                                      | Search conditions, see search_condition definition                       |
| search_content     | string   | No                                      | Fuzzy search content                                                     |
| conditions         | array    | No                                      | Filter conditions                                                        |
| start              | int      | No                                      | Data offset. Default: 0                                                  |
| page_size          | int      | No                                      | Number of records to retrieve. Omit or set to -1 to retrieve all records |
| action             | string   | No                                      | Permission type. Default: agent_view. See action definition              |

##### node_list

| Field         | Type     | <div style="width: 50pt">Required</div> | Description                        |
|---------------|----------|-----------------------------------------|------------------------------------|
| object_id     | string   | Yes                                     | Node type ID                       |
| instance_id   | string   | Yes                                     | Node instance ID                   |
| meta          | object   | Yes                                     | Metadata, see meta definition      |

###### search_limit

| Field             | Type    | <div style="width: 50pt">Required</div> | Description                               |
|-------------------|---------|-----------------------------------------|-------------------------------------------|
| host_ids          | array   | No                                      | List of host IDs                          |
| node_list         | array   | No                                      | List of nodes                             |
| limit_host_ids    | array   | No                                      | Restrict search only to these host IDs    |

###### search_condition

| Field        | Type     | <div style="width: 50pt">Required</div> | Description                                                          |
|--------------|----------|-----------------------------------------|----------------------------------------------------------------------|
| ip           | string   | No                                      | Internal IP address                                                  |
| ipv6         | string   | No                                      | Internal IPv6 address                                                |
| os_type      | string   | No                                      | Operating system type                                                |
| host_name    | string   | No                                      | Host name                                                            |
| cloud_name   | string   | No                                      | Cloud area name                                                      |
| alive        | int      | No                                      | Agent status: 1 = alive, 0 = not alive                               |
| content      | string   | No                                      | Fuzzy search content (applies to IP, hostname, OS, cloud area name)  |

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

### Response Example

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

### Response Parameters Description

#### response

| Field     | Type    | Description                                                            |
|-----------|---------|------------------------------------------------------------------------|
| result    | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code      | int     | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string  | Error message returned when the request fails                          |
| data      | array   | Data returned by the request, see definition below                     |

#### data

| Field             | Type     | Description                                              |
|-------------------|----------|----------------------------------------------------------|
| agent_statistics  | object   | Agent status statistics, see agent_statistics definition |
| node              | object   | Node information, see node definition                    |

##### agent_statistics

| Field           | Type  | Description                           |
|-----------------|-------|---------------------------------------|
| total_count     | int   | Total number of agents under the node |
| alive_count     | int   | Number of alive agents                |
| not_alive_count | int   | Number of non-alive agents            |

##### node

| Field         | Type     | Description                     |
|---------------|----------|---------------------------------|
| object_id     | string   | Node type ID                    |
| instance_id   | int      | Instance ID                     |
| meta          | object   | Metadata, see meta definition   |

###### meta

| Field         | Type     | Description         |
|---------------|----------|---------------------|
| bk_biz_id     | int      | Business ID         |
| scope_type    | string   | Resource scope type |
| scope_id      | string   | Resource scope ID   |