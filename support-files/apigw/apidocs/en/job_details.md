### Function Description

Query task details

### Request Parameters

#### Interface Parameters

| Field       | Type    | <div style="width: 50pt">Required</div> | Description                                  |
|-------------|---------|-----------------------------------------|----------------------------------------------|
| id          | int     | Yes                                     | Job ID                                       |
| page        | int     | No                                      | Page number for pagination. Default: 1       |
| pagesize    | int     | No                                      | Number of items per page. Default: 10        |
| conditions  | array   | No                                      | search_condition. See conditions definition  |

##### conditions

| Field   | Type     | <div style="width: 50pt">Required</div> | Description                                                                                                                                                                                                                                     |
|---------|----------|-----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| key     | string   | No                                      | Filter type: ip, instance_id, or status                                                                                                                                                                                                         |
| value   | string   | No                                      | Query keywords: 1: When the key is ip, you can specify the query IP address; 2: When the key is instance_id, you can specify the corresponding instance ID; 3: When the key is status, you can specify the query status. See status definition  |

##### status

| Status Type | Type    | Description         |
|-------------|---------|---------------------|
| PENDING     | string  | Pending execution   |
| RUNNING     | string  | Currently running   |
| FAILED      | string  | Execution failed    |
| SUCCESS     | string  | Execution succeeded |
| PART_FAILED | string  | Partially failed    |
| TERMINATED  | string  | Terminated          |
| REMOVED     | string  | Removed             |
| FILTERED    | string  | Filtered out        |
| IGNORED     | string  | Ignored             |

### Request Example

```json
{
    "job_id": 1,
    "conditions": [
        {
            "key": "status",
            "value": "SUCCESS"
        }
    ],
    "page": 1,
    "pagesize": 10
}
```

### Response Example

```json
{
  "result": true,
  "data": {
    "job_id": 1,
    "created_by": "admin",
    "job_type": "UPGRADE_AGENT",
    "job_type_display": "升级 Agent",
    "ip_filter_list": [],
    "total": 0,
    "list": [],
    "statistics": {
      "total_count": 1,
      "failed_count": 0,
      "ignored_count": 0,
      "pending_count": 0,
      "running_count": 0,
      "success_count": 1
    },
    "status": "SUCCESS",
    "end_time": "2021-09-16 15:07:20+0800",
    "start_time": "2021-09-16 15:06:03+0800",
    "cost_time": "77",
    "meta": {
      "type": "AGENT",
      "step_type": "AGENT",
      "op_type": "UPGRADE",
      "op_type_display": "升级",
      "step_type_display": "Agent"
    }
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

| Field              | Type           | Description                                                   |
|--------------------|----------------|---------------------------------------------------------------|
| job_id             | int            | Job ID                                                        |
| created_by         | string         | User who created the job                                      |
| job_type           | string         | Job type. See job_type definition                             |
| job_type_display   | string         | Job type name                                                 |
| ip_filter_list     | string arary   | The filtered IP list is not within the specified filter range |
| total              | int            | Total number of host instances in the job                     |
| list               | object         | Paginated list of host execution details. See list definition |
| statistics         | object         | Task Statistics. See statistics definition                    |
| status             | string         | Execution Status. See status definition                       |
| end_time           | string         | Completion time                                               |
| start_time         | string         | Start time                                                    |
| cost_time          | string         | Duration in seconds                                           |
| meta               | object         | Metadata about the job. See meta definition                   |

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

##### list

| Field            | Type     | Description                                      |
|------------------|----------|--------------------------------------------------|
| filter_host      | bool     | Whether this host was filtered out               |
| bk_host_id       | int      | Host ID                                          |
| ip               | string   | IP address                                       |
| inner_ip         | string   | IPv4 address                                     |
| inner_ipv6       | string   | IPv6 address                                     |
| bk_cloud_id      | int      | Cloud area ID                                    |
| bk_cloud_name    | string   | Cloud area name                                  |
| bk_biz_id        | int      | Business ID                                      |
| bk_biz_name      | string   | Business name                                    |
| job_id           | int      | Job ID                                           |
| status           | string   | Execution status per host. See status definition |
| status_display   | string   | Task execution status name                       |

##### statistics

| Field          | Type  | Description                      |
|----------------|-------|----------------------------------|
| total_count    | int   | Total number of target hosts     |
| failed_count   | int   | Number of failed executions      |
| ignored_count  | int   | Number of ignored hosts          |
| pending_count  | int   | Number of pending executions     |
| running_count  | int   | Number of currently running      |
| success_count  | int   | Number of successfully executed  |

##### meta

| Field              | Type    | Description                                                  |
|--------------------|---------|--------------------------------------------------------------|
| type               | string  | Target object type: AGENT, PLUGIN, PROXY                     |
| step_type          | string  | Step type                                                    |
| op_type            | string  | Operation type. See op_type definition                       |
| op_type_display    | string  | Display name of operation.                                   |
| step_type_display  | string  | Step type name: AGENT, PLUGIN, PROXY                         |
| name               | string  | Subscription name                                            |
| category           | string  | Subscription category: None (regular), POLICY (policy-based) |
| plugin_name        | string  | Plugin name                                                  |

###### op_type

| Field            | Type     | Description           |
|------------------|----------|-----------------------|
| INSTALL          | string   | Install               |
| REINSTALL        | string   | Reinstall             |
| UNINSTALL        | string   | Uninstall             |
| REMOVE           | string   | Remove                |
| REPLACE          | string   | Replace               |
| UPGRADE          | string   | Upgrade               |
| IMPORT           | string   | Import                |
| UPDATE           | string   | Update                |
| START            | string   | Start                 |
| STOP             | string   | Stop                  |
| RELOAD           | string   | Reload                |
| RESTART          | string   | Restart               |
| DELEGATE         | string   | Delegate              |
| UNDELEGATE       | string   | Undelegate            |
| DEBUG            | string   | Debug                 |
| MANUAL_INSTALL   | string   | Manual installation   |
| PACKING          | string   | Packaging             |
| STOP_AND_DELETE  | string   | Stop and delete       |
| PUSH             | string   | Push configuration    |
| IGNORED          | string   | Ignored               |
| POLICY_CONTROL   | string   | Policy control        |
| REMOVE_CONFIG    | string   | Remove configuration  |
| PUSH_CONFIG      | string   | Push configuration    |
