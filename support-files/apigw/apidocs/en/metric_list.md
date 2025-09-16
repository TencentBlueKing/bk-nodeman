### Function Description

Health statistics metrics

### Request Parameters

#### Interface Parameters

### Request Example

```json
{}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "metric_alias": "redis.status",
            "category": "redis",
            "collect_type": "backend",
            "description": "Redis 状态",
            "collect_metric": "redis.status",
            "solution": [
                {
                    "reason": "进程：redis未启动或连接不上",
                    "solution": "确保进程：redis状态正常"
                }
            ],
            "node_name": "redis",
            "collect_args": "{}",
            "result": {
                "name": "redis.status",
                "value": "3643811",
                "status": 0,
                "message": ""
            },
            "server_ip": "10.244.9.222"
        },
        {
            "metric_alias": "database.status",
            "category": "database",
            "collect_type": "backend",
            "description": "数据库状态",
            "collect_metric": "database.status",
            "solution": [
                {
                    "reason": "进程：mysql未启动或连接不上",
                    "solution": "确保进程：mysql状态正常"
                }
            ],
            "node_name": "mysql",
            "collect_args": "{}",
            "result": {
                "name": "database.status",
                "value": "ok",
                "status": 0,
                "message": ""
            },
            "server_ip": "10.244.9.222"
        },
        {
            "metric_alias": "rabbitmq.status",
            "category": "rabbitmq",
            "collect_type": "backend",
            "description": "rabbitmq 队列长度, 单个队列阀值为10000条",
            "collect_metric": "rabbitmq.status",
            "solution": [
                {
                    "reason": "进程：rabbitmq未启动或连接不上",
                    "solution": "确保进程：rabbitmq状态正常"
                }
            ],
            "node_name": "rabbitmq",
            "collect_args": "{}",
            "result": {
                "name": "rabbitmq.status",
                "value": "",
                "status": 0,
                "message": ""
            },
            "server_ip": "10.244.9.222"
        },
        {
            "metric_alias": "celery.beat.status",
            "category": "celery",
            "collect_type": "backend",
            "description": "celery beat 状态",
            "node_name": "celery",
            "collect_metric": "celery.beat_process.status",
            "collect_args": "{\"process_name\": \"nodeman_celery_beat\"}",
            "solution": [
                {
                    "reason": "进程：celery未启动或连接不上",
                    "solution": "确保进程：celery状态正常"
                }
            ],
            "result": {
                "name": "celery.beat_process.status",
                "value": null,
                "status": 4,
                "message": "[Errno 2] No such file or directory"
            },
            "server_ip": "10.244.9.222"
        }
    ],
    "code": 0,
    "message": ""
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

| Field           | Type    | Description                                    |
|-----------------|---------|------------------------------------------------|
| metric_alias    | string  | Metric name (alias)                            |
| category        | string  | Category of the metric (e.g., redis, database) |
| collect_type    | string  | Data collection type (e.g., backend)           |
| description     | string  | Description of the metric                      |
| node_name       | string  | Node name associated with the metric           |
| collect_metric  | string  | Actual metric name collected                   |
| collect_args    | string  | Collection arguments in JSON string format     |
| solution        | array   | Troubleshooting guide, see solution definition |
| result          | object  | Collection result, see result definition       |
| server_ip       | string  | Target server IP address                       |

##### solution

| Field     | Type   | Description                       |
|-----------|--------|-----------------------------------|
| reason    | string | Possible cause of the issue       |
| solution  | string | Recommended resolution steps      |

##### result

| Field     | Type   | Description                                   |
|-----------|--------|-----------------------------------------------|
| name      | string | Name of the metric                            |
| value     | string | Collected value (may be null or empty)        |
| status    | int    | Status code: 0 = success, >0 = error          |
| message   | string | Additional message or error details           |
