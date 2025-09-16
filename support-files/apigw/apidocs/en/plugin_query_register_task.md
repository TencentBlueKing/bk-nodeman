### Function Description

Query plugin register task

### Request Parameters

#### Interface Parameters

| Field   | Type  | <div style="width: 50pt">Required</div> | Description |
|---------|-------|-----------------------------------------|-------------|
| job_id  | int   | Yes                                     | Job ID      |

### Request Example

```json
{
  "job_id": 123456
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "is_finish": false,
        "status": "RUNNING",
        "message": "~",
    },
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field      | Type     | Description                         |
| ------- |--------|----------------------------|
| result  | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code    | int    | Error code. 0 indicates success; values greater than 0 indicate errors  |
| message | string | Error message returned when the request fails                |
| data    | object |  Data returned by the request, see definition below           |

#### data

| Field       | Type    | Description                                                         |
|-------------|---------|---------------------------------------------------------------------|
| is_finish   | bool    | Whether the registration task has completed                         |
| status      | string  | Execution status of the task (e.g., "RUNNING", "SUCCESS", "FAILED") |
| message     | string  | Log output or detailed message from the task execution              |
