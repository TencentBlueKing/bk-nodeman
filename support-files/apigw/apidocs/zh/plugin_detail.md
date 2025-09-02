### 功能描述

插件详情

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段   | 类型   | <div style="width: 50pt">必选</div> | 描述   |
|------|------|-----------------------------------|------|
| id   | int  | 是                                 | 插件id |

### 请求参数示例

```json
{
  "id": 1
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "id": 1,
        "description": "系统基础信息采集",
        "name": "basereport",
        "category": "官方插件",
        "source_app_code": "bk_nodeman",
        "scenario": "CMDB上的实时数据，蓝鲸监控里的主机监控，包含CPU，内存，磁盘等",
        "deploy_type": "整包部署",
        "plugin_packages": [
            {
                "id": 1,
                "pkg_name": "basereport-10.1.12.tgz",
                "module": "gse_plugin",
                "project": "basereport",
                "version": "10.1.12",
                "config_templates": [
                    {"id": 1, "name": "basereport.conf", "version": "10.1", "is_main": true}
                ],
                "os": "linux",
                "cpu_arch": "x86_64",
                "support_os_cpu": "linux_x86_64",
                "pkg_mtime": "2019-11-25 21:58:30",
                "creator": "test_person",
                "is_ready": true
            },
            {
                "id": 2,
                "pkg_name": "bkmonitorbeat-1.7.1.tgz",
                "module": "gse_plugin",
                "project": "bkmonitorbeat",
                "version": "1.7.1",
                "config_templates": [
                    {"id": 1, "name": "child1.conf", "version": "1.0", "is_main": false},
                    {"id": 2, "name": "child2.conf", "version": "1.1", "is_main": false},
                    {"id": 3, "name": "bkmonitorbeat.conf", "version": "0.1", "is_main": true}
                ],
                "os": "windows",
                "cpu_arch": "x86",
                "support_os_cpu": "windows_x86",
                "pkg_mtime": "2019-11-25 21:58:30",
                "creator": "test_person",
                "is_ready": true
            }
        ]
    },
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

