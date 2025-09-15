### 功能描述

创建配置模板

### 请求参数

#### 接口参数

| 字段                 | 类型       | <div style="width: 50pt">必选</div> | 描述       |
|--------------------|----------| --------------------------------- |----------|
| plugin_name        | string   | 是                                 | 插件名      |
| plugin_version     | string   | 是                                 | 版本号     |
| name               | string   | 是                                 | 配置模板名    |
| version            | string   | 是                                 | 配置模板版本   |
| format             | string   | 是                                 | 文件格式     |
| file_path          | string   | 是                                 | 文件在该插件目录中相对路径   |
| content            | string   | 是                                 | 配置内容      |
| md5                | string   | 是                                 | md5值     |
| is_release_version | bool     | 是                                 | 是否已经发布版本 |

### 请求参数示例

```json
{
    "plugin_name": "clb_traffic",
    "plugin_version": "*",
    "name": "env.yaml",
    "file_path": "etc",
    "format": "yaml",
    "content": "R1NFX0FHRU5UX0hPTUU6IHt7IGNvbnRyb2xfaW5mby5nc2VfYWdlbnRfaG9tZSB9fQpCS19QTFVHSU5fTE9HX1BBVEg",
    "md5": "dab43f1b255a78e1d288783c62fcf1b",
    "version": "11",
    "is_release_version": false
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "plugin_name": "xxxxx",
        "plugin_version": "1.0.0",
        "name": "env.yaml",
        "version": "10",
        "format": "yaml",
        "file_path": "etc",
        "content": "GSE_AGENT_HOME: {{ control_info.gse_agent_home }}\nBK_PLUGIN_LOG_PATH: {{ control_info.log_path }}\nBK_PLUGIN_PID_PATH: {{ control_info.pid_path }}\n\n\n\n\n\n\n\n\n\n\n\n\n\nBK_CMD_ARGS: {{ cmd_args }}",
        "md5": "dabd43f1b255a78e1d288783c62fcf1b",
        "is_release_version": false,
        "ids": [19524, 19525, 19526, 19527, 19528]
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

| 字段                 | 类型        | 描述            |
|--------------------|-----------|---------------|
| plugin_name        | string    | 插件名           |
| plugin_version     | string    | 版本号           |
| name               | string    | 配置模板名         |
| version            | string    | 配置模板版本        |
| format             | string    | 文件格式          |
| file_path          | string    | 文件在该插件目录中相对路径 |
| content            | string    | 配置内容          |
| md5                | string    | md5值          |
| is_release_version | bool      | 是否已经发布版本      |
| ids                | int array | 创建的模板id       |
