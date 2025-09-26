### Function Description

Task execution result

### Request Parameters

#### Interface Parameters

| Field            | Type         | <div style="width: 50pt">Required</div> | Description                                                            |
|------------------|--------------|-----------------------------------------|------------------------------------------------------------------------|
| subscription_id  | int          | Yes                                     | Subscription ID for which to query task results                        |
| page             | int          | No                                      | Page number for paginated results. Default: `1`                        |
| pagesize         | int          | No                                      | Number of items per page. Default: `10`                                |
| statuses         | string array | No                                      | List of task statuses to filter by, e.g., `["SUCCESS", "FAILED"]`      |
| return_all       | bool         | No                                      | Whether to return all records without pagination. Default: `false`     |
| instance_id_list | string array | No                                      | List of instance IDs to filter results                                 |
| task_id_list     | int array    | No                                      | Specific task IDs to retrieve results for                              |
| need_detail      | bool         | No                                      | Whether to include detailed execution logs and steps. Default: `false` |

### Request Example

```json
{
    "subscription_id": 1,
    "return_all": true
}
```

### Response Example

```json
{
    "result": true,
    "code": 0,
    "message": "",
    "data": {
      "total": 1,
      "list": [
        {
          "task_id": 1,
          "record_id": 1,
          "instance_id": "host|instance|host|127.0.0.1-0-0",
          "create_time": "2020-12-23 16:46:01",
          "pipeline_id": "149cb17976da4040b75523d495886b3d",
          "start_time": "2020-12-23 16:46:01",
          "finish_time": "2020-12-23 16:47:08",
          "instance_info": {
            "host": {
              "bk_biz_id": 4,
              "bk_host_id": 1,
              "bk_biz_name": "测试业务",
              "bk_cloud_id": 0,
              "bk_cloud_name": "直连区域",
              "bk_host_innerip": "127.0.0.1",
              "bk_supplier_account": "0"
            },
            "service": {
            }
          },
          "status": "SUCCESS",
          "steps": [
            {
              "id": "agent",
              "type": "AGENT",
              "action": "INSTALL_AGENT",
              "extra_info": {
              },
              "pipeline_id": "ac9db1d43b5d438886f08ad8c771005e",
              "finish_time": "2020-12-23 16:47:08",
              "start_time": "2020-12-23 16:46:01",
              "create_time": "2020-12-23 16:46:01",
              "status": "SUCCESS",
              "node_name": "[agent] 安装",
              "step_code": null,
              "target_hosts": [
                {
                  "pipeline_id": "d7e4d0e1235941609b4367114dcfe029",
                  "node_name": "[INSTALL_AGENT] 安装 0:127.0.0.1",
                  "sub_steps": [
                    {
                      "pipeline_id": "913dc70fd5844639b8d72c9d3d7717fc",
                      "index": 0,
                      "node_name": "注册主机到配置平台",
                      "finish_time": "2020-12-23 16:46:01",
                      "start_time": "2020-12-23 16:46:01",
                      "create_time": "2020-12-23 16:46:01",
                      "status": "SUCCESS"
                    },
                    {
                      "pipeline_id": "e8a16636b1f94640aa3928f19ef87eb9",
                      "index": 1,
                      "node_name": "选择接入点",
                      "finish_time": "2020-12-23 16:46:01",
                      "start_time": "2020-12-23 16:46:01",
                      "create_time": "2020-12-23 16:46:01",
                      "status": "SUCCESS"
                    },
                    {
                      "pipeline_id": "b99c6872c3eb4c479423514f2d3b00ec",
                      "index": 2,
                      "node_name": "安装",
                      "finish_time": "2020-12-23 16:46:32",
                      "start_time": "2020-12-23 16:46:01",
                      "create_time": "2020-12-23 16:46:01",
                      "status": "SUCCESS"
                    },
                    {
                      "pipeline_id": "d7f55570fe714c28b7cca56064833be9",
                      "index": 3,
                      "node_name": "查询Agent状态",
                      "finish_time": "2020-12-23 16:46:52",
                      "start_time": "2020-12-23 16:46:32",
                      "create_time": "2020-12-23 16:46:01",
                      "status": "SUCCESS"
                    },
                    {
                      "pipeline_id": "d17003f106a64d88b8038e77ea9db29b",
                      "index": 4,
                      "node_name": "托管 processbeat 插件进程",
                      "finish_time": "2020-12-23 16:46:58",
                      "start_time": "2020-12-23 16:46:52",
                      "create_time": "2020-12-23 16:46:01",
                      "status": "SUCCESS"
                    },
                    {
                      "pipeline_id": "81aeb52bb37945788b3d254979854651",
                      "index": 5,
                      "node_name": "托管 exceptionbeat 插件进程",
                      "finish_time": "2020-12-23 16:47:03",
                      "start_time": "2020-12-23 16:46:58",
                      "create_time": "2020-12-23 16:46:01",
                      "status": "SUCCESS"
                    },
                    {
                      "pipeline_id": "53a5644de57c4c818fef2e38227aebc2",
                      "index": 6,
                      "node_name": "托管 basereport 插件进程",
                      "finish_time": "2020-12-23 16:47:08",
                      "start_time": "2020-12-23 16:47:03",
                      "create_time": "2020-12-23 16:46:01",
                      "status": "SUCCESS"
                    },
                    {
                      "pipeline_id": "54a91fb0720f47c59fea2dfbf64f4d77",
                      "index": 7,
                      "node_name": "更新任务状态",
                      "finish_time": "2020-12-23 16:47:08",
                      "start_time": "2020-12-23 16:47:08",
                      "create_time": "2020-12-23 16:46:01",
                      "status": "SUCCESS"
                    }
                  ],
                  "finish_time": "2020-12-23 16:47:08",
                  "start_time": "2020-12-23 16:46:01",
                  "create_time": "2020-12-23 16:46:01",
                  "status": "SUCCESS"
                }
              ]
            }
          ]
        }
      ],
      "status_counter": {
        "SUCCESS": 1,
        "total": 1
      }
    }
}
```

### Response Parameters Description

#### response

| Field     | Type     | Description                                                            |
|-----------|----------|------------------------------------------------------------------------|
| result    | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code      | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string   | Error message returned when the request fails                          |
| data      | object   | Data returned by the request                                           |

#### data

| Field             | Type      | Description                                                                     |
|-------------------|-----------|---------------------------------------------------------------------------------|
| total             | int       | Total number of instance records                                                |
| list              | array     | List of instance execution statuses. See `list` definition                      |
| status_counter    | object    | Global status statistics for the subscription. See `status_counter` definition  |

##### status_counter

| Field  | Type   | Description                                                       |
|--------|--------|-------------------------------------------------------------------|
| status | string | execution status. e.g.: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED` |
| total  | int    | Count of instances for each execution status.                     |

##### list

| Field         | Type       | Description                                                 |
|---------------|------------|-------------------------------------------------------------|
| task_id       | int        | Task ID                                                     |
| record_id     | int        | Record ID                                                   |
| instance_id   | string     | Instance ID                                                 |
| create_time   | string     | Creation time                                               |
| pipeline_id   | string     | Pipeline node ID assigned by the workflow engine            |
| start_time    | string     | Task start execution time                                   |
| finish_time   | string     | Task completion time                                        |
| instance_info | object     | Host instance details. See `instance_info` definition       |
| status        | string     | Execution status: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED` |
| steps         | array      | Subscription execution steps. See `steps` definition        |

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
