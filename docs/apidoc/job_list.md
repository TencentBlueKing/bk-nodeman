### 功能描述

任务历史

## 请求参数

{{ common_args_desc }}

### 接口参数
| 字段                   | 类型            | 必选 | 描述                                                                 | 示例值                                         |
|------------------------|-----------------|------|---------------------------------------------------------------------|---------------------------------------------|
| job_id               | list[int]       | 否   | 任务ID列表（多值查询）                                              | [5673379, 5673380]                          |
| status               | list[string]    | 否   | 任务状态（可选值：PENDING/RUNNING/SUCCESS/FAILED）           | ["SUCCESS", "RUNNING"]                      |
| created_by           | list[string]    | 否   | 任务创建者列表                                                      | ["admin", "user1"]                          |
| bk_biz_id            | list[int]       | 否   | 业务ID列表                                                          | [659, 702]                                  |
| inner_ip_list        | list[string]    | 否   | 主机内网IP列表                                     | ["10.0.0.1", "10.0.0.2"]                    |
| step_type            | list[string]    | 否   | 任务类型（可选值：AGENT/PLUGIN/PROXY）                         | ["AGENT", "PROXY"]                          |
| op_type              | list[string]    | 否   | 操作类型（可选值：INSTALL/REINSTALL/UPGRADE）                 | ["REINSTALL", "UPGRADE"]                    |
| policy_name          | list[string]    | 否   | 策略名称列表                                                        | ["策略A", "策略B"]                              |
| page                 | int             | 否   | 当前页数（默认1，范围：1-1000）                                  | 1                                           |
| pagesize             | int             | 否   | 分页大小（默认10，最大值：100）                                   | 20                                          |
| sort                 | object          | 否   | 排序规则（见下方👇）                                                | {"head": "total_count", "sort_type": "DEC"} |
| hide_auto_trigger_job| boolean         | 否   | 是否隐藏自动部署任务（默认false）                                 | true                                        |
| start_time           | string          | 否   | 任务开始时间范围起点（格式：YYYY-MM-DD HH:mm:ss）                 | "2025-06-01 00:00:00"                       |
| end_time             | string          | 否   | 任务开始时间范围终点（格式：YYYY-MM-DD HH:mm:ss）                 | "2025-06-30 23:59:59"                       |

#### sort 子对象
| 字段        | 类型   | 必选 | 描述                                                                 | 可选值                          |
|-------------|--------|------|---------------------------------------------------------------------|---------------------------------|
| head      | string | 是   | 排序字段：total_count（总数）failed_count（失败数）success_count（成功数） | total_count/failed_count/success_count |
| sort_type | string | 是   | 排序方式：ASC（升序）DEC（降序）                                  | ASC/DEC                     |

---

##  返回结果参数说明
### response
| 字段       | 类型    | 描述                          |
|------------|---------|-------------------------------|
| result   | bool    | 请求成功与否（true/false） |
| code     | int     | 错误码（0表示成功）          |
| message  | string  | 失败时的错误信息               |
| data     | object  | 返回数据（见下方👇）           |

### data
| 字段    | 类型          | 描述              |
|---------|---------------|-------------------|
| total | int           | 符合条件的总任务数 |
| list  | list[object]  | 任务列表          |

### list 
| 字段                  | 类型          | 描述                                                                 |
|-----------------------|---------------|---------------------------------------------------------------------|
| id                  | int           | 任务ID                                                              |
| created_by          | string        | 任务创建者                                                          |
| job_type            | string        | 任务类型（如 REINSTALL_AGENT）                                     |
| job_type_display    | string        | 任务类型显示名称（如“重装 Agent”）                                    |
| start_time          | string        | 任务开始时间（格式：YYYY-MM-DD HH:mm:ss+0800）                     |
| end_time            | string        | 任务结束时间（未完成时为 null）                                     |
| status              | string        | 任务状态（如 SUCCESS）                                             |
| cost_time           | string        | 任务耗时（单位：秒）                                                |
| bk_biz_scope_display| list[string]  | 业务名称列表（如 ["GSE"]）                                         |
| statistics          | object        | 任务统计信息（见下方👇）                                             |
| type                | string        | 任务对象类型（AGENT/PLUGIN/PROXY）                             |
| op_type             | string        | 操作类型（如 REINSTALL）                                           |
| op_type_display     | string        | 操作类型显示名称（如“重装”）                                          |

### statistics 统计对象
| 字段              | 类型  | 描述         |
|-------------------|-------|-------------|
| total_count     | int   | 总实例数     |
| failed_count    | int   | 失败实例数   |
| ignored_count   | int   | 忽略实例数   |
| pending_count   | int   | 等待执行数   |
| running_count   | int   | 正在执行数   |
| success_count   | int   | 成功实例数   |