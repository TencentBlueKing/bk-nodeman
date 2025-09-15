### Function Description

Query synchronization task status

### Request Parameters

#### Interface Parameters

| Field        | Type     | <div style="width: 50pt">Required</div> | Description |
|--------------|----------|-----------------------------------------|-------------|
| task_id      | string   | Yes                                     | Task ID     |

### Request Example

```json
{
    "task_id": "0ffdb6ef-95ab-46dc-a37a-3443db7608a2"
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "task_id": "0ffdb6ef-95ab-46dc-a37a-3443db7608a2",
        "status": "PENDING"
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

| Field             | Type    | Description                                                |
|-------------------|---------|------------------------------------------------------------|
| task_id           | int     | Task ID                                                    |
| status            | int     | Current status of the sync task. See `status` enumeration  |

##### status

| Status Type | Type    | Description                                     |
|-------------|---------|-------------------------------------------------|
| PENDING     | string  | Task is queued and awaiting execution           |
| STARTED     | string  | Task has started processing                     |
| RETRY       | string  | Task is being retried after a transient failure |
| FAILURE     | string  | Task has failed permanently                     |
| SUCCESS     | string  | Task completed successfully                     |

