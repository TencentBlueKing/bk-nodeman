### 功能描述

查询安装通道详情

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段          | 类型   | <div style="width: 50pt">必选</div> | 描述         |
| ----------- | ---- | --------------------------------- | ---------- |
| with_hidden | bool | 否                                 | 是否包括隐藏安装通道 |

### 请求参数示例

```json
{
    "bk_app_code": "esb_test",
    "bk_app_secret": "xxx",
    "bk_username": "admin",
    "bk_token": "xxx",
    "with_hidden": true
}
```

### 返回结果示例Ï

```json
{
    "result": true,
    "data": [
        {
            "id": 1,
            "name": "默认安装通道",
            "bk_cloud_id": 0,
            "jump_servers": [
                "127.0.0.1"
            ],
            "upstream_servers": {
                "dataserver": [
                    "127.0.0.2",
                    "127.0.0.3"
                ],
                "taskserver": [
                    "127.0.0.2",
                    "127.0.0.3"
                ],
                "btfileserver": [
                    "127.0.0.2",
                    "127.0.0.3"
                ]
            },
            "hidden": false
        },
        {
            "id": 2,
            "name": "隐藏安装通道",
            "bk_cloud_id": 0,
            "jump_servers": [
                "127.0.0.4"
            ],
            "upstream_servers": {
                "dataserver": [
                    "127.0.0.4",
                    "127.0.0.5"
                ],
                "taskserver": [
                    "127.0.0.4",
                    "127.0.0.5"
                ],
                "btfileserver": [
                    "127.0.0.4",
                    "127.0.0.5"
                ]
            },
            "hidden": true
        }
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
| data    | array  | 请求返回的数据，见data定义            |

#### data

| 字段               | 类型           | <div style="width: 50pt">必选</div> | 描述                                |
| ---------------- | ------------ | --------------------------------- | --------------------------------- |
| id               | int          | 是                                 | 安装通道ID                            |
| name             | string       | 是                                 | 安装通道名称                            |
| bk_cloud_id      | int          | 是                                 | 安装通道管控区域 ID                       |
| jump_servers     | string array | 是                                 | 安装通道跳板机 IP                        |
| upstream_servers | object       | 是                                 | 安装通道上游 GSE 地址，见 stream_servers 定义 |
| hidden           | bool         | 是                                 | 是否为隐藏安装通道                         |

##### upstream_servers

| 字段           | 类型           | <div style="width: 50pt">必选</div> | 描述            |
| ------------ | ------------ | --------------------------------- | ------------- |
| dataserver   | string array | 是                                 | GSE 数据服务器列表   |
| taskserver   | string array | 是                                 | GSE 任务服务器列表   |
| btfileserver | string array | 是                                 | GSE BT文件服务器列表 |
