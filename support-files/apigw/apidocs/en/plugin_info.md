### Function Description

Query plugin information

### Request Parameters

#### Interface Parameters

| Field      | Type       | <div style="width: 50pt">Required</div> | Description                                    |
|------------|------------|-----------------------------------------|------------------------------------------------|
| name       | string     | Yes                                     | Plugin name                                    |
| version    | string     | No                                      | Plugin version                                 |
| cpu_arch   | string     | No                                      | CPU architecture (e.g., x86, x86_64)           |
| os         | string     | No                                      | Target operating system (e.g., linux, windows) |

### Request Example

```json
{
    "name": "bkmonitorbeat",
    "version": "2.9.1.209",
    "os": "linex"
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "id": 9,
            "module": "gse_plugin",
            "project": "bkmonitorbeat",
            "version": "2.9.1.209",
            "os": "windows",
            "cpu_arch": "x86",
            "pkg_name": "bkmonitorbeat-2.9.1.209.tgz",
            "pkg_size": 13759268,
            "pkg_mtime": "2023-05-24 04:31:33.868368+00:00",
            "md5": "350d6f165b291f8e51a98a193e9d05b6",
            "creator": "admin",
            "location": "http://127.0.0.1/download/windows/x86",
            "is_ready": false,
            "is_release_version": true,
            "name": "bkmonitorbeat",
            "source_app_code": "bk_nodeman"
        },
        {
            "id": 12,
            "module": "gse_plugin",
            "project": "bkmonitorbeat",
            "version": "2.9.1.209",
            "os": "windows",
            "cpu_arch": "x86_64",
            "pkg_name": "bkmonitorbeat-2.9.1.209.tgz",
            "pkg_size": 13890930,
            "pkg_mtime": "2023-05-24 04:31:49.547280+00:00",
            "md5": "7f8473812eee909bd2f8879916a10261",
            "creator": "admin",
            "location": "http://127.0.0.1/download/windows/x86_64",
            "is_ready": false,
            "is_release_version": true,
            "name": "bkmonitorbeat",
            "source_app_code": "bk_nodeman"
        }
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field      | Type     | Description                         |
| ------- |--------| -------------------------- |
| result  | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code    | int    | Error code. 0 indicates success; values greater than 0 indicate errors  |
| message | string | Error message returned when the request fails                |
| data    | array  | Data returned by the request, see definition below            |

#### data

| Field               | Type     | Description                                            |
|---------------------|----------|--------------------------------------------------------|
| id                  | int      | Plugin package ID                                      |
| module              | string   | Module/service name (e.g., `gse_plugin`)               |
| project             | string   | Project name                                           |
| version             | string   | Plugin version                                         |
| os                  | string   | Target operating system (e.g., linux, windows)         |
| cpu_arch            | string   | CPU architecture (e.g., x86, x86_64)                   |
| pkg_name            | string   | Package filename (e.g., `bkmonitorbeat-2.9.1.209.tgz`) |
| pkg_size            | int      | Package size in bytes                                  |
| pkg_mtime           | string   | Last modification time of the package                  |
| md5                 | string   | MD5 checksum of the package                            |
| creator             | string   | User who uploaded the package                          |
| location            | string   | Download URL for the plugin package                    |
| is_ready            | bool     | Whether the package is available for deployment        |
| is_release_version  | bool     | Whether this version has been officially released      |
| name                | string   | Plugin name                                            |
| source_app_code     | string   | Source application code (e.g., `bk_nodeman`)           |
