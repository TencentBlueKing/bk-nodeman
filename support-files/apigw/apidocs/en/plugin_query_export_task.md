### Function Description

Get an export task result

### Request Parameters

#### Interface Parameters

| Field   | Type | <div style="width: 50pt">Required</div> | Description |
|---------|------|-----------------------------------------|-------------|
| job_id  | int  | Yes                                     | Job ID      |

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
        "is_finish": true,
        "is_failed": false,
        "download_url": "http://127.0.0.1//backend/export/download/",
        "error_message": "haha"
    },
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
| data      | object   | Data returned by the request, see definition below                     |

#### data

| Field         | Type    | Description                             |
|---------------|---------|-----------------------------------------|
| is_finish     | bool    | Whether the export task has completed   |
| is_failed     | bool    | Whether the export task failed          |
| download_url  | string  | URL to download the exported file       |
| error_message | string  | Error log or message if the task failed |
