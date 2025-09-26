### Function Description

Retry failed task

### Request Parameters

#### Interface Parameters

| Field                | Type      | <div style="width: 50pt">Required</div> | Description                                                                                               |
|----------------------|-----------|-----------------------------------------|-----------------------------------------------------------------------------------------------------------|
| subscription_id      | int       | Yes                                     | Subscription ID                                                                                           |
| instance_id_list     | array     | No                                      | List of instance IDs. See `instance_id_list` definition.                                                  |
| task_id_list         | array     | No                                      | List of task IDs to retry.                                                                                |
| actions              | object    | No                                      | Actions to execute. See `actions` definition. If not provided, uses the actions from the most recent task |

##### instance_id_list

Converted from the host instance information in the scope, it is spliced by the following fields and can be queried through the `task_result_subscription` API interface. The rule is: {object_type}|{node_type}|{type}|{id}. 
<br>Example: 1: host|instance|host|1, 2: host|instance|host|127.0.0.1-1-0

| Field       | Type      | <div style="width: 50pt">Required</div> | Description                                                                                                      |
|-------------|-----------|-----------------------------------------|------------------------------------------------------------------------------------------------------------------|
| object_type | string    | Yes                                     | Object type: `host` (host), `service` (service)                                                                  |
| node_type   | string    | Yes                                     | Node type: `topo` (dynamic topology), `instance` (static instance), `service_template`, `set_template`           |
| type        | string    | Yes                                     | Type of service: `host` (host), `bk_obj_id` (template ID)                                                        |
| id          | string    | Yes                                     | Instance ID: <br>1. Generated from IP, cloud ID, supplier ID, separated by "-"<br>2. `bk_host_id` (CMDB Host ID) |

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
    "instance_id_list": ["host|instance|host|1"],
    "task_id_list": [1],
    "actions": {"agent": "INSTALL_AGENT"}
}
```

### Response Example

```json
{
    "result": true,
    "code": 0,
    "message": "",
    "data": {
       "task_id": 415
    }
}
```

### Response Parameters Description

#### response

| Field    | Type    | Description                                                            |
|----------|---------|------------------------------------------------------------------------|
| result   | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code     | int     | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string  | Error message returned when the request fails                          |
| data     | object  | Data returned by the request                                           |

##### data

| Field       | Type | Description                                   |
|-------------|------|-----------------------------------------------|
| task_id     | int  | New task ID created for the retry operation   |
