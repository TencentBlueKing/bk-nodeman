### Function Description

Operate on job tasks. Used for operations like host offline or restart that only require the `bk_host_id` parameter. This interface cannot be used for installing/replacing Proxy.

### Request Parameters

#### Interface Parameters

| Field                       | Type       | <div style="width: 50pt">Required</div> | Description                                                                                                                                                                                                                                 |
|-----------------------------|------------|-----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| job_type                    | string     | Yes                                     | Job type, see `job_type` definition                                                                                                                                                                                                         |
| bk_biz_id                   | int array  | Yes                                     | Business ID                                                                                                                                                                                                                                 |
| conditions                  | array      | No                                      | Search conditions. Supports `os_type`, `ip`, `status`, `version`, `bk_cloud_id`, `node_from`, and fuzzy search `query`. See `conditions` definition                                                                                         |
| bk_host_id                  | int array  | No                                      | Host ID                                                                                                                                                                                                                                     |
| exclude_hosts               | int array  | No                                      | Excluded hosts for cross-page selection. Either `bk_host_id` or `exclude_hosts` is required. Note: Filters like cloud area ID and business ID are only effective in cross-page selection mode, and `bk_host_id` is not allowed in this mode |
| is_install_latest_plugins   | bool       | No                                      | Whether to install the latest plugin version. Default: true (install latest)                                                                                                                                                                |

##### conditions

Dictionary composed of a specified key and value. Example: `{"key": "inner_ip", "value": ["127.0.0.1"]}`

| Key                   | Type   | Description                                                                                                               |
|-----------------------|--------|---------------------------------------------------------------------------------------------------------------------------|
| inner_ip              | string | Host internal IPv4 address                                                                                                |
| node_from             | string | Node source: `CMDB` (synced from Configuration Platform), `EXCEL` (imported via SaaS table), `NODE_MAN` (Node Management) |
| node_type             | string | Node type: `AGENT`, `PROXY`, `PAGENT`                                                                                     |
| bk_addressing         | string | Addressing method: `0` (Static), `1` (Dynamic)                                                                            |
| bk_host_name          | string | Host name                                                                                                                 |
| os_type               | string | Operating System: `LINUX`, `WINDOWS`, `AIX`, `SOLARIS`                                                                    |
| status                | string | Process status, see `status` definition                                                                                   |
| version               | string | Agent version                                                                                                             |
| is_manual             | string | Manual installation                                                                                                       |
| bk_cloud_id           | string | Cloud area ID                                                                                                             |
| install_channel_id    | string | Installation channel ID                                                                                                   |
| topology              | string | Precise search for cluster and module                                                                                     |
| query                 | string | Fuzzy search for IP, OS, Agent status, Agent version, Cloud area. When `value` is a list, it performs multi-fuzzy search  |
| source_id             | string | Source ID                                                                                                                 |
| plugin_name           | string | Plugin name. Expands to all plugin names under the task                                                                   |
| ${plugin_name}        | string | Exact search for plugin version. `${plugin_name}` is the target plugin name                                               |
| ${plugin_name}_status | string | Exact search for plugin status. `${plugin_name}` is the target plugin name                                                |


##### status

| Status Valu    | Type       | Description        |
|----------------|------------|--------------------|
| RUNNING        | string     | Running            |
| UNKNOWN        | string     | Unknown            |
| TERMINATED     | string     | Terminated         |
| NOT_INSTALLED  | string     | Not Installed      |
| UNREGISTER     | string     | Unregistered       |
| REMOVED        | string     | Removed            |
| MANUAL_STOP    | string     | Manually Stopped   |

###### job_type

| Field                       | Type    | Description                   |
|-----------------------------|---------|-------------------------------|
| RESTART_AGENT               | string  | Restart Agent                 |
| RESTART_PROXY               | string  | Restart Proxy                 |
| REINSTALL_PROXY             | string  | Reinstall Proxy               |
| REINSTALL_AGENT             | string  | Reinstall Agent               |
| UPGRADE_PROXY               | string  | Upgrade Proxy                 |
| UPGRADE_AGENT               | string  | Upgrade Agent                 |
| REMOVE_AGENT                | string  | Remove Agent                  |
| UNINSTALL_AGENT             | string  | Uninstall Agent               |
| UNINSTALL_PROXY             | string  | Uninstall Proxy               |
| IMPORT_PROXY                | string  | Import Proxy Machine          |
| IMPORT_AGENT                | string  | Import Agent Machine          |
| MAIN_START_PLUGIN           | string  | Start Plugin                  |
| MAIN_STOP_PLUGIN            | string  | Stop Plugin                   |
| MAIN_RESTART_PLUGIN         | string  | Restart Plugin                |
| MAIN_RELOAD_PLUGIN          | string  | Reload Plugin                 |
| MAIN_DELEGATE_PLUGIN        | string  | Delegate Plugin               |
| MAIN_UNDELEGATE_PLUGIN      | string  | Undelegate Plugin             |
| MAIN_INSTALL_PLUGIN         | string  | Install Plugin                |
| MAIN_STOP_AND_DELETE_PLUGIN | string  | Stop Plugin and Delete Policy |
| RELOAD_AGENT                | string  | Reload Configuration          |
| RELOAD_PROXY                | string  | Reload Configuration          |
| PACKING_PLUGIN              | string  | Pack Plugin                   |
| PUSH_CONFIG_PLUGIN          | string  | Push Plugin Configuration     |
| REMOVE_CONFIG_PLUGIN        | string  | Remove Plugin Configuration   |
| MANUAL_INSTALL_AGENT        | string  | Manual Agent Installation     |
| MANUAL_INSTALL_PROXY        | string  | Manual Proxy Installation     |

### Request Example

```json
{
    "job_type": "RESTART_AGENT",
    "conditions": [
        {
            "key": "inner_ip",
            "value": ["127.0.0.1"]
        }
    ],
    "exclude_hosts": [
        2000026002,
        2000062520,
        2000062463
    ]
}
```

### Response Example

```json
{
  "result": true,
  "data": {
    "job_id": 1741,
    "job_url": "https://localhost.com/#/task-list/detail/1741"
  },
  "code": 0,
  "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Type    | Description                                                            |
|----------|---------|------------------------------------------------------------------------|
| result   | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code     | int     | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string  | Error message returned when the request fails                          |
| data     | object  | Data returned by the request, see definition below                     |

#### data

| Field     | Type    | Description       |
|-----------|---------|-------------------|
| job_id    | int     | Job ID            |
| job_url   | string  | Job task link URL |
