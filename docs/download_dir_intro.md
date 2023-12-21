# 节点管理文件源目录说明

## 背景

文件源的作用

* 多实例（节点管理后台）之间文件共享
* 后台程序进行无差别的文件读写
* 通过作业平台分发到其他机器

节点管理支持二进制及容器化部署

* 二进制：使用 NFS（Network File System）
  作为「文件源」，多实例部署时，每个后台实例所在的主机都挂在一致的路径 `/data/bkee/public/bknodeman/`
* 容器化：使用 蓝鲸制品库（BkRepo）作为「文件源」（Job 支持 BkRepo
  文件分发），和「二进制」一样，使用 `/data/bkee/public/bknodeman/` 作为文件存储目录

## 目录说明

> `/data/bkee/public/bknodeman/`

```
.
# GSE 1.0 Agent 安装/升级包
# 安装包：在节点管理 Agent「安装」「重装」操作使用
# 升级包：以 `_upgrade.tgz` 结尾，在节点管理 Agent「升级」操作使用
├── gse_client-linux-aarch64.tgz
├── gse_client-linux-aarch64_upgrade.tgz
├── gse_client-linux-x86_64.tgz
├── gse_client-linux-x86_64_upgrade.tgz
├── gse_client-linux-x86.tgz
├── gse_client-linux-x86_upgrade.tgz
├── gse_client-windows-x86_64.tgz
├── gse_client-windows-x86_64_upgrade.tgz
├── gse_client-windows-x86.tgz
├── gse_client-windows-x86_upgrade.tgz
├── gse_proxy-linux-x86_64.tgz
├── gse_proxy-linux-x86_64_upgrade.tgz
# GSE 2.0 / 插件安装包目录
# 两层子目录存放规则：{安装包所支持的操作系统}/{安装包所支持的 CPU 架构}；例如：/linux/x86_64，即存放适配系统架构为 Linux x86_64 的所有安装包
# 安装包命名规则：{安装包名称}-{安装包版本}
# GSE 2.0 安装包：名为「gse_agent」「gse_proxy」的安装包，注意：版本为 stable（例如 gse_agent-stable.tgz）将在节点管理 > v2.4.1 下线
├── linux
│   ├── aarch64
│   │   ├── gse_agent-stable.tgz
│   │   ├── gse_agent-v2.1.3-beta.10.tgz
│   │   └── bkmonitorbeat-3.11.1100.tgz
│   ├── x86
│   │   ├── gse_agent-stable.tgz
│   │   ├── gse_agent-v2.1.3-beta.10.tgz
│   │   └── bkmonitorbeat-3.11.1100.tgz
│   └── x86_64
│   │   ├── gse_agent-stable.tgz
│   │   ├── gse_proxy-stable.tgz
│   │   ├── gse_agent-v2.1.3-beta.10.tgz
│   │   └── bkmonitorbeat-3.11.1100.tgz
├── windows
│   ├── x86
│   │   ├── gse_agent-stable.tgz
│   │   ├── gse_agent-v2.1.3-beta.10.tgz
│   │   └── bkmonitorbeat-3.11.1100.tgz
│   └── x86_64
│       ├── gse_agent-stable.tgz
│       ├── gse_agent-v2.1.3-beta.10.tgz
│       └── bkmonitorbeat-3.11.1100.tgz
# GSE 2.0 Agent 操作指令集封装脚本，会在 Agent 包导入时放入到安装包中
├── gsectl
│   ├── agent
│   │   ├── gsectl
│   │   └── gsectl.bat
│   └── proxy
│   │   └── gsectl.bat
# 插件操作指令集
# 1. fetch_used_ports：Exporter 插件端口探测
# 2. operate_plugin：用于监控插件 Debug
# 3. start / stop / reload / restart / stop_debug：分别用于官方插件的启动、停止、重载、重启、停止 Debug
# 4. update_binary: 插件安装脚本
├── plugin_scripts
│   ├── fetch_used_ports.bat
│   ├── fetch_used_ports.ksh
│   ├── fetch_used_ports.sh
│   ├── operate_plugin.bat
│   ├── operate_plugin.ksh
│   ├── operate_plugin.sh
│   ├── remove_config.bat
│   ├── remove_config.ksh
│   ├── remove_config.sh
│   ├── restart.bat
│   ├── restart.sh
│   ├── start.bat
│   ├── start.sh
│   ├── stop.bat
│   ├── stop.sh
│   ├── reload.sh
│   ├── stop_debug.bat
│   ├── stop_debug.ksh
│   ├── stop_debug.sh
│   ├── update_binary.bat
│   ├── update_binary.ksh
│   └── update_binary.sh
# GSE 2.0 安装脚本
├── agent_tools
│   └── agent2
│       ├── setup_agent.bat
│       ├── setup_proxy.sh
│       └── setup_agent.sh
# GSE 1.0 安装脚本
├── setup_agent.bat
├── setup_agent.ksh
├── setup_agent.sh
├── setup_solaris_agent.sh
├── setup_agent.zsh
├── setup_proxy.sh
# GSE 1.0 / 2.0 P-Agent 安装时，在 Proxy 上执行该脚本，执行「下发命令到 P-Agent」的逻辑
├── setup_pagent2.py
├── setup_pagent.py
# 升级 Agent 二进制脚本（1.0 / 2.0 通用）
├── upgrade_agent.sh.tpl
# Proxy 依赖包，用于 Proxy Python、Nginx 环境搭建
├── py36.tgz
├── nginx-portable.tgz
├── start_nginx.sh.tpl
# Windows Agent 安装依赖
├── ntrights.exe
├── base64.exe
├── curl-ca-bundle.crt
├── curl.exe
├── curl.exe.old
├── libcurl-x64.dll
├── tcping.exe
├── unixdate.exe
├── handle.exe
├── jq.exe
├── 7z.dll
├── 7z.exe
# GSE 1.0 zk 加密工具
├── encryptedpasswd
├── gse_public_key
├── encrypted_tools
│   ├── linux_aarch64
│   └── linux_x86_64
# 用于 GSE 1.0 / 2.0 Windows P-Agent 安装远程到目标机器
└── wmiexec.py
```
