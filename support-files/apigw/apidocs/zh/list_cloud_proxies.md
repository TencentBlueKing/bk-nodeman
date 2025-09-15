### 功能描述

查询管控区域下proxy列表

### 请求参数

#### 接口参数

| 字段          | 类型  | <div style="width: 50pt">必选</div> | 描述       |
| ----------- | --- |----------------------------------|----------|
| bk_cloud_id | int | 是                                | 管控区域 ID  |

### 请求参数示例

```json
{
    "bk_cloud_id": 1
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
        {
            "bk_cloud_id": 1,
            "bk_host_id": 1,
            "inner_ip": "127.0.0.1",
            "inner_ipv6": "",
            "outer_ip": "127.0.0.2",
            "outer_ipv6": "",
            "login_ip": "127.0.0.3",
            "data_ip": "",
            "bk_biz_id": 331,
            "is_manual": true,
            "extra_data": {
                "data_path": "/var/lib/gse",
                "bt_speed_limit": null,
                "peer_exchange_switch_for_agent": 0,
                "enable_compression": false
            },
            "bk_biz_name": "test",
            "ap_id": 1,
            "ap_name": "默认接入点",
            "status": "TERMINATED",
            "status_display": "异常",
            "version": "",
            "account": "root",
            "auth_type": "MANUAL",
            "port": 22,
            "re_certification": true,
            "job_result": {
                
            },
            "pagent_count": 0,
            "permissions": {
                "operate": true
            }
        }
    ],
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型     | 描述                         |
| ------- |--------| -------------------------- |
| result  | bool   | 请求成功与否。true:请求成功；false请求失败 |
| code    | int    | 错误编码。 0表示success，>0表示失败错误  |
| message | string | 请求失败返回的错误信息                |
| data    | array  | 请求返回的数据，见data定义            |

#### data

| 字段                | 类型       | 描述                                                      |
|-------------------|----------|---------------------------------------------------------|
| bk_cloud_id       | int      | 管控区域ID                                                  |
| bk_host_id        | int      | 主机ID                                                    |
| inner_ip          | string   | 内网IPv4地址                                                |
| inner_ipv6        | string   | 内网IPv6地址                                                |
| outer_ip          | string   | 外网IPv4地址                                                |
| outer_ipv6        | string   | 外网IPv6地址                                                |
| login_ip          | string   | 登录IP                                                    |
| data_ip           | string   | 数据IP                                                    |
| bk_biz_id         | string   | 业务ID                                                    |
| is_manual         | string   | 是否手动安装模式                                                |
| extra_data        | string   | 额外信息，见extra_data定义                                      |
| bk_biz_name       | string   | 业务名称                                                    |
| ap_id             | int      | 接入点ID                                                   |
| ap_name           | string   | 接入点名称                                                   |
| status            | string   | 运行状态，见status定义                                          |
| status_display    | string   | 运行执行状态名称，见status定义                                      |
| version           | string   | Agent版本                                                 |
| account           | string   | 用户名                                                     |
| auth_type         | string   | 认证类型，1：PASSWORD，密码认证 2: KEY，秘钥认证 3：TJJ_PASSWORD，默认为密码认证 |
| port              | string   | 登录端口                                                    |
| re_certification  | bool     | 鉴权信息是否过期                                                |
| job_result        | object   | 执行任务结果，见job_result定义                                    |
| pagent_count      | int      | 使用proxy的PAGENT个数                                        |
| permissions       | object   | 是否具备操作权限                                                |

##### extra_data

| 字段                             | 类型     | 描述                 |
| ------------------------------ | ------ | ------------------ |
| bt_speed_limit                 | int    | bt传输限制速度值，单位M/s    |
| peer_exchange_switch_for_agent | int    | bt传输开关，1: 开启 0: 关闭 |
| data_path                      | string | 数据文件路径             |
| enable_compression             | bool   | 数据压缩开关             |

##### status

| 状态类型          | 类型     | 描述   |
| ------------- | ------ | ---- |
| RUNNING       | string | 运行中  |
| UNKNOWN       | string | 未知状态 |
| TERMINATED    | string | 已终止  |
| NOT_INSTALLED | string | 未安装  |
| UNREGISTER    | string | 未注册  |
| REMOVED       | string | 已移除  |
| MANUAL_STOP   | string | 手动停止 |

##### job_result

| 字段             | 类型       | 描述                 |
|----------------|----------|--------------------|
| instance_id    | string   | 实例ID               |
| job_id         | int      | 作业ID               |
| status         | string   | 执行状态，见job_status定义 |
| current_step   | string   | 当前步骤名称             |
