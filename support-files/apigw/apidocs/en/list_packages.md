### Function Description

Query the plugin package list

### Request Parameters

#### Interface Parameters

| Field    | Type     | <div style="width: 50pt">Required</div> | Description                                             |
|----------|----------|-----------------------------------------|---------------------------------------------------------|
| process  | string   | Yes                                     | Specific process name                                   |
| os       | string   | Yes                                     | Operating System: `LINUX`, `WINDOWS`, `AIX`, `SOLARIS`  |


### Request Example

```json
{
    "process": "bkmonitorbeat",
    "os": "linux"
}
```

### Response Example

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

### Response Parameters Description

#### response

| Field      | Type     | Description                         |
| ------- |--------| -------------------------- |
| result  | bool   | Indicates whether the request succeeded. true: success; false: failure |
| code    | int    | Error code. 0 indicates success; values greater than 0 indicate errors  |
| message | string | Error message returned when the request fails                |
| data    | array  | Data returned by the request, see definition below            |

#### data

| Field        | Type   | Description                 |
|--------------|--------|-----------------------------|
| id           | int    | Plugin package ID           |
| pkg_name     | string | Package file name           |
| version      | string | Plugin version              |
| module       | string | Subscription task name      |
| project      | string | Project name                |
| pkg_size     | int    | Package size in bytes       |
| pkg_path     | string | Package path                |
| md5          | string | MD5 checksum                |
| pkg_mtime    | string | Package modification time   |
| pkg_ctime    | string | Package creation time       |
| location     | string | Download URL of the package |
| os           | string | Operating system            |
| cpu_arch     | string | CPU architecture            |

