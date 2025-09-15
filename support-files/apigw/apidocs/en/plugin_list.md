### Function Description

Query plugin list

### Request Parameters

#### Interface Parameters

| Field       | Type    | <div style="width: 50pt">Required</div> | Description                                |
|-------------|---------|-----------------------------------------|--------------------------------------------|
| page        | int     | No                                      | Current page number, default is 1          |
| pagesize    | int     | No                                      | Page size, default is 10                   |
| search      | string  | No                                      | Fuzzy search by plugin name                |
| simple_all  | bool    | No                                      | Return brief information for all plugins   |

### Request Example

```json
{}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "total": 4,
        "list": [
            {
                "id": 3,
                "description": "蓝鲸监控指标采集器",
                "scenario": "蓝鲸监控拨测采集器 支持多协议多任务的采集，监控和可用率计算，提供多种运行模式和热加载机制",
                "name": "bkmonitorbeat",
                "category": "official",
                "source_app_code": null,
                "deploy_type": null,
                "is_ready": true
            },
            {
                "id": 4,
                "description": "蓝鲸日志采集器66611",
                "scenario": "计算平台，蓝鲸监控，日志检索等和日志相关的数据. 首次使用插件管理进行操作前，先到日志检索/数据平台等进行设置插件的功能项",
                "name": "bkunifylogbeat",
                "category": "official",
                "source_app_code": null,
                "deploy_type": null,
                "is_ready": true
            },
            {
                "id": 8,
                "description": "腾讯蓝鲸的 APM 服务端组件，负责接收蓝鲸监控的自定义时序指标及自定义事件上报，以及 Prometheus、OpenTelemetry、Jaeger，Skywalking 等主流开源组件的遥测数据",
                "scenario": "蓝鲸监控，日志检索，应用性能监控等相关的数据. 首次使用插件管理进行操作前，先到相关平台进行设置插件的功能项",
                "name": "bk-collector",
                "category": "official",
                "source_app_code": null,
                "deploy_type": null,
                "is_ready": true
            },
            {
                "id": 9,
                "description": "bscp服务配置分发和热更新",
                "scenario": "bscp服务配置分发和热更新",
                "name": "bkbscp",
                "category": "official",
                "source_app_code": null,
                "deploy_type": null,
                "is_ready": true
            }
        ]
    },
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Type     | Description                                                            |
|----------|----------|------------------------------------------------------------------------|
| result   | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code     | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string   | Error message returned when the request fails                          |
| data     | object   | Data returned by the request, see definition below                     |

##### data

| Field             | Type     | Description                             |
|-------------------|----------|-----------------------------------------|
| id                | int      | Plugin ID                               |
| description       | string   | Plugin description                      |
| scenario          | string   | Usage scenario                          |
| name              | string   | Plugin name                             |
| category          | string   | Plugin category (e.g., "official")      |
| source_app_code   | string   | Source application code (can be null)   |
| deploy_type       | string   | Deployment method                       |
| is_ready          | bool     | Whether the plugin is enabled/available |

