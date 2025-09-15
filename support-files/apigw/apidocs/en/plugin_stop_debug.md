### Function Description

Stop debug

### Request Parameters

#### Interface Parameters

| Field     | Type     | <div style="width: 50pt">Required</div> | Description |
|-----------|----------|-----------------------------------------|-------------|
| task_id   | int      | yES                                     | Task ID     |

### Request Example

```json
{
    "task_id": 123456
}
```

### Response Example

```json
{
    "result": true,
    "data": null,
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
| data     | null    | Data returned by the request                                           |


