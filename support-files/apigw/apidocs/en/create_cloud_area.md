### Function Description

Create bk-network area

### Request Parameters

#### Interface Parameters

| Field         | Type        | <div style="width: 50pt">Required</div>  | Description            |
|---------------|-------------|------------------------------------------|------------------------|
| bk_cloud_na   | string      | Yes                                      | Bk-Network area name   |
| isp           | string      | Yes                                      | Cloud service provider |
| ap_id         | int         | Yes                                      | Access point ID        |

### Request Example

```json
{
    "bk_cloud_name": "xxx",
    "isp": "企业私有云",
    "ap_id": 3
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "bk_cloud_id": 81
    },
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field      | Type     | Description                         |
| ------- | ------ | -------------------------- |
| result  | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code    | int    | Error code. 0 indicates success; values greater than 0 indicate errors  |
| message | string | Error message returned when the request fails                |
| data    | object | Data returned by the request, see definition below            |

#### data

| Field           | Type  | Description        |
|-----------------|-------|--------------------|
| bk_cloud_id     | int   | Bk-Network area ID |

