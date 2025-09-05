### 功能描述

获取一个导出任务结果

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段      | 类型  | <div style="width: 50pt">必选</div> | 描述   |
|---------| --- | --------------------------------- |------|
| job_id | int | 是                                 | 任务ID |

### 请求参数示例

```json
{
  "job_id": 123456
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "is_finish": true,
        "is_failed": false,
        "download_url": "http://127.0.0.1//backend/export/download/",
        "error_message": "haha"
    },
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型      | 描述                         |
| ------- |---------|----------------------------|
| result  | bool    | 请求成功与否。true:请求成功；false请求失败 |
| code    | int     | 错误编码。 0表示success，>0表示失败错误  |
| message | string  | 请求失败返回的错误信息                |
| data    | array   |  请求返回的数据，见data定义           |

#### data

| 字段            | 类型     | <div style="width: 50pt">必选</div> | 描述      |
|---------------|--------|-----------------------------------|---------|
| is_finish     | bool   | 是                                 | 是否完成    |
| is_failed     | bool   | 是                                 | 是否失败    |
| download_url  | string | 是                                 | 文件下载url |
| error_message | string | 是                                 | 错误日志内容  |
