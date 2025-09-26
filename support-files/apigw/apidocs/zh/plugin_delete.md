 ### 功能描述

 删除插件

 ### 请求参数

 #### 接口参数

 | 字段    | 类型   | <div style="width: 50pt">必选</div> | 描述  |
 |-------|------| --------------------------------- |-----|
 | name  | int  | 是                                 | 插件名 |

 ### 请求参数示例

 ```json
 {
     "name": "prometheus_poe_exporter"
 }
 ```

 ### 返回结果示例

 ```json
 {
     "result": true,
     "code": 0,
     "message": "",
     "data": null
 }
 ```

 ### 返回结果参数说明

 #### response

 | 字段      | 类型     | 描述                         |
 | ------- |--------| -------------------------- |
 | result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
 | code    | int    | 错误编码。 0表示success，>0表示失败错误  |
 | message | string | 请求失败返回的错误信息                |
 | data    | null   | 请求返回的数据                    |
