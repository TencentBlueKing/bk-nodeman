### 功能描述

查询多个节点拓扑路径

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段               | 类型     | <div style="width: 50pt">必选</div> | 描述                        |
|------------------|--------| --------------------------------- |---------------------------|
| node_list        | array  | 是                                 | 主机列表，见 node_list 定义       |
| action           | string | 否                                 | 权限类型，见 action 定义          |

##### node_list

| 字段          | 类型       | <div style="width: 50pt">必选</div> | 描述                                         |
|-------------|----------|-----------------------------------|--------------------------------------------|
| object_id   | string   | 是                                 | 节点类型ID |
| instance_id | string   | 是                                 | 节点实例ID                              |
| meta        | object   | 是                                 | 元数据，见 meta 定义                              |

###### action

| 字段              | 类型     | 描述        |
|-----------------| ------ |-----------|
| agent_view      | string | agent查询   |
| agent_operate   | string | agent操作   |
| proxy_operate   | string | proxy操作   |
| plugin_view     | string | 插件查看      |
| plugin_operate  | string | 插件操作      |
| strategy_view   | string | 策略查看   |
| strategy_create | string | 策略创建 |

###### meta

| 字段          | 类型     | <div style="width: 50pt">必选</div> | 描述 |
|-------------|--------|-----------------------------------|----|
| bk_biz_id   | int    | 否                                 |业务 ID |
| scope_type  | string | 是                                 |资源范围类型 |
| scope_id    | string | 是                                 |资源范围ID |


### 请求参数示例

```json
{
    "action": "strategy_create",
    "node_list": [
        {
            "object_id": "biz",
            "instance_id": 1,
            "meta": {
                "scope_type": "biz",
                "scope_id": "1",
                "bk_biz_id": 1
            }
        },
        {
            "object_id": "biz",
            "instance_id": 1,
            "meta": {
                "scope_type": "biz",
                "scope_id": "2",
                "bk_biz_id": 2
            }
        }
    ]
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        [
            {
                "meta": {
                    "scope_type": "biz",
                    "scope_id": "1",
                    "bk_biz_id": 1
                },
                "object_id": "biz",
                "object_name": "业务",
                "instance_id": 1,
                "instance_name": "蓝鲸"
            }
        ],
        [
            {
                "meta": {
                    "scope_type": "biz",
                    "scope_id": "2",
                    "bk_biz_id": 2
                },
                "object_id": "biz",
                "object_name": "业务",
                "instance_id": 2,
                "instance_name": "蓝鲸运营"
            }
        ]
    ],
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型     | 描述                         |
| ------- | ------ | -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | object | 请求返回的数据，见data定义            |
 
#### data

| 字段            | 类型     | <div style="width: 50pt">必选</div> | 描述          |
|---------------|--------| --------------------------------- |-------------|
| meta          | object | 是                                 | 元数据，见meta定义 |
| object_id     | string | 是                                 | 节点类型ID      |
| object_name   | string | 是                                 | 节点类型名称      |
| instance_id   | int    | 是                                 | 节点实例ID      |
| instance_name | string | 是                                 | 节点实例名称      |

###### meta

| 字段          | 类型     | <div style="width: 50pt">必选</div> | 描述 |
|-------------|--------|-----------------------------------|----|
| bk_biz_id   | int    | 否                                 |业务 ID |
| scope_type  | string | 是                                 |资源范围类型 |
| scope_id    | string | 是                                 |资源范围ID |