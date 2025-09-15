### Function Description

Switch subscription

### Request Parameters

#### Interface Parameters

| Field             | Type     | <div style="width: 50pt">Required</div> | Description                                                                      |
|-------------------|----------|-----------------------------------------|----------------------------------------------------------------------------------|
| subscription_id   | int      | Yes                                     | Subscription ID to be operated on                                                |
| action            | string   | Yes                                     | Control action: `enable` to activate, `disable` to deactivate the subscription   |

### Request Example

```json
{
    "subscription_id": 1,
    "action": "disable"
}
```

### Response Example

```json
{
    "result": true,
    "code": 0,
    "message": "success",
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
