### Function Description

Query host policy

### Request Parameters

#### Interface Parameters

| Field         | Type | <div style="width: 50pt">Required</div> | Description |
|---------------|------|-----------------------------------------|-------------|
| bk_host_id    | int  | Yes                                     | Host ID     |

### Request Example

```json
{
    "bk_host_id": 123456
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "name": "test",
            "category": "policy",
            "plugin_name": "bkunifylogbeat",
            "auto_trigger": true,
            "version": "7.7.2-rc.29",
            "install_path": "/usr/local/gse2_tenant/plugins/bin",
            "is_latest": true,
            "status": "SUCCESS",
            "update_time": "2025-08-27 06:52:29+0800",
            "instance_id": "host|instance|host|123456",
            "job_id": 11,
            "job_type": "MAIN_INSTALL_PLUGIN",
            "updated_by": "admin",
            "deploy_type": null,
            "config_template": "bkunifylogbeat.conf",
            "plugin_version": "7.7.2-rc.29"
        }
    ],
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
| data      | array    | Data returned by the request, see definition below                     |

#### data

| Field               | Type     | Description                                              |
|---------------------|----------|----------------------------------------------------------|
| name                | string   | Strategy name                                            |
| category            | string   | Execution status category                                |
| plugin_name         | string   | Plugin name                                              |
| auto_trigger        | bool     | Whether the execution was auto-triggered                 |
| version             | string   | Version of the deployed package                          |
| install_path        | string   | Installation directory path on the target host           |
| is_latest           | bool     | Whether the deployed version is the latest available     |
| status              | string   | Current strategy status (e.g., RUNNING, SUCCESS, FAILED) |
| update_time         | string   | Last update time                                         |
| instance_id         | string   | Instance ID                                              |
| job_id              | int      | Job ID for tracking execution tasks                      |
| job_type            | string   | Type of job, e.g., INSTALL, UPDATE, RESTART              |
| updated_by          | string   | User who last modified the strategy                      |
| deploy_type         | string   | Deployment method                                        |
| config_template     | string   | Configuration template used for deployment               |
| plugin_version      | string   | plugin version                                           |
