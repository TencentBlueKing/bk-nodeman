### 功能描述

健康统计指标

### 请求参数

{{ common_args_desc }}

#### 接口参数

### 请求参数示例

```json
{}
```

### 返回结果示例

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

### 返回结果参数说明

#### response

| 字段      | 类型           | 描述                         |
| ------- | ------------ | -------------------------- |
| result  | bool         | 请求成功与否。true:请求成功；false请求失败 |
| code    | int          | 错误编码。 0表示success，>0表示失败错误  |
| message | string       | 请求失败返回的错误信息                |
| data    | array | 请求返回的数据，见data定义            |
