### Function Description

Installation job tasks, including new Agent installation, new Proxy installation, reinstallation, replacement, etc.

### Request Parameters

#### Interface Parameters

| Field                      | Type     | <div style="width: 50pt">Required</div> | Description                                                                    |
|----------------------------|----------|-----------------------------------------|--------------------------------------------------------------------------------|
| job_type                   | string   | Yes                                     | Job type, see `job_type` definition                                            |
| hosts                      | array    | Yes                                     | Host list, see `hosts` definition                                              |
| replace_host_id            | int      | No                                      | Replaced Proxy host ID                                                         |
| is_install_latest_plugins  | bool     | No                                      | Whether to install the latest plugin version. Default: true (install latest)   |

##### hosts

| Field                           | Type     | <div style="width: 50pt">Required</div> | Description                                                                                                                                   |
|---------------------------------|----------|-----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| bk_biz_id                       | int      | Yes                                     | Business ID                                                                                                                                   |
| bk_cloud_id                     | int      | Yes                                     | Cloud area ID                                                                                                                                 |
| bk_host_id                      | int      | No                                      | Host ID                                                                                                                                       |
| bk_addressing                   | int      | No                                      | Addressing method: 0 - Static, 1 - Dynamic                                                                                                    |
| ap_id                           | int      | No                                      | Access point ID                                                                                                                               |
| install_channel_id              | int      | No                                      | Installation channel ID                                                                                                                       |
| inner_ip                        | string   | No                                      | Internal IPv4 address. One of `inner_ip` or `inner_ipv6` is required                                                                          |
| outer_ip                        | string   | No                                      | External IP                                                                                                                                   |
| login_ip                        | string   | No                                      | Login IP                                                                                                                                      |
| data_ip                         | string   | No                                      | Data IP                                                                                                                                       |
| inner_ipv6                      | string   | No                                      | Internal IPv6                                                                                                                                 |
| outer_ipv6                      | string   | No                                      | External IPv6                                                                                                                                 |
| os_type                         | string   | Yes                                     | Operating system: `LINUX`, `WINDOWS`, `AIX`, `SOLARIS`                                                                                        |
| auth_type                       | string   | No                                      | Authentication type: `PASSWORD`, `KEY`, `TJJ_PASSWORD`. Default is password authentication. Required for non-manual and non-reload operations |
| account                         | string   | No                                      | Account                                                                                                                                       |
| password                        | string   | No                                      | Password                                                                                                                                      |
| port                            | int      | No                                      | Port                                                                                                                                          |
| key                             | string   | No                                      | Private key                                                                                                                                   |
| is_manual                       | bool     | No                                      | Manual mode flag                                                                                                                              |
| retention                       | int      | No                                      | Password retention days. Default: 1 day                                                                                                       |
| peer_exchange_switch_for_agent  | int      | No                                      | Acceleration setting. Default: 0                                                                                                              |
| bt_speed_limit                  | string   | No                                      | Transfer speed limit (e.g., "10MB/s")                                                                                                         |
| enable_compression              | bool     | No                                      | Data compression toggle. Default: disabled                                                                                                    |
| data_path                       | string   | No                                      | Data file path                                                                                                                                |

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

### Request Example

```json
{
    "job_type": "INSTALL_AGENT",
    "hosts": [
        {
            "bk_cloud_id": 0,
            "ap_id": 1,
            "bk_biz_id": 2,
            "os_type": "LINUX",
            "inner_ip": "127.0.0.1",
            "outer_ip": "127.0.0.2",
            "login_ip": "127.0.0.3",
            "data_ip": "127.0.0.4",
            "account": "root",
            "port": 22,
            "auth_type": "PASSWORD",
            "password": "password",
            "key": "key",
            "retention": 1
        },
        {
            "bk_cloud_id": 2,
            "ap_id": 1,
            "bk_biz_id": 2,
            "os_type": "LINUX",
            "inner_ip": "127.0.0.1",
            "outer_ip": "127.0.0.2",
            "login_ip": "127.0.0.3",
            "data_ip": "127.0.0.4",
            "account": "root",
            "port": 22,
            "auth_type": "PASSWORD",
            "password": "password",
            "key": "key",
            "retention": 1
        }
    ]
}
```

### Response Example

```json
{
  "result": false,
  "code": 3801013,
  "data": {
    "job_id": "",
    "ip_filter": [
      {
        "bk_biz_id": 2,
        "bk_biz_name": "蓝鲸",
        "ip": "127.0.0.1",
        "inner_ip": "127.0.0.1",
        "inner_ipv6": null,
        "bk_host_id": null,
        "bk_cloud_name": "1",
        "bk_cloud_id": 2,
        "status": "IGNORED",
        "job_id": "",
        "exception": "no_proxy",
        "msg": "该管控区域下不存在代理"
      }
    ]
  },
  "message": "不存在可用代理（3801013）",
  "errors": null
}
```

### Response Parameters Description

#### response

| Field      | Type     | Description                         |
| ------- |--------| -------------------------- |
| result  | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code    | int    | Error code. 0 indicates success; values greater than 0 indicate errors  |
| message | string | Error message returned when the request fails                |
| data    | object | Data returned by the request, see definition below            |

#### data

| Field       | Type    | Description                                               |
|-------------|---------|-----------------------------------------------------------|
| job_id      | int     | Job ID                                                    |
| ip_filter   | array   | List of filtered/failing hosts, see ip_filter definition  |

##### ip_filter

| Field          | Type     | Description                             |
|----------------|----------|-----------------------------------------|
| bk_biz_id      | int      | Host business ID                        |
| bk_biz_name    | string   | Host business name                      |
| ip             | string   | IP address                              |
| inner_ip       | string   | Internal IPv4 address                   |
| inner_ipv6     | string   | Internal IPv6 address                   |
| bk_host_id     | int      | Host ID                                 |
| bk_cloud_name  | string   | Cloud area name                         |
| bk_cloud_id    | int      | Cloud area ID                           |
| status         | string   | Execution status, see status definition |
| job_id         | int      | Job ID                                  |
| exception      | string   | Filter reason                           |
| msg            | string   | Detailed failure message                |

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
