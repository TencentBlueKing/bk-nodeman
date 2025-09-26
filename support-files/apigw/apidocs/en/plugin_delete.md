 ### Function Description

 Delete plugin

 ### Request Parameters

 #### Interface Parameters

 | Field | Type   | <div style="width: 50pt">Required</div> | Description   |
 |-------|--------|-----------------------------------------|---------------|
 | name  | int    | Yes                                     | Plugin name   |

 ### Request Example

 ```json
 {
     "name": "prometheus_poe_exporter"
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

 | Field     | Type     | Description                                                            |
 |-----------|----------|------------------------------------------------------------------------|
 | result    | bool     | Indicates whether the request succeeded. true: success; false: failure |
 | code      | int      | Error code. 0 indicates success; values greater than 0 indicate errors |
 | message   | string   | Error message returned when the request fails                          |
 | data      | null     | Data returned by the request                                           |
