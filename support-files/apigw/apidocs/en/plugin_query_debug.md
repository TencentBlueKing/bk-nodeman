### Function Description

Query plugin debug result

### Request Parameters

#### Interface Parameters

| Field    | Type  | <div style="width: 50pt">Required</div> | Description     |
|----------|-------|-----------------------------------------|-----------------|
| task_id  | int   | Yes                                     | Debug task ID   |

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
    "data": {
        "status": "SUCCESS",
        "step": "reset_retry_times",
        "message": "********* 开始初始化进程状态 **********\n开始 初始化进程状态.\n初始化进程状态 成功"
    },
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
| data     | object  | Data returned by the request, see definition below                     |

#### data

| Field     | Type   | Description                                                             |
|-----------|--------|-------------------------------------------------------------------------|
| status    | string | Current status of the debug task (e.g., "SUCCESS", "FAILED", "RUNNING") |
| step      | string | Current or last executed step in the debug process                      |
| message   | string | Log output or detailed message from the debug execution                 |
