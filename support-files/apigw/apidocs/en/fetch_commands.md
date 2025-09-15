### Function Description

Fetch installation commands

### Request Parameters

#### Interface Parameters

| Field                    | Type   | <div style="width: 50pt">Required</div> | Description                           |
|--------------------------|--------|-----------------------------------------|---------------------------------------|
| bk_host_id               | int    | Yes                                     | Host ID                               |
| sub_inst_id              | int    | Yes                                     | Instance ID                           |
| host_install_pipeline_id | string | Yes                                     | Host installation pipeline ID         |
| is_uninstall             | bool   | Yes                                     | Whether it is an uninstall operation  |

### Request Example

```json
{
    "bk_host_id": 101536,
    "host_install_pipeline_id": "093c4a90c32d43b58e7384e4f5f52ccb",
    "is_uninstall": false,
    "sub_inst_id": 1682256
}
```

### Response Example

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
                                "text": "nohup bash /tmp/setup_agent.sh -O 28668 -E 28925 -A 28625 -V 58931 -B 20020 -S 60020 -Z 60030 -K 20030 -e",
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

### Response Parameters Description

#### response

| Field    | Type     | Description                         |
|----------|----------| -------------------------- |
| result   | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code     | int      | Error code. 0 indicates success; values greater than 0 indicate errors  |
| message  | string   | Error message returned when the request fails                |
| data     | object   | Data returned by the request, see definition below            |

#### data

| Field       | Type  | Description                                       |
|-------------| ----- |---------------------------------------------------|
| solutions   | array | Installation solutions, see solutions definition  |

##### solutions

| Field                 | Type   | Description                               |
|-----------------------|--------|-------------------------------------------|
| type                  | string | Script execution type                     |
| description           | string | Description of script execution type      |
| target_host_solutions | array  | Target host execution solutions           |
| steps                 | array  | Installation steps, see steps definition  |

###### steps

| Field        | Type   | Description                             |
|--------------| ------ |-----------------------------------------|
| type         | string | Step type                               |
| description  | string | Description of the step action          |
| contents     | array  | Step contents, see contents definition  |

###### contents

| Field             | Type   | Description                     |
|-------------------| ------ |---------------------------------|
| name              | string | Name of the content             |
| text              | string | Installation command            |
| description       | string | Description of the command      |
| child_dir         | string | Subdirectory                    |
| show_description  | bool   | Whether to display description  |
| always_download   | bool   | Whether to update in real time  |


