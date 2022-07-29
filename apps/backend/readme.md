## 核心目录结构说明

apps/backend/
├── agent               # 定义AGENT相关操作的流程步骤
│   └── manager.py      # 步骤源于apps.backend.components.collections.agent
├── plugin              # 定义插件相关操作的流程步骤
│   └── manager.py      # 步骤源于apps.backend.components.collections.plugin
├── components          # 封装组件用于编排流程
│   └── collections
│       ├── base.py     # 组件封装基类
│       ├── agent.py    # AGENT任务组件封装
│       ├── job.py      # 作业平台组件封装
│       └── plugin.py   # 插件任务组件封装
├── subscription
│   ├── agent_tasks.py  # AGENT任务构造（兼容性代码，可不关注）
│   ├── errors.py       # 封装统一的异常类
│   ├── handler.py      # 订阅任务处理器，用于衔接views 和 models+apis
│   ├── serializers.py  # 统一的序列化器
│   ├── steps           
│   │   ├── base.py     # 任务流程步骤编排基类
│   │   ├── agent.py    # AGENT任务流程步骤编排
│   │   └── plugin.py   # 插件任务流程步骤编排
│   ├── tools.py        # 封装部分工具方法
│   └── tasks.py        # 构造编排pipeline任务
└── tests               # 单元测试代码，目录结构与被测试的目录结构一致，如 components/collections/collections/plugin.py 的测试代码位于 tests/components/collections/collections/plugin.py


## 部分Agent配置说明
- clean_script_files_beginhour   # 每天开始执行清理的时间点
- clean_script_files_maxhours    # 从文件创建时间开始计算文件最多保留小时数
- clean_script_files_stepcount   # 每次清理一百个文件时，强制 sleep 30ms 避免cpu负载过高
- processeventdataid             # 进程告警事件
- btServerOuterIP                # ``PROXY``服务器外网地址
- btfilesvrscfg                  # ``BTSERVER``配置项, 对应服务器监听地址应为蓝鲸``GSE``服务器的外网地址