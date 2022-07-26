### 功能描述

订阅详情

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段                   | 类型     | <div style="width: 50pt">必选</div> | 描述         |
| -------------------- | ------ | --------------------------------- | ---------- |
| subscription_id_list | object | 是                                 | 订阅ID列表     |
| show_deleted         | bool   | 否                                 | 是否显示已删除的订阅 |

### 请求参数示例

```json
{
    "bk_app_code": "esb_test",
    "bk_app_secret": "xxx",
    "bk_token": "xxx",
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
            "name": 'basereport-策略范围主机',
            "enable": True,
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
                        "bk_obj_id": "module",

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
                                "cpu_arch": "x86_64",

                            },
                            {
                                "name": "env.yaml",
                                "version": "2",
                                "os": "windows",
                                "cpu_arch": "x86_64",

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
                                "version": "1",

                            },

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
}
```

### 返回结果参数说明

#### response

| 字段         | 类型     | 描述                         |
| ---------- | ------ | -------------------------- |
| result     | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code       | int    | 错误编码。 0表示success，>0表示失败错误  |
| message    | string | 请求失败返回的错误信息                |
| data       | object | 请求返回的数据                    |
| permission | object | 权限信息                       |
| request_id | string | 请求链id                      |

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
|              |           |                                |

##### scope

| 字段           | 类型     | 描述     |
| ------------ | ------ | ------ |
| bk_biz_id    | int    | 订阅任务ID |
| bk_biz_scope |        |        |
| object_type  | string | 订阅任务名称 |
| object_type  | string | 订阅任务名称 |
| object_type  | string | 订阅任务名称 |
| object_type  | string | 订阅任务名称 |
