### Function Description

Create plugin packaging export task

### Request Parameters

#### Interface Parameters

| Field          | Type     | <div style="width: 50pt">Required</div> | Description                                 |
|----------------|----------|-----------------------------------------|---------------------------------------------|
| category       | string   | Yes                                     | Plugin category type (e.g., `gse_plugin`)   |
| query_params   | object   | Yes                                     | Query criteria, see query_params definition |
| creator        | string   | Yes                                     | Task creator                                |
| bk_app_code    | string   | Yes                                     | Source system application code              |

#### query_params

| Field        | Type    | <div style="width: 50pt">Required</div> | Description                                    |
|--------------|---------|-----------------------------------------|------------------------------------------------|
| project      | string  | Yes                                     | Plugin name                                    |
| version      | string  | Yes                                     | Plugin version to export                       |
| os           | string  | No                                      | Target operating system (e.g., linux, windows) |
| cpu_arch     | string  | No                                      | CPU architecture (e.g., x86_64, arm64)         |

### Request Example

```json
{
    "category": "gse_plugin",
    "query_params": {
        "project": "test_plugin",
        "version": "1.0.0"
    },
    "creator": "test_person",
    "bk_app_code": "bk_test_app"
}
```

### Response Example

```json
{
    "result": true,
    "data": {
       "job_id": 1
    },
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field     | Type    | Description                                                            |
|-----------|---------|------------------------------------------------------------------------|
| result    | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code      | int     | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string  | Error message returned when the request fails                          |
| data      | object  | Data returned by the request, see definition below                     |

#### data

| Field     | Type   | Description                   |
|-----------|--------|-------------------------------|
| job_id    | int    | Unique ID of the export job   |

