### 功能描述

查询管控区域列表

### 请求参数

#### 接口参数

| 字段                | 类型   | <div style="width: 50pt">必选</div> | 描述            |
| ----------------- | ---- | --------------------------------- | ------------- |
| with_default_area | bool | 否                                 | 是否返回直连区域，默认为否 |

### 请求参数示例

```json
{
    "with_default_area": false
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "bk_cloud_id": 1,
            "bk_cloud_name": "测试",
            "isp": "Tencent",
            "ap_id": 1,
            "is_visible": true,
            "node_count": 10,
            "proxy_count": 2,
            "ap_name": "默认接入点",
            "isp_name": "腾讯云",
            "isp_icon": "PHN2ZyB2aWV3Qm",
            "exception": "",
            "proxies": null,
            "permissions": {
                "view": true,
                "edit": true,
                "delete": true
            }
        }
    ],
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型      | 描述                         |
| ------- |---------| -------------------------- |
| result  | bool    | 请求成功与否。true:请求成功；false请求失败 |
| code    | int     | 错误编码。 0表示success，>0表示失败错误  |
| message | string  | 请求失败返回的错误信息                |
| data    | array   | 请求返回的数据，见data定义            |

#### data

| 字段            | 类型     | 描述                    |
| ------------- |--------| --------------------- |
| bk_cloud_id   | int    | 管控区域ID                 |
| bk_cloud_name | string | 管控区域名称                 |
| isp           | string | 云服务商                  |
| ap_id         | int    | 接入点ID，-1代表自动选择接入点     |
| is_visible    | string | 是否可见                  |
| node_count    | int    | 主机数量                  |
| proxy_count   | int    | proxy主机数量             |
| ap_name       | string | 接入点名称                 |
| isp_name      | string | 云服务商名称                |
| isp_icon      | string | 云服务商图标                |
| exception     | string | 管控区域内异常的信息             |
| proxies       | array  | 管控区域内异常的Proxy          |
| permissions   | object | 对应操作权限，见permissions定义 |

##### permissions

| 状态类型   | 类型   | 描述   |
| ------ | ---- | ---- |
| view   | bool | 查看权限 |
| edit   | bool | 编辑权限 |
| delete | bool | 删除权限 |
