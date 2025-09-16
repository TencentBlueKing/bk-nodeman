### Function Description

Plugin status operation

### Request Parameters

#### Interface Parameters

| Field       | Type        | <div style="width: 50pt">Required</div> | Description                                                                       |
|-------------|-------------|-----------------------------------------|-----------------------------------------------------------------------------------|
| operation   | string      | Yes                                     | Status operation to perform. Supported values: `ready` (enable), `stop` (disable) |
| id          | int array   | Yes                                     | List of plugin IDs to apply the operation on                                      |


### Request Example

```json
{
    "operation": "stop",
    "id": [1, 2]
}
```

### Response Example

```json
{
    "result": true,
    "data": [1, 2],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field     | Type     | Description                                                            |
|-----------|----------|------------------------------------------------------------------------|
| result    | bool     | Indicates whether the request succeeded. true: success; false: failure |
| code      | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
| message   | string   | Error message returned when the request fails                          |
| data      | object   | Data returned by the request, see definition below                     |

#### data

| Field  | Type       | Description                                            |
|--------|------------|--------------------------------------------------------|
| data   | int array  | List of plugin IDs that were successfully operated on  |