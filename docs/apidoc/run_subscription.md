### 功能描述

创建订阅

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段              | 类型        | <div style="width: 50pt">必选</div> | 描述                             |
| --------------- | --------- | --------------------------------- | ------------------------------ |
| subscription_id | int       | 是                                 | 订阅ID                           |
| scope           | object    | 是                                 | 事件订阅监听的范围, 见scope定义            |
| actions | object array | 否 | 动作范围，见actions定义 |

#### actions

| 字段     | 类型     | <div style="width: 50pt">必选</div> | 描述             |
| ------ | ------ | --------------------------------- | -------------- |
| 主机实例     | string | 是                                 |           |
| config | object | 否                                 | 步骤配置，见config定义 |
| params | object | 是                                 | 步骤参数，见params定义 |

#### scope

| 字段        | 类型            | 必选  | 描述                                                                                  |
| --------- | ------------- | --- | ----------------------------------------------------------------------------------- |
| bk_biz_id | int           | 否   | 蓝鲸业务ID                                                                              |
| node_type | string        | 是   | 节点类别，1: TOPO，动态实例（拓扑）2: INSTANCE，静态实例 3: SERVICE_TEMPLATE，服务模板 4: SET_TEMPLATE，集群模板 |
| nodes     | objects array | 是   | 节点列表，见nodes定义                                                                       |


###### nodes

| 字段                  | 类型     | 必选  | 描述                      |
| ------------------- | ------ | --- | ----------------------- |
| bk_supplier_account | int    | 否   | 开发商ID                   |
| bk_cloud_id         | int    | 否   | 云区域ID                   |
| ip                  | string | 否   | 主机IP地址                  |
| bk_host_id          | int    | 否   | 主机ID                    |
| bk_biz_id           | int    | 否   | 业务ID                    |
| bk_inst_id          | int    | 否   | 实例ID                    |
| bk_obj_id           | int    | 否   | 对象ID                    |
| instance_info       | object | 否   | 主机示例信息，见instance_info定义 |

instance_info

| 字段                             | 类型     | 必选  | 描述                                              |
| ------------------------------ | ------ | --- | ----------------------------------------------- |
| key                            | string | 否   | 秘钥                                              |
| port                           | string | 否   | 安装端口                                            |
| ap_id                          | int    | 否   | 接入点ID                                           |
| account                        | string | 否   | 登录用户                                            |
| os_type                        | string | 否   | 操作系统类型                                          |
| login_ip                       | string | 否   | 登录IP地址                                          |
| data_ip                        | string | 否   | 数据IP地址                                          |
| inner_ip                       | string | 否   | 内网IPV4地址                                        |
| inner_ipv6                     | string | 否   | 内网IPv6地址                                        |
| outer_ip                       | string | 否   | 外网IP地址                                          |
| outer_ipv6                     | string | 否   | 外网IPV6地址                                        |
| password                       | string | 否   | 密码                                              |
| username                       | string | 否   | 操作用户                                            |
| auth_type                      | string | 否   | 认证类型，1：PASSWORD，密码认证 2: KEY，秘钥认证 3：TJJ_PASSWORD |
| bk_biz_id                      | int    | 否   | 业务ID                                            |
| is_manual                      | bool   | 否   | 是否为手动安装                                         |
| retention                      | string | 否   | 密码保留天数，默认只保留1天                                  |
| bk_os_type                     | string | 否   | 操作系统类型                                          |
| bk_biz_name                    | string | 否   | 业务名称                                            |
| bk_cloud_id                    | int    | 否   | 云区域ID                                           |
| bk_cloud_name                  | string | 否   | 云区域名称                                           |
| bt_speed_limit                 | string | 否   | 传输限速                                            |
| host_node_type                 | string | 否   | 主机节点类型，1: AGENT，2：PAGENT 3: PROXY               |
| bk_host_innerip                | string | 否   | 主机内网IP地址                                        |
| bk_host_outerip                | string | 否   | 主机外网IP地址                                        |
| install_channel_id             | int    | 否   | 安装通道ID                                          |
| bk_supplier_account            | int    | 否   | 服务商ID                                           |
| peer_exchange_switch_for_agent | int    | 否   | 加速设置，默认是开启                                      |
| data_path                      | string | 否   | 数据文件路径                                          |

###### job_type

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

### 请求参数示例

```json
{
    "bk_app_code": "esb_test",
    "bk_app_secret": "xxx",
    "bk_username": "admin",
    "bk_token": "xxx",
    "run_immediately": true,
    "subscription_id": 1521,
    "scope": {
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
                    "peer_exchange_switch_for_agent": 1
                },
                "bk_supplier_account": "0"
            }
        ]
    },
    "steps": [
        {
            "id": "agent",
            "config": {
                "job_type": "INSTALL_AGENT"
            },
            "params": {
                "context": {

                },
                "blueking_language": "zh-hans"
            }
        }
    ]
}
```

### 返回结果示例

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

### 返回结果参数说明

#### response

| 字段      | 类型     | 描述                         |
| ------- | ------ | -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | object | 请求返回的数据，见data定义            |

#### data

| 字段              | 类型  | 描述   |
| --------------- | --- | ---- |
| subscription_id | int | 订阅ID |
| task_id         | int | 任务ID |
