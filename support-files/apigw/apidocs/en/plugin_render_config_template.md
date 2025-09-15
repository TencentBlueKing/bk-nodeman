### Function Description

Render plugin config template

### Request Parameters

#### Interface Parameters

| Field          | Type       | <div style="width: 50pt">Required</div>  | Description                                                                  |
|----------------|------------|------------------------------------------|------------------------------------------------------------------------------|
| plugin_name    | string     | No                                       | Name of the plugin                                                           |
| plugin_version | string     | No                                       | Version of the plugin                                                        |
| name           | string     | No                                       | Name of the configuration template to render                                 |
| version        | string     | No                                       | Version of the configuration template to render.                             |
| id             | int array  | No                                       | Specific configuration template version IDs to render.                       |
| data           | object     | Yes                                      | Key-value pairs of variables used to render the template (e.g., host, port). |

### Request Example

```json
{
    "plugin_name": "poe_prometheus_exporter",
    "plugin_version": "*",
    "name": "bkmonitorbeat_debug.yaml",
    "version": "1",
    "data": {
        "host": "127.0.0.1",
        "port": "9090",
        "period": "10",
        "metric_url": "127.0.0.1:9090/metrics"
    }
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "id": 9,
        "md5": "dab43f1b255a78e1d288783c62fcf1b",
        "creator": "admin",
        "source_app_code": "bk_nodeman"
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

| Field           | Type   | Description                                           |
|-----------------|--------|-------------------------------------------------------|
| id              | int    | ID of the rendered plugin configuration file instance |
| md5             | string | MD5 checksum of the generated configuration file      |
| creator         | string | User who triggered the rendering process              |
| source_app_code | string | Source application code (e.g., `bk_nodeman`)          |
