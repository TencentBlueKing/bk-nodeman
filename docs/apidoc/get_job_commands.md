### 功能描述

获取安装命令

### 请求参数

{{common_args_desc }}

#### 路径参数

| 字段 | 类型 | <div style="width: 50pt">必选</div> | 描述   |
| ---- | ---- | ----------------------------------- | ------ |
| pk   | int  | 是                                  | 任务ID |

#### 接口参数

| 字段         | 类型 | <div style="width: 50pt">必选</div> | 描述       |
| ------------ | ---- | ----------------------------------- | ---------- |
| bk_host_id   | int  | 是                                  | 主机ID     |
| is_uninstall | bool | 否                                  | 是否为卸载 |

### 请求参数示例

```json
{
    "bk_app_code": "esb_test",
    "bk_app_secret": "xxx",
    "bk_username": "admin",
    "bk_host_id": 1
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "solutions": [
            {
                "type": "shell",
                "description": "通过 bash 进行安装",
                "steps": [
                    {
                        "type": "commands",
                        "contents": [
                            {
                                "name": "create_dir",
                                "text": "sudo mkdir -p /tmp/",
                                "description": "创建 /tmp/",
                                "child_dir": null,
                                "show_description": false,
                                "always_download": false
                            }
                        ],
                        "description": "创建依赖目录"
                    },
                    {
                        "type": "commands",
                        "contents": [
                            {
                                "name": "combine",
                                "text": "curl setup_agent.sh -o /tmp/setup_agent.sh && chmod +x /tmp/setup_agent.sh'",
                                "description": "下载安装脚本并赋予执行权限",
                                "child_dir": null,
                                "show_description": false,
                                "always_download": false
                            }
                        ],
                        "description": "下载安装脚本并赋予执行权限"
                    },
                    {
                        "type": "commands",
                        "contents": [
                            {
                                "name": "run_cmd",
                                "text": "bash /tmp/setup_agent.sh",
                                "description": "执行安装脚本",
                                "child_dir": null,
                                "show_description": false,
                                "always_download": false
                            }
                        ],
                        "description": "执行安装脚本"
                    }
                ],
                "target_host_solutions": []
            }
        ]
    },
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段    | 类型   | 描述                                       |
| ------- | ------ | ------------------------------------------ |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误    |
| message | string | 请求失败返回的错误信息                     |
| data    | object | 请求返回的数据，见data定义                 |

#### data

| 字段      | 类型  | 描述                      |
| --------- | ----- | ------------------------- |
| solutions | array | 安装方案，见solutions定义 |

##### solutions

| 字段                  | 类型   | 描述                  |
| --------------------- | ------ | --------------------- |
| type                  | string | 脚本执行类型          |
| description           | string | 脚本执行类型描述      |
| target_host_solutions | array  | 执行目标方案          |
| steps                 | array  | 安装步骤，见steps定义 |

###### steps

| 字段        | 类型   | 描述                         |
| ----------- | ------ | ---------------------------- |
| type        | string | 安装步骤类型                 |
| description | string | 安装步骤动作描述             |
| contents    | array  | 安装步骤内容，见contents定义 |

###### contents

| 字段             | 类型   | 描述             |
| ---------------- | ------ | ---------------- |
| name             | string | 安装内容名称     |
| text             | string | 安装命令         |
| description      | string | 安装命令描述     |
| child_dir        | string | 子路径           |
| show_description | bool   | 是否展示描述信息 |
| always_download  | bool   | 是否实时更新     |
