### 功能描述

上传文件接口

### 请求参数

#### 接口参数

| 字段              | 类型       | <div style="width: 50pt">必选</div> | 描述                                |
|-----------------|----------| --------------------------------- |-----------------------------------|
| md5             | string   | 是                                 | 上传端计算的文件md5                       |
| file_name       | string   | 是                                 | 上传端提供的文件名                         |
| module          | string   | 否                                 | 插件所属模块                            |
| download_url    | string   | 否                                 | 文件下载url                           |
| file_path       | string   | 否                                 | 文件保存路径，和 file_path 两种参数模式至少要有一种满足 |

### 请求参数示例

```json
{
  "md5": "e86c07536ada151dd85ca533874e8883",
  "file_name": "bkmonitorbeat-2.0.48.tgz",
  "download_url": "http://xxxx/bkmonitorbeat-2.0.48.tgz"
}
```

### 返回结果示例

```json
{
    "result": true,
    "data": {
        "id": 1,
        "name": "bkmonitorbeat-2.0.48.tgz",
        "pkg_size": "2333"
    },
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
| data    | object | 请求返回的数据，见data定义            |

#### data

| 字段                 | 类型     | 描述    |
|--------------------|--------|-------|
| id                 | int    | 插件包id |
| name               | string | 包名    |
| pkg_size           | string | 包大小   |

