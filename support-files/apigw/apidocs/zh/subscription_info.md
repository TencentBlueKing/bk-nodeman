### 功能描述

查询订阅详情

### 请求参数

#### 接口参数

| 字段                   | 类型     | <div style="width: 50pt">必选</div> | 描述         |
| -------------------- | ------ | --------------------------------- | ---------- |
| subscription_id_list | object | 是                                 | 订阅ID列表     |
| show_deleted         | bool   | 否                                 | 是否显示已删除的订阅 |

### 请求参数示例

```json
{
  "subscription_id_list": [
    1
  ],
  "show_deleted": false
}
```

### 返回结果示例

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

### 返回结果参数说明

#### response

| 字段      | 类型     | 描述                         |
| ------- |--------| -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | array  | 请求返回的数据，见data定义            |

#### data

| 字段           | 类型        | 描述                             |
| ------------ | --------- | ------------------------------ |
| id           | int       | 订阅任务ID                         |
| name         | string    | 订阅任务名称                         |
| enable       | bool      | 是否启用订阅，false为不启用，ture为是启用      |
| category     | string    | 订阅类别，1：policy ，2：debug，3: once |
| plugin_name  | string    | 插件名                            |
| bk_biz_scope | int array | 订阅监听业务范列表，包含相关业务ID             |
| scope        | object    | 事件订阅监听的范围，见scope定义             |
| pid          | int       | 父策略ID，如不指定默认值为-1               |
| target_hosts | object    | 下发的目标机器列表，见target_hosts定义      |
| steps        | object    | 事件订阅触发的动作列表，见steps定义           |

#### steps

| 字段     | 类型     | 描述                             |
| ------ | ------ | ------------------------------ |
| id     | string | 步骤标识符                          |
| type   | string | 步骤类型，1:AGENT，2：PLUGIN，3: PROXY |
| config | object | 步骤配置，见config定义                 |
| params | object | 步骤参数，见params定义                 |

#### scope

| 字段            | 类型            |描述                                                                                  |
| ------------- | ------------- | ----------------------------------------------------------------------------------- |
| bk_biz_id     | int           | 蓝鲸业务ID                                                                              |
| bk_biz_scope  | int array     | 蓝鲸业务ID列表                                                                            |
| node_type     | string        | 节点类别，1: TOPO，动态实例（拓扑）2: INSTANCE，静态实例 3: SERVICE_TEMPLATE，服务模板 4: SET_TEMPLATE，集群模板 |
| object_type   | string        | 对象类型，1：HOST，主机类型  2：SERVICE，服务类型                                                    |
| need_register | bool          | 是否需要注册到CMDB，false是不注册，true是注册。默认为不注册                                                |
| nodes         | objects       | 节点列表，见nodes定义                                                                       |

##### config

| 字段                   | 类型            |描述                                                                |
| -------------------- | ------------- | ----------------------------------------------------------------- |
| plugin_name          | string        | 插件名                                                               |
| plugin_version       | string        | 插件版本，如不确定具体版本，可指定为latest                                          |
| config_templates     | objects       | 配置模板列表，见config_templates定义                                        |
| job_type             | string        | 作业类型，官方插件是基于多配置的管理模式，安装、卸载、启用、停用等操作仅涉及到配置的增删，具体见job_type定义        |
| check_and_skip       | bool          | 安装主插件支持检查是否存在并跳过，1：true， 版本不一致时进行安装 2: false， 忽略版本不一致的情况，只要保证存活即可 |
| is_version_sensitive | bool          | 是否强校验安装版本                                                         |

###### config_templates

| 字段       | 类型     |描述                                               |
| -------- | ------ | ------------------------------------------------ |
| name     | string | 配置文件名                                            |
| version  | string | 配置文件版本号                                          |
| is_main  | bool   | 是否为主配置                                           |
| os       | string | 操作系统，1：LINUX 2：WINDOWS 3：AIX 4：SOLARIS           |
| cpu_arch | string | CPU类型，1：x86 2：x86_64 3：powerpc 4：aarch64 5：sparc |

###### params

| 字段          | 类型     |描述                 |
| ----------- | ------ | ------------------ |
| port_range  | string | 端口范围               |
| context     | object | 配置文件渲染上下文          |
| keep_config | bool   | 是否保留原有配置文件         |
| no_restart  | bool   | 是否仅更新文件，不重启进程，默认为否 |

###### nodes

| 字段                  | 类型     |描述                      |
| ------------------- | ------ | ----------------------- |
| bk_supplier_account | int    | 开发商ID                   |
| bk_cloud_id         | int    | 管控区域ID                   |
| ip                  | string | 主机IP地址                  |
| bk_host_id          | int    | 主机ID                    |
| bk_biz_id           | int    | 业务ID                    |
| bk_inst_id          | int    | 实例ID                    |
| bk_obj_id           | int    | 对象ID                    |
| instance_info       | object | 主机实例信息，见instance_info定义 |

instance_info

| 字段                             | 类型     |描述                                                      |
| ------------------------------ | ------ | ------------------------------------------------------- |
| key                            | string | 秘钥                                                      |
| port                           | string | 安装端口                                                    |
| ap_id                          | int    | 接入点ID                                                   |
| account                        | string | 登录用户                                                    |
| os_type                        | string | 操作系统，1：LINUX 2：WINDOWS 3：AIX 4：SOLARIS                  |
| login_ip                       | string | 登录IP地址                                                  |
| data_ip                        | string | 数据IP地址                                                  |
| inner_ip                       | string | 内网IPV4地址                                                |
| inner_ipv6                     | string | 内网IPv6地址                                                |
| outer_ip                       | string | 外网IP地址                                                  |
| outer_ipv6                     | string | 外网IPV6地址                                                |
| password                       | string | 密码                                                      |
| username                       | string | 操作用户                                                    |
| auth_type                      | string | 认证类型，1：PASSWORD，密码认证 2: KEY，秘钥认证 3：TJJ_PASSWORD，默认为密码认证 |
| bk_biz_id                      | int    | 业务ID                                                    |
| is_manual                      | bool   | 是否为手动安装                                                 |
| retention                      | string | 密码保留天数，默认只保留1天                                          |
| bk_os_type                     | string | 操作系统，1：LINUX 2：WINDOWS 3：AIX 4：SOLARIS                  |
| bk_biz_name                    | string | 业务名称                                                    |
| bk_cloud_id                    | int    | 管控区域ID                                                   |
| bk_cloud_name                  | string | 管控区域名称                                                   |
| bt_speed_limit                 | string | 传输限速                                                    |
| host_node_type                 | string | 主机节点类型，1: AGENT，2：PAGENT 3: PROXY                       |
| bk_host_innerip                | string | 主机内网IP地址                                                |
| bk_host_outerip                | string | 主机外网IP地址                                                |
| install_channel_id             | int    | 安装通道ID                                                  |
| bk_supplier_account            | int    | 服务商ID                                                   |
| peer_exchange_switch_for_agent | int    | 加速设置，默认是关闭                                              |
| data_path                      | string | 数据文件路径                                                  |
| enable_compression             | bool   | 数据压缩开关，默认是关闭                                              |
