### Function Description

Query the proxy set of the bk-network area under the business

### Request Parameters

#### Interface Parameters

| Field      | Type  | <div style="width: 50pt">Required</div> | Description |
|------------|-------|-----------------------------------------|-------------|
| bk_biz_id  | int   | Yes                                     | Business ID |

### Request Example

```json
{
    "bk_biz_id": 1
}
```

### Response Example

```json
{
  "result": true,
  "data": [
    {
      "bk_cloud_id": 0,
      "bk_addressing": "0",
      "inner_ip": "127.0.0.1",
      "inner_ipv6": "",
      "outer_ip": "",
      "outer_ipv6": "",
      "login_ip": "127.0.0.2",
      "data_ip": "",
      "bk_biz_id": 1
    },
    {
      "bk_cloud_id": 0,
      "bk_addressing": "0",
      "inner_ip": "127.0.0.3",
      "inner_ipv6": "",
      "outer_ip": "",
      "outer_ipv6": "",
      "login_ip": "127.0.0.4",
      "data_ip": "",
      "bk_biz_id": 1
    }
  ],
  "code": 0,
  "message": ""
}
```

### Response Parameters Description

#### response

| Field     | Type      | Description                                                            |
|-----------|-----------|------------------------------------------------------------------------|
| result    | bool      | Indicates whether the request succeeded. true: success; false: failure |
| code      | int       | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string    | Error message returned when the request fails                          |
| data      | array     | Data returned by the request, see definition below                     |

#### data

| Field           | Type     | Description                                   |
|-----------------|----------|-----------------------------------------------|
| bk_cloud_id     | int      | Cloud area ID                                 |
| bk_addressing   | int      | Addressing method: 1: 0, static 2: 1, dynamic |
| inner_ip        | string   | Host internal IPv4 address                    |
| inner_ipv6      | string   | Host internal IPv6 address                    |
| outer_ip        | string   | Host external IPv4 address                    |
| outer_ipv6      | string   | Host external IPv6 address                    |
| login_ip        | string   | Login IP                                      |
| data_ip         | string   | Data IP                                       |
| bk_biz_id       | int      | Business ID                                   |

