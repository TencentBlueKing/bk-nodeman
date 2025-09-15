### Function Description

Release plugin config template

### Request Parameters

#### Interface Parameters

| Field           | Type      | <div style="width: 50pt">Required</div> | Description                                                    |
|-----------------|-----------|-----------------------------------------|----------------------------------------------------------------|
| plugin_name     | string    | No                                      | Name of the plugin.                                            |
| plugin_version  | string    | No                                      | Version of the plugin.                                         |
| name            | string    | No                                      | Name of the configuration template to publish                  |
| version         | string    | No                                      | Version of the configuration template to publish               |
| id              | int array | No                                      | List of specific configuration template version IDs to publish |

### Request Example

```json
{
    "plugin_name": "ds_metric_report",
    "plugin_version": "10_31",
    "name": "env.yaml.tpl",
    "version": "10"
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "id": 9,
            "plugin_name": "ds_metric_report",
            "plugin_version": "10_31",
            "name": "env.yaml.tpl",
            "version": "10",
            "format": "yaml",
            "file_path": "etc",
            "is_release_version": true,
            "creator": "admin",
            "content": "R1NFX0FHRU5UX0hPTUU6IHt7IGNvbnRyb2xfaW5mby5nc2VfYWdlbnRfaG9tZSB9fQpCS19QTFVHSU5fTE9HX1BBVEg",
            "source_app_code": "bk_nodeman"
        },
        {
            "id": 8,
            "plugin_name": "ds_metric_report",
            "plugin_version": "10_31",
            "name": "env.yaml.tpl",
            "version": "10",
            "format": "yaml",
            "file_path": "etc",
            "is_release_version": true,
            "creator": "admin",
            "content": "R1NFX0FHRU5UX0hPTUU6IHt7IGNvbnRyb2xfaW5mby5nc2VfYWdlaG9tZSB9fQpCS19QTFVHSU5fTE9HX1BBVEg",
            "source_app_code": "bk_nodeman"
        }
    ],
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
| data      | array   | Data returned by the request, see definition below                     |

#### data

| Field               | Type   | Description                                                         |
|---------------------|--------|---------------------------------------------------------------------|
| id                  | int    | Configuration template version ID                                   |
| plugin_name         | string | Name of the associated plugin                                       |
| plugin_version      | string | Version of the associated plugin                                    |
| name                | string | Name of the configuration template (e.g., `env.yaml.tpl`)           |
| version             | string | Version of the configuration template                               |
| format              | string | File format (e.g., `yaml`, `conf`, `json`)                          |
| file_path           | string | Relative path of the file within the plugin directory (e.g., `etc`) |
| is_release_version  | bool   | Whether this template version has been officially released          |
| creator             | string | User who created the template                                       |
| content             | string | Base64-encoded content of the configuration template                |
| source_app_code     | string | Source application code (e.g., `bk_nodeman`)                        |
