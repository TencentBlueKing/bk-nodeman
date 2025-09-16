### Function Description

Query plugin list

### Request Parameters

#### Interface Parameters

| Field     | Type     | <div style="width: 50pt">Required</div> | Description                                       |
|-----------|----------|-----------------------------------------|---------------------------------------------------|
| category  | string   | Yes                                     | Plugin category: official, external, or scripts   |

### Request Example

```json
{
    "category": "official"
}
```

### Response Example

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

### Response Parameters Description

#### response

| Field      | Type      | Description                         |
| ------- |---------|----------------------------|
| result  | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code    | int     | Error code. 0 indicates success; values greater than 0 indicate errors  |
| message | string  | Error message returned when the request fails                |
| data    | array   | Data returned by the request, see definition below            |

#### data

| Field                 | Type     | Description                                                        |
|-----------------------|----------|--------------------------------------------------------------------|
| id                    | int      | Plugin ID                                                          |
| name                  | string   | Plugin name                                                        |
| description           | string   | Plugin description in Chinese                                      |
| scenario              | string   | Usage scenario in Chinese                                          |
| description_en        | string   | Plugin description in English                                      |
| scenario_en           | string   | Usage scenario in English                                          |
| category              | string   | Category: official, external, scripts                              |
| config_file           | string   | Configuration file name                                            |
| config_format         | string   | Format of config file (e.g., yaml, json)                           |
| use_db                | bool     | Whether the plugin requires a database                             |
| is_binary             | bool     | Whether the plugin is a binary executable                          |
| auto_launch           | bool     | Whether to automatically start the plugin after agent installation |
| node_manage_control   | string   | Node management control information                                |
| launch_node           | string   | Target node type for deployment (e.g., all)                        |
| is_ready              | bool     | Whether the plugin is ready for use                                |
| deploy_type           | string   | Deployment method (reserved field, may be null)                    |
| auto_type             | int      | Auto-management type (1: auto-managed)                             |
| source_app_code       | string   | Source system App Code                                             |