### Function Description

Plugin package status operation

### Request Parameters

#### Interface Parameters

| Field         | Type     | <div style="width: 50pt">Required</div> | Description                                                                                           |
|---------------|----------|-----------------------------------------|-------------------------------------------------------------------------------------------------------|
| operation     | string   | Yes                                     | Status operation: `release` - `online`, `offline` - `offline`, `ready` - `enable`, `stop` - `disable` |
| id            | array    | No                                      | List of plugin package IDs. Either `id` or (`name`, `version`) must be provided.                      |
| name          | string   | No                                      | Plugin name. Either `id` or (`name`, `version`) must be provided.                                     |
| version       | string   | No                                      | Plugin version.                                                                                       |
| cpu_arch      | string   | No                                      | CPU architecture.                                                                                     |
| os            | string   | No                                      | Operating system.                                                                                     |
| md5_list      | array    | Yes                                     | List of MD5 checksums.                                                                                |

### Request Example

```json
{
    "operation": "stop",
    "name": "bkmonitorbeat",
    "version": "3.63.3482",
    "os": "linux",
    "cpu_arch": "x86",
    "md5_list": ["8329838ebbbfba3a72ef5e6011d740af"]
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        55
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Type     | Description                                                                                                      |
|----------|----------|------------------------------------------------------------------------------------------------------------------|
| result   | bool     | Indicates whether the request succeeded. true: success; false: failure                                           |
| code     | int      | Error code. 0 indicates success; values greater than 0 indicate errors                                           |
| message  | string   | Error message returned when the request fails                                                                    |
| data     | array    | Data returned by the request, containing a list of plugin package IDs that successfully completed the operation  |

