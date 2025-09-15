### Function Description

Query the proxy list with operation permissions of the bk-network area

### Request Parameters

#### Interface Parameters

| Field         | Type | <div style="width: 50pt">Required</div> | Description   |
|---------------|------|-----------------------------------------|---------------|
| bk_cloud_id   | int  | Yes                                     | Cloud area ID |

### Request Example

```json
{
    "bk_cloud_id": 1
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "bk_cloud_id": 1,
            "bk_host_id": 1,
            "inner_ip": "127.0.0.1",
            "inner_ipv6": "",
            "outer_ip": "127.0.0.2",
            "outer_ipv6": "",
            "login_ip": "127.0.0.3",
            "data_ip": "",
            "bk_biz_id": 331,
            "is_manual": true,
            "extra_data": {
                "data_path": "/var/lib/gse",
                "bt_speed_limit": null,
                "peer_exchange_switch_for_agent": 0,
                "enable_compression": false
            },
            "bk_biz_name": "test",
            "ap_id": 1,
            "ap_name": "默认接入点",
            "status": "TERMINATED",
            "status_display": "异常",
            "version": "",
            "account": "root",
            "auth_type": "MANUAL",
            "port": 22,
            "re_certification": true,
            "job_result": {
                
            },
            "pagent_count": 0,
            "permissions": {
                "operate": true
            }
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

| Field               | Type      | Description                                                                          |
|---------------------|-----------|--------------------------------------------------------------------------------------|
| bk_cloud_id         | int       | Cloud area ID                                                                        |
| bk_host_id          | int       | Host ID                                                                              |
| inner_ip            | string    | Internal IPv4 address                                                                |
| inner_ipv6          | string    | Internal IPv6 address                                                                |
| outer_ip            | string    | External IPv4 address                                                                |
| outer_ipv6          | string    | External IPv6 address                                                                |
| login_ip            | string    | Login IP                                                                             |
| data_ip             | string    | Data IP                                                                              |
| bk_biz_id           | string    | Business ID                                                                          |
| is_manual           | string    | Whether in manual installation mode                                                  |
| extra_data          | string    | Additional information, see extra_data definition                                    |
| bk_biz_name         | string    | Business name                                                                        |
| ap_id               | int       | Access point ID                                                                      |
| ap_name             | string    | Access point name                                                                    |
| status              | string    | Running status, see status definition                                                |
| status_display      | string    | Display name of running status, see status definition                                |
| version             | string    | Agent version                                                                        |
| account             | string    | Username                                                                             |
| auth_type           | string    | Authentication type: PASSWORD, KEY, TJJ_PASSWORD. Default is password authentication |
| port                | string    | Login port                                                                           |
| re_certification    | bool      | Whether authentication has expired                                                   |
| job_result          | object    | Task execution result, see job_result definition                                     |
| pagent_count        | int       | Number of PAGENTs using the proxy                                                    |
| permissions         | object    | Whether operation permissions are granted                                            |

##### extra_data

| Field                          | Type    | Description                               |
|--------------------------------|---------|-------------------------------------------|
| bt_speed_limit                 | int     | BT transfer speed limit value (unit: M/s) |
| peer_exchange_switch_for_agent | int     | BT transfer switch: 1 (on), 0 (off)       |
| data_path                      | string  | Data file path                            |
| enable_compression             | bool    | Data compression toggle                   |

##### status

| 状态Type          | Type     | Description       |
|-----------------|----------|-------------------|
| RUNNING         | string   | Running           |
| UNKNOWN         | string   | Unknown           |
| TERMINATED      | string   | Terminated        |
| NOT_INSTALLED   | string   | Not Installed     |
| UNREGISTER      | string   | Unregistered      |
| REMOVED         | string   | Removed           |
| MANUAL_STOP     | string   | Manually Stopped  |

##### job_result

| Field            | Type      | Description                                 |
|------------------|-----------|---------------------------------------------|
| instance_id      | string    | Instance ID                                 |
| job_id           | int       | Job ID                                      |
| status           | string    | Execution status, see job_status definition |
| current_step     | string    | Current step name                           |

