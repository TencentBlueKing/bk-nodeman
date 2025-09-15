### 功能描述

任务执行详细结果

### 请求参数

#### 接口参数

| 字段              | 类型        | <div style="width: 50pt">必选</div> | 描述     |
|-----------------|-----------|-----------------------------------|--------|
| subscription_id | int       | 是                                 | 订阅ID   |
| task_id         | int       | 否                                 | 任务ID   |
| task_id_list    | int array | 否                                 | 任务ID列表 |
| instance_id     | string    | 是                                 | 实例ID   |


### 请求参数示例

```json
{
    "subscription_id": 864317,
    "instance_id": "host|instance|host|10.0.0.3-0",
    "task_id_list": [
        374776866
    ]
}
```

### 返回结果示例

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
                                "log": "[2025-08-30 22:50:55 INFO] 开始 查询主机密码.\n[2025-08-30 22:50:56 INFO] 当前主机验证类型无需查询密码\n[2025-08-30 22:50:56 INFO] 查询主机密码 成功",
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

### 返回结果参数说明

#### response

| 字段      | 类型     | 描述                         |
| ------- | ------ | -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | object | 请求返回的数据，见data定义            |

#### data

| 字段            | 类型      | 描述                      |
| ------------- |---------|-------------------------|
| task_id       | int     | 任务ID                    |
| record_id     | int     | 记录ID                    |
| instance_id   | string  | 实例ID                    |
| create_time   | string  | 创建时间                    |
| pipeline_id   | string  | Pipeline节点ID            |
| start_time    | string  | 启动时间                    |
| finish_time   | string  | 完成时间                    |
| instance_info | object  | 主机实例信息，见instance_info定义 |
| status        | string  | 执行状态，见status 定义         |
| steps         | array   | 订阅步骤信息，见steps 定义        |

##### instance_info

当need_detail参数为True时，展示信息将包括但不限于以下字段

| 字段      | 类型     | 描述                |
| ------- | ------ | ----------------- |
| host    | object | 主机信息，见host定义      |
| service | object | 服务实例信息，见service定义 |

##### host

| 字段                  | 类型     | 描述         |
| ------------------- | ------ | ---------- |
| bk_biz_id           | int    | 蓝鲸业务ID     |
| bk_host_innerip_v6  | string | 主机IPV6内网地址 |
| bk_host_innerip     | string | 主机IPV4内网地址 |
| bk_cloud_id         | int    | 管控区域ID      |
| bk_supplier_account | int    | 服务商ID      |
| bk_host_name        | string | 主机名        |
| bk_host_id          | int    | 主机ID       |
| bk_biz_name         | string | 业务名称       |
| bk_cloud_name       | string | 管控区域名称      |

##### service

| 字段           | 类型     | 描述     |
| ------------ | ------ | ------ |
| id           | int    | 服务实例ID |
| name         | string | 服务实例名称 |
| bk_module_id | int    | 模块ID   |
| bk_host_id   | int    | 主机ID   |

##### status

| 状态类型        | 类型     | 描述   |
| ----------- | ------ | ---- |
| PENDING     | string | 等待执行 |
| RUNNING     | string | 正在执行 |
| FAILED      | string | 执行失败 |
| SUCCESS     | string | 执行成功 |
| PART_FAILED | string | 部分失败 |
| TERMINATED  | string | 已终止  |
| REMOVED     | string | 已移除  |
| FILTERED    | string | 被过滤的 |
| IGNORED     | string | 已忽略  |

##### steps

| 字段           | 类型       | 描述                             |
|--------------|----------|--------------------------------|
| id           | string   | 步骤ID                           |
| type         | string   | 步骤类型，1:AGENT，2：PLUGIN，3: PROXY |
| index        | object   | 额外信息                           |
| action       | string   | 订阅动作，见actions定义                |
| node_name    | string   | Pipeline节点ID                   |
| extra_info   | string   | 额外信息                           |
| pipeline_id  | string   | Pipeline节点ID                   |
| status       | string   | 执行状态，见status定义                 |
| start_time   | string   | 启动时间                           |
| finish_time  | string   | 完成时间                           |
| target_hosts | object   | 目标主机执行信息，见target_hosts定义       |

###### target_hosts

| 字段          | 类型     | 描述                                                            |
|-------------| ------ |---------------------------------------------------------------|
| status      | string | 执行状态                                                          |
| pipeline_id | string | Pipeline节点ID                                                  |
| start_time  | string | 启动时间                                                          |
| finish_time | string | 完成时间                                                          |
| node_name   | string | Pipeline节点名称                                                  |
| sub_steps   | object | 子步骤执行信息，一个完整的订阅步骤可以由很多子步骤组装完成，改步骤展示每一个字步骤的相关信息, 见sub_steps 定义 |

###### actions

Agent

| 字段              | 类型     | 描述        |
| --------------- | ------ | --------- |
| INSTALL_AGENT   | string | 安装Agent   |
| RESTART_AGENT   | string | 重启Agent   |
| REINSTALL_AGENT | string | 重装Agent   |
| UNINSTALL_AGENT | string | 卸载Agent   |
| REMOVE_AGENT    | string | 移除Agent   |
| UPGRADE_AGENT   | string | 升级Agent   |
| RELOAD_AGENT    | string | 重载Agent配置 |
| INSTALL_PROXY   | string | 安装Proxy   |
| RESTART_PROXY   | string | 重启Proxy   |
| REINSTALL_PROXY | string | 重装Proxy   |
| UNINSTALL_PROXY | string | 卸载Proxy   |
| UPGRADE_PROXY   | string | 升级Proxy   |
| RELOAD_PROXY    | string | 重载Proxy配置 |

Plugin

| 字段                          | 类型     | 描述             |
| --------------------------- | ------ | -------------- |
| MAIN_START_PLUGIN           | string | 启动插件进程         |
| MAIN_STOP_PLUGIN            | string | 停止插件进程         |
| MAIN_RESTART_PLUGIN         | string | 重启插件进程         |
| MAIN_RELOAD_PLUGIN          | string | 重载插件配置         |
| MAIN_DELEGATE_PLUGIN        | string | 托管插件           |
| MAIN_UNDELEGATE_PLUGIN      | string | 取消插件托管         |
| MAIN_INSTALL_PLUGIN         | string | 安装插件           |
| DEBUG_PLUGIN                | string | 调试插件           |
| STOP_DEBUG_PLUGIN           | string | 停止调试插件         |
| MAIN_INSTALL_PLUGIN         | string | 部署插件程序，下发并安装插件 |
| MAIN_STOP_AND_DELETE_PLUGIN | string | 停用插件并删除订阅      |

官方插件，是基于多配置的管理模式，安装、卸载、启用、停用等操作仅涉及到配置的增删 

| 字段          | 类型     | 描述     |
| ----------- | ------ | ------ |
| INSTALL     | string | 下发插件配置 |
| UNINSTALL   | string | 移除插件配置 |
| PUSH_CONFIG | string | 下发插件配置 |
| START       | string | 下发插件配置 |
| STOP        | string | 移除插件配置 |

非官方插件

| 字段          | 类型     | 描述     |
| ----------- | ------ | ------ |
| INSTALL     | string | 部署插件   |
| UNINSTALL   | string | 卸载插件   |
| PUSH_CONFIG | string | 下发插件配置 |
| START       | string | 启动插件进程 |
| STOP        | string | 停止插件进程 |