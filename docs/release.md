# Release

## 2.2.27 - 2022-09-27 


### optimization: 
  * 国际化处理 (closed #1146)
  * 修复插件状态搜索存在 SQL 注入问题 (fixed #1556) 

## 2.2.26 - 2022-09-26 


### optimization: 
  * 复制IP默认以换行符进行分隔 (closed #1140)

### minor: 
  * pyOpenSSL 版本固化 21.0.0 (closed #1144)

## 2.2.25 - 2022-09-23 


### bugfix: 
  * 插件状态 - 过滤图标不展示问题修复 (closed #1137)

## 2.2.24 - 2022-09-23 


### bugfix: 
  * Agent状态 - 表格的缩略规则不一致 (closed #1104)
  * 插件状态 - 过滤图标被遮挡 (closed #1092)

### optimization: 
  * 资源配额 - 规则及使用增加说明tips (closed #1087)

## 2.2.23 - 2022-09-22 


### optimization: 
  * 插件包 表格列展示不全时提供tooltips (closed #1086)
  * API 在线文档在生产环境隐藏 (closed #1107)
  * 资源配额 - 修改 执行文案改为下发配额 (closed #1089)
  * 新建云区域界面 去掉'选择接入点'的'选择'二字. (closed #1097)
  * 部署策略 - 编辑类型button更改为保存并执行 (closed #1094)
  * 插件停用时，应提供的是启用操作，而不是去部署 (closed #1085)
  * 安装agent默认为已选择的单个业务 (closed #1095)
  * 安装 Agent 被忽略主机展示完整业务名称 (closed #1102)
  * 统一弹框话术 (closed #1084)
  * 调整 Agent 卸载指引 (#1100 closed #1103)
  * 资源配额-配额百分比例含义不明确 (closed #1093)
  * 手动安装的安装说明需要完善 (closed #1082)

### bugfix: 
  * 卸载界面去除安装agent提示 (closed #1099)
  * Windows卸载命令拼接错误 (closed #1078)
  * 编辑配额 - 编辑返回后，业务由全业务变成了单个业务 (closed #1088)
  * 手动卸载无指导方案问题 (fixed #1100)
  * 修复插件操作流水记录 Windows 服务器目录分隔符错误的问题 (fixed #1090)

### feature: 
  * 云区域 - 调整列【proxy数量】为【可用Proxy数量】 (closed #1083)

## 2.2.22 - 2022-09-14 


### feature: 
  * 部署策略执行被抑制时，主抑制策略增加超链接 (closed #889)
  * Agent 安装前置创建目录 (closed #977)
  * 完善权限中心「业务运维」权限配置，新增业务只读推荐权限 (closed #1060)
  * 订阅更新接口支持 steps 更新 (closed #1002)
  * 增加埋点，Trace 接入 (#603)
  * 重装 agent 时保存的密码如果仍在有效期内，需要回显成 * (close #905)
  * 产品导航新版设计 (close #882)

### optimization: 
  * 安装命令生成执行方案，Windows 非直连安装 Agent 支持 Cygwin (close #740)
  * 云区域支持全量排序 (closed #1046)
  * 插件任务版本提示优化 (close #1048)
  * 插件操作执行预览补充当前插件版本 (closed #1049)
  * 补充 language 到 PaaSV2 部署配置 (closed #1042)
  * 手动安装操作指引完善 (closed #722)
  * 插件订阅变更计算移除冗余配置实例生成逻辑 (closed #1003)
  * 手动安装操作指引完善 (closed #722)
  * helm charts matchLabels 补充 (closed #1024)

### bugfix: 
  * 指定安装通道安装 Agent 自动选择接入点报错 (closed #949)
  * 修复判断主机能否使用第三方查询密码服务不可用的问题 (fixed #1008)
  * 自定义业务拓扑场景下新建策略报错 (closed #1010)
  * 插件模板序列化器错误 (closed #1037)

### docs: 
  * 常用 API 文档整理 (closed #930)

## 2.2.21 - 2022-08-12 


### bugfix: 
  * 修复插件调试接口报错的问题 (fixed #995)

### feature: 
  * 插件管理支持版本标签 (closed #732)

## 2.2.20 - 2022-08-10 


### bugfix: 
  * AIX 适配升级脚本语法错误 (closed #987)
  * JOB API适配接口错误 (closed #988)

### feature: 
  * Agent 安装表单优化 (closed #869)
  * 未启用 DHCP 适配时前端关闭部分入口 (closed #978)

## 2.2.19 - 2022-08-02 


### feature: 
  * 支持 AIX 操作系统区分版本 (closed #815)
  * 历史任务-执行日志整体重试改为重试 (closed #899)
  * JOB API 适配 (closed #785)
  * Agent 安装 DHCP 场景适配 (closed #787)
  * GSE 多版本 API 适配 (closed #780)
  * Redis 单节点与哨兵模式支持不同密码 (closed #844)
  * 产品页面支持 IPV6 主机导入 (closed #776)
  * 产品 logo 增加加跳转至首页的超链 (closed #915)
  * Agent 导入表头支持云区域搜索 (closed #913)
  * 主机 Agent 信息绑定关系维护 (closed #782 closed #783)
  * 支持多个node版本开发、打包 (closed #938)
  * 支持主机名展示及过滤 (closed #936)
  * 安装上报 bk_agent_id 持久化 (closed #781)
  * 云区域排序规则  (closed #897)
  * aaS 适配动态 IP 安装校验，统一业务逻辑 IPv6 表示法 (closed #926 closed #927 #787)
  * IPv4/IPv6 双栈 k8s 部署适配 (closed #970)
  * 支持 bk_agent_id (closed #562)
  * Nginx 重新编译，修复 DNS 漏洞 (closed #918)

### bugfix: 
  * Agent 安装校验提示信息错位 (closed #669)
  * Linux Agent dbgipc 配置渲染值有误 (fixed #973)

### docs: 
  * 开源信息更新 (closed #953)

### optimization: 
  * Agent 状态查询兼容 NOT FOUND 场景 (closed #863)
  * IPv6 校验及展示优化 (closed #942)
  * GSE 配置文件去掉相关注释，保证json格式合法 (closed #955)

## 2.2.18 - 2022-07-07 


### feature: 
  * 支持 bkmonitorproxy 的资源配额设置 (closed #868)
  *  查看类的弹窗点击非遮罩处需要能够关闭 (closed #859)

### optimization: 
  * 登录跳转取消弹框 (close #843)
  * 添加主机到 CMDB 兼容接口数据延迟的情况 (close #920)
  * 部署策略展示顺序优化 (closed #856 closed #857)
  * 手动安装引导页去除冗余提示信息 (closed #855)
  * 登录跳转取消弹框 (closed #843)

### bugfix: 
  * 修复 KubeVersion < 1.18-0 ingress 渲染错误：Service(nodeman/bk-nodeman-saas-api) do not have port 80. 的问题 (fixed #876)
  * Agent 安装表单无法选择操作系统 (closed #865)
  * Windows 拼接注册服务名称错误 (closed #870)
  * 已选中的策略需要有一个「选中态」样式 (closed #858)
  * 二进制部署下任务链接返回错误 (closed #841)

## 2.2.17 - 2022-06-13 


### feature: 
  * 提出插件管理页面的安装操作入口 (closed #807)

### optimization: 
  * 更新 Charts 依赖 (closed #827)

## 2.2.16 - 2022-06-09 


### optimization: 
  * 消除运行环境差异 (closed #779)
  * Agent 管理列表「业务拓扑」支持拖动改变宽度 (closed #470)
  * 重装 Agent 保留procinfo.json文件 (closed #791)
  * Linux 相关 Agent 安装服务探测优化 (closed #774)
  * 插件包解析页面 '支持系统' 列展示操作系统类型 (closed #711)

### bugfix: 
  * 节点列表-操作流水跳转到部署策略后 Drawer 未关闭 (close #689)
  * 版本日志展示位置调整 (closed #756)

## 2.2.15 - 2022-06-01 


### optimization: 
  * 页面安装插件不展示子配置 (closed #793)
  * Agent新增事件告警配置 (closed #799)

### bugfix: 
  * 非直连 Windows 机器安装 Agent, gsecmdline 报错 (closed #664)
  * 打包部署报错：Package 'protobuf' requires a different Python: 3.6.X not in '>=3.7' (fixed #796)
  * 安装预设插件检查任务是否就绪不准确 (#790)

### docs: 
  * Helm Charts NOTES 新增同步主机相关数据指引 (closed #798)

## 2.2.14 - 2022-05-19 


### feature: 
  * 多环境部署镜像差异化构建方案 (closed #735)

### optimization: 
  * 主机存在性校验兼容 CMDB 注册延迟 (closed #765)
  * 完善 CMDB 资源监听处理日志 (closed #763)
  * celery 队列消费不及时 (closed #767)

### bugfix: 
  * 订阅状态统计不准确 (closed #758)

## 2.2.13 - 2022-05-12 


### feature: 
  * 安装主插件支持检查是否存在并跳过 (closed #509)
  * 插件配置模板新增节点管理侧上下文 (closed #741)
  * bkunifylogbeat cpu limit 调整为 30% (closed #745)

### bugfix: 
  * AIX 服务器接入点信息获取失败 (closed #737)

### optimization: 
  * celery 启动命令优化 (closed #743)
  * 提供更准确的 GSE 服务发现规则 (closed #733)
  * 检查订阅任务是否就绪接口 任务ID列表为空时取最新任务ID进行判断 (close #713)
  * 节点列表仅展示存在插件的状态 (closed #705)
  * 统计订阅任务数据接口优化 (closed #695)
  * Windows Agent 安装脚本移除启动插件相关逻辑(close #726)

## 2.2.12 - 2022-04-27 


### bugfix: 
  * 二进制部署后台状态展示异常(close #741)
  * Helm ServiceMonitor 渲染错误 (fixed #701)
  * init_official_plugins 命令支持第三方存储(close #708)

### feature: 
  * Agent 安装接口提供 是否安装最新版本插件 选项 (closed #692)
  * 同步业务主机接口 (closed #694)
  * SaaS 相关任务创建接口返回任务链接 (closed #691)
  * Agent 操作前同步增量主机 (closed #706)

### optimization: 
  * Agent 安装操作若主机存在于同业务下，视为重装 (closed #707)

## 2.2.11 - 2022-04-15 


### bugfix: 
  * 修复多插件场景上下文渲染错误的问题 (fixed #683)

### feature: 
  * blueapps 升级至 4.2.3 (closed #685)

## 2.2.10 - 2022-04-15 


### optimization: 
  * 插件配置实例查询优化 (closed #677)
  * 修复下发服务模板采集报错：keyError 'service_template_id' 的问题 (fixed #679)
  * 安装Proxy时检查 GSE_BT_SERVER 的网络连通性 (close #612)

### feature: 
  * 国际化 (closed #672)
  * 支持通过 Helm Chart 部署节点管理到 Kubernetes (closed #584)
  * Mac Os安装Agent脚本(close #663)

### bugfix: 
  * 修复 Proxy 重载配置导致临时文件路径置空的问题 (closed #627)
  * 修复 cookies 清除或过期后登录跳转异常的问题 (fixed #675)
  * 国际化 - 前端补充 (closed #670)
  * 插件调试后残余debug进程的问题 (fixed #655)
  * 修复插件部署策略编辑预览报错的问题 (closed #661)
  * 修复插件包停用后仍可被选中的问题 (closed #658)

### test: 
  * 配置模板渲染单元测试(close #646)

## 2.2.9 - 2022-03-31 


### optimization: 
  * 安装 PROXY 时下发的安装包使用接入点指定的包 (close #622)
  * subscription statistic 接口缓存不生效的问题 (close #634)
  * Agent 非 root 安装切换 sudo 执行安装命令 (closed #637)
  * Django Admin 优化 (close #619)

### bugfix: 
  * 登陆续期窗口登陆后界面显示异常(close #626)
  * 同名多配置文件渲染时过滤错误(close #624)
  * CMDB 资源池删除主机后节点管理未同步 (fixed #639)
  * 插件版本全部停用时报错(close #629)

## 2.2.8 - 2022-03-23 


### feature: 
  * 依赖包升级 (fixed #601)
  * 可观测性建设 (close #603)
  * 作业平台业务集支持 (close #604)

### optimization: 
  * 插件订阅变更计算优化 (closed #599)
  * Windows安装使用ntrights添加权限 (close #616)

### bugfix: 
  * 已重试成功主机，下次重试仍会执行 (closed #350)
  * 修复协程 MySQL server has gone away 的问题 (closed #610)
  * Agent安装为Proxy未更新节点类型 (fixed #605)
  * 安装 Proxy 去除 check_policy_gse_to_proxy 步骤 (fixed #612)
  * 标准运维接口调用问题修复 (fixed #606)

## 2.2.7 - 2022-03-15 


### bugfix: 
  * 修复 Agent 安装失败：'NoneType' object has no attribute 'get' 的问题 (fixed #587)
  * 手动卸载没有给出命令 (fixed #581)
  * 修复手动安装命令获取失败的问题 (fixed #586)
  * 修复选择接入点报错 could not convert string to float (fixed #578)
  * 无法编辑保存proxy主机信息 (fixed #589)
  * 修复作业平台少数IP超时导致整体任务失败的问题 (fixed #573)

### feature: 
  * Agent 配置调整脚本清理策略(close #580)

### optimization: 
  * 仅初始化情况下更新默认接入点下载地址 (closed #594)
  * 多内网IP兼容 (closed #572)

## 2.2.6 - 2022-03-10 


### bugfix: 
  * PaaSV2部署下admin页面缺少静态文件 (close #570)

## 2.2.5 - 2022-03-09 


### bugfix: 
  * Agent 批量操作按钮跨页全选模式下仅在过滤安装方式后可用 (close #498)
  * 安装预装插件时不存在的插件包报错 (close #565)
  * 修复 Proxy dataflow.conf addresses 渲染值有误的问题 (fixed #552)
  * 修复 Windows 通过 Cygwin 安装 Agent 密码解密失败的问题 (fixed #555)
  * Agent 状态查询提前终止后卡住 (fixed #524)
  * 修复PAGENT上游节点错误的问题 (close #458)
  * 修复卸载 Agent 失败: not enough values to unpack (expected 2, got 1) 的问题 (closed #544)
  * 部署策略灰度列表展开错位 (close #449)

### feature: 
  * 支持子订阅功能 (close #517)
  * PaaS 镜像部署适配 (closed #558)
  * 接入点支持配置内网回调地址 (close #440)

### docs: 
  * Agent 安装压力测试文档 (closed #476)

## 2.2.4 - 2022-03-04 


## 2.2.3 - 2022-03-04 


### feature: 
  * 资源限额接口权限控制 (close #536)

## 2.2.2 - 2022-03-04 


### optimization: 
  * 资源配额 - 搜索、业务下拉 优化 (close #527)
  * 优化CPU架构获取和检查 (close #530)

### bugfix: 
  * 资源配额相关的问题修复 (close #523)
  * 修复存在未完成任务时，已失败的任务会重复刷错误日志的问题 (closed #520)
  * 解决主机数量超过200时CMDB接口报错问题 (fixed #521)

### feature: 
  * 接入点支持配置内网回调地址 (closed #440)
  * 直连安装 Windows Agent 放开仅允许 445 端口的限制 (close #507)
  * Agent 安装默认值支持全局配置 (closed #445)
  *  Agent 安装默认值支持全局配置 (close #512)
  * Cygwin 安装 Agent 支持 curl 拉取依赖文件 (closed #532)

## 2.2.1 - 2022-03-01 


### bugfix: 
  * 权限弹窗未展示完整 (fixed #501)
  * 多级目录copy_file_to_nginx报错的问题 (fixed #490)
  * 手动安装命令错误(fixed issue#496)
  * 云区域相关接口报错修复 (fixed #499)
  * 版本日志路由错误问题 (fixed #489)
  * 旧版本非标准路径crontab清理 (close #473)

### feature: 
  * 资源限额功能 (closed #478)
  * 作业平台调用支持业务集 (closed #493)
  * 优化插件配置模板扩充方式 (close #518)
  * ZK账号加密支持多操作系统工具区分 (closed #448)
  * 铁将军密码库接入 (closed #459)
  * Windows 直连安装 Agent 支持 Cygwin (closed #475)
  * feature: 插件配置文件支持多系统(close #392)

### optimization: 
  * 提升通过 SSH 通道批量安装 Agent 的稳定性和效率 (closed #463)

## 2.2.0 - 2022-02-21 


### feature: 
  * Agent 并发安装性能提升
  * 提供验证访问模块可达的接口 (closed #441)

## 2.2.0 - 2022-01-20 


### feature: 
  * 提供验证访问模块可达的接口 (closed #441)
  * Agent 并发安装性能提升

## 2.1.365 - 2022-01-19 


### bugfix: 
  * redis sentinel 连接死循环(fixed #427)

### feature: 
  * 去掉 agent、proxy 的「移除」入口(close #436)
  * 插件操作入口优化(close #434)

### optimization: 
  * Agent升级去除目录保护(close #428)

## 2.1.364 - 2022-01-11 


### feature: 
  * 补充周期任务的单元测试 (close #391)
  * gent 管理页面支持在 url 中进行条件过滤 (fixed #405)
  * 异步接口超时复制IP失败优化 (close #404)

### optimization: 
  * 周期任务削峰打散度不足 (close #400)
  * 安装脚本优化(close #415)

### bugfix: 
  * 修复 PyNaCl 依赖安装报错的问题 (fixed #422)

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
  - GSE部分端口网络不通 (fixed #146)
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