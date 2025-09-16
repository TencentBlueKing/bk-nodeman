### Function Description

Plugin detail

### Request Parameters

#### Interface Parameters

| Field  | Type  | <div style="width: 50pt">Required</div> | Description |
|--------|-------|-----------------------------------------|-------------|
| id     | int   | Yes                                     | Plugin Id   |

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
    "data": {
        "id": 1,
        "description": "系统基础信息采集",
        "name": "basereport",
        "category": "官方插件",
        "source_app_code": "bk_nodeman",
        "scenario": "CMDB上的实时数据，蓝鲸监控里的主机监控，包含CPU，内存，磁盘等",
        "deploy_type": "整包部署",
        "plugin_packages": [
            {
                "id": 1,
                "pkg_name": "basereport-10.1.12.tgz",
                "module": "gse_plugin",
                "project": "basereport",
                "version": "10.1.12",
                "config_templates": [
                    {"id": 1, "name": "basereport.conf", "version": "10.1", "is_main": true}
                ],
                "os": "linux",
                "cpu_arch": "x86_64",
                "support_os_cpu": "linux_x86_64",
                "pkg_mtime": "2019-11-25 21:58:30",
                "creator": "test_person",
                "is_ready": true
            },
            {
                "id": 2,
                "pkg_name": "bkmonitorbeat-1.7.1.tgz",
                "module": "gse_plugin",
                "project": "bkmonitorbeat",
                "version": "1.7.1",
                "config_templates": [
                    {"id": 1, "name": "child1.conf", "version": "1.0", "is_main": false},
                    {"id": 2, "name": "child2.conf", "version": "1.1", "is_main": false},
                    {"id": 3, "name": "bkmonitorbeat.conf", "version": "0.1", "is_main": true}
                ],
                "os": "windows",
                "cpu_arch": "x86",
                "support_os_cpu": "windows_x86",
                "pkg_mtime": "2019-11-25 21:58:30",
                "creator": "test_person",
                "is_ready": true
            }
        ]
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

| Field             | Type     | Description                                                |
|-------------------|----------|------------------------------------------------------------|
| id                | int      | Plugin ID                                                  |
| description       | string   | Plugin description                                         |
| name              | string   | Plugin name                                                |
| category          | string   | Plugin category (e.g., "Official Plugin")                  |
| source_app_code   | string   | Source application code (e.g., `bk_nodeman`)               |
| scenario          | string   | Usage scenario description                                 |
| deploy_type       | string   | Deployment method (e.g., "Full-package Deployment")        |
| plugin_packages   | array    | List of plugin packages, see `plugin_packages` definition  |

##### plugin_packages

| Field             | Type     | Description                                                             |
|-------------------|----------|-------------------------------------------------------------------------|
| id                | int      | Package ID                                                              |
| pkg_name          | string   | Package filename (e.g., `basereport-10.1.12.tgz`)                       |
| module            | string   | Associated service/module                                               |
| project           | string   | Project name                                                            |
| version           | string   | Package version                                                         |
| config_templates  | array    | List of configuration templates, see `config_templates` definition      |
| os                | string   | Target operating system (e.g., linux, windows)                          |
| cpu_arch          | string   | CPU architecture (e.g., x86_64)                                         |
| support_os_cpu    | string   | Supported OS-CPU combination (e.g., linux_x86_64)                       |
| pkg_mtime         | string   | Last modification time of the package (in "YYYY-MM-DD HH:mm:ss" format) |
| creator           | string   | User who created/uploaded the package                                   |
| is_ready          | bool     | Whether the package is ready for deployment                             |

##### config_templates

| Field     | Type    | Description                                   |
|-----------|---------|-----------------------------------------------|
| id        | int     | Configuration template ID                     |
| name      | string  | Configuration filename                        |
| version   | string  | Template version                              |
| is_main   | bool    | Whether this is the main configuration file   |
 