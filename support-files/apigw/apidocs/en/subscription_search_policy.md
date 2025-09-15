### Function Description

Search deploy policy

### Request Parameters

#### Interface Parameters

| Field        | Type         | <div style="width: 50pt">Required</div> | Description                                                                              |
|--------------|--------------|-----------------------------------------|------------------------------------------------------------------------------------------|
| bk_biz_ids   | int array    | No                                      | List of business IDs to filter strategies                                                |
| only_root    | bool         | No                                      | Whether to return only root (top-level) strategies. Default: `false`                     |
| conditions   | array        | No                                      | Search conditions for filtering strategies.                                              |
| page         | int          | No                                      | Page number for pagination. Default: `1`                                                 |
| pagesize     | int          | No                                      | Number of items per page. Default: `10`                                                  |
| ordering     | object       | No                                      | Specifies sort order for results. Example: `{ "field": "update_time", "order": "desc" }` |

### Request Example

```json
{
    "bk_biz_ids": [
        555,
        100791
    ],
    "only_root": true,
    "conditions": [
        {
            "key": "plugin_name",
            "value": "bkmonitorbeat"
        }
    ],
    "page": 1,
    "pagesize": 20
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "total": 10,
        "list": [
            {
                "id": 1,
                "name": "日志采集",
                "plugin_name": "basereport",
                "nodes_scope": {
                    "host_count": 99,
                    "node_count": 123
                },
                "bk_biz_scope": [1, 2, 3],
                "operator": "admin",
                "updated_at": "2020-07-26 19:17:56"
            },
            {
                "id": 2,
                "name": "日志采集2",
                "plugin_name": "basereport",
                "nodes_scope": {
                    "host_count": 80,
                    "node_count": 123
                },
                "bk_biz_scope": [1, 2],
                "operator": "admin",
                "updated_at": "2020-07-26 19:17:56"
            }
        ]
    },
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
| data      | object  | Data returned by the request, see definition below                     |

#### data

| Field         | Type          | Description                                          |
|---------------|---------------|------------------------------------------------------|
| id            | int           | Strategy ID                                          |
| name          | string        | Strategy name                                        |
| plugin_name   | string        | Plugin name associated with the strategy             |
| nodes_scope   | object        | Node scope defining the target topology or instances |
| bk_biz_scope  | int array     | List of business IDs that the subscription monitors  |
| operator      | string        | User who last operated on the strategy               |
| updated_at    | string        | Last update time                                     |
