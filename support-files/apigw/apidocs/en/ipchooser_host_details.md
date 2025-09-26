### Function Description

Get machine details based on host critical information

### Request Parameters

#### Interface Parameters

| Field                | Type     | <div style="width: 50pt">Required</div>   | Description                                                             |
|----------------------|----------|-------------------------------------------|-------------------------------------------------------------------------|
| host_list            | array    | Yes                                       | List of hosts, see host_list definition                                 | 
| agent_realtime_state | bool     | No                                        | real-time agent status. Default: false                                  |
| all_scope            | bool     | No                                        | Whether to retrieve topology across all resource scopes. Default: false |
| scope_list           | array    | No                                        | Resource scope list for the topology，see scope_list definition          |
| action               | string   | No                                        | Permission type. Default: agent_view. See action definition             |

##### host_list

| Field    | Type    | <div style="width: 50pt">Required</div> | Description                                                                         |
|----------|---------|-----------------------------------------|-------------------------------------------------------------------------------------|
| host_id  | int     | No                                      | Host ID. Either `host_id` 和 (`ip`,`cloud_id`) must be provided..                    |
| cloud_id | int     | No                                      | Cloud area ID. host_id takes precedence; otherwise, ip + cloud_id is used.          |
| ip       | string  | No                                      | IPv4 address of the host. Either `host_id` 和 (`ip`,`cloud_id`) must be provided.    |
| meta     | object  | Yes                                     | Metadata, see meta definition                                                       |

###### scope_list

| Field          | Type     | <div style="width: 50pt">Required</div> | Description         |
|----------------|----------|-----------------------------------------|---------------------|
| scope_type     | string   | Yes                                     | Resource scope type |
| scope_id       | string   | Yes                                     | Resource scope ID   |
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

###### meta

| Field         | Type     | <div style="width: 50pt">Required</div> | Description         |
|---------------|----------|-----------------------------------------|---------------------|
| bk_biz_id     | int      | No                                      | Business ID         |
| scope_type    | string   | Yes                                     | Resource scope type |
| scope_id      | string   | Yes                                     | Resource scope ID   |

### Request Example

```json
{
    "host_list": [
        {
            "host_id": 1,
            "meta": {
                "scope_type": "biz",
                "scope_id": "10003",
                "bk_biz_id": 10003
            }
        },
        {
            "host_id": 2,
            "meta": {
                "scope_type": "biz",
                "scope_id": "10003",
                "bk_biz_id": 10003
            }
        }
    ],
    "all_scope": false,
    "scope_list": [
        {
            "scope_type": "biz",
            "scope_id": "10003"
        }
    ],
    "agent_realtime_state": true
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "meta": {
                "scope_type": "biz",
                "scope_id": "10003",
                "bk_biz_id": 10003
            },
            "host_id": 1,
            "agent_id": "0200000000525400b43e7d1700234471265z",
            "ip": "10.0.0.1",
            "ipv6": "",
            "host_name": "",
            "os_name": "Linux",
            "os_type": "Linux",
            "alive": 1,
            "cloud_area": {
                "id": 0,
                "name": "直连区域"
            },
            "biz": {
                "id": 10003,
                "name": "蓝鲸"
            },
            "bk_host_id": 1,
            "bk_biz_id": 10003,
            "bk_agent_id": "0200000000525400b43e7d1700234471265z",
            "bk_agent_alive": 1,
            "bk_cloud_id": 0
        }
    ],
    "code": 0,
    "message": ""
}
```

 ### Response Parameters Description

 #### response

| Field    | Type    | Description                                                            |
|----------|---------|------------------------------------------------------------------------|
| result   | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code     | int     | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string  | Error message returned when the request fails                          |
| data     | array   | Data returned by the request, see definition below                     |

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