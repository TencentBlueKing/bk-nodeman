### 功能描述

开始调试

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段             | 类型     | <div style="width: 50pt">必选</div> | 描述                |
|----------------|--------|-----------------------------------|-------------------|
| plugin_id      | int    | 否                                 | 插件id              |
| plugin_name    | string | 否                                 | 插件名               |
| version        | string | 否                                 | 版本号               |
| config_ids     | array  | 否                                 | 配置id              |
| object_type    | string | 否                                 | 对象类型              |
| node_type      | string | 否                                 | 节点类别              |
| host_info      | object | 否                                 | 主机信息，见host_info定义 |
| instance_info  | object | 否                                 | 实例信息，见instance_info定义   |

#### host_info

| 字段             | 类型     | <div style="width: 50pt">必选</div> | 描述           |
|----------------|--------| --------------------------------- |--------------|
| bk_host_id     | int    | 否                                 | 目标机器主机ID     |
| ip             | string | 否                                 | 目标机器IP       |
| bk_cloud_id    | int    | 否                                 | 目标机器管控区域ID   |
| bk_supplier_id | int    | 否                                 | 目标机器开发商ID    |
| bk_biz_id      | int    | 否                                 | 目标机器业务ID     |

#### instance_info

| 字段          | 类型     | 必选  | 描述     |
|-------------|--------| --- |--------|
| bk_biz_id   | int    | 是   | 蓝鲸业务ID |
| id          | int    | 否   | ID     |
| bk_inst_id  | string | 否   | 实例ID   |
| bk_obj_id   | string | 否   | 模型ID   |


### 请求参数示例

```json
{
    "plugin_name": "tagent_monitor",
    "version": "1.1",
    "config_ids": [
        11573,
        11573
    ],
    "host_info": {
        "bk_supplier_id": 0,
        "bk_host_id": 100,
        "bk_biz_id": 10
    }
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "task_id": 123456789
    },
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

| 字段               | 类型     | 描述           |
|------------------|--------|--------------|
| task_id          | int    | 任务id         |

