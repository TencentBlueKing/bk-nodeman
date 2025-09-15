### Function Description

List all install channels

### Request Parameters

#### Interface Parameters

| Field         | Type   | <div style="width: 50pt">Required</div> | Description                                      |
|---------------|--------|-----------------------------------------|--------------------------------------------------|
| with_hidden   | bool   | No                                      | Whether to include hidden installation channels  | 

### Request Example

```json
{
    "with_hidden": true
}
```

### Response Example

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

### Response Parameters Description

#### response

| Field     | Type    | Description                                                            |
|-----------|---------|------------------------------------------------------------------------|
| result    | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code      | int     | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string  | Error message returned when the request fails                          |
| data      | array   | Data returned by the request, see definition below                     |

#### data

| Field             | Type          | Description                                                    |
|-------------------|---------------|----------------------------------------------------------------|
| id                | int           | Installation channel ID                                        |
| name              | string        | Installation channel name                                      |
| bk_cloud_id       | int           | Cloud area ID of the installation channel                      |
| jump_servers      | string array  | Jump server IPs for the installation channel                   |
| upstream_servers  | object        | Upstream GSE server addresses, see upstream_servers definition |
| hidden            | bool          | Whether the channel is hidden                                  |

##### upstream_servers

| Field         | Type             | Description                   |
|---------------|------------------|-------------------------------|
| dataserver    | string array     | List of GSE data servers      |
| taskserver    | string array     | List of GSE task servers      |
| btfileserver  | string array     | List of GSE BT file servers   |
