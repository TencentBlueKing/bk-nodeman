### Function Description

enable/disable business subscription inspection

### Request Parameters

#### Interface Parameters

| Field       | Type        | <div style="width: 50pt">Required</div> | Description                                                                                                  |
|-------------|-------------|-----------------------------------------|--------------------------------------------------------------------------------------------------------------|
| bk_biz_ids  | int array   | Yes                                     | List of business IDs to apply the action on                                                                  |
| action      | string      | Yes                                     | Control action: `enable` to activate inspection, `disable` to deactivate inspection for the given businesses |


### Request Example

```json
{
    "bk_biz_ids": [78],
    "action": "enable"
}
```

### Response Example

```json
{
    "result": true,
    "data": {
        "bk_biz_ids": [
            78
        ],
        "action": "enable"
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

| Field       | Type        | Description                                                                          |
|-------------|-------------|--------------------------------------------------------------------------------------|
| bk_biz_ids  | int array   | List of business IDs                                                                 |
| action      | string      | The performed action: `enable` or `disable`, indicating inspection status control    |

