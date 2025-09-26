### Function Description

Query subscription instance status

### Request Parameters

#### Interface Parameters

| Field                  | Type      | <div style="width: 50pt">Required</div> | Description                                                                                                                                         |
|------------------------|-----------|-----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| subscription_id_list   | int array | Yes                                     | List of subscription IDs to query                                                                                                                   |
| show_task_detail       | bool      | No                                      | Whether to return detailed task execution information (e.g., logs, step details). Default: false                                                  |
| need_detail            | bool      | No                                      | Whether to include detailed host and service information in instance_info. If true, returns full host and service objects. Default: false |

### Request Example

```json
{
    "subscription_id_list": [
        1
      ],
      "show_task_detail": false,
      "need_detail": false
}
```

### Response Example

```json
{
    "result": true,
    "code": 0,
    "message": "",
    "data": [
        {
            "subscription_id":1,
            "instances": [
                {
                    "instance_id": "host|instance|host|35",
                    "status": "SUCCESS",
                    "create_time": "2020-12-28 16:48:11+0800",
                    "host_statuses": [

                    ],
                    "instance_info": {
                        "host": {
                            "bk_biz_id": 5,
                            "bk_host_id": 35,
                            "bk_biz_name": "test",
                            "bk_cloud_id": 0,
                            "bk_host_name": "",
                            "bk_cloud_name": "直连区域",
                            "bk_host_innerip": "127.0.0.1",
                            "bk_supplier_account": "0"
                        },
                        "service": {

                        }
                    },
                    "running_task": null,
                    "last_task": {
                        "id": 150,
                        "record_id": 214,
                        "create_time": "2020-12-28 16:48:11",
                        "pipeline_id": "6de50ec13864470d9a9418613ed10da8",
                        "start_time": "2020-12-28 08:48:13",
                        "finish_time": "2020-12-28 08:50:09",
                        "steps": [
                            {
                                "id": "exceptionbeat",
                                "type": "PLUGIN",
                                "action": "MAIN_INSTALL_PLUGIN",
                                "node_name": "[exceptionbeat] 部署插件程序",
                                "pipeline_id": "5b702f51a5944d519f4abcc2678f0ed3",
                                "status": "SUCCESS",
                                "start_time": "2020-12-28 08:48:13",
                                "finish_time": "2020-12-28 08:50:09",
                                "target_hosts": [
                                    {
                                        "node_name": "[exceptionbeat] 部署插件程序 0:127.0.0.1",
                                        "pipeline_id": "5b702f51a5944d519f4abcc2678f0ed3",
                                        "status": "SUCCESS",
                                        "start_time": "2020-12-28 08:48:13",
                                        "finish_time": "2020-12-28 08:50:09",
                                        "sub_steps": [
                                            {
                                                "index": 0,
                                                "node_name": "查询Agent状态",
                                                "step_code": null,
                                                "pipeline_id": "5b702f51a5944d519f4abcc2678f0ed3",
                                                "log": "",
                                                "ex_data": null,
                                                "status": "SUCCESS",
                                                "start_time": "2020-12-28 08:48:13",
                                                "finish_time": "2020-12-28 08:48:13"
                                            },
                                            {
                                                "index": 1,
                                                "node_name": "更新插件部署状态",
                                                "step_code": null,
                                                "pipeline_id": "6c8ff413abb04cb492265466337e9ba0",
                                                "log": "",
                                                "ex_data": null,
                                                "status": "SUCCESS",
                                                "start_time": "2020-12-28 08:48:13",
                                                "finish_time": "2020-12-28 08:48:13"
                                            },
                                            {
                                                "index": 2,
                                                "node_name": "批量下发插件包",
                                                "step_code": null,
                                                "pipeline_id": "52bb6f6fb0cc4e7a9d6a6cf476921e6c",
                                                "log": "",
                                                "ex_data": null,
                                                "status": "SUCCESS",
                                                "start_time": "2020-12-28 08:48:13",
                                                "finish_time": "2020-12-28 08:49:23",
                                                "inputs": {
                                                    "instance_info": {
                                                        "host": {
                                                            "operator": "admin",
                                                            "bk_biz_id": 5,
                                                            "bk_os_bit": "",
                                                            "bk_host_id": 35,
                                                            "bk_os_name": "",
                                                            "bk_os_type": "1",
                                                            "bk_biz_name": "test",
                                                            "bk_cloud_id": 0,
                                                            "bk_host_name": "",
                                                            "bk_cloud_name": "直连区域",
                                                            "bk_cpu_module": "",
                                                            "bk_bak_operator": "admin",
                                                            "bk_host_innerip": "127.0.0.1",
                                                            "bk_host_outerip": "",
                                                            "bk_supplier_account": "0"
                                                        },
                                                        "scope": [
                                                            {
                                                                "ip": "127.0.0.1",
                                                                "bk_cloud_id": 0,
                                                                "bk_supplier_id": 0
                                                            }
                                                        ],
                                                        "process": {

                                                        },
                                                        "service": null
                                                    }
                                                }
                                            },
                                            {
                                                "index": 3,
                                                "node_name": "安装插件包",
                                                "step_code": null,
                                                "pipeline_id": "0d0d62d071d44456bccdf7bbf9b18489",
                                                "log": "",
                                                "ex_data": null,
                                                "status": "SUCCESS",
                                                "start_time": "2020-12-28 08:49:23",
                                                "finish_time": "2020-12-28 08:49:54"
                                            },
                                            {
                                                "index": 4,
                                                "node_name": "渲染并下发配置",
                                                "step_code": null,
                                                "pipeline_id": "85f252a390b14f1aa9c9538f5d6faf6e",
                                                "log": "",
                                                "ex_data": null,
                                                "status": "SUCCESS",
                                                "start_time": "2020-12-28 08:49:54",
                                                "finish_time": "2020-12-28 08:49:59"
                                            },
                                            {
                                                "index": 5,
                                                "node_name": "重启 exceptionbeat 插件进程",
                                                "step_code": null,
                                                "pipeline_id": "e2534a4f17f545b2b341cc278b173a74",
                                                "log": "",
                                                "ex_data": null,
                                                "status": "SUCCESS",
                                                "start_time": "2020-12-28 08:49:59",
                                                "finish_time": "2020-12-28 08:50:09"
                                            },
                                            {
                                                "index": 6,
                                                "node_name": "更新插件部署状态",
                                                "step_code": null,
                                                "pipeline_id": "9767216b9e734736ac70d7a8a429cb71",
                                                "log": "",
                                                "ex_data": null,
                                                "status": "SUCCESS",
                                                "start_time": "2020-12-28 08:50:09",
                                                "finish_time": "2020-12-28 08:50:09"
                                            },
                                            {
                                                "index": 7,
                                                "node_name": "重置重试次数",
                                                "step_code": null,
                                                "pipeline_id": "95959096c4904e0c97d8b72a78cae308",
                                                "log": "",
                                                "ex_data": null,
                                                "status": "SUCCESS",
                                                "start_time": "2020-12-28 08:50:09",
                                                "finish_time": "2020-12-28 08:50:09"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ],
                        "status": "SUCCESS"
                    }
                }
            ]
        }
    ]
}
```

### Response Parameters Description

#### response

| Field    | Type   | Description                                                            |
|----------|--------|------------------------------------------------------------------------|
| result   | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code     | int    | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string | Error message returned when the request fails                          |
| data     | array  | Data returned by the request, see definition below                     |

#### data

| Field            | Type    | Description                                                |
|------------------|---------|------------------------------------------------------------|
| subscription_id  | int     | Subscription ID                                            |
| instances        | object  | Host instance information list, see instances definition   |

##### instances

| Field          | Type     | Description                                                     |
|----------------|----------|-----------------------------------------------------------------|
| instance_id    | string   | Instance ID                                                     |
| status         | string   | Execution status, refer to status definition                    |
| create_time    | string   | Creation time in ISO format (e.g., YYYY-MM-DDTHH:mm:ssZ)        |
| host_statuses  | object   | Process/plugin status on the host, see host_statuses definition |
| instance_info  | object   | Detailed host and service info, see instance_info definition    |
| running_task   | object   | Currently running execution task, see running_task definition   |
| last_task      | object   | Last executed task, see last_task definition                    |

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

##### host_statuses

| Field        | Type     | Description                                   |
|--------------|----------|-----------------------------------------------|
| name       | string | Process or plugin name                        |
| status     | string | Process status, see proc_status definition  |
| version    | string | Version number                                |
| group_id   | int    | Plugin group ID                               |

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

##### proc_status

| Status Type    | Type    | Description        |
|----------------|---------|--------------------|
| RUNNING        | string  | Running normally   |
| UNKNOWN        | string  | Unknown status     |
| TERMINATED     | string  | Terminated         |
| NOT_INSTALLED  | string  | Not installed      |
| UNREGISTER     | string  | Unregistered       |
| REMOVED        | string  | Removed            |
| MANUAL_STOP    | string  | Manually stopped   |

##### running_task

| Field             | Type    | Description                          |
|-------------------|---------|--------------------------------------|
| id                | int     | Subscription task ID                 |
| is_auto_trigger   | bool    | Whether the task was auto-triggered  |

##### last_task

| Field        | Type     | Description                                                 |
|--------------|----------|-------------------------------------------------------------|
| id           | int      | Subscription task ID                                        |
| record_id    | int      | Record ID for tracking                                      |
| create_time  | string   | Task creation time (ISO format)                             |
| pipeline_id  | int      | Pipeline ID of the execution flow                           |
| finish_time  | int      | Finish time                                                 |
| steps        | array    | List of execution steps, each step contains status and logs |
| status       | string   | Final execution status (refer to status enum)               |
