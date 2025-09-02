 ### 功能描述

根据用户手动输入的`IP`/`IPv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息

 ### 请求参数

 {{ common_args_desc }}

 #### 接口参数

| 字段           | 类型     | <div style="width: 50pt">必选</div> | 描述                                        |
|--------------|--------|-----------------------------------|-------------------------------------------|
| ip_list      | array  | 否                                 | IPv4 列表，支持的输入格式：`cloud_id:ip` / `ip`"     |
| ipv6_list    | array  | 否                                 | IPv6 列表，支持的输入格式：`cloud_id:ipv6` / `ipv6`" |
| key_list     | array  | 否                                 | 关键字列表，解析出的`主机名`、`host_id` 等关键字信息          |
| search_limit | object | 否                                 | 检索范围限制                                    |
| all_scope    | bool   | 否                                 | 是否获取所有资源范围的拓扑结构，默认为 `false`"              |
| scope_list   | array  | 否                                 | 要获取拓扑结构的资源范围数组                            |
| action       | string | 否                                 | 权限类型，默认为`agent_view`,见 action 定义 |

###### action

| 字段              | 类型     | 描述      |
|-----------------| ------ |---------|
| agent_view      | string | agent查询 |
| agent_operate   | string | agent操作 |
| proxy_operate   | string | proxy操作 |
| plugin_view     | string | 插件查看    |
| plugin_operate  | string | 插件操作    |
| strategy_view   | string | 策略查看    |
| strategy_create | string | 策略创建    |


 ### 请求参数示例
```
{
    "ip_list": ["127.0.0.1"],
    "all_scope": true
}
 ```

 ### 返回结果示例

 ```json
{
    "result": true,
    "data": [
        {
            "meta": {
                "scope_type": "biz",
                "scope_id": "1",
                "bk_biz_id": 1
            },
            "host_id": 124,
            "agent_id": "0200000000525400e621961747626850980c",
            "ip": "127.0.0.1",
            "ipv6": "",
            "host_name": "",
            "os_name": "Linux",
            "os_type": "Linux",
            "alive": 1,
            "cloud_area": {
                "id": 0,
                "name": "直连区域"
            },
            "biz": {
                "id": 1,
                "name": "蓝鲸"
            },
            "bk_host_id": 124,
            "bk_biz_id": 1,
            "bk_agent_id": "0200000000525400e621961747626850980c",
            "bk_agent_alive": 1,
            "bk_cloud_id": 0
        }
    ],
    "code": 0,
    "message": ""
}
 ```

 ### 返回结果参数说明

 #### response

 | 字段      | 类型     | 描述                         |
 | ------- | ------ | -------------------------- |
 | result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
 | code    | int    | 错误编码。 0表示success，>0表示失败错误  |
 | message | string | 请求失败返回的错误信息                |
 | data    | object | 请求返回的数据                    |
