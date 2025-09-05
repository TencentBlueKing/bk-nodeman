### 功能描述

获取主机策略列表

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段           | 类型  | <div style="width: 50pt">必选</div> | 描述   |
|--------------|-----|-----------------------------------|------|
| bk_host_id   | int | 是                                 | 主机ID |

### 请求参数示例

```json
{
    "bk_host_id": 123456
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "name": "test",
            "category": "policy",
            "plugin_name": "bkunifylogbeat",
            "auto_trigger": true,
            "version": "7.7.2-rc.29",
            "install_path": "/usr/local/gse2_tenant/plugins/bin",
            "is_latest": true,
            "status": "SUCCESS",
            "update_time": "2025-08-27 06:52:29+0800",
            "instance_id": "host|instance|host|123456",
            "job_id": 11,
            "job_type": "MAIN_INSTALL_PLUGIN",
            "updated_by": "admin",
            "deploy_type": null,
            "config_template": "bkunifylogbeat.conf",
            "plugin_version": "7.7.2-rc.29"
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

| 字段              | 类型     | 描述      |
|-----------------|--------|---------|
| name            | string | 策略名     |
| category        | string | 执行状态    |
| plugin_name     | string | 插件名     |
| auto_trigger    | bool   | 是否为自动触发 |
| version         | string | 插件版本    |
| install_path    | string | 安装路径    |
| is_latest       | bool   | 是否为最新   |
| status          | string | 策略状态    |
| update_time     | string | 更新时间    |
| instance_id     | string | 实例ID    |
| job_id          | int    | 作业ID    |
| job_type        | string | 作业类型    |
| updated_by      | string | 修改者     |
| deploy_type     | string | 部署方式    |
| config_template | string | 配置模板    |
| plugin_version  | string | 插件版本    |
