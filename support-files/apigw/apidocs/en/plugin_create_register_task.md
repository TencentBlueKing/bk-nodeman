### Function Description

Create registration task

### Request Parameters

#### Interface Parameters

| Field                         | Type     | <div style="width: 50pt">Required</div> | Description                                                                        |
|-------------------------------|----------|-----------------------------------------|------------------------------------------------------------------------------------|
| file_name                     | string   | Yes                                     | Name of the plugin package file to register (e.g., `bkunifylogbeat-7.1.28.tgz`)    |
| is_release                    | bool     | Yes                                     | Whether to immediately release the plugin after registration                       |
| is_template_load              | bool     | No                                      | Whether to load configuration templates from the package                           |
| is_template_overwrite         | bool     | No                                      | Whether to overwrite existing configuration templates if they already exist        |
| select_pkg_relative_paths     | array    | No                                      | List of relative paths within the package to register; defaults to all if omitted  |

### Request Example

```json
{
    "file_name": "bkunifylogbeat-7.1.28.tgz",
    "is_release": true
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

| Field      | Type     | Description                         |
| ------- | ------ | -------------------------- |
| result  | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code    | int    | Error code. 0 indicates success; values greater than 0 indicate errors  |
| message | string | Error message returned when the request fails                |
| data    | object | Data returned by the request, see definition below            |

#### data

| Field     | Type   | Description                           |
|-----------|--------|---------------------------------------|
| job_id    | int    | Unique ID of the registration task    |
