### Function Description

Collect task result detail

### Request Parameters

#### Interface Parameters

| Field           | Type  | <div style="width: 50pt">Required</div> | Description |
|-----------------|-------|-----------------------------------------|-------------|
| job_id          | int   | Yes                                     | Job ID      |
| instance_id     | int   | Yes                                     | Instance ID        |

### Request Example

```json
{
    "job_id": "6679052",
    "instance_id": "host|instance|host|127.0.0.1-633-0"
}
```

### Response Example

```json
{
    "result": true,
    "data": {
       "celery_id": 123
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

| Field        | Type  | Description    |
|--------------|-------|----------------|
| celery_id    | int   | Celery task ID |
