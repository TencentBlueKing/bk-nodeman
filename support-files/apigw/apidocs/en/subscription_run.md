### Function Description

Run subscription

### Request Parameters

#### Interface Parameters

| Field           | Type      | <div style="width: 50pt">Required</div> | Description                                                                                                 |
|-----------------|-----------|-----------------------------------------|-------------------------------------------------------------------------------------------------------------|
| subscription_id | int       | Yes                                     | Subscription ID to execute                                                                                  |
| scope           | object    | Yes                                     | Execution scope defining target instances.                                                                  |
| actions         | object    | No                                      | Custom actions to run. See `actions` definition. If not provided, uses the action from the most recent task |

#### actions

Dictionary composed of step ID and job type, e.g.: `{"agent": "INSTALL_AGENT"}`

| Field       | Type     | <div style="width: 50pt">Required</div> | Description                                                |
|-------------|----------|-----------------------------------------|------------------------------------------------------------|
| step_id     | string   | Yes                                     | Subscription step ID, specified when creating subscription |
| job_type    | string   | Yes                                     | Job type, see `job_type` definition                        |


###### job_type

Agent

| Field            | Type     | Description                 |
|------------------|----------|-----------------------------|
| INSTALL_AGENT    | string   | Install Agent               |
| RESTART_AGENT    | string   | Restart Agent               |
| REINSTALL_AGENT  | string   | Reinstall Agent             |
| UNINSTALL_AGENT  | string   | Uninstall Agent             |
| REMOVE_AGENT     | string   | Remove Agent                |
| UPGRADE_AGENT    | string   | Upgrade Agent               |
| RELOAD_AGENT     | string   | Reload Agent configuration  |
| INSTALL_PROXY    | string   | Install Proxy               |
| RESTART_PROXY    | string   | Restart Proxy               |
| REINSTALL_PROXY  | string   | Reinstall Proxy             |
| UNINSTALL_PROXY  | string   | Uninstall Proxy             |
| UPGRADE_PROXY    | string   | Upgrade Proxy               |
| RELOAD_PROXY     | string   | Reload Proxy configuration  |

Plugin

| Field                         | Type    | Description                       |
|-------------------------------|---------|-----------------------------------|
| MAIN_START_PLUGIN             | string  | Start plugin process              |
| MAIN_STOP_PLUGIN              | string  | Stop plugin process               |
| MAIN_RESTART_PLUGIN           | string  | Restart plugin process            |
| MAIN_RELOAD_PLUGIN            | string  | Reload plugin configuration       |
| MAIN_DELEGATE_PLUGIN          | string  | Delegate plugin                   |
| MAIN_UNDELEGATE_PLUGIN        | string  | Undelegate plugin                 |
| DEBUG_PLUGIN                  | string  | Debug plugin                      |
| STOP_DEBUG_PLUGIN             | string  | Stop debugging plugin             |
| MAIN_INSTALL_PLUGIN           | string  | Deploy and install plugin         |
| MAIN_STOP_AND_DELETE_PLUGIN   | string  | Stop and uninstall plugin         |

Official plugins is based on a multi-configuration management mode. Operations such as installation, uninstallation, activation, and deactivation only involve adding and deleting configurations. 

| Field         | Type     | Description                 |
|---------------|----------|-----------------------------|
| INSTALL       | string   | Push plugin configuration   |
| UNINSTALL     | string   | Remove plugin configuration |
| PUSH_CONFIG   | string   | Push configuration          |
| START         | string   | Push configuration          |
| STOP          | string   | Remove configuration        |

Non-Official plugins

| Field        | Type     | Description           |
|--------------|----------|-----------------------|
| INSTALL      | string   | Deploy plugin         |
| UNINSTALL    | string   | Uninstall plugin      |
| PUSH_CONFIG  | string   | Push configuration    |
| START        | string   | Start plugin process  |
| STOP         | string   | Stop plugin process   |

### Request Example

```json
{
    "subscription_id": 1,
    "scope": {
        "bk_biz_id": 2,
        "object_type": "SERVICE",
        "node_type": "TOPO",
        "nodes": [
            {
                "bk_host_id": 12
            },
            {
                "bk_inst_id": 33,
                "bk_obj_id": "module"
            },
            {
                "ip": "127.0.0.1",
                "bk_cloud_id": 0,
                "bk_supplier_id": 0
            },
            {
                "ip": "127.0.0.1",
                "bk_cloud_id": 1,
                "instance_info": {
                    "key": "",
                    "port": 22,
                    "ap_id": 1,
                    "account": "root",
                    "os_type": "LINUX",
                    "login_ip": "127.0.0.1",
                    "password": "Qk=",
                    "username": "admin",
                    "auth_type": "PASSWORD",
                    "bk_biz_id": 337,
                    "data_path": "/var/lib/gse",
                    "is_manual": false,
                    "retention": -1,
                    "bk_os_type": "1",
                    "bk_biz_name": "xxxxxx",
                    "bk_cloud_id": 1,
                    "bk_cloud_name": "xxxx",
                    "bt_speed_limit": null,
                    "host_node_type": "PROXY",
                    "bk_host_innerip": "127.0.0.1",
                    "bk_host_outerip": "127.0.0.1",
                    "install_channel_id": null,
                    "bk_supplier_account": "0",
                    "peer_exchange_switch_for_agent": 0,
                    "enable_compression": false
                },
                "bk_supplier_account": "0"
            }
        ]
    },
    "actions": {
        "testscript": "UNINSTALL",
        "bkmonitorbeat": "UNINSTALL"
    }
}
```

### Response Example

```json
{
    "result": true,
    "code": 0,
    "message": "success",
    "data": {
        "subscription_id": 1,
        "task_id": 1
    }
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

| Field             | Type | Description     |
|-------------------|------|-----------------|
| subscription_id   | int  | Subscription ID |
| task_id           | int  | Task ID         |
