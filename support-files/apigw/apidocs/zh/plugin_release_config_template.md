### 功能描述

发布配置模板

### 请求参数

#### 接口参数

| 字段             | 类型        | <div style="width: 50pt">必选</div> | 描述     |
|----------------|-----------|-----------------------------------|--------|
| plugin_name    | string    | 否                                 | 插件名    |
| plugin_version | string    | 否                                 | 版本号    |
| name           | string    | 否                                 | 配置模板名  |
| version        | string    | 否                                 | 配置模板版本 |
| id             | int array | 否                                 | 配置模板版本id     |

### 请求参数示例

```json
{
    "plugin_name": "ds_metric_report",
    "plugin_version": "10_31",
    "name": "env.yaml.tpl",
    "version": "10"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "id": 9,
            "plugin_name": "ds_metric_report",
            "plugin_version": "10_31",
            "name": "env.yaml.tpl",
            "version": "10",
            "format": "yaml",
            "file_path": "etc",
            "is_release_version": true,
            "creator": "admin",
            "content": "R1NFX0FHRU5UX0hPTUU6IHt7IGNvbnRyb2xfaW5mby5nc2VfYWdlbnRfaG9tZSB9fQpCS19QTFVHSU5fTE9HX1BBVEg",
            "source_app_code": "bk_nodeman"
        },
        {
            "id": 8,
            "plugin_name": "ds_metric_report",
            "plugin_version": "10_31",
            "name": "env.yaml.tpl",
            "version": "10",
            "format": "yaml",
            "file_path": "etc",
            "is_release_version": true,
            "creator": "admin",
            "content": "R1NFX0FHRU5UX0hPTUU6IHt7IGNvbnRyb2xfaW5mby5nc2VfYWdlaG9tZSB9fQpCS19QTFVHSU5fTE9HX1BBVEg",
            "source_app_code": "bk_nodeman"
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

| 字段                 | 类型     | 描述           |
|--------------------|--------|--------------|
| id                 | int    | 配置模板版本id     |
| plugin_name        | string | 插件名          |
| plugin_version     | string | 版本号          |
| name               | string | 配置模板名        |
| version            | string | 配置模板版本       |
| format             | string | 文件格式        |
| file_path          | string | 文件在该插件目录中相对路径         |
| is_release_version | string | 是否已经发布版本     |
| creator            | string | 创建者        |
| content            | string | 配置内容         |
| source_app_code    | string | 来源系统app_code |
