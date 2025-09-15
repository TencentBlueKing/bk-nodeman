### Function Description

Release plugin package

### Request Parameters

#### Interface Parameters

| Field       | Type      | <div style="width: 50pt">Required</div> | Description                                                                                          |
|-------------|-----------|-----------------------------------------|------------------------------------------------------------------------------------------------------|
| id          | int array | No                                      | List of plugin package IDs. Either `id` OR the combination of `name` and `version` must be provided. |
| name        | string    | No                                      | Name of the plugin package                                                                           |
| version     | string    | No                                      | Version number of the plugin package                                                                 |
| cpu_arch    | string    | No                                      | CPU architecture (e.g., "x86", "x86_64")                                                             |
| os          | string    | No                                      | Operating system (e.g., "linux", "windows")                                                          |
| md5_list    | array     | Yes                                     | List of MD5 checksums for the packages to be released                                                |

### Request Example

```json
{
    "name": "tconnd",
    "version": "5.6",
    "md5_list": [
        "de3c381a8904e5349f62d907a8d8d60b"
    ]
}
```

### Response Example

```json
{
    "result": true,
    "data": [1, 2, 4],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Type        | Description                                                            |
|----------|-------------|------------------------------------------------------------------------|
| result   | bool        | Indicates whether the request succeeded. true: success; false: failure |
| code     | int         | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string      | Error message returned when the request fails                          |
| data     | int array   | Data returned by the request, see definition below                     |

#### data

| Field | Type      | Description                           |
|-------|-----------|---------------------------------------|
| data  | int array | List of released plugin package IDs   |