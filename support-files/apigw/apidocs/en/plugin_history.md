### Function Description

Query plugin history

### Request Parameters

#### Interface Parameters

| Field | Type  | <div style="width: 50pt">Required</div> | Description |
|-------|-------|-----------------------------------------|-------------|
| id    | int   | Yes                                     | Plugin ID   |

### Request Example

```json
{
  "id": 1
}
```

### Response Example

```json
{
    "result": true,
    "data": [
      {
        "id": 1,
        "pkg_name": "basereport-1.0.tgz",
        "project": "basereport",
        "version": "1.0",
        "pkg_size": 4391830,
        "md5": "35bf230be9f3c1b878ef7665be34e14e",
        "config_templates": [
            {"name": "bkunifylogbeat.conf", "version": "1.0", "is_main": false},
            {"name": "bkunifylogbeat1.conf", "version": "1.1", "is_main": false},
            {"name": "bkunifylogbeat-main.config", "version": "0.1", "is_main": true}
        ],
        "pkg_mtime": "2019-11-25 21:58:30",
        "creator": "test_person",
        "is_ready": true,
        "is_release_version": true
      },
      {
        "id": 2,
        "pkg_name": "basereport-1.1.tgz",
        "module": "gse_plugin",
        "project": "basereport",
        "version": "1.1",
        "os": "linux",
        "cpu_arch": "x86",
        "md5": "35bf230be9f3c1b878ef7665be34e14e",
        "pkg_size": 4391830,
        "config_templates": [
            {"id": 1, "name": "child1.conf", "version": "1.0", "is_main": false},
            {"id": 2, "name": "child2.conf", "version": "2.0", "is_main": false},
            {"id": 3, "name": "bkunifylogbeat-main.config", "version": "0.2", "is_main": true}
        ],
        "pkg_mtime": "2019-11-25 22:01:30",
        "creator": "test_person",
        "is_ready": true,
        "is_newest": true,
        "is_release_version": true
      }
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Type      | Description                                                            |
|----------|-----------|------------------------------------------------------------------------|
| result   | bool      | Indicates whether the request succeeded. true: success; false: failure |
| code     | int       | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string    | Error message returned when the request fails                          |
| data     | array     | Data returned by the request, see definition below                     |

#### data

| Field               | Type     | Description                                                             |
|---------------------|----------|-------------------------------------------------------------------------|
| id                  | int      | Plugin package ID                                                       |
| pkg_name            | string   | Package filename (e.g., `basereport-1.0.tgz`)                           |
| module              | string   | Associated service/module (e.g., `gse_plugin`)                          |
| project             | string   | Project name                                                            |
| version             | string   | Package version                                                         |
| os                  | string   | Target operating system (e.g., linux, windows)                          |
| cpu_arch            | string   | CPU architecture (e.g., x86, x86_64)                                    |
| md5                 | string   | MD5 checksum of the package                                             |
| pkg_size            | int      | Package size in bytes                                                   |
| config_templates    | array    | List of configuration templates, see `config_templates` definition      |
| pkg_mtime           | string   | Last modification time of the package (in "YYYY-MM-DD HH:mm:ss" format) |
| creator             | string   | User who uploaded the package                                           |
| is_ready            | bool     | Whether the package is available for use                                |
| is_newest           | bool     | Whether this is the latest version                                      |
| is_release_version  | bool     | Whether this version has been officially released                       |

##### config_templates

| Field     | Type    | Description                                   |
|-----------|---------|-----------------------------------------------|
| name      | string  | Configuration template filename               |
| version   | string  | Template version                              |
| is_main   | bool    | Whether this is the main configuration file   |
