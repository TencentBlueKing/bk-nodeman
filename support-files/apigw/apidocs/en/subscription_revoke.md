### Function Description

Revoke running task

### Request Parameters

#### Interface Parameters

| Field                | Type      | <div style="width: 50pt">Required</div> | Description                                                            |
|----------------------|-----------|-----------------------------------------|------------------------------------------------------------------------|
| subscription_id      | int       | Yes                                     | Subscription ID                                                        |
| instance_id_list     | array     | No                                      | List of instance IDs to terminate. See `instance_id_list` definition.  |

##### instance_id_list

Constructed from host instance information within the scope by concatenating the following fields: `{object_type}|{node_type}|{type}|{id}`. 
<br>Example: 1: `host|instance|host|1`  2: `host|instance|host|127.0.0.1-1-0`

| Field         | Type      | <div style="width: 50pt">Required</div> | Description                                                                                                                             |
|---------------|-----------|-----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| object_type   | string    | Yes                                     | Object type: `1`: `host` (host), `2`: `service` (service)                                                                               |
| node_type     | string    | Yes                                     | Node category: `1`: `topo` (dynamic instance/topology), `2`: `instance` (static instance), `3`: `service_template`, `4`: `set_template` |
| type          | string    | Yes                                     | Service type: `1`: `host` (host), `2`: `bk_obj_id` (template ID)                                                                        |
| id            | string    | Yes                                     | Service instance ID: <br>1. Generated from IP, `bk_cloud_id`, `bk_supplier_id` using delimiter "-" <br>2. `bk_host_id` (Host ID)        |

### Request Example

```json
{
    "subscription_id": 1,
    "instance_id_list": ["host|instance|host|1"]
}
```

### Response Example

```json
{
    "result": true,
    "code": 0,
    "message": "",
    "data": null
}
```

### Response Parameters Description

#### response

| Field     | Type    | Description                                                            |
|-----------|---------|------------------------------------------------------------------------|
| result    | bool    | Indicates whether the request succeeded. true: success; false: failure |
| code      | int     | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string  | Error message returned when the request fails                          |
| data      | null    | Data returned by the request                                           |
