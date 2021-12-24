# Release

## 2.1.363 - 2021-12-24 


### optimization: 
  * windows脚本兼容性优化 (fixed #397)

## 2.1.362 - 2021-12-24 


### optimization: 
  * 忽略无效拓扑节点 (close #191)
  * 重装 Agent Windows 登录端口自动更正 (close #363)
  * Agent 安装弹出参数校验失败列 (close #376)

### bugfix: 
  * 安装通道服务器文件同步
  * 跨页全选情况下安装通道没有默认值 (close #377)
  * 富容器场景Agent安装脚本问题修复 (fixed #384)
  * windows安装上报系统架构错误 (fixed #394)
  * Firefox 浏览器粘贴 IP 解析错误 (close #378)

### feature: 
  * 周期任务同步进程状态 (close #380)

## 2.1.361 - 2021-12-17 


### bugfix: 
  * P-Agent无法连接外网时，安装失败的问题 (fixed #354)
  * 使用私钥安装P-Agent时，校验key失败的问题 (fixed #365)

## 2.1.360 - 2021-12-16 


### bugfix: 
  * 使用私钥安装P-Agent时，校验key失败的问题 (fixed #365)
  * P-Agent无法连接外网时，安装失败的问题 (fixed #354)
  * 任务历史详情左侧IP列表分页异常 (fixed #349)
  * 编辑proxy密码报错系统错误 (fixed #355)
  * 表格锁边及滚动问题 (fixed #364)
  * 修复windows插件卸载失败的问题 (fixed #366)
  * 插件配置版本匹配不符合预期的问题 (fixed #357)

## 2.1.359 - 2021-12-14 


## 2.1.358 - 2021-12-14 


### optimization: 
  * 任务日志 优化error、debug类型展示 (close #333)
  * 下发插件匹配不到插件包时报错粒度优化 (close #250)

### feature: 
  * 新增CMDB进程实例监听，优化周期任务 (close #329)

### bugfix: 
  * 节点列表页面加载异常 (fixed #334)
  * 修复插件操作选择部署版本时报错无权限的问题 (closed #346)

## 2.1.357 - 2021-12-09 


### bugfix: 
  * 修复后台管理页面显示异常的问题 (fixed #330)

## 2.1.356 - 2021-12-08 


### optimization: 
  * 升级 Django3 (closed #111)

### feature: 
  * 敏感信息传输加密 (closed #226)
  * PaaS容器部署适配 (closed #10)
  * 灰度策略支持自定义输入多IP (closed #235)
  * 服务器文件迁移到存储源执行命令 (closed #260)
  * 更新Proxy文件兼容制品库 (close #181)
  * 展示自开插件的状态 (close #95)
  * 通过接口获得操作系统类型 (closed #230)
  * Windows Agent安装支持用administrator用户注册服务(close #277)
  * 新增安装通道上游配置项，适配更复杂网络场景 (closed #234)

### bugfix: 
  * 手动安装window机器补充curl.exe下载链接 (closed #321)
  * 修复访问后台接口出现 JWT 校验异常的问题 (fixed #323)

## 2.1.355 - 2021-11-04 


### bugfix: 
  * gse agent 缺少 dbgipc 配置项(close #244)
  * 手动安装p-agent,windows服务器失败(close #233)
  * 修复本地存储保存文件与源文件不一致的问题 (fixed #254)
  * 修复查询主机插件操作流水异常的问题 (fixed #252)

### optimization: 
  * 优化、统一用户退出操作  (closed #220)
  * workflow 优化 (#121)
  * 前端 api module 代码生成规范改进(closed #228)

### feature: 
  * 新增安装通道上游配置项，适配更复杂网络场景(close #234)

### docs: 
  * 安装通道多级代理nginx配置补充(closed #227)

## 2.1.354 - 2021-11-04 

### bugfix: 
  * gse agent 缺少 dbgipc 配置项(close #244)
  * 手动安装p-agent,windows服务器失败(close #233)
### optimization: 
  * 优化、统一用户退出操作  (closed #220)
  * workflow 优化 (#121)
  * 前端 api module 代码生成规范改进(closed #228)
### feature: 
  * 新增安装通道上游配置项，适配更复杂网络场景(close #234)
### docs: 
  * 安装通道多级代理nginx配置补充(closed #227)

## 2.1.353

- optimization
  - 统一'gsectl.bat'安装脚本的来源为gse对应的安装包 (closed #205)

## 2.1.353

- optimization
  - 统一'gsectl.bat'安装脚本的来源为gse对应的安装包 (closed #205)

## 2.1.352

- optimization
  - 添加DB重连机制 (close #211)
  - 2.0to2.1 升级脚本中虚拟环境的路径应取决于全局变量 (closed #207)
- bugfix
  - 修复移除主机后部署策略巡检执行异常的问题 (fixed #206)
  - windows的agent配置中pluginipc应该为47200 (fixed #210)
- feature
  - pre-commit 自动生成dev_log(closed #209)
- optmization
  - 安装agent时，获取配置文件失败时安装流程主动终止 (close #195)

## 2.1.351

- optimization
  - 策略名称移除仅包含汉字英文数字下划线的限制 (closed #198)
- bugfix
  - 修复Proxy安装脚本二进制路径错误的问题 (fixed #200)

## 2.1.351

- optimization
  - 策略名称移除仅包含汉字英文数字下划线的限制 (closed #198)
- bugfix
  - 修复Proxy安装脚本二进制路径错误的问题 (fixed #200)

## 2.1.350

- optimization
  - 周期任务削峰 (closed #182)
  - CMDB list_hosts_without_biz 聚合查询 (closed #192)

## 2.1.349

- bugfix
  - 升级agent失败 (fixed #175)
  - settings.NGINX_DOWNLOAD_PATH 变量不存在 (fixed #177)

## 2.1.348

- optimization
  - 获取指定类型环境变量 (closed #126)
  - 单元测试仅统计有效文件 (closed #145)
  - statistic接口支持不传plugin_name参数(close #73)
- bugfix
  - 因Gse升级导致升级Proxy失败 (fixed #170)
  - subscription/fetch_commands 接口报错 (fixed #159)
  - 修复周期任务执行报错：ZeroDivisionError('division by zero',) (fixed #153)
  - 清除cookies后重新登录异常问题 (close #156)
  - 社区版GSE部分端口网络不通 (fixed #146)
  - Agent转安装Proxy报错问题(fixed #161)
  - 修复插件列表前端403报错 (fixed #158)
  - 节点列表无法过滤手动停止主机  (fixed #151)
  - Agent安装IP换行样式异常 (fixed #160)
  - 任务详情标题显示异常 (fixed #162)
  - 修复停用插件不可再重新启用的问题 (fixed #157)
  - 修复主机类型订阅 nodes 传入信息错误导致 KeyError 的问题 (fixed #132)
  - 某些情况下suse操作系统pid获取为空 (fixed #128)
  - 修复初次部署Django migrate报错：globalsettings doesn't exist (fixed #152)
  - 同步插件进程状态异常 (fixed #149)
- feature
  - 作业平台文件分发支持制品库 (closed #2)
  - 插件包管理支持对象存储模式 (#2)

## 2.1.347

- bugfix
  - 后台渲染变量与settings读取不一致 (fixed #122)

## 2.1.346

- feature
  - 支持gse的transmit进程更换为data (resolved #96)
  - agent配置zkauth支持加密 (close #97)
- optimization
  - 支持测试锚点 (close #105)
- bugfix
  - 安装proxy脚本渲染错误 (fixed #98)
  - 修复登录超时无弹框问题 (close #107)
  - 非管理员P-agent安装使用全业务安装查询Job无权限问题(fixed #112)
  - 安装proxy不应选择上游节点(fixed #100)

## 2.1.345

- optimization
  - 支持使用CMDB主机监听事件触发订阅变更 (close #85)

## 2.1.344

- bugfix
  - 修复重复收集相同的自动触发任务的问题 (fixed #1)
- optimization
  - 支持使用CMDB主机监听事件触发订阅变更 (close #85)

## 2.1.343

- feature
  - UI、代码优化 (#48)
  - 使用全业务执行作业安装P-Agent (fixed #74)

## 2.1.342

- feature
  - 支持安装通道功能 (#5)
  - 支持接入点中 cityid 和 regionid 配置为空 (#46)
- bugfix
  - Windows P-Agent 安装时路径转义导致作业平台报错的问题 (#52)
  - 修复停止插件调试回收流程不完整的问题 (fixed #8)
  - host_policy 接口鉴权 (fixed #56)
- docs
  - 调整文档和图片(#33)

## 2.1.0
- 新功能
    - 开放基础功能