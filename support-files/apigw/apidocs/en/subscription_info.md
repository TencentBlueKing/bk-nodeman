### Function Description

Subscription information

### Request Parameters

#### Interface Parameters

| Field                   | Type  | <div style="width: 50pt">Required</div> | Description                                                    |
|-------------------------|-------|-----------------------------------------|----------------------------------------------------------------|
| subscription_id_list    | array | Yes                                     | List of subscription IDs                                       |
| show_deleted            | bool  | No                                      | Whether to include deleted subscriptions. Default is `false`.  |

### Request Example

```json
{
  "subscription_id_list": [
    1
  ],
  "show_deleted": false
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "id": 1,
            "name": "basereport-策略范围主机",
            "enable": true,
            "category": "once",
            "plugin_name": "basereport",
            "bk_biz_scope": [
                1,
                2,
                3
            ],
            "scope": {
                "bk_biz_id": 1,
                "object_type": "SERVICE",
                "node_type": "TOPO",
                "nodes": [
                    {
                        "bk_inst_id": 33,
                        "bk_obj_id": "module"

                    },
                    {
                        "ip": "127.0.0.1",
                        "bk_cloud_id": 0,
                        "bk_supplier_id": 0
                    }
                ]
            },
            "pid": 1,
            "target_hosts": [
                {
                    "ip": "127.0.0.1",
                    "bk_cloud_id": 0,
                    "bk_supplier_id": 0
                }
            ],
            "steps": [
                {
                    "id": "mysql_exporter",
                    "type": "PLUGIN",
                    "config": {
                        "plugin_name": "mysql_exporter",
                        "plugin_version": "2.3",
                        "config_templates": [
                            {
                                "name": "config.yaml",
                                "version": "2",
                                "os": "windows",
                                "cpu_arch": "x86_64"

                            },
                            {
                                "name": "env.yaml",
                                "version": "2",
                                "os": "windows",
                                "cpu_arch": "x86_64"

                            }
                        ]
                    },
                    "params": {
                        "port_range": "9102,10000-10005,20103,30000-30100",
                        "context": {
                            "--web.listen-host": "127.0.0.1",
                            "--web.listen-port": "{{ control_info.port }}"
                        }
                    }
                },
                {
                    "id": "bkmonitorbeat",
                    "type": "PLUGIN",
                    "config": {
                        "plugin_name": "bkmonitorbeat",
                        "plugin_version": "1.7.0",
                        "config_templates": [
                            {
                                "name": "bkmonitorbeat_exporter.yaml",
                                "version": "1"

                            }

                        ]
                    },
                    "params": {
                        "context": {
                            "metrics_url": "XXX",
                            "labels": {
                                "$for": "cmdb_instance.scopes",
                                "$item": "scope",
                                "$body": {
                                    "bk_target_ip": "{{ cmdb_instance.host.bk_host_innerip }}",
                                    "bk_target_cloud_id": "{{ cmdb_instance.host.bk_cloud_id }}",
                                    "bk_target_topo_level": "{{ scope.bk_obj_id }}",
                                    "bk_target_topo_id": "{{ scope.bk_inst_id }}",
                                    "bk_target_service_category_id": "{{ cmdb_instance.service.service_category_id }}",
                                    "bk_target_service_instance_id": "{{ cmdb_instance.service.id }}",
                                    "bk_collect_config_id": 1
                                }
                            }
                        }
                    }
                }
            ]
        }
    ]
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

| Field           | Type    | Description                                                               |
|-----------------|---------|---------------------------------------------------------------------------|
| id              | int     | Subscription task ID                                                      |
| name            | string  | Subscription task name                                                    |
| enable          | bool    | Whether the subscription is enabled: `false` = disabled, `true` = enabled |
| category        | string  | Subscription category: `policy`, `debug`, `once`                          |
| plugin_name     | string  | Plugin name                                                               |
| bk_biz_scope    | int     | List of business IDs that the subscription applies to                     |
| scope           | object  | Scope of the subscription event. See `scope` definition                   |
| pid             | int     | Parent policy ID. Default is `-1` if not set                              |
| target_hosts    | object  | List of target hosts for deployment. See `target_hosts` definition        |
| steps           | object  | List of actions triggered by the subscription. See `steps` definition     |

#### steps

| Field      | Type     | Description                                 |
|------------|----------|---------------------------------------------|
| id         | string   | Step identifier                             |
| type       | string   | Step type: `AGENT`, `PLUGIN`, `PROXY`       |
| config     | object   | Step configuration. See `config` definition |
| params     | object   | Step parameters. See `params` definition    |

#### scope

| Field           | Type    | Description                                                                                            |
|-----------------|---------|--------------------------------------------------------------------------------------------------------|
| bk_biz_id       | int     | BlueKing Business ID                                                                                   |
| bk_biz_scope    | int     | List of BlueKing Business IDs                                                                          |
| node_type       | string  | Node type: `TOPO` (dynamic topology), `INSTANCE` (static instance), `SERVICE_TEMPLATE`, `SET_TEMPLATE` |
| object_type     | string  | Object type: `HOST` (host), `SERVICE` (service)                                                        |
| need_register   | bool    | Whether to register to CMDB: `false` = no registration, `true` = registration. Default is `false`.     |
| nodes           | object  | List of nodes. See `nodes` definition                                                                  |

##### config

| Field                  | Type   | Description                                                                                                                                                                    |
|------------------------|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| plugin_name            | string | Name of the plugin                                                                                                                                                             |
| plugin_version         | string | Plugin version. Use `"latest"` if version is not specified                                                                                                                     |
| config_templates       | object | List of configuration templates. See `config_templates` definition                                                                                                             |
| job_type               | string | Job type. Official plugins use multi-config management; install/uninstall operations are handled via configuration changes                                                     |
| check_and_skip         | bool   | Whether to skip installation if plugin already exists: `true` = skip if same version; reinstall if version differs; `false` = ignore version mismatch, ensure process is alive |
| is_version_sensitive   | bool   | Whether to strictly enforce version match during installation                                                                                                                  |

###### config_templates

| Field       | Type     | Description                                                  |
|-------------|----------|--------------------------------------------------------------|
| name        | string   | Configuration file name                                      |
| version     | string   | Version of the configuration template                        |
| is_main     | bool     | Whether it is the main configuration                         |
| os          | string   | Operating system: `linux`, `windows`, `aix`, `solaris`       |
| cpu_arch    | string   | CPU architecture: `x86`, `x86_64`, `powerpc`, `aarch64`, `sparc` |

###### params

| Field          | Type   | Description                                                                        |
|----------------|--------|------------------------------------------------------------------------------------|
| port_range     | string | Port range used by the plugin                                                      |
| context        | object | Context variables for rendering configuration files                                |
| keep_config    | bool   | Whether to preserve existing configuration files                                   |
| no_restart     | bool   | Whether to update files only without restarting the process. Default is `false`.   |

###### nodes

| Field                 | Type      | Description                                            |
|-----------------------|-----------|--------------------------------------------------------|
| bk_supplier_account   | int       | Supplier account ID                                    |
| bk_cloud_id           | int       | Cloud area (ap_id) ID                                  |
| ip                    | string    | Host IP address                                        |
| bk_host_id            | int       | Host ID in CMDB                                        |
| bk_biz_id             | int       | Business ID                                            |
| bk_inst_id            | int       | Instance ID                                            |
| bk_obj_id             | string    | Object ID (e.g., module, set)                          |
| instance_info         | object    | Host instance information. See `instance_info` below   |

##### instance_info

| Field                             | Type    | Description                                                                  |
|-----------------------------------|---------|------------------------------------------------------------------------------|
| key                               | string  | SSH private key content                                                      |
| port                              | string  | Installation port                                                            |
| ap_id                             | int     | Access point ID                                                              |
| account                           | string  | Login username                                                               |
| os_type                           | string  | OS type: `linux`, `windows`, `aix`, `solaris`                                |
| login_ip                          | string  | Login IP address                                                             |
| data_ip                           | string  | Data transmission IP                                                         |
| inner_ip                          | string  | Internal IPv4 address                                                        |
| inner_ipv6                        | string  | Internal IPv6 address                                                        |
| outer_ip                          | string  | External IPv4 address                                                        |
| outer_ipv6                        | string  | External IPv6 address                                                        |
| password                          | string  | Password (encrypted)                                                         |
| username                          | string  | System user for execution                                                    |
| auth_type                         | string  | Authentication type: `password`, `key`, `tjj_password` (default: `password`) |
| bk_biz_id                         | int     | Business ID                                                                  |
| is_manual                         | bool    | Whether installed manually                                                   |
| retention                         | string  | Password retention duration (days). Default: 1 day                           |
| bk_os_type                        | string  | OS type: `linux`, `windows`, `aix`, `solaris` (same as `os_type`)            |
| bk_biz_name                       | string  | Business name                                                                |
| bk_cloud_id                       | int     | Cloud area ID                                                                |
| bk_cloud_name                     | string  | Cloud area name                                                              |
| bt_speed_limit                    | string  | File transfer speed limit (KB/s)                                             |
| host_node_type                    | string  | Host node type: `agent`, `pagent`, `proxy`                                   |
| bk_host_innerip                   | string  | Internal IP of the host                                                      |
| bk_host_outerip                   | string  | External IP of the host                                                      |
| install_channel_id                | int     | Installation channel ID                                                      |
| bk_supplier_account               | int     | Supplier account                                                             |
| peer_exchange_switch_for_agent    | int     | P2P acceleration switch (0: off, 1: on)                                      |
| data_path                         | string  | Custom data directory path. Default is false                                 |
| enable_compression                | bool    | Enable data compression during transmission. Default is false                |
