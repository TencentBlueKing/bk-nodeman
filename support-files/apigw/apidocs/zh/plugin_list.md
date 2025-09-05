### 功能描述

查询插件列表

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段            | 类型     | <div style="width: 50pt">必选</div> | 描述         |
|---------------|--------| --------------------------------- |------------|
| page          | int    | 否                                 | 当前页数，默认为1  |
| pagesize      | int    | 否                                 | 分页大小，默认为10 |
| search        | string | 否                                 | 插件名称模糊搜索   |
| simple_all    | bool   | 否                                 | 返回全部简要信息   |

### 请求参数示例

```json
{}
```

### 返回结果示例

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

### 返回结果参数说明

#### response

| 字段      | 类型           | 描述                         |
| ------- | ------------ | -------------------------- |
| result  | bool         | 请求成功与否。true:请求成功；false请求失败 |
| code    | int          | 错误编码。 0表示success，>0表示失败错误  |
| message | string       | 请求失败返回的错误信息                |
| data    | array | 请求返回的数据，见data定义            |

#### data

| 字段              | 类型     | <div style="width: 50pt">必选</div> | 描述                    |
|-----------------|--------| --------------------------------- |-----------------------|
| id              | int    | 是                                 | 插件ID                  |
| description     | string | 是                                 | 插件描述                  |
| scenario        | string | 是                                 | 使用场景                  |
| name            | string | 是                                 | 插件名称                  |
| category        | string | 是                                 | 插件类型                  |
| source_app_code | string | 否                                 | 来源系统app code                  |
| deploy_type     | string | 否                                 | 部署方式             |
| is_ready        | bool   | 否                                 | 是否启用插件                 |

