### Function Description

Query log

### Request Parameters

#### Interface Parameters

| Field        | Type     | <div style="width: 50pt">Required</div> | Description |
|--------------|----------|-----------------------------------------|-------------|
| job_id       | int      | Yes                                     | Job ID      |
| instance_id  | string   | Yes                                     | Instance ID |

### Request Example

```json
{
    "job_id": 1,
    "instance_id": "host|instance|host|123456"
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
            "step": "更新任务状态",
            "status": "SUCCESS",
            "log": "[2021-09-16 15:06:04 INFO] 开始更新任务状态",
            "start_time": "2021-09-16 15:06:04",
            "finish_time": "2021-09-16 15:06:04"
        },
        {
            "step": "批量下发升级包",
            "status": "SUCCESS",
            "log": "[2021-09-16 15:06:04 INFO] 开始下发升级包......",
            "start_time": "2021-09-16 15:06:04",
            "finish_time": "2021-09-16 15:06:39"
        },
        {
            "step": "执行升级脚本",
            "status": "SUCCESS",
            "log": "[2021-09-16 15:06:39 INFO] 开始执行升级脚本\n[2021-09-16 15:06:39 INFO]...........",
            "start_time": "2021-09-16 15:06:39",
            "finish_time": "2021-09-16 15:06:45"
        },
        {
            "step": "查询Agent状态",
            "status": "SUCCESS",
            "log": "[2021-09-16 15:06:45 INFO] 开始查询 GSE 状态期望的GSE主机状态为RUNNING......",
            "start_time": "2021-09-1615: 06: 45",
            "finish_time": "2021-09-1615: 07: 20"
        },
        {
            "step": "更新任务状态",
            "status": "SUCCESS",
            "log": "[2021-09-1615: 0720 INFO]开始更新任务状态",
            "start_time": "2021-09-1615: 07: 20",
            "finish_time": "2021-09-1615: 07: 20"
        }
    ]
}
```

### Response Parameters Description

#### response

| Field     | Type     | Description                                                            |
|-----------|----------|------------------------------------------------------------------------|
| result    | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code      | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string   | Error message returned when the request fails                          |
| data      | array    | Data returned by the request, see definition below                     |

#### data

| Field        | Type     | Description                             |
|--------------|----------|-----------------------------------------|
| step         | string   | Step name                               |
| status       | string   | Execution status, see status definition |
| log          | string   | Execution log                           |
| start_time   | string   | Start time                              |
| finish_time  | string   | Finish time                             |

##### status

| Status Type | Type    | Description         |
|-------------|---------|---------------------|
| PENDING     | string  | Pending execution   |
| RUNNING     | string  | Currently running   |
| FAILED      | string  | Execution failed    |
| SUCCESS     | string  | Execution succeeded |
| PART_FAILED | string  | Partially failed    |
| TERMINATED  | string  | Terminated          |
| REMOVED     | string  | Removed             |
| FILTERED    | string  | Filtered out        |
| IGNORED     | string  | Ignored             |
