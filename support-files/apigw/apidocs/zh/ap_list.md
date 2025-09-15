### 功能描述

查询接入点列表

### 请求参数

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

#### data

| 字段                 | 类型       | 描述                            |
|--------------------|----------|-------------------------------|
| id                 | int      | 接入点ID                         |
| name               | string   | 接入点名称                         |
| ap_type            | string   | 接入点类型                         |
| region_id          | string   | 区域id                          |
| city_id            | string   | 城市id                          |
| btfileserver       | array    | GSE BT文件服务器列表，见btfileserver定义 |
| dataserver         | array    | GSE 数据服务器列表，见dataserver定义     |
| taskserver         | array    | GSE 任务服务器列表，见taskserver定义     |
| zk_hosts           | array    | ZK服务器列表，见zk_hosts定义           |
| zk_account         | string   | ZK账号                          |
| package_inner_url  | string   | 安装包内网地址                       |
| package_outer_url  | string   | 安装包外网地址                       |
| agent_config       | object   | Agent配置信息                     |
| status             | string   | 接入点状态                         |
| description        | string   | 接入点描述                         |
| is_enabled         | bool     | 是否启用                          |
| is_default         | bool     | 是否默认接入点，不可删除                  |
| proxy_package      | array    | Proxy上的安装包                    |
| file_cache_dirs    | string   | 文件缓存目录                        |
| gse_version        | string   | GSE 版本                        |
| nginx_path         | string   | Nginx路径                       |
| creator            | array    | 接入点创建者                        |
| port_config        | object   | GSE端口配置，见port_config定义        |
| outer_callback_url | string   | 节点管理外网回调地址                    |
| callback_url       | string   | 节点管理内网回调地址                    |
| permissions        | object   | 对应操作权限，见permissions定义         |

##### btfileserver

| 字段          | 类型      | 描述              |
|-------------|---------|-----------------|
| inner_ip    | string  | GSE BT文件服务器内网IP |
| outer_ip    | string  | GSE BT文件服务器外网IP |

##### dataserver

| 字段           | 类型      | 描述              |
|--------------|---------|-----------------|
| inner_ip     | string  | GSE 数据服务器内网IP   |
| outer_ip     | string  | GSE 数据服务器外网IP   |

##### taskserver

| 字段           | 类型        | 描述              |
|--------------|-----------|-----------------|
| inner_ip     | string    | GSE 任务服务器内网IP   |
| outer_ip     | string    | GSE 任务服务器外网IP   |

##### zk_hosts

| 字段         | 类型      | 描述        |
|------------|---------|-----------|
| zk_ip      | string  | ZK服务器IP地址 |
| zk_port    | string  | ZK服务器端口   |

##### agent_config

| 字段                   | 类型     | 描述                |
|----------------------|--------|-------------------|
| dataipc              | string | 数据上报 IPC 通信通道文件路径 |
| log_path             | string | 日志路径              |
| run_path             | string | 运行时数据路径           |
| data_path            | string | 数据文件路径            |
| pluginipc            | string | 插件通信 IPC 通道文件路径   |
| temp_path            | string | 临时文件路径            |
| setup_path           | string | 二进制文件所在路径         |
| hostid_path          | string | host_id 文件路径      |
| alarm_event_data_id  | int    | 告警/事件上报数据 ID      |

##### port_config

| 字段                        | 类型  | 描述                  |
|---------------------------|-----|---------------------|
| bt_port                   | int | BT 文件传输端口           |
| io_port                   | int | IO 通道端口             |
| data_port                 | int | 数据上报端口              |
| proc_port                 | int | 进程管理端口              |
| trunk_port                | int | 主控通道端口              |
| bt_port_end               | int | BT 端口范围结束值          |
| tracker_port              | int | BT Tracker 服务端口     |
| bt_port_start             | int | BT 端口范围起始值          |
| db_proxy_port             | int | 数据库代理端口             |
| file_svr_port             | int | 文件服务端口              |
| api_server_port           | int | 本地 API 服务端口         |
| file_svr_port_v1          | int | 文件服务端口              |
| agent_thrift_port         | int | Agent Thrift RPC 端口 |
| btsvr_thrift_port         | int | BT 服务 Thrift 端口     |
| data_prometheus_port      | int | Prometheus 数据暴露端口   |
| file_metric_bind_port     | int | 文件服务指标监听端口          |
| file_topology_bind_port   | int | 文件拓扑通信端口            |

##### permissions

| 状态类型   | 类型   | 描述   |
| ------ | ---- | ---- |
| view   | bool | 查看权限 |
| edit   | bool | 编辑权限 |
| delete | bool | 删除权限 |