### Function Description

Task execution detailed result

### Request Parameters

#### Interface Parameters

| Field           | Type         | <div style="width: 50pt">Required</div> | Description                                         |
|-----------------|--------------|-----------------------------------------|-----------------------------------------------------|
| subscription_id | int          | Yes                                     | Subscription ID                                     |
| task_id         | int          | No                                      | Specific task ID to query                           |
| task_id_list    | int array    | No                                      | List of task IDs to retrieve details for            |
| instance_id     | string       | Yes                                     | Instance ID for which to retrieve execution details |


### Request Example

```json
{
    "subscription_id": 864317,
    "instance_id": "host|instance|host|10.0.0.3-0",
    "task_id_list": [
        374776866
    ]
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "task_id": 37699070,
        "record_id": 16808245,
        "instance_id": "host|instance|host|10.0.0.3-0-0",
        "create_time": "2025-08-30 22:50:51",
        "pipeline_id": "6fd6f30c27644005b91e13610eb47ba7",
        "instance_info": {
            "host": {
                "key": "",
                "port": 36000,
                "ap_id": 8,
                "ticket": null,
                "account": "root",
                "data_ip": null,
                "os_type": "LINUX",
                "inner_ip": "10.0.0.3",
                "login_ip": null,
                "password": "",
                "username": "xxxx",
                "auth_type": "PASSWORD",
                "bk_biz_id": 639,
                "is_manual": false,
                "retention": 1,
                "bk_host_id": 5867355,
                "bk_os_type": "1",
                "inner_ipv6": null,
                "outer_ipv6": null,
                "bk_biz_name": "测试业务",
                "bk_cloud_id": 0,
                "bk_addressing": "static",
                "bk_cloud_name": "直连区域",
                "is_use_ap_map": false,
                "bt_speed_limit": null,
                "host_node_type": "AGENT",
                "bk_host_innerip": "10.0.0.3",
                "bk_host_outerip": "",
                "bk_host_innerip_v6": null,
                "bk_host_outerip_v6": null,
                "enable_compression": false,
                "install_channel_id": null,
                "bk_supplier_account": "tencent",
                "is_need_inject_ap_id": false,
                "force_update_agent_id": false,
                "agent_setup_extra_info": {
                    "force_update_agent_id": false
                },
                "peer_exchange_switch_for_agent": 0
            },
            "meta": {
                "GSE_VERSION": "V2"
            }
        },
        "start_time": "2025-08-30 22:50:52",
        "finish_time": "2025-08-30 22:51:30",
        "steps": [
            {
                "id": "agent",
                "type": "AGENT",
                "index": 0,
                "action": "INSTALL_AGENT_2",
                "node_name": "[agent] 安装",
                "extra_info": {},
                "pipeline_id": "17b41450da974d26950f766d57fc6f74",
                "status": "FAILED",
                "start_time": "2025-08-30 22:50:52",
                "finish_time": "2025-08-30 22:51:30",
                "target_hosts": [
                    {
                        "node_name": "[agent] 安装 0:127.0.0.1",
                        "pipeline_id": "17b41450da974d26950f766d57fc6f74",
                        "status": "FAILED",
                        "start_time": "2025-08-30 22:50:52",
                        "finish_time": "2025-08-30 22:51:30",
                        "sub_steps": [
                            {
                                "index": 0,
                                "node_name": "新增或更新主机信息",
                                "step_code": "add_or_update_hosts",
                                "pipeline_id": "17b41450da974d26950f766d57fc6f74",
                                "log": "[2025-08-30 22:50:52 INFO] 开始 新增或更新主机信息.\n[2025-08-30 22:50:52 INFO] 更新 CMDB 主机信息:\n {\n  \"bk_host_id\": 5867355,\n  \"properties\": {\n    \"bk_host_innerip\": \"10.0.0.3\",\n    \"bk_os_type\": \"1\"\n  }\n}\n[2025-08-30 22:50:55 INFO] 新增或更新主机信息 成功",
                                "ex_data": null,
                                "status": "SUCCESS",
                                "start_time": "2025-08-30 22:50:52",
                                "finish_time": "2025-08-30 22:50:55"
                            },
                            {
                                "index": 1,
                                "node_name": "查询主机密码",
                                "step_code": "query_password",
                                "pipeline_id": "6e2285f848624efd9c902ab0d928b052",
                                "log": "[2025-08-30 22:50:55 INFO] 开始 查询主机密码.\n[2025-08-30 22:50:56 INFO] 当前主机验证Type无需查询密码\n[2025-08-30 22:50:56 INFO] 查询主机密码 成功",
                                "ex_data": null,
                                "status": "SUCCESS",
                                "start_time": "2025-08-30 22:50:55",
                                "finish_time": "2025-08-30 22:50:56"
                            },
                            {
                                "index": 2,
                                "node_name": "选择接入点",
                                "step_code": "choose_access_point",
                                "pipeline_id": "c161a8f3953c4bcd8fd76c86e46e403c",
                                "log": "[2025-08-30 22:50:56 INFO] 开始 选择接入点.\n[2025-08-30 22:50:56 INFO] 当前主机已分配接入点 [GSE2_内网接入点]\n[2025-08-30 22:50:56 INFO] 选择接入点 成功",
                                "ex_data": null,
                                "status": "SUCCESS",
                                "start_time": "2025-08-30 22:50:56",
                                "finish_time": "2025-08-30 22:50:56",
                                "inputs": {
                                    "instance_info": {
                                        "host": {
                                            "key": "",
                                            "port": 36000,
                                            "ap_id": 8,
                                            "ticket": null,
                                            "account": "root",
                                            "data_ip": null,
                                            "os_type": "LINUX",
                                            "inner_ip": "10.0.0.3",
                                            "login_ip": null,
                                            "password": "",
                                            "username": "xxxx",
                                            "auth_type": "PASSWORD",
                                            "bk_biz_id": 639,
                                            "is_manual": false,
                                            "retention": 1,
                                            "bk_host_id": 5867355,
                                            "bk_os_type": "1",
                                            "inner_ipv6": null,
                                            "outer_ipv6": null,
                                            "bk_biz_name": "测试业务",
                                            "bk_cloud_id": 0,
                                            "bk_addressing": "static",
                                            "bk_cloud_name": "直连区域",
                                            "is_use_ap_map": false,
                                            "bt_speed_limit": null,
                                            "host_node_type": "AGENT",
                                            "bk_host_innerip": "10.0.0.3",
                                            "bk_host_outerip": "",
                                            "bk_host_innerip_v6": null,
                                            "bk_host_outerip_v6": null,
                                            "enable_compression": false,
                                            "install_channel_id": null,
                                            "bk_supplier_account": "tencent",
                                            "is_need_inject_ap_id": false,
                                            "force_update_agent_id": false,
                                            "agent_setup_extra_info": {
                                                "force_update_agent_id": false
                                            },
                                            "peer_exchange_switch_for_agent": 0
                                        },
                                        "meta": {
                                            "GSE_VERSION": "V2"
                                        }
                                    }
                                }
                            },
                            {
                                "index": 3,
                                "node_name": "安装",
                                "step_code": "install",
                                "pipeline_id": "39d4faffbea845a6ab32edac5dd40ad1",
                                "log": "[2025-08-30 22:50:56 INFO] 开始 安装.\n[2025-08-30 22:50:56 INFO] 选择的安装通道为: 默认通道\n[2025-08-30 22:50:58 ERROR] [3803007] 远程连接失败：[Errno 111] Connect call failed ('10.0.0.3', 36000)\n[2025-08-30 22:50:58 DEBUG] ******* Begin of collected logs: *******\nTraceback (most recent call last):\n  File \"/app/apps/core/remote/conns/asyncssh_impl.py\", line 63, in connect\n    **self.options\n  File \"/venv/lib/python3.6/site-packages/asyncssh/connection.py\", line 6895, in connect\n    timeout=options.connect_timeout)\n  File \"/usr/local/lib/python3.6/asyncio/tasks.py\", line 358, in wait_for\n    return fut.result()\n  File \"/venv/lib/python3.6/site-packages/asyncssh/connection.py\", line 300, in _connect\n    local_addr=local_addr)\n  File \"/usr/local/lib/python3.6/asyncio/base_events.py\", line 798, in create_connection\n    raise exceptions[0]\n  File \"/usr/local/lib/python3.6/asyncio/base_events.py\", line 785, in create_connection\n    yield from self.sock_connect(sock, address)\n  File \"/usr/local/lib/python3.6/asyncio/selector_events.py\", line 439, in sock_connect\n    return (yield from fut)\n  File \"/usr/local/lib/python3.6/asyncio/selector_events.py\", line 469, in _sock_connect_cb\n    raise OSError(err, 'Connect call failed %s' % (address,))\nConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 36000)\n\nThe above exception was the direct cause of the following exception:\n\nTraceback (most recent call last):\n  File \"/venv/lib/python3.6/site-packages/asgiref/sync.py\", line 482, in thread_handler\n    raise exc_info[1]\n  File \"/app/apps/utils/exc.py\", line 68, in wrapped_async_executor\n    result = await wrapped(*args, **kwargs)\n  File \"/app/apps/prometheus/helper.py\", line 105, in wrapped_async_executor\n    result = await wrapped(*args, **kwargs)\n  File \"/app/apps/backend/components/collections/agent_new/install.py\", line 693, in execute_shell_solution_async\n    async with conns.AsyncsshConn(**install_sub_inst_obj.conns_init_params) as conn:\n  File \"/app/apps/core/remote/conns/asyncssh_impl.py\", line 122, in __aenter__\n    await self.connect()\n  File \"/app/apps/core/remote/conns/asyncssh_impl.py\", line 74, in connect\n    raise exceptions.DisconnectError({\"err_msg\": e}) from e\napps.core.remote.exceptions.DisconnectError: [3803007] 远程连接失败：[Errno 111] Connect call failed ('127.0.0.1', 36000)\n\n******** End of collected logs *********\n[2025-08-30 22:51:30 ERROR] 安装 失败，请先尝试查看日志并处理，若无法解决，请联系管理员处理。",
                                "ex_data": null,
                                "status": "FAILED",
                                "start_time": "2025-08-30 22:50:56",
                                "finish_time": "2025-08-30 22:51:30"
                            },
                            {
                                "index": 4,
                                "node_name": "绑定主机 Agent 信息",
                                "step_code": "bind_host_agent",
                                "pipeline_id": "8e075d0cac7b40e4a9644fcaae9237de",
                                "log": "",
                                "ex_data": null,
                                "status": "PENDING",
                                "start_time": null,
                                "finish_time": null
                            },
                            {
                                "index": 5,
                                "node_name": "升级为 Agent-ID 配置",
                                "step_code": "upgrade_to_agent_id",
                                "pipeline_id": "f7100d038a9c49a0aefddb93ac30e9e8",
                                "log": "",
                                "ex_data": null,
                                "status": "PENDING",
                                "start_time": null,
                                "finish_time": null
                            },
                            {
                                "index": 6,
                                "node_name": "查询Agent状态",
                                "step_code": "get_agent_status",
                                "pipeline_id": "e0efb1779c2b4bfabd6bd190d6f7244d",
                                "log": "",
                                "ex_data": null,
                                "status": "PENDING",
                                "start_time": null,
                                "finish_time": null
                            },
                            {
                                "index": 7,
                                "node_name": "推送主机身份信息",
                                "step_code": "push_host_identifier",
                                "pipeline_id": "20b8fc7629494915a1fdd1d2756e5cb0",
                                "log": "",
                                "ex_data": null,
                                "status": "PENDING",
                                "start_time": null,
                                "finish_time": null
                            },
                            {
                                "index": 8,
                                "node_name": "推送环境变量文件",
                                "step_code": "push_environ_files",
                                "pipeline_id": "31d5fc6fee66475f98bf1b64fabcee5c",
                                "log": "",
                                "ex_data": null,
                                "status": "PENDING",
                                "start_time": null,
                                "finish_time": null
                            },
                            {
                                "index": 9,
                                "node_name": "安装预设插件",
                                "step_code": "install_plugins",
                                "pipeline_id": "501d6af8ee9d4cec93e7117ae14be32a",
                                "log": "",
                                "ex_data": null,
                                "status": "PENDING",
                                "start_time": null,
                                "finish_time": null
                            }
                        ]
                    }
                ]
            }
        ],
        "status": "FAILED"
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

| Field           | Type      | Description                                                 |
|-----------------|-----------|-------------------------------------------------------------|
| task_id         | int       | Task ID                                                     |
| record_id       | int       | Record ID                                                   |
| instance_id     | string    | Instance ID                                                 |
| create_time     | string    | Creation time                                               |
| pipeline_id     | string    | Pipeline node ID assigned by the workflow engine            |
| start_time      | string    | Task start execution time                                   |
| finish_time     | string    | Task completion time                                        |
| instance_info   | object    | Host instance details. See `instance_info` definition       |
| status          | string    | Execution status: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED` |
| steps           | array     | Subscription execution steps. See `steps` definition        |

##### instance_info

When need_detail=true, the displayed information will include but is not limited to the following Fields

| Field       | Type       | Description                                             |
|-------------|------------|---------------------------------------------------------|
| host        | object     | Host information, see host definition                   |
| service     | object     | Service instance information, see service definition    |

##### host

| Field               | Type       | Description                     |
|---------------------|------------|---------------------------------|
| bk_biz_id           | int        | BlueKing business ID            |
| bk_host_innerip_v6  | string     | IPv6 inner network IP address   |
| bk_host_innerip     | string     | IPv4 inner network IP address   |
| bk_cloud_id         | int        | Cloud area (access point) ID    |
| bk_supplier_account | int        | Supplier account ID (usually 0) |
| bk_host_name        | string     | Host name                       |
| bk_host_id          | int        | Host ID in CMDB                 |
| bk_biz_name         | string     | Business name                   |
| bk_cloud_name       | string     | Cloud area name                 |

##### service

| Field           | Type   | Description           |
|-----------------|--------|-----------------------|
| id              | int    | Service instance ID   |
| name            | string | Service instance name |
| bk_module_id    | int    | Module ID in CMDB     |
| bk_host_id      | int    | Associated host ID    |

##### status

| Status Type   | Type     | Description                   |
|---------------|----------|-------------------------------|
| PENDING       | string   | Pending execution             |
| RUNNING       | string   | Currently running             |
| FAILED        | string   | Execution failed              |
| SUCCESS       | string   | Execution succeeded           |
| PART_FAILED   | string   | Partially failed              |
| TERMINATED    | string   | Terminated manually           |
| REMOVED       | string   | Removed                       |
| FILTERED      | string   | Filtered out (not applicable) |
| IGNORED       | string   | Ignored                       |

##### steps

| Field           | Type      | Description                                                           |
|-----------------|-----------|-----------------------------------------------------------------------|
| type            | string    | Step type: `AGENT`, `PLUGIN`, or `PROXY`                              |
| actions         | string    | Subscription actions performed in this step. See `actions` definition |
| extra_info      | object    | Additional metadata related to the step                               |
| create_time     | string    | Step creation time                                                    |
| pipeline_id     | string    | Pipeline node ID for this step                                        |
| start_time      | string    | Step start execution time                                             |
| finish_time     | string    | Step completion time                                                  |
| status          | string    | Execution status: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`           |
| node_name       | string    | Name of the node associated with this step                            |
| step_code       | string    | Execution code for the pipeline node                                  |
| target_hosts    | object    | Execution details for target hosts. See `target_hosts` definition     |

###### target_hosts

| Field          | Type      | Description                                                                                                                    |
|----------------|-----------|--------------------------------------------------------------------------------------------------------------------------------|
| create_time    | string    | Creation time                                                                                                                  |
| pipeline_id    | string    | Pipeline node ID                                                                                                               |
| start_time     | string    | Start time of execution on the target host                                                                                     |
| finish_time    | string    | Completion time on the target host                                                                                             |
| node_name      | string    | Name of the pipeline node                                                                                                      |
| sub_steps      | object    | Execution details of sub-steps within this step. A complete step may consist of multiple sub-steps. See `sub_steps` definition |

###### sub_steps

| Field        | Type    | Description                                                 |
|--------------|---------|-------------------------------------------------------------|
| create_time  | string  | Sub-step creation time                                      |
| pipeline_id  | string  | Pipeline node ID for the sub-step                           |
| start_time   | string  | Sub-step start time                                         |
| finish_time  | string  | Sub-step completion time                                    |
| status       | string  | Execution status: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED` |
| index        | int     | Execution order index of the sub-step                       |
| node_name    | string  | Name of the sub-step node                                   |

###### actions

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