 ### Function Description

Get real machine information based on keywords such as `IP`/`IPv6`/`hostname`/`host_id` manually entered by the user

 ### Request Parameters

 #### Interface Parameters

| Field         | Type    | <div style="width: 50pt">Required</div>  | Description                                                             |
|---------------|---------|------------------------------------------|-------------------------------------------------------------------------|
| ip_list       | array   | No                                       | List of IPv4 addresses. Supported formats: cloud_id:ip or ip            |
| ipv6_list     | array   | No                                       | List of IPv6 addresses. Supported formats: cloud_id:ipv6 or ipv6        |
| key_list      | array   | No                                       | List of keywords, such as hostname or host_id                           |
| search_limit  | object  | No                                       | Search scope restrictions                                               |
| all_scope     | bool    | No                                       | Whether to retrieve topology across all resource scopes. Default: false |
| scope_list    | array   | No                                       | Array of resource scopes for which to retrieve topology                 |
| action        | string  | No                                       | Permission type. Default: agent_view. See action definition             |

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
```
{
    "ip_list": ["127.0.0.1"],
    "all_scope": true
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
                "scope_id": "1",
                "bk_biz_id": 1
            },
            "host_id": 124,
            "agent_id": "0200000000525400e621961747626850980c",
            "ip": "127.0.0.1",
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
                "id": 1,
                "name": "蓝鲸"
            },
            "bk_host_id": 124,
            "bk_biz_id": 1,
            "bk_agent_id": "0200000000525400e621961747626850980c",
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

| Field    | Type     | Description                                                            |
|----------|----------|------------------------------------------------------------------------|
| result   | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code     | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string   | Error message returned when the request fails                          |
| data     | array    | Data returned by the request, see definition below                     |

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