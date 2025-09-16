### 功能描述

创建注册任务

### 请求参数

#### 接口参数

| 字段                           | 类型     | <div style="width: 50pt">必选</div> | 描述                    |
|------------------------------|--------|-----------------------------------|-----------------------|
| file_name                    | string | 是                                 | 文件名称                  |
| is_release                   | bool   | 是                                 | 是否立即发布该插件             |
| is_template_load             | bool   | 否                                 | 是否需要读取配置文件            |
| is_template_overwrite        | bool   | 否                                 | 是否可以覆盖已经存在的配置文件       |
| select_pkg_relative_paths    | array  | 否                                 | 选择注册的插件包相对路径，缺省默认全选   |

### 请求参数示例

```json
{
    "file_name": "bkunifylogbeat-7.1.28.tgz",
    "is_release": true
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
       "job_id": 1
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

| 字段             | 类型    | 描述   |
|----------------|-------|------|
| job_id         | int   | 任务id |
