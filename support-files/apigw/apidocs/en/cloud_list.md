### Function Description

Query bk-network area list

### Request Parameters

#### Interface Parameters

| Field               | Type  | <div style="width: 50pt">Required</div> | Description                                                       |
|---------------------|-------|-----------------------------------------|-------------------------------------------------------------------|
| with_default_area   | bool  | NO                                      | Whether to return the direct-connection area. Default is false.   |

### Request Example

```json
{
    "with_default_area": false
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "bk_cloud_id": 1,
            "bk_cloud_name": "测试",
            "isp": "Tencent",
            "ap_id": 1,
            "is_visible": true,
            "node_count": 10,
            "proxy_count": 2,
            "ap_name": "默认接入点",
            "isp_name": "腾讯云",
            "isp_icon": "PHN2ZyB2aWV3Qm",
            "exception": "",
            "proxies": null,
            "permissions": {
                "view": true,
                "edit": true,
                "delete": true
            }
        }
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field      | Type      | Description                         |
| ------- |---------| -------------------------- |
| result  | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code    | int     | Error code. 0 indicates success; values greater than 0 indicate errors  |
| message | string  | Error message returned when the request fails                |
| data    | array   | Data returned by the request, see definition below            |

#### data

| Field          | Type     | Description                                        |
|----------------|--------|----------------------------------------------------|
| bk_cloud_id    | int    | Bk-Network area ID                                 |
| bk_cloud_name  | string | Bk-Network area Name                               |
| isp            | string | Cloud service provider                             |
| ap_id          | int    | Access point ID; -1 means auto-selection           |
| is_visible     | string | Whether the area is visible                        |
| node_count     | int    | Number of hosts                                    |
| proxy_count    | int    | Number of proxy hosts                              |
| ap_name        | string | Access point name                                  |
| isp_name       | string | Name of the cloud service provider                 |
| isp_icon       | string | Icon of the cloud service provider                 |
| exception      | string | Exception information within the Bk-Network area   |
| proxies        | array  | Proxy hosts with exceptions in the Bk-Network area |
| permissions    | object | Operation permissions, see permissions definition  |

##### permissions

| Permission Type | Type   | Description       |
|-----------------|--------|-------------------|
| view            | bool   | View permission   |
| edit            | bool   | Edit permission   |
| delete          | bool   | Delete permission |
