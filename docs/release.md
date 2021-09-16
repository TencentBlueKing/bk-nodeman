# Release

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