### 功能描述

创建订阅

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段              | 类型     | <div style="width: 50pt">必选</div> | 描述          |
| --------------- | ------ | --------------------------------- | ----------- |
| name            | string | 否                                 | 订阅名称        |
| scope           | object | 是                                 | 事件订阅监听的范围   |
| steps           | object | 是                                 | 事件订阅触发的动作列表 |
| target_hosts    | object | 否                                 | 下发的目标机器列表   |
| run_immediately | bool   | 否                                 | 是否立即执行      |
| is_main         | bool   | 否                                 | 是否为主配置      |
| plugin_name     | string | 否                                 | 插件名         |
| bk_biz_scope    | object | 否                                 | 订阅监听业务范围    |
| category        | string | 否                                 | 订阅类型        |
| pid             | int    | 否                                 | 父策略ID       |
|                 |        |                                   |             |

#### steps

| 字段               | 类型     | <div style="width: 50pt">必选</div> | 描述                                                                                                                 |
| ---------------- | ------ | --------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| id               | string | 是                                 | 步骤标识符                                                                                                              |
| type             | string | 是                                 | 步骤类型，1: AGENT，2：PLUGIN，3: PROXY                                                                                    |
| config           | object | 是                                 | 步骤配置                                                                                                               |
| params           | object | 是                                 | 步骤参数                                                                                                               |
| file_source_id   | int    | 否                                 | file_type为3时，file_source_id与file_source_code选择一个填写，若都填写，优先使用file_source_id，第三方文件源Id，可从get_job_detail接口返回结果中的步骤详情获取 |
| file_source_code | string | 否                                 | file_type为3时，file_source_id与file_source_code选择一个填写，若都填写，优先使用file_source_id，第三方文件源标识，可从作业平台的文件分发页面->选择文件源文件弹框中获取    |

#### account

| 字段    | 类型     | 必选  | 描述                                                               |
| ----- | ------ | --- | ---------------------------------------------------------------- |
| id    | long   | 否   | 源执行帐号ID，可从get_account_list接口获取。与alias必须存在一个。当同时存在alias和id时，id优先。 |
| alias | string | 否   | 源执行帐号别名，可从账号页面获取，推荐使用。与alias必须存在一个。当同时存在alias和id时，id优先。          |

#### server

| 字段                 | 类型    | 必选  | 描述                                           |
| ------------------ | ----- | --- | -------------------------------------------- |
| host_id_list       | array | 否   | 主机ID列表                                       |
| ip_list            | array | 否   | ***不推荐使用，建议使用host_id_list参数***。主机IP 列表，定义见ip |
| dynamic_group_list | array | 否   | 动态分组列表，定义见dynamic_group                      |
| topo_node_list     | array | 否   | 动态 topo 节点列表，定义见topo_node                    |

#### ip

| 字段          | 类型     | 必选  | 描述    |
| ----------- | ------ | --- | ----- |
| bk_cloud_id | long   | 是   | 云区域ID |
| ip          | string | 是   | IP地址  |

#### topo_node_list

| 字段        | 类型     | 必选  | 描述                                                  |
| --------- | ------ | --- | --------------------------------------------------- |
| id        | long   | 是   | 动态topo节点ID，对应CMDB API 中的 bk_inst_id                 |
| node_type | string | 是   | 动态topo节点类型，对应CMDB API 中的 bk_obj_id,比如"module","set" |

### 请求参数示例

```json
{
    "bk_app_code": "esb_test",
    "bk_app_secret": "xxx",
    "bk_token": "xxx",
    "bk_scope_type": "biz",
    "bk_scope_id": "1",
    "file_target_path": "/tmp/",
    "transfer_mode": 1,
    "file_source_list": [
        {
            "file_list": [
                "/tmp/REGEX:[a-z]*.txt"
            ],
            "account": {
                "id": 100
            },
            "server": {
                "dynamic_group_list": [
                    {
                        "id": "blo8gojho0skft7pr5q0"
                    },
                    {
                        "id": "blo8gojho0sabc7priuy"
                    }
                ],
                "host_id_list": [
                    101,102
                ],
                "topo_node_list": [
                    {
                        "id": 1000,
                        "node_type": "module"
                    }
                ]
            },
            "file_type": 1
        },
        {
            "file_list": [
                "testbucket/test.txt"
            ],
            "file_type": 3,
            "file_source_id": 1
        },
        {
            "file_list": [
                "testbucket/test2.txt"
            ],
            "file_type": 3,
            "file_source_code": "testInnerCOS"
        }
    ],
    "target_server": {
        "dynamic_group_list": [
            {
                "id": "blo8gojho0skft7pr5q0"
            },
            {
                "id": "blo8gojho0sabc7priuy"
            }
        ],
        "host_id_list": [
            103,104
        ],
        "topo_node_list": [
            {
                "id": 1000,
                "node_type": "module"
            }
        ]
    },
    "account_id": 101
}
```

### 返回结果示例

```json
{
    "result": true,
    "code": 0,
    "message": "success",
    "data": {
        "job_instance_name": "API Quick Distribution File1521101427176",
        "job_instance_id": 10000,
        "step_instance_id": 10001
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

| 字段                | 类型   | 描述     |
| ----------------- | ---- | ------ |
| job_instance_id   | long | 作业实例ID |
| job_instance_name | long | 作业实例名称 |
| step_instance_id  | long | 步骤实例ID |
