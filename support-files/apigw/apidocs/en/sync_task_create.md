### Function Description

Create synchronization task

### Request Parameters

#### Interface Parameters

| Field        | Type      | <div style="width: 50pt">Required</div> | Description                      |
|--------------|-----------|-----------------------------------------|----------------------------------|
| task_name    | string    | Yes                                     | Name of the synchronization task |
| task_params  | object    | No                                      | Task call parameters             |

### Request Example

```json
{
    "task_name": "sync_cmdb_host"
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "task_id": "0ffdb6ef-95ab-46dc-a37a-3443db7608a2"
    },
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
| data     | object   | Data returned by the request, see definition below                     |

#### data

| Field            | Type    | Description |
|------------------|---------|-------------|
| task_id          | int     | Task id     |

