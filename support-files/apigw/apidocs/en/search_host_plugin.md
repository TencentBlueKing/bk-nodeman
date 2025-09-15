### Function Description

Query the list of plugins on the host

### Request Parameters

#### Interface Parameters

| Field                      | Type      | <div style="width: 50pt">Required</div> | Description                                                                        |
|----------------------------|-----------|-----------------------------------------|------------------------------------------------------------------------------------|
| bk_biz_id                  | int array | No                                      | List of business (bk_biz) IDs to filter hosts.                                     |
| bk_host_id                 | int array | No                                      | List of specific host IDs to query.                                                |
| bk_cloud_id                | int array | No                                      | List of cloud area IDs to filter hosts.                                            |
| conditions                 | array     | No                                      | Search conditions, see `conditions` definition.                                    |
| exclude_hosts              | int array | No                                      | List of host IDs to exclude when "select all across pages" is used.                |
| page                       | int       | No                                      | Page number, default is 1.                                                         |
| pagesize                   | int       | No                                      | Number of results per page, default is 10.                                         |
| only_ip                    | bool      | No                                      | If `true`, only returns IP addresses; other fields are omitted. Default: `false`.  |
| simple                     | bool      | No                                      | If `true`, returns only basic info (`bk_host_id`, `bk_biz_id`). Default: `false`.  |
| detail                     | bool      | No                                      | If `true`, returns detailed node information. Default: `false`.                    |
| with_agent_status_counter  | bool      | No                                      | If `true`, returns agent status statistics (e.g., process info). Default: `false`. |

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


### Request Example

```json
{
    "bk_host_id": [
        1
    ],
    "detail": true
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "total": 1,
        "list": [
            {
                "bk_biz_id": 2,
                "bk_host_id": 1,
                "bk_cloud_id": 0,
                "bk_host_name": "",
                "bk_addressing": "0",
                "inner_ip": "127.0.0.1",
                "inner_ipv6": "",
                "os_type": "LINUX",
                "cpu_arch": "x86_64",
                "node_type": "Agent",
                "node_from": "NODE_MAN",
                "status": "RUNNING",
                "version": "1.7.19",
                "status_display": "正常",
                "bk_cloud_name": "直连区域",
                "bk_biz_name": "蓝鲸",
                "job_result": {
                    "instance_id": "host|instance|host|1",
                    "job_id": 1434,
                    "status": "SUCCESS",
                    "current_step": "正在重装"
                },
                "plugin_status": [
                    {
                        "name": "basereport",
                        "status": "RUNNING",
                        "version": "10.12.76",
                        "host_id": 1
                    }
                ],
                "operate_permission": true
            }
        ]
    },
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field   | Type     | Description                                                            |
|---------|----------|------------------------------------------------------------------------|
| result  | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code    | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message | string   | Error message returned when the request fails                          |
| data    | object   | Data returned by the request, see definition below                     |

#### data

| Field    | Type    | Description                                                 |
|----------|---------|-------------------------------------------------------------|
| total    | int     | Total number of hosts                                       |
| list     | array   | List of summarized host information, see `list` definition  |

##### list

| Field                | Type      | Description                                                      |
|----------------------|-----------|------------------------------------------------------------------|
| bk_cloud_id          | int       | Cloud area ID                                                    |
| bk_biz_id            | int       | Business ID                                                      |
| bk_host_id           | int       | Host ID                                                          |
| bk_host_name         | string    | Host name                                                        |
| bk_addressing        | int       | Addressing method: `0`: static, `1`: dynamic                     |
| node_type            | string    | Node type: `Agent`, `Proxy`, `Pagent`                            |
| os_type              | string    | Operating system: `LINUX`, `WINDOWS`, `AIX`, `SOLARIS`           |
| inner_ip             | string    | Internal IPv4 address                                            |
| inner_ipv6           | string    | Internal IPv6 address                                            |
| cpu_arch             | string    | CPU architecture: `x86`, `x86_64`, `powerpc`, `aarch64`, `sparc` |
| status               | string    | Host Agent status, see status enumeration                        |
| status_display       | string    | Display name of execution status, see status enumeration         |
| bk_cloud_name        | string    | Cloud area name                                                  |
| bk_biz_name          | string    | Business name                                                    |
| job_result           | object    | Job execution result, see job_result definition                  |
| plugin_status        | array     | Plugin status list, see plugin_status definition                 |
| operate_permission   | bool      | Whether the user has operation permission                        |

##### plugin_status

| Field     | Type     | Description                             |
|-----------|----------|-----------------------------------------|
| name      | string   | Plugin name                             |
| status    | int      | Plugin status, see `status` enumeration |
| version   | string   | Plugin version                          |
| host_id   | int      | Host ID                                 |

##### job_result

| Field          | Type     | Description                                    |
|----------------|----------|------------------------------------------------|
| instance_id    | string   | Instance ID, see `instance_id` format          |
| job_id         | int      | Job ID                                         |
| status         | string   | Execution status, see `job_status` enumeration |
| current_step   | string   | Current step name                              |

##### status

| Status Type   | Type      | Description       |
|---------------|-----------|-------------------|
| RUNNING       | string    | Running           |
| UNKNOWN       | string    | Unknown           |
| TERMINATED    | string    | Terminated        |
| NOT_INSTALLED | string    | Not Installed     |
| UNREGISTER    | string    | Unregistered      |
| REMOVED       | string    | Removed           |
| MANUAL_STOP   | string    | Manually Stopped  |

###### job_status

| Status Type | Type     | Description |
|-------------|----------|-------------|
| RUNNING     | string   | Running     |
| QUEUE       | string   | In Queue    |
| PENDING     | string   | Pending     |
| FAILED      | string   | Failed      |
| SUCCESS     | string   | Success     |

###### instance_id

Constructed from host instance information within the scope by concatenating the following fields: `{object_type}|{node_type}|{type}|{id}`. 
<br>Example: 1: `host|instance|host|1`  2: `host|instance|host|127.0.0.1-1-0`

| Field         | Type      | Description                                                                                                                             |
|---------------|-----------|-----------------------------------------------------------------------------------------------------------------------------------------|
| object_type   | string    | Object type: `1`: `host` (host), `2`: `service` (service)                                                                               |
| node_type     | string    | Node category: `1`: `topo` (dynamic instance/topology), `2`: `instance` (static instance), `3`: `service_template`, `4`: `set_template` |
| type          | string    | Service type: `1`: `host` (host), `2`: `bk_obj_id` (template ID)                                                                        |
| id            | string    | Service instance ID: <br>1. Generated from IP, `bk_cloud_id`, `bk_supplier_id` using delimiter "-" <br>2. `bk_host_id` (Host ID)        |
