### Function Description

Start debug

### Request Parameters

#### Interface Parameters

| Field           | Type     | <div style="width: 50pt">Required</div> | Description                                                                                          |
|-----------------|----------|-----------------------------------------|------------------------------------------------------------------------------------------------------|
| plugin_id       | int      | No                                      | Unique ID of the plugin to debug                                                                     |
| plugin_name     | string   | No                                      | Name of the plugin to debug.                                                                         |
| version         | string   | No                                      | Version of the plugin to debug.                                                                      |
| config_ids      | array    | No                                      | List of configuration template IDs to apply during debugging.                                        |
| object_type     | string   | No                                      | Type of the target object (e.g., `HOST`, `SERVICE`).                                                 |
| node_type       | string   | No                                      | Type of the node (e.g., `AGENT`, `PROXY`, `PLUGIN`).                                                 |
| host_info       | object   | No                                      | Target host information. Required if debugging on a host. See host_info definition.                  |
| instance_info   | object   | No                                      | Target instance information. Required if debugging on a CMDB instance. See instance_info definition. |

#### host_info

| Field             | Type     | <div style="width: 50pt">Required</div> | Description                     |
|-------------------|----------|-----------------------------------------|---------------------------------|
| bk_host_id        | int      | No                                      | Host ID in CMDB                 |
| ip                | string   | No                                      | IP address of the target host   |
| bk_cloud_id       | int      | No                                      | Cloud area ID                   |
| bk_supplier_id    | int      | No                                      | Supplier ID (usually 0)         |
| bk_biz_id         | int      | No                                      | Business ID the host belongs to |

| Field        | Type    | Required  | Description                                      |
|--------------|---------|-----------|--------------------------------------------------|
| bk_biz_id    | int     | Yes       | Business ID the instance belongs to              |
| id           | int     | No        | Custom instance ID                               |
| bk_inst_id   | string  | No        | Instance ID in CMDB                              |
| bk_obj_id    | string  | No        | Object ID (model) in CMDB (e.g., `biz`, `set`)   |


### Request Example

```json
{
    "plugin_name": "tagent_monitor",
    "version": "1.1",
    "config_ids": [
        11573,
        11573
    ],
    "host_info": {
        "bk_supplier_id": 0,
        "bk_host_id": 100,
        "bk_biz_id": 10
    }
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "task_id": 123456789
    },
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Type     | Description                                                            |
|----------|----------|------------------------------------------------------------------------|
| result   | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code     | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string   | Error message returned when the request fails                          |
| data     | object   | Data returned by the request, see definition below                     |

#### data

| Field    | Type  | Description                                                                 |
|----------|-------|-----------------------------------------------------------------------------|
| task_id  | int   | Unique ID of the initiated debug task, used for subsequent status polling   |

