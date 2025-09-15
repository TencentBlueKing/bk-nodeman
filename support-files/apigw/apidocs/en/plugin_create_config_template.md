### Function Description

Create config template

### Request Parameters

#### Interface Parameters

| Field                 | Type      | <div style="width: 50pt">Required</div> | Description                                                 |
|-----------------------|-----------|-----------------------------------------|-------------------------------------------------------------|
| plugin_name           | string    | Yes                                     | Plugin name                                                 |
| plugin_version        | string    | Yes                                     | Plugin version (use `*` to indicate latest or all versions) |
| name                  | string    | Yes                                     | Configuration template name                                 |
| version               | string    | Yes                                     | Configuration template version                              |
| format                | string    | Yes                                     | File format (e.g., yaml, json, conf, properties)            |
| file_path             | string    | Yes                                     | Relative file path under the plugin directory               |
| content               | string    | Yes                                     | Base64-encoded or plain text configuration content          |
| md5                   | string    | Yes                                     | MD5 checksum of the configuration content                   |
| is_release_version    | bool      | Yes                                     | Whether this is a released version (vs. draft)              |

### Request Example

```json
{
    "plugin_name": "clb_traffic",
    "plugin_version": "*",
    "name": "env.yaml",
    "file_path": "etc",
    "format": "yaml",
    "content": "R1NFX0FHRU5UX0hPTUU6IHt7IGNvbnRyb2xfaW5mby5nc2VfYWdlbnRfaG9tZSB9fQpCS19QTFVHSU5fTE9HX1BBVEg",
    "md5": "dab43f1b255a78e1d288783c62fcf1b",
    "version": "11",
    "is_release_version": false
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "plugin_name": "xxxxx",
        "plugin_version": "1.0.0",
        "name": "env.yaml",
        "version": "10",
        "format": "yaml",
        "file_path": "etc",
        "content": "GSE_AGENT_HOME: {{ control_info.gse_agent_home }}\nBK_PLUGIN_LOG_PATH: {{ control_info.log_path }}\nBK_PLUGIN_PID_PATH: {{ control_info.pid_path }}\n\n\n\n\n\n\n\n\n\n\n\n\n\nBK_CMD_ARGS: {{ cmd_args }}",
        "md5": "dabd43f1b255a78e1d288783c62fcf1b",
        "is_release_version": false,
        "ids": [19524, 19525, 19526, 19527, 19528]
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

| Field               | Type       | Description                                   |
|---------------------|------------|-----------------------------------------------|
| plugin_name         | string     | Plugin name                                   |
| plugin_version      | string     | Plugin version                                |
| name                | string     | Configuration template name                   |
| version             | string     | Configuration template version                |
| format              | string     | File format (e.g., yaml, json)                |
| file_path           | string     | Relative path in plugin directory             |
| content             | string     | Decoded configuration content                 |
| md5                 | string     | MD5 hash of the content                       |
| is_release_version  | bool       | Whether this is a released version            |
| ids                 | int array  | List of created template IDs (one per target) |
