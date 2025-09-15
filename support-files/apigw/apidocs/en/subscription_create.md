### Function Description

Create subscription

### Request Parameters

#### Interface Parameters

| Field             | Type         | <div style="width: 50pt">Required</div> | Description                                                                                                                                                             |
|-------------------|--------------|-----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| name              | string       | No                                      | Subscription name                                                                                                                                                       |
| scope             | object       | Yes                                     | Event subscription monitoring scope, see scope definition                                                                                                               |
| steps             | object       | Yes                                     | List of actions triggered by the event subscription                                                                                                                     |
| target_hosts      | object       | No                                      | Target host list for plugin deployment, used in remote collection scenarios. Host configurations within scope will be deployed to corresponding hosts within this range |
| run_immediately   | bool         | No                                      | Whether to execute immediately                                                                                                                                          |
| is_main           | bool         | No                                      | Whether it is the main configuration                                                                                                                                    |
| plugin_name       | string       | No                                      | Plugin name                                                                                                                                                             |
| bk_biz_scope      | int array    | No                                      | Business ID list monitored by the subscription, containing relevant business IDs                                                                                        |
| category          | string       | No                                      | Subscription category: 1: debug, debugging; 2: once, one-time subscription                                                                                              |
| pid               | int          | No                                      | Parent policy ID, defaults to -1 if not specified                                                                                                                       |

#### steps

| Field     | Type      | <div style="width: 50pt">Required</div> | Description                               |
|-----------|-----------|-----------------------------------------|-------------------------------------------|
| id        | string    | Yes                                     | Step identifier                           |
| type      | string    | Yes                                     | Step type: 1: AGENT, 2: PLUGIN, 3: PROXY  |
| config    | object    | Yes                                     | Step configuration, see config definition |
| params    | object    | Yes                                     | Step parameters, see params definition    |

#### scope

| Field              | Type         | Required   | Description                                                                                                                                           |
|--------------------|--------------|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| bk_biz_id          | int          | No         | BlueKing business ID                                                                                                                                  |
| bk_biz_scope       | int array    | No         | BlueKing business ID list                                                                                                                             |
| node_type          | string       | Yes        | Node type: 1: TOPO (dynamic instance/topology), 2: INSTANCE (static instance), 3: SERVICE_TEMPLATE (service template), 4: SET_TEMPLATE (set template) |
| object_type        | string       | Yes        | Object type: 1: HOST (host type), 2: SERVICE (service type)                                                                                           |
| need_register      | bool         | No         | Whether to register to CMDB: false means no registration, true means registration. Default is no registration                                         |
| nodes              | objects      | Yes        | Node list, see nodes definition                                                                                                                       |
| instance_selector  | objects      | No         | Host attribute filter list                                                                                                                            |

##### config

| Field                    | Type      | Required | Description                                                                                                                                                                                                    |
|--------------------------|-----------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| plugin_name              | string    | No       | Plugin name                                                                                                                                                                                                    |
| plugin_version           | string    | No       | Plugin version. If the specific version is uncertain, specify as "latest"                                                                                                                                      |
| config_templates         | objects   | No       | Configuration template list, see config_templates definition                                                                                                                                                   |
| job_type                 | string    | No       | Job type. Official plugins use a multi-configuration management model. Operations like install, uninstall, enable, disable involve only adding or removing configurations. See job_type definition for details |
| check_and_skip           | bool      | No       | For installing the main plugin, supports checking existence and skipping: 1: true, install when versions differ; 2: false, ignore version differences, ensure process is alive                                 |
| is_version_sensitive     | bool      | No       | Whether to strictly verify the installation version                                                                                                                                                            |

###### config_templates

| Field      | Type    | Required | Description                                                              |
|------------|---------|----------|--------------------------------------------------------------------------|
| name       | string  | Yes      | Configuration file name                                                  |
| version    | string  | Yes      | Configuration file version                                               |
| is_main    | bool    | No       | Whether it is the main configuration                                     |
| os         | string  | No       | Operating system: 1: LINUX, 2: WINDOWS, 3: AIX, 4: SOLARIS               |
| cpu_arch   | string  | No       | CPU architecture: 1: x86, 2: x86_64, 3: powerpc, 4: aarch64, 5: sparc    |

###### params

| Field          | Type   | Required  | Description                                                                    |
|----------------|--------|-----------|--------------------------------------------------------------------------------|
| port_range     | string | No        | Port range                                                                     |
| context        | object | No        | Configuration file rendering context                                           |
| keep_config    | bool   | No        | Whether to retain existing configuration files                                 |
| no_restart     | bool   | No        | Whether to update files only without restarting the process. Default is false  |

###### nodes

| Field                 | Type       | Required | Description                                                    |
|-----------------------|------------|----------|----------------------------------------------------------------|
| bk_supplier_account   | int        | No       | Supplier ID                                                    |
| bk_cloud_id           | int        | No       | Cloud area ID                                                  |
| ip                    | string     | No       | Host IP address                                                |
| bk_host_id            | int        | No       | Host ID                                                        |
| bk_biz_id             | int        | No       | Business ID                                                    |
| bk_inst_id            | int        | No       | Instance ID                                                    |
| bk_obj_id             | int        | No       | Object ID                                                      |
| instance_info         | object     | No       | Host instance information, see instance_info definition        |

###### instance_info

| Field                             | Type       | Required  | Description                                                                                                                                  |
|-----------------------------------|------------|-----------|----------------------------------------------------------------------------------------------------------------------------------------------|
| key                               | string     | No        | Secret key                                                                                                                                   |
| port                              | string     | No        | Installation port                                                                                                                            |
| ap_id                             | int        | No        | Access point ID                                                                                                                              |
| account                           | string     | No        | Login user                                                                                                                                   |
| os_type                           | string     | No        | Operating system: 1: LINUX, 2: WINDOWS, 3: AIX, 4: SOLARIS                                                                                   |
| login_ip                          | string     | No        | Login IP address                                                                                                                             |
| data_ip                           | string     | No        | Data IP address                                                                                                                              |
| inner_ip                          | string     | No        | Internal IPv4 address. Either `inner_ip` or `inner_ipv6` must be provided                                                                    |
| inner_ipv6                        | string     | No        | Internal IPv6 address                                                                                                                        |
| outer_ip                          | string     | No        | External IP address                                                                                                                          |
| outer_ipv6                        | string     | No        | External IPv6 address                                                                                                                        |
| password                          | string     | No        | Password                                                                                                                                     |
| username                          | string     | No        | Operation user                                                                                                                               |
| auth_type                         | string     | No        | Authentication type: 1: PASSWORD (password authentication), 2: KEY (key authentication), 3: TJJ_PASSWORD. Default is password authentication |
| bk_biz_id                         | int        | No        | Business ID                                                                                                                                  |
| is_manual                         | bool       | No        | Whether it is manual installation                                                                                                            |
| retention                         | string     | No        | Password retention days, default is 1 day                                                                                                    |
| bk_os_type                        | string     | No        | Operating system: 1: LINUX, 2: WINDOWS, 3: AIX, 4: SOLARIS                                                                                   |
| bk_biz_name                       | string     | No        | Business name                                                                                                                                |
| bk_cloud_id                       | int        | No        | Cloud area ID                                                                                                                                |
| bk_cloud_name                     | string     | No        | Cloud area name                                                                                                                              |
| bt_speed_limit                    | string     | No        | Transfer speed limit                                                                                                                         |
| host_node_type                    | string     | No        | Host node type: 1: AGENT, 2: PAGENT, 3: PROXY                                                                                                |
| bk_host_innerip                   | string     | No        | Host internal IP address                                                                                                                     |
| bk_host_outerip                   | string     | No        | Host external IP address                                                                                                                     |
| install_channel_id                | int        | No        | Installation channel ID                                                                                                                      |
| bk_supplier_account               | int        | No        | Supplier ID                                                                                                                                  |
| peer_exchange_switch_for_agent    | int        | No        | Acceleration setting, default is off                                                                                                         |
| enable_compression                | bool       | No        | Data compression switch, default is off                                                                                                      |
| data_path                         | string     | No        | Data file path                                                                                                                               |


###### instance_selector

| Field   | Type     | Required  | Description                    |
|---------|----------|-----------|--------------------------------|
| key     | string   | No        | Host attribute                 |
| value   | string   | No        | List of host attribute values  |

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
    "run_immediately": true,
    "scope": {
        "instance_selector": [{"key": "os_type", "value": ["LINUX"]}],
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
                    "peer_exchange_switch_for_agent": 1,
                    "enable_compression": false
                },
                "bk_supplier_account": "0"
            }
        ]
    },
    "target_hosts": [
        {
            "ip": "127.0.0.1",
            "bk_cloud_id": 0,
            "bk_supplier_id": 0
        }
    ],
    "steps": [
        {
            "id": "agent",
            "type": "AGENT",
            "config": {
                "job_type": "INSTALL_AGENT"
            },
            "params": {
                "context": {

                },
                "blueking_language": "zh-hans"
            }
        },
        {
            "id": "main:bkunifylogbeat",
            "type": "PLUGIN",
            "config": {
                "job_type": "MAIN_INSTALL_PLUGIN",
                "check_and_skip": true,
                "is_version_sensitive": false,
                "plugin_name": "bkunifylogbeat",
                "plugin_version": "latest",
                "config_templates": [
                    {
                        "name": "bkunifylogbeat.conf",
                        "version": "latest",
                        "is_main": true
                    }
                ]
            },
            "params": {
                "context": {

                }
            }
        },
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

| Field   | Type     | Description                                                            |
|---------|----------|------------------------------------------------------------------------|
| result  | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code    | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message | string   | Error message returned when the request fails                          |
| data    | object   | Data returned by the request, see definition below                     |

#### data

| Field            | Type | Description     |
|------------------|------|-----------------|
| subscription_id  | int  | Subscription ID |
| task_id          | int  | Task ID         |
