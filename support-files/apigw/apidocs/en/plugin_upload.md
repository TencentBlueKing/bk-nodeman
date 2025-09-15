### Function Description

Upload file

### Request Parameters

#### Interface Parameters

| Field         | Type    | <div style="width: 50pt">Required</div> | Description                                                                                                      |
|---------------|---------|-----------------------------------------|------------------------------------------------------------------------------------------------------------------|
| md5           | string  | Yes                                     | MD5 checksum of the file, calculated by the client before upload                                                 |
| file_name     | string  | Yes                                     | Original filename of the uploaded file                                                                           |
| module        | string  | No                                      | Module to which the plugin package belongs                                                                       |
| download_url  | string  | No                                      | Publicly accessible URL from which the server can download the file directly. Required if not using file upload. |
| file_path     | string  | No                                      | Local file path on the server (used internally). Either `download_url` or `file_path` must be provided.          |
```json
{
  "md5": "e86c07536ada151dd85ca533874e8883",
  "filename": "bkmonitorbeat-2.0.48.tgz",
  "download_url": "http://xxxx/bkmonitorbeat-2.0.48.tgz"
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "id": 1,
        "name": "bkmonitorbeat-2.0.48.tgz",
        "pkg_size": "2333"
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

| Field                | Type   | Description                                       |
|----------------------|--------|---------------------------------------------------|
| id                   | int    | Unique ID assigned to the uploaded plugin package |
| name                 | string | Name of the uploaded package file                 |
| pkg_size             | string | Size of the package in bytes (as a string)        |

