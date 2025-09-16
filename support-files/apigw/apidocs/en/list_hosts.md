### Function Description

Query host list

### Request Parameters

#### Interface Parameters

| Field            | Type          | <div style="width: 50pt">Required</div> | Description                                    |
|------------------|---------------|-----------------------------------------|------------------------------------------------|
| bk_biz_id        | int array     | No                                      | Business ID                                    |
| bk_host_id       | int array     | No                                      | Host ID                                        |
| bk_cloud_id      | int array     | No                                      | Cloud Area ID                                  |
| version          | string array  | No                                      | Agent version                                  |
| exclude_hosts    | int array     | No                                      | Excluded hosts when selecting all across pages |
| conditions       | array         | No                                      | Search conditions, see `conditions` definition |
| extra_data       | string array  | No                                      | Additional information to display              |
| page             | int           | No                                      | Current page number, default is 1              |
| pagesize         | int           | No                                      | Page size, default is 10                       |
| only_ip          | bool          | No                                      | Return only IP addresses, no other fields      |
| running_count    | bool          | No                                      | Whether to return only running status count    |

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
        1,
        2,
        3
    ],
    "conditions": [
         {
             "key": "inner_ip",
             "value": ["127.0.0.1"]
         }
     ],
    "extra_data": [
        "job_result"
    ],
    "pagesize": 20,
    "page": 1,
    "only_ip": false,
    "running_count": false
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
        "status": "RUNNING",
        "version": "1.7.15",
        "bk_cloud_id": 0,
        "bk_biz_id": 2,
        "bk_host_id": 2,
        "bk_host_name": "",
        "bk_addressing": "0",
        "os_type": "LINUX",
        "inner_ip": "127.0.0.1",
        "inner_ipv6": "",
        "outer_ip": "",
        "outer_ipv6": "",
        "ap_id": 1,
        "install_channel_id": null,
        "login_ip": "",
        "data_ip": "",
        "created_at": "2022-07-12 18:58:36+0800",
        "updated_at": "2022-07-12 18:58:36+0800",
        "is_manual": true,
        "extra_data": {
          "bt_speed_limit": null,
          "peer_exchange_switch_for_agent": 0,
          "enable_compression": false
        },
        "status_display": "正常",
        "bk_cloud_name": "直连区域",
        "install_channel_name": null,
        "bk_biz_name": "蓝鲸",
        "identity_info": {},
        "job_result": {
          "instance_id": "host|instance|host|2",
          "job_id": 1656,
          "status": "FAILED",
          "current_step": "正在重装"
        },
        "topology": [
          "蓝鲸 / 中控机 / controller_ip",
          "蓝鲸 / 公共组件 / consul",
          "蓝鲸 / 公共组件 / redis",
          "蓝鲸 / 公共组件 / rabbitmq",
          "蓝鲸 / 公共组件 / beanstalk",
          "蓝鲸 / 管控平台 / license",
          "蓝鲸 / 监控平台v3 / monitor"
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

| Field     | Type     | Description                                                            |
|-----------|----------|------------------------------------------------------------------------|
| result    | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code      | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string   | Error message returned when the request fails                          |
| data      | object   | Data returned by the request, see definition below                     |

#### data

| Field               | Type    | Description                                                            |
|---------------------|---------|------------------------------------------------------------------------|
| total               | int     | Total number of hosts                                                  |
| list                | array   | List of host information, see list definition                          |
| running_count       | int     | Number of hosts currently running                                      |
| no_permission_count | int     | Number of hosts without operation permission                           |
| manual_statistics   | array   | Manual installation statistics: `true` for manual, `false` otherwise   |

##### list

| Field                | Type         | Description                                           |
|----------------------|--------------|-------------------------------------------------------|
| bk_cloud_id          | int          | Cloud area ID                                         |
| bk_biz_id            | int          | Business ID                                           |
| bk_host_id           | int          | Host ID                                               |
| bk_host_name         | string       | Host name                                             |
| bk_addressing        | int          | Addressing method: 0 (static), 1 (dynamic)            |
| os_type              | string       | Operating system: LINUX, WINDOWS, AIX, SOLARIS        |
| inner_ip             | string       | Internal IPv4 address                                 |
| inner_ipv6           | string       | Internal IPv6 address                                 |
| outer_ip             | string       | External IPv4 address                                 |
| outer_ipv6           | string       | External IPv6 address                                 |
| ap_id                | int          | Access point ID                                       |
| install_channel_id   | int          | Installation channel ID                               |
| login_ip             | string       | Login IP                                              |
| data_ip              | string       | Data IP                                               |
| status               | string       | Running status, see status definition                 |
| version              | string       | Agent version                                         |
| created_at           | string       | Creation time                                         |
| updated_at           | string       | Update time                                           |
| is_manual            | bool         | Whether in manual mode                                |
| extra_data           | object       | Extra information, see extra_data definition          |
| status_display       | string       | Display name of running status, see status definition |
| bk_cloud_name        | string       | Cloud area name                                       |
| install_channel_name | string       | Installation channel name                             |
| bk_biz_name          | string       | Business name                                         |
| identity_info        | object       | Authentication information                            |
| job_result           | object       | Task execution result, see job_result definition      |
| topology             | string array | Topology information                                  |
| operate_permission   | bool         | Whether operation permission is granted               |

##### status

| Status Type   | Type     | Description        |
|---------------|----------|--------------------|
| RUNNING       | string   | Running            |
| UNKNOWN       | string   | Unknown            |
| TERMINATED    | string   | Terminated         |
| NOT_INSTALLED | string   | Not installed      |
| UNREGISTER    | string   | Unregistered       |
| REMOVED       | string   | Removed            |
| MANUAL_STOP   | string   | Manually stopped   |

##### extra_data

| Field                          | Type  | Description                                 |
|--------------------------------|-------|---------------------------------------------|
| bt_speed_limit                 | int   | BT transfer speed limit, in MB/s            |
| peer_exchange_switch_for_agent | int   | BT transfer switch: 1: enabled, 0: disabled |
| enable_compression             | bool  | Data compression switch, default disabled   |

##### job_result

| Field          | Type     | Description                                  |
|----------------|----------|----------------------------------------------|
| instance_id    | string   | Instance ID                                  |
| job_id         | int      | Job ID                                       |
| status         | string   | Execution status, see job_status definition  |
| current_step   | string   | Name of current step                         |

##### job_status

| Status Type | Type     | Description       |
|-------------|----------|-------------------|
| RUNNING     | string   | Running           |
| QUEUE       | string   | In queue          |
| PENDING     | string   | Pending execution |
| FAILED      | string   | Failed            |
| SUCCESS     | string   | Success           |
