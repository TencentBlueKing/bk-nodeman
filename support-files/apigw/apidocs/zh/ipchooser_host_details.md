### 功能描述

根据主机关键信息获取机器详情信息

### 请求参数

#### 接口参数

| 字段                   | 类型      | <div style="width: 50pt">必选</div> | 描述                        |
|----------------------|---------| --------------------------------- |---------------------------|
| host_list            | array   | 是                                 | 主机列表，见 host_list 定义       | 
| agent_realtime_state | bool    | 否                                 | agent实时状态，默认为False        |
| all_scope            | bool    | 否                                 | 是否获取所有资源范围的拓扑结构，默认为 false |
| scope_list           | array   | 否                                 | 要获取拓扑结构的资源范围数组，见 scope_list 定义           |
| action               | string  | 否                                 | 权限类型，默认为`agent_view`,见 action 定义 |

##### host_list

| 字段      | 类型     | <div style="width: 50pt">必选</div> | 描述                                         |
|---------|--------|-----------------------------------|--------------------------------------------|
| host_id | int    | 否                                 | 主机 ID，优先取 `host_id`，否则取 `ip` + `cloud_id`" |
| ip      | string | 否                                 | IPv4 协议下的主机IP                              |
| meta    | object | 否                                 | 元数据，见 meta 定义                              |

###### scope_list

| 字段             | 类型     | <div style="width: 50pt">必选</div> | 描述      |
|----------------|--------|-----------------------------------|---------|
| scope_type     | string | 是                                 | 资源范围类型  |
| scope_id       | string | 否                                 | 资源范围ID  |
| bk_biz_id      | int    | 否                                 | 业务ID    |

###### action

| 字段              | 类型     | 描述      |
|-----------------| ------ |---------|
| agent_view      | string | agent查询 |
| agent_operate   | string | agent操作 |
| proxy_operate   | string | proxy操作 |
| plugin_view     | string | 插件查看    |
| plugin_operate  | string | 插件操作    |
| strategy_view   | string | 策略查看    |
| strategy_create | string | 策略创建    |

###### meta

| 字段          | 类型     | <div style="width: 50pt">必选</div> | 描述 |
|-------------|--------|-----------------------------------|----|
| bk_biz_id   | int    | 否                                 |业务 ID |
| scope_type  | string | 是                                 |资源范围类型 |
| scope_id    | string | 是                                 |资源范围ID |    |

### 请求参数示例

```json
{
    "host_list": [
        {
            "host_id": 1,
            "meta": {
                "scope_type": "biz",
                "scope_id": "10003",
                "bk_biz_id": 10003
            }
        },
        {
            "host_id": 2,
            "meta": {
                "scope_type": "biz",
                "scope_id": "10003",
                "bk_biz_id": 10003
            }
        }
    ],
    "all_scope": false,
    "scope_list": [
        {
            "scope_type": "biz",
            "scope_id": "10003"
        }
    ],
    "agent_realtime_state": true
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "meta": {
                "scope_type": "biz",
                "scope_id": "10003",
                "bk_biz_id": 10003
            },
            "host_id": 1,
            "agent_id": "0200000000525400b43e7d1700234471265z",
            "ip": "10.0.0.1",
            "ipv6": "",
            "host_name": "",
            "os_name": "Linux",
            "os_type": "Linux",
            "alive": 1,
            "cloud_area": {
                "id": 0,
                "name": "直连区域"
            },
            "biz": {
                "id": 10003,
                "name": "蓝鲸"
            },
            "bk_host_id": 1,
            "bk_biz_id": 10003,
            "bk_agent_id": "0200000000525400b43e7d1700234471265z",
            "bk_agent_alive": 1,
            "bk_cloud_id": 0
        }
    ],
    "code": 0,
    "message": ""
}
```

 ### 返回结果参数说明

 #### response

| 字段      | 类型     | 描述                         |
| ------- |--------| -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | array  | 请求返回的数据，见data定义            |

#### data

| 字段             | 类型     | 描述                     |
|----------------|--------|------------------------|
| meta           | object | 元数据，见 meta 定义          |
| host_id        | int    | 主机ID                   |
| agent_id       | string | AgentID                |
| ip             | string | 内网IP                   |
| ipv6           | string | 内网IPv6                 |
| host_name      | string | 主机名称                   |
| os_name        | string | 操作系统名称                 |
| os_type        | string | 操作系统类型                 |
| alive          | int    | Agent存活状态，1表示存活，0表示未存活 |
| cloud_area     | object | 管控区域信息，见cloud_area定义   |
| biz            | object | 业务信息，见biz定义            |
| bk_host_id     | int    | 主机ID                   |
| bk_biz_id      | int    | 业务ID                   |
| bk_agent_id    | string | AgentID                |
| bk_agent_alive | int    | Agent存活状态，1表示存活，0表示未存活 |
| bk_cloud_id    | int    | 管控区域ID                 |

#### meta

| 字段          | 类型     | 描述 |
|-------------|--------|----|
| bk_biz_id   | int    | 业务 ID |
| scope_type  | string | 资源范围类型 |
| scope_id    | string | 资源范围ID |

#### cloud_area

| 字段       | 类型     | 描述     |
|----------|--------|--------|
| id       | int    | 管控区域ID |
| name     | string | 管控区域名称 |

#### biz

| 字段       | 类型     | 描述   |
|----------|--------|------|
| id       | int    | 业务ID |
| name     | string | 业务名称 |