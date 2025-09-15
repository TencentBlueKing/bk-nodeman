### Function Description

Statistic subscription task data

### Request Parameters

#### Interface Parameters

| Field                  | Type        | <div style="width: 50pt">Required</div> | Description               |
|------------------------|-------------|-----------------------------------------|---------------------------|
| subscription_id_list   | int array   | Yes                                     | List of subscription IDs  |

### Request Example

```json
{
    "subscription_id_list": [100, 101]
}
```

### Response Example

```json
{
    "result": true,
    "data": [
        {
            "subscription_id": 100,
            "status": [
                {
                    "status": "SUCCESS",
                    "count": 3
                },
                {
                    "status": "PENDING",
                    "count": 0
                },
                {
                    "status": "FAILED",
                    "count": 0
                },
                {
                    "status": "RUNNING",
                    "count": 0
                }
            ],
            "versions": [
                {
                    "version": "7.7.2-rc.29",
                    "count": 3,
                    "name": "bkunifylogbeat"
                }
            ],
            "instances": 3
        },
        {
            "subscription_id": 101,
            "status": [
                {
                    "status": "SUCCESS",
                    "count": 2
                },
                {
                    "status": "PENDING",
                    "count": 0
                },
                {
                    "status": "FAILED",
                    "count": 0
                },
                {
                    "status": "RUNNING",
                    "count": 0
                }
            ],
            "versions": [
                {
                    "version": "7.7.2-rc.29",
                    "count": 3,
                    "name": "bkmonitorbeat"
                }
            ],
            "instances": 2
        }
    ],
    "code": 0,
    "message": ""
}
```

### Response Parameters Description

#### response

| Field    | Type      | Description                                                            |
|----------|-----------|------------------------------------------------------------------------|
| result   | bool      | Indicates whether the request succeeded. true: success; false: failure |
| code     | int       | Error code. 0 indicates success; values greater than 0 indicate errors |
| message  | string    | Error message returned when the request fails                          |
| data     | array     | Data returned by the request, see definition below                     |

#### data

| Field             | Type    | Description                                              |
|-------------------|---------|----------------------------------------------------------|
| subscription_id   | int     | Subscription ID                                          |
| status            | array   | List of status counts. See `status` definition           |
| versions          | array   | List of version distributions. See `versions` definition |
| instances         | int     | Total number of instances under this subscription        |

##### status

| Field  | Type     | Description                                                 |
|--------|----------|-------------------------------------------------------------|
| status | string   | Execution status: `SUCCESS`, `PENDING`, `FAILED`, `RUNNING` |
| count  | int      | Number of instances in this status                          |

##### versions

| Field    | Type     | Description                              |
|----------|----------|------------------------------------------|
| version  | string   | Plugin version                           |
| count    | int      | Number of instances running this version |
| name     | string   | Plugin name                              |