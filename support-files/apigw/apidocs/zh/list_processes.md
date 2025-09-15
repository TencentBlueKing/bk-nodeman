### 功能描述

查询插件列表

### 请求参数

#### 接口参数

| 字段         | 类型     | <div style="width: 50pt">必选</div> | 描述   |
|------------|--------| --------------------------------- | ---- |
| category   | string | 是                                 | category为official, external 或 scripts |

### 请求参数示例

```json
{
    "category": "official"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "id": 18,
            "name": "bkunifylogbeat",
            "description": "蓝鲸日志采集器",
            "scenario": "计算平台，蓝鲸监控，日志检索等和日志相关的数据. 首次使用插件管理进行操作前，先到日志检索/数据平台等进行设置插件的功能项",
            "description_en": "BlueKing Log Collector",
            "scenario_en": "BKData, BKMonitor, BKLog and other data collection related to logs. For the first use, you need to go to the corresponding platform to set up related function items",
            "category": "official",
            "config_file": "bkunifylogbeat.conf",
            "config_format": "yaml",
            "use_db": false,
            "is_binary": true,
            "auto_launch": false,
            "node_manage_control": "",
            "launch_node": "all",
            "is_ready": true,
            "deploy_type": null,
            "auto_type": 1,
            "source_app_code": null
        },
        {
            "id": 4,
            "name": "bkmonitorbeat",
            "description": "蓝鲸监控指标采集器",
            "scenario": "蓝鲸监控拨测采集器 支持多协议多任务的采集，监控和可用率计算，提供多种运行模式和热加载机制",
            "description_en": "",
            "scenario_en": "",
            "category": "official",
            "config_file": "bkmonitorbeat.conf",
            "config_format": "yaml",
            "use_db": false,
            "is_binary": true,
            "auto_launch": true,
            "node_manage_control": "",
            "launch_node": "all",
            "is_ready": true,
            "deploy_type": null,
            "auto_type": 1,
            "source_app_code": null
        }
    ],
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型      | 描述                         |
| ------- |---------|----------------------------|
| result  | bool    | 请求成功与否。true:请求成功；false请求失败 |
| code    | int     | 错误编码。 0表示success，>0表示失败错误  |
| message | string  | 请求失败返回的错误信息                |
| data    | array   | 请求返回的数据，见data定义            |

#### data

| 字段                  | 类型      | 描述                |
|---------------------|---------|-------------------|
| id                  | int     | 插件id              |
| name                | string  | 插件名               |
| description         | string  | 插件描述              |
| scenario            | string  | 使用场景              |
| description_en      | string  | 英文插件描述            |
| scenario_en         | string  | 英文使用场景            |
| category            | string  | 所属范围              |
| config_file         | string  | 配置文件名称            |
| config_format       | string  | 配置文件格式类型          |
| use_db              | bool    | 是否使用数据库           |
| is_binary           | bool    | 是否二进制文件           |
| auto_launch         | bool    | 是否在成功安装agent后自动拉起 |
| node_manage_control | string  | 节点管理管控插件信息        |
| launch_node         | string  | 宿主节点类型要求          |
| is_ready            | bool    | 是否启用插件            |
| deploy_type         | string  | 部署方式              |
| auto_type           | bool    | 托管类型              |
| source_app_code     | string  | 来源系统app_code      | 