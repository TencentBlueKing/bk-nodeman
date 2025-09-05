### 功能描述

查询接入点列表

### 请求参数

{{ common_args_desc }}

#### 接口参数


### 请求参数示例

```json
{}
```

### 返回结果示例

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

### 返回结果参数说明

#### response

| 字段      | 类型      | 描述                         |
| ------- |---------| -------------------------- |
| result  | bool    | 请求成功与否。true:请求成功；false请求失败 |
| code    | int     | 错误编码。 0表示success，>0表示失败错误  |
| message | string  | 请求失败返回的错误信息                |
| data    | array   | 请求返回的数据，见data定义            |

