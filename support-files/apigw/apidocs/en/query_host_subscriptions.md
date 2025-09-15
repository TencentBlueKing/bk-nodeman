### Function Description

Query host subscriptions

### Request Parameters

#### Interface Parameters

| Field               | Type    | <div style="width: 50pt">Required</div> | Description                                                                                          |
|---------------------|---------|-----------------------------------------|------------------------------------------------------------------------------------------------------|
| bk_host_id          | string  | No                                      | Host ID in CMDB. Either `bk_host_id` OR the combination of `ip` and `bk_cloud_id` must be provided.  |
| ip                  | string  | No                                      | IP address of the target host. Must be used with `bk_cloud_id`.                                      |
| bk_host_innerip     | string  | No                                      | Inner IP address. Either `bk_host_id` OR the combination of `ip` and `bk_cloud_id` must be provided. |
| bk_cloud_id         | string  | No                                      | Cloud area ID associated with the IP.                                                                |
| bk_supplier_id      | string  | No                                      | Supplier ID, default is `"0"`.                                                                       |
| source_type         | string  | Yes                                     | Source type of the subscription. Valid values: `default`, `subscription`, `debug`.                   |

### Request Example

```json
{
  "bk_host_id": 123456,
  "source_type": "subscription"
}
```

### Response Example

```json
{
    "result": true,
    "data": [
      {
        "id": 817,
        "source_type": "subscription",
        "source_id": "93",
        "name": "bkunifylogbeat",
        "version": "1.10.58",
        "status": "RUNNING"
      }
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Type      | Description                                                            |
|----------|-----------|------------------------------------------------------------------------|
| result   | bool      | Indicates whether the request succeeded. true: success; false: failure |
| code     | int       | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string    | Error message returned when the request fails                          |
| data     | array     | Data returned by the request, see definition below                     |

#### data

| Field       | Type   | Description                                     |
|-------------|--------|-------------------------------------------------|
| id          | int    | Process ID                                      |
| source_type | string | Source type of the subscription                 |
| source_id   | string | ID of the originating source                    |
| name        | string | Plugin name                                     |
| version     | string | Plugin version                                  |
| status      | string | Current process status. See `status` definition |

##### status

| Status Type      | Type     | Description         |
|------------------|----------|---------------------|
| RUNNING          | string   | Running normally    |
| UNKNOWN          | string   | Unknown state       |
| TERMINATED       | string   | Terminated          |
| NOT_INSTALLED    | string   | Not installed       |
| UNREGISTER       | string   | Unregistered        |
| REMOVED          | string   | Removed             |
| MANUAL_STOP      | string   | Manually stopped    |
| AGENT_NO_ALIVE   | string   | Agent is not alive  |


