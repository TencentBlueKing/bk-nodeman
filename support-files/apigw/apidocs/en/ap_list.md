### Function Description

Query access point list

### Request Parameters

#### Interface Parameters

### Request Example

```json
{}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "id": 1,
            "name": "默认接入点",
            "ap_type": "system",
            "region_id": "test",
            "city_id": "test",
            "btfileserver": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.1"
                }
            ],
            "dataserver": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.1"
                }
            ],
            "taskserver": [
                {
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.1"
                }
            ],
            "zk_hosts": [
                {
                    "zk_ip": "bk-zookeeper",
                    "zk_port": "2181"
                }
            ],
            "zk_account": "bkzk",
            "package_inner_url": "https://xxx.com/bknodeman/download",
            "package_outer_url": "https://xxx.com/bknodeman/download",
            "agent_config": {
                "linux": {
                    "dataipc": "/usr/local/gse2_tenant/agent/data/ipc.state.report",
                    "log_path": "/var/log/gse2_tenant",
                    "run_path": "/var/run/gse2_tenant",
                    "data_path": "/var/lib/gse2_tenant",
                    "pluginipc": "/usr/local/gse2_tenant/agent/lib/ipc.state.message",
                    "temp_path": "/tmp",
                    "setup_path": "/usr/local/gse2_tenant",
                    "hostid_path": "/var/lib/bktenant/host/hostid",
                    "alarm_event_data_id": 1000
                },
                "windows": {
                    "dataipc": "47000",
                    "log_path": "C:\\gse2_tenant\\logs",
                    "run_path": "C:\\gse2_tenant\\data",
                    "data_path": "C:\\gse2_tenant\\data",
                    "pluginipc": 26002,
                    "temp_path": "C:\\Temp",
                    "setup_path": "C:\\gse2_tenant",
                    "hostid_path": "C:\\bktenant\\data\\host\\hostid",
                    "alarm_event_data_id": 1000
                }
            },
            "status": null,
            "description": "GSE默认接入点",
            "is_enabled": true,
            "is_default": true,
            "proxy_package": [
                "gse_client-windows-x86.tgz",
                "gse_client-windows-x86_64.tgz",
                "gse_client-linux-x86.tgz",
                "gse_client-linux-x86_64.tgz",
                "gse_client-aix6-powerpc.tgz",
                "gse_client-aix7-powerpc.tgz"
            ],
            "file_cache_dirs": "/data/gse2_tenant/file_cache",
            "gse_version": "V2",
            "nginx_path": "",
            "creator": [
                "admin"
            ],
            "port_config": {
                "bt_port": 20020,
                "io_port": 28668,
                "data_port": 28625,
                "proc_port": 50000,
                "trunk_port": 48331,
                "bt_port_end": 60030,
                "tracker_port": 20030,
                "bt_port_start": 60020,
                "db_proxy_port": 58817,
                "file_svr_port": 28925,
                "api_server_port": 50002,
                "file_svr_port_v1": 58926,
                "agent_thrift_port": 48669,
                "btsvr_thrift_port": 58931,
                "data_prometheus_port": 29402,
                "file_metric_bind_port": 29404,
                "file_topology_bind_port": 28930
            },
            "outer_callback_url": "",
            "callback_url": "",
            "permissions": {
                "edit": false,
                "delete": false,
                "view": false
            }
        }
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Tpye   | Description                                                            |
|----------|--------|------------------------------------------------------------------------|
| result   | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code     | int    | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string | Error message returned when the request fails                          |
| data     | array  | Data returned by the request, see definition below                     |

#### data

| Field                  | Type       | Description                                                    |
|------------------------|------------|----------------------------------------------------------------|
| id                     | int        | Access point ID                                                |
| name                   | string     | Access point name                                              |
| ap_type                | string     | Access point type                                              |
| region_id              | string     | Region ID                                                      |
| city_id                | string     | City ID                                                        |
| btfileserver           | array      | List of GSE BT file servers, see `btfileserver` definition     |
| dataserver             | array      | List of GSE data servers, see `dataserver` definition          |
| taskserver             | array      | List of GSE task servers, see `taskserver` definition          |
| zk_hosts               | array      | List of ZK servers, see `zk_hosts` definition                  |
| zk_account             | string     | ZK account                                                     |
| package_inner_url      | string     | Internal network URL for installation packages                 |
| package_outer_url      | string     | External network URL for installation packages                 |
| agent_config           | object     | Agent configuration information, see `agent_config` definition |
| status                 | string     | Access point status                                            |
| description            | string     | Description of the access point                                |
| is_enabled             | bool       | Whether enabled                                                |
| is_default             | bool       | Whether it is the default access point (cannot be deleted)     |
| proxy_package          | array      | Installation packages on Proxy                                 |
| file_cache_dirs        | string     | File cache directory                                           |
| gse_version            | string     | GSE version                                                    |
| nginx_path             | string     | Nginx path                                                     |
| creator                | array      | Creator(s) of the access point                                 |
| port_config            | object     | GSE port configuration, see `port_config` definition           |
| outer_callback_url     | string     | NodeMan external callback URL                                  |
| callback_url           | string     | NodeMan internal callback URL                                  |
| permissions            | object     | Operation permissions, see `permissions`                       |

##### btfileserver

| Field       | Type     | Description                                |
|-------------|----------|--------------------------------------------|
| inner_ip    | string   | Internal IP address of GSE BT file server  |
| outer_ip    | string   | External IP address of GSE BT file server  |

##### dataserver

| Field       | Type     | Description                               |
|-------------|----------|-------------------------------------------|
| inner_ip    | string   | Internal IP address of GSE data server    |
| outer_ip    | string   | External IP address of GSE data server    |

##### taskserver

| Field       | Type     | Description                              |
|-------------|----------|------------------------------------------|
| inner_ip    | string   | Internal IP address of GSE task server   |
| outer_ip    | string   | External IP address of GSE task server   |

##### zk_hosts

| Field       | Type     | Description                        |
|-------------|----------|------------------------------------|
| zk_ip       | string   | IP address of the ZK server        |
| zk_port     | string   | Port of the ZK server              |

##### agent_config

| Field                   | Type     | Description                                       |
|-------------------------|----------|---------------------------------------------------|
| dataipc                 | string   | IPC communication channel path for data reporting |
| log_path                | string   | Log file path                                     |
| run_path                | string   | Runtime data path                                 |
| data_path               | string   | Data file storage path                            |
| pluginipc               | string   | IPC communication channel path for plugins        |
| temp_path               | string   | Temporary file path                               |
| setup_path              | string   | Binary file installation path                     |
| hostid_path             | string   | File path for host_id                             |
| alarm_event_data_id     | int      | Data ID for alarm/event reporting                 |

##### port_config

| Field                         | Type  | Description                                           |
|-------------------------------|-------|-------------------------------------------------------|
| bt_port                       | int   | BT file transfer port                                 |
| io_port                       | int   | IO channel port                                       |
| data_port                     | int   | Data reporting port                                   |
| proc_port                     | int   | Process management port                               |
| trunk_port                    | int   | Main control channel port                             |
| bt_port_end                   | int   | End value of BT port range                            |
| tracker_port                  | int   | BT Tracker service port                               |
| bt_port_start                 | int   | Start value of BT port range                          |
| db_proxy_port                 | int   | Database proxy port                                   |
| file_svr_port                 | int   | File server port                                      |
| api_server_port               | int   | Local API service port                                |
| file_svr_port_v1              | int   | File server port (v1)                                 |
| agent_thrift_port             | int   | Agent Thrift RPC port                                 |
| btsvr_thrift_port             | int   | BT service Thrift port                                |
| data_prometheus_port          | int   | Prometheus metrics exposure port                      |
| file_metric_bind_port         | int   | File service metrics listening port                   |
| file_topology_bind_port       | int   | File topology communication port                      |

##### permissions

| Permission Type | Type | Description       |
|-----------------|------|-------------------|
| view            | bool | View permission   |
| edit            | bool | Edit permission   |
| delete          | bool | Delete permission |

