### 功能描述

批量获取含各节点主机数量的拓扑树

### 请求参数

#### 接口参数

| 字段         | 类型     | <div style="width: 50pt">必选</div> | 描述                                 |
|------------|--------| --------------------------------- |------------------------------------|
| all_scope  | bool   | 否                                 | 是否获取所有资源范围的拓扑结构，默认为 `false`"       |
| scope_list | array  | 否                                 | 要获取拓扑结构的资源范围数组，见scope_list定义       |
| action     | string | 否                                 | 权限类型，默认为`agent_view`,见 action 定义   |

###### scope_list

| 字段             | 类型     | <div style="width: 50pt">必选</div> | 描述      |
|----------------|--------|-----------------------------------|---------|
| scope_type     | string | 是                                 | 资源范围类型  |
| scope_id       | string | 否                                 | 资源范围ID  |
| bk_biz_id      | int    | 否                                 | 业务ID    |

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

### 请求参数示例

```json
{
    "all_scope": false,
    "scope_list": [
        {
            "scope_type": "biz",
            "scope_id": "10003"
        }
    ]
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "instance_id": 5000445,
            "instance_name": "EIAM政务认证",
            "object_id": "biz",
            "object_name": "业务",
            "meta": {
                "scope_type": "biz",
                "scope_id": "5000445",
                "bk_biz_id": 5000445
            },
            "count": 1,
            "child": [
                {
                    "instance_id": 5026009,
                    "instance_name": "空闲机池",
                    "object_id": "set",
                    "object_name": "集群",
                    "meta": {
                        "scope_type": "biz",
                        "scope_id": "5000445",
                        "bk_biz_id": 5000445
                    },
                    "count": 1,
                    "child": [
                        {
                            "instance_id": 5067855,
                            "instance_name": "故障机",
                            "object_id": "module",
                            "object_name": "模块",
                            "meta": {
                                "scope_type": "biz",
                                "scope_id": "5000445",
                                "bk_biz_id": 5000445
                            },
                            "count": 0,
                            "child": [],
                            "lazy": false
                        },
                        {
                            "instance_id": 5067854,
                            "instance_name": "空闲机",
                            "object_id": "module",
                            "object_name": "模块",
                            "meta": {
                                "scope_type": "biz",
                                "scope_id": "5000445",
                                "bk_biz_id": 5000445
                            },
                            "count": 1,
                            "child": [],
                            "lazy": false
                        },
                        {
                            "instance_id": 5067856,
                            "instance_name": "待回收",
                            "object_id": "module",
                            "object_name": "模块",
                            "meta": {
                                "scope_type": "biz",
                                "scope_id": "5000445",
                                "bk_biz_id": 5000445
                            },
                            "count": 0,
                            "child": [],
                            "lazy": false
                        }
                    ],
                    "lazy": false
                }
            ],
            "lazy": false
        }
    ],
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段        | 类型     | 描述                         |
|-----------|--------|----------------------------|
| result    | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code      | int    | 错误编码。 0表示success，>0表示失败错误  |
| message   | string | 请求失败返回的错误信息                |
| data      | array  | 请求返回的数据，见data定义            |
 
#### data

| 字段            | 类型     | 描述                 |
|---------------|--------|--------------------|
| meta          | object | 元数据，见meta定义        |
| object_id     | string | 节点类型ID             |
| object_name   | string | 节点类型名称             |
| instance_id   | int    | 节点实例ID             |
| instance_name | string | 节点实例名称             |
| count         | int    | 节点数量               |
| child         | array  | 子节点，见child定义       |
| lazy          | bool   | 是否采取懒加载策略（仅返回一级节点） |

#### child

| 字段            | 类型     | 描述                 |
|---------------|--------|--------------------|
| meta          | object | 元数据，见meta定义        |
| object_id     | string | 节点类型ID             |
| object_name   | string | 节点类型名称             |
| instance_id   | int    | 节点实例ID             |
| instance_name | string | 节点实例名称             |
| count         | int    | 节点数量               |
| child         | array  | 子节点，见child定义       |
| lazy          | bool   | 是否采取懒加载策略（仅返回一级节点） |

###### meta

| 字段          | 类型     | 描述       |
|-------------|--------|----------|
| bk_biz_id   | int    | 业务 ID    |
| scope_type  | string | 资源范围类型   |
| scope_id    | string | 资源范围ID   |