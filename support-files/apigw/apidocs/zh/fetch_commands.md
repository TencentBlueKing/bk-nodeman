### 功能描述

返回安装命令

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段                       | 类型     | <div style="width: 50pt">必选</div> | 描述        |
|--------------------------|--------| --------------------------------- |-----------|
| bk_host_id               | string | 是                                 | 主机ID      |
| sub_inst_id              | string | 是                                 | 实例ID      |
| host_install_pipeline_id | string | 是                                 | 主机安装流水线ID |
| is_uninstall             | bool   | 是                                 | 是否为卸载     |

### 请求参数示例

```json
{
    "bk_host_id": 101536,
    "host_install_pipeline_id": "093c4a90c32d43b58e7384e4f5f52ccb",
    "is_uninstall": false,
    "sub_inst_id": 1682256
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
                                "name": "combine",
                                "text": "bash -c 'exec 2>&1 && mkdir -p /etc/sysconfig/gse/bkte/user_conf && mkdir -p /tmp/ && mkdir -p /usr/local/gse2_bkte/agent/data'",
                                "description": "创建依赖目录",
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
                                "text": "bash -c 'exec 2>&1 && curl http://127.0.0.1:17980//agent_tools/agent2/setup_agent.sh -o /tmp/setup_agent.sh --connect-timeout 5 -sSfg -x http://127.0.0.1:17981 && chmod +x /tmp/setup_agent.sh'",
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
                                "text": "nohup bash /tmp/setup_agent.sh -O 28668 -E 28925 -A 28625 -V 58931 -B 20020 -S 60020 -Z 60030 -K 20030 -e"
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

| 字段      | 类型     | 描述                         |
| ------- | ------ | -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | object | 请求返回的数据，见data定义            |

