### Function Description

Batch page query the host information contained in multiple topology nodes and search conditions

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
            "instance_id": 5016860,
            "meta": {
                "scope_type": "biz",
                "scope_id": "5016860",
                "bk_biz_id": 5016860
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
    "data": {
        "total": 2,
        "data": [
            {
                "meta": {
                    "scope_type": "biz",
                    "scope_id": "31",
                    "bk_biz_id": 31
                },
                "host_id": 72,
                "agent_id": "02000000005254005ea7e817503824736673",
                "ip": "127.0.0.1",
                "ipv6": "",
                "host_name": "VM-0-1-tencentos",
                "os_name": "Linux",
                "os_type": "Linux",
                "alive": 1,
                "cloud_area": {
                    "id": 0,
                    "name": "直连区域"
                },
                "biz": {
                    "id": 31,
                    "name": "demo"
                },
                "bk_host_id": 72,
                "bk_biz_id": 31,
                "bk_agent_id": "02000000005254005ea7e817503824736673",
                "bk_agent_alive": 1,
                "bk_cloud_id": 0
            },
            {
                "meta": {
                    "scope_type": "biz",
                    "scope_id": "31",
                    "bk_biz_id": 31
                },
                "host_id": 4,
                "agent_id": "02000000005254006c51121744010286088t",
                "ip": "127.0.0.2",
                "ipv6": "",
                "host_name": "VM-0-2-tencentos",
                "os_name": "Linux",
                "os_type": "Linux",
                "alive": 1,
                "cloud_area": {
                    "id": 0,
                    "name": "直连区域"
                },
                "biz": {
                    "id": 31,
                    "name": "demo"
                },
                "bk_host_id": 4,
                "bk_biz_id": 31,
                "bk_agent_id": "02000000005254006c51121744010286088t",
                "bk_agent_alive": 1,
                "bk_cloud_id": 0
            }
        ]
    },
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Type   | Description                                                            |
|----------|--------|------------------------------------------------------------------------|
| result   | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code     | int    | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string | Error message returned when the request fails                          |
| data     | array  | Data returned by the request, see definition below                     |

#### data

| Field  | Type  | Description                                       |
|--------|-------|---------------------------------------------------|
| total  | int   | Total number of hosts matching the criteria       |
| data   | array | List of host details, see inner data definition   |

#### data

| Field           | Type    | Description                                   |
|-----------------|---------|-----------------------------------------------|
| meta            | object  | Metadata, see meta definition                 |
| host_id         | int     | Host ID                                       |
| agent_id        | string  | Agent ID                                      |
| ip              | string  | Internal IP address                           |
| ipv6            | string  | Internal IPv6 address                         |
| host_name       | string  | Host name                                     |
| os_name         | string  | Operating system name                         |
| os_type         | string  | Operating system type                         |
| alive           | int     | Agent status: 1 = alive, 0 = not alive        |
| cloud_area      | object  | Cloud area info, see cloud_area definition    |
| biz             | object  | Business info, see biz definition             |
| bk_host_id      | int     | Host ID                                       |
| bk_biz_id       | int     | Business ID                                   |
| bk_agent_id     | string  | Agent ID                                      |
| bk_agent_alive  | int     | Agent status (CMDB): 1 = alive, 0 = not alive |
| bk_cloud_id     | int     | Cloud area ID                                 |

#### meta

| Field        | Type    | Description           |
|--------------|---------|-----------------------|
| bk_biz_id    | int     | Business ID           |
| scope_type   | string  | Resource scope type   |
| scope_id     | string  | Resource scope type   |

#### cloud_area

| Field      | Type     | Description      |
|------------|----------|------------------|
| id         | int      | Cloud area ID    |
| name       | string   | Cloud area name  |

#### biz

| Field     | Type     | Description    |
|-----------|----------|----------------|
| id        | int      | Business ID    |
| name      | string   | Business name  |