### Function Description

Get public key list

### Request Parameters

#### Interface Parameters

| Field              | Type  | <div style="width: 50pt">Required</div> | Description          |
|--------------------|-------|-----------------------------------------|----------------------|
| names              | int   | No                                      | List of key names    |

### Request Example

```json
{
    "names": ["DEFAULT"]
}
```

### Response Example

```json
{
    "result": true,
    "data": [
      {
        "name": "DEFAULT",
        "description": "默认RSA密钥",
        "content": "-----BEGIN PUBLIC KEY-----\n xxx\n-----END PUBLIC KEY-----"
      }
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field     | Type     | Description                                                            |
|-----------|----------|------------------------------------------------------------------------|
| result    | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code      | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string   | Error message returned when the request fails                          |
| data      | array    | Data returned by the request, see definition below                     |

#### data

| Field        | Type    | Description     |
|--------------|---------|-----------------|
| name         | string  | Key name        |
| description  | string  | Key description |
| content      | string  | Key content     |
