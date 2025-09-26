 ### Function Description

Check task ready

 ### Request Parameters

 #### Interface Parameters

 | Field            | Type        | <div style="width: 50pt">Required</div> | Description        |
 |------------------|-------------|-----------------------------------------|--------------------|
 | subscription_id  | int         | Yes                                     | Subscription ID    |
 | task_id_list     | int array   | No                                      | List of task IDs   |

 ### Request Example

 ```json
 {
     "subscription_id": 1
 }
 ```

 ### Response Example

 ```json
 {
     "result": true,
     "code": 0,
     "message": "",
     "data": true
 }
 ```

 ### Response Parameters Description

 #### response

 | Field    | Type     | Description                                                            |
 |----------|----------|------------------------------------------------------------------------|
 | result   | bool     | Indicates whether the request succeeded. true: success; false: failure |
 | code     | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
 | message  | string   | Error message returned when the request fails                          |
 | data     | bool     | Data returned by the request                                           |
