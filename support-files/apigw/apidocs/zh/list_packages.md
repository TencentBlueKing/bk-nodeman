### 功能描述

查询进程包列表

### 请求参数

{{ common_args_desc }}

#### 接口参数

| 字段      | 类型     | <div style="width: 50pt">必选</div> | 描述   |
|---------|--------| --------------------------------- | ---- |
| process | string | 是                                 | process为具体进程名 |

### 请求参数示例

```json
{
    "process": "bkmonitorbeat"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": [
      {
        "id":2,
        "pkg_name":"basereport-10.1.12.tgz",
        "version":"10.1.12",
        "module":"gse_plugin",
        "project":"basereport",
        "pkg_size":4561957,
        "pkg_path":"/data/bkee/miniweb/download/linux/x86_64",
        "md5":"046779753b6709635db0c861a1b0020e",
        "pkg_mtime":"2019-11-01 20:46:52.404139",
        "pkg_ctime":"2019-11-01 20:46:52.404139",
        "location":"http://x.x.x.x/download/linux/x86_64",
        "os":"linux",
        "cpu_arch":"x86_64"
      },
      {
        "id":1,
        "pkg_name":"basereport-10.1.9.tgz",
        "version":"10.1.9",
        "module":"gse_plugin",
        "project":"basereport",
        "pkg_size":4562217,
        "pkg_path":"/data/bkee/miniweb/download/linux/x86_64",
        "md5":"6fe084f450352b1fa598a41a72800bc8",
        "pkg_mtime":"2019-08-26 19:17:56.905309",
        "pkg_ctime":"2019-08-26 19:17:56.905309",
        "location":"http://x.x.x.x/download/linux/x86_64",
        "os":"linux",
        "cpu_arch":"x86_64"
      }
    ],
    "code": 0,
    "message": ""
}
```

### 返回结果参数说明

#### response

| 字段      | 类型           | 描述                         |
| ------- | ------------ | -------------------------- |
| result  | bool         | 请求成功与否。true:请求成功；false请求失败 |
| code    | int          | 错误编码。 0表示success，>0表示失败错误  |
| message | string       | 请求失败返回的错误信息                |
| data    | array | 请求返回的数据，见data定义            |
