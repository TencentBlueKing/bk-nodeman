### 功能描述

获取主机订阅列表

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段              | 类型          | <div style="width: 50pt">必选</div> | 描述                                            |
|-----------------|-------------|-----------------------------------|-----------------------------------------------|
| bk_host_id      | string      | 否                                 | 目标机器主机ID，bk_host_id 和 (ip, bk_cloud_id) 必须有一组 |
| ip              | string      | 否                                 | 目标机器IP                                        |
| bk_host_innerip | string      | 否                                 | 目标机器IP，bk_host_id 和 (ip, bk_cloud_id) 必须有一组   |
| bk_cloud_id     | string      | 否                                 | 目标机器管控区域ID                                    |
| bk_supplier_id  | string      | 否                                 | 目标机器开发商ID，默认为"0"                              |
| source_type     | string      | 是                                 | 来源类型，可选[default, subscription, debug]         |

### 请求参数示例

```json
{
  "bk_host_id": 123456,
  "source_type": "subscription"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
      {
        "id": 817,
        "source_type": "subscription",
        "source_id": "93",
        "name": "bkunifylogbeat",
        "version": "1.10.58",
        "status": "RUNNING"
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

#### data

| 字段          | 类型     | <div style="width: 50pt">必选</div> | 描述             |
|-------------|--------| --------------------------------- |----------------|
| id          | int    | 是                                 | 进程ID           |
| source_type | string | 是                                 | 来源类型           |
| source_id   | string | 是                                 | 来源ID           |
| name        | string | 是                                 | 插件名称           |
| version     | string | 是                                 | 插件版本           |
| status      | string | 否                                 | 进程状态，见status定义 |

##### status

| 状态类型             | 类型     | 描述      |
|------------------| ------ |---------|
| RUNNING          | string | 运行中     |
| UNKNOWN          | string | 未知状态    |
| TERMINATED       | string | 已终止     |
| NOT_INSTALLED    | string | 未安装     |
| UNREGISTER       | string | 未注册     |
| REMOVED          | string | 已移除     |
| MANUAL_STOP      | string | 手动停止    |
| AGENT_NO_ALIVE   | string | AGENT异常 |


