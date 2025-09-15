### 功能描述

查询日志

### 请求参数

#### 接口参数

| 字段          | 类型     | <div style="width: 50pt">必选</div> | 描述      |
| ----------- |--------| --------------------------------- |---------|
| job_id      | int    | 是                                 | 任务ID    |
| instance_id | string | 是                                 | 任务实例ID  |

### 请求参数示例

```json
{
    "job_id": 1,
    "instance_id": "host|instance|host|123456"
}
```

### 返回结果示例

```json
{
    "result": true,
    "code": 0,
    "message": "success",
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

### 返回结果参数说明

#### response

| 字段      | 类型     | 描述                         |
| ------- | ------ | -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | array  | 请求返回的数据，见data定义            |

#### data

| 字段          | 类型     | 描述             |
| ----------- | ------ | -------------- |
| step        | string | 节点名称           |
| status      | string | 执行状态，见status定义 |
| log         | string | 执行日志           |
| start_time  | string | 启动时间           |
| finish_time | string | 完成时间           |

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
