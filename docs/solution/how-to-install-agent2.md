如何通过节点管理安装 Agent 2.0

## 部署调整

### 占位变量说明

* `{{ ENV }}`：环境代号，用于区分单台机器所部署的不同环境 Agent，**如果具有多环境的场景，建议区分环境代号**
* `{{ BKAPP_BK_GSE_APIGATEWAY }}`：GSE 2.0 API 网关访问地址，例如：
  `https://example.com/api/bk-gse/prod`
* `{{ GSE_CERT_PATH }}`：证书路径（仅二进制环境）

### 二进制环境

#### 配置证书

将蓝鲸 GSE 证书挂载/拷贝到 `{{ GSE_CERT_PATH }}` 路径下

#### 环境变量配置

```shell  
export BKAPP_ENABLE_DHCP="true"
export GSE_VERSION="V2"
# GSE 的 API 网关地址  
export BKAPP_BK_GSE_APIGATEWAY="{{ BKAPP_BK_GSE_APIGATEWAY }}"
export GSE_ENABLE_PUSH_ENVIRON_FILE="True"
export GSE_ENVIRON_DIR="/etc/sysconfig/gse/{{ ENV }}"
export GSE_ENVIRON_WIN_DIR="C:\\\\Windows\\\\System32\\\\config\\\\gse\\\\{{ ENV }}"
export GSE_CERT_PATH="{{ GSE_CERT_PATH }}"
```

### 容器化环境

#### 配置证书（可选）

> 社区版环境 helm 模板已自动读取环境的 GSE 证书，这种情况下该步骤可跳过

将证书文件内容转为 base64 编码

```yaml
## --------------------------------------  
## GSE 证书  
## --------------------------------------  
gseCert:
  ## 证书 CA 内容配置（base64）  
  ca: ""
  ## Server 侧 CERT 内容配置（base64）  
  cert: ""
  ## Server 侧 KEY 内容配置（base64）  
  key: ""
  ## 证书密码文件内容配置, 用于解密证书密码  
  certEncryptKey: ""

  ## API 侧 CERT##
  apiClient:
    ## API 侧 CERT 内容配置, 用于其他服务调用 GSE（base64）
    cert: ""
    ## API 侧 KEY 内容配置, 用于其他服务调用 GSE（base64） 
    key: ""

  ## Agent 侧 CERT##  
  agent:
    ## Agent 侧 CERT 内容配置, 用于 Agent 链路（base64）  
    cert: ""
    ## Agent 侧 KEY 内容配置, 用于 Agent 链路（base64）  
    key: ""
```

#### 环境变量配置

```yaml  
config:
  bkAppEnableDHCP: true
  gseVersion: V2
  bkAppBkGseApiGateway: { { BKAPP_BK_GSE_APIGATEWAY } }
  gseEnablePushEnvironFile: true
  gseEnvironDir: /etc/sysconfig/gse/{{ ENV }}
  gseEnvironWinDir: C:\\Windows\\System32\\config\\gse\\{{ ENV }}
```  

环境变量说明请参考：[bk-nodman 系统配置](https://github.com/TencentBlueKing/bk-nodeman/blob/v2.3.x/support-files/kubernetes/helm/bk-nodeman/README.md#bk-nodeman-%E7%B3%BB%E7%BB%9F%E9%85%8D%E7%BD%AE)

## 接入点调整

### 前置条件

* 「运维提供」可用的 GSE 2.0 Server（CLB）
* 「运维提供」Server（CLB）安全组策略已配置

### 无需灰度

> 适用场景：全量安装 2.0 Agent，无需保留 1.0 的接入点，安装路径不变

1. 进入节点管理管理页：`{节点管理页面访问地址}/admin_nodeman/node_man/accesspoint/`

2. 修复 `GSE 版本` 为 `V2`

3. 修改  `GSE端口配置`  中部分端口配置为：

```yaml
tracker_port: 20030
db_proxy_port: 58817
file_svr_port: 28925
file_svr_port_v1: 58926
btsvr_thrift_port: 58931
data_prometheus_port: 29402
file_metric_bind_port: 29404
bt_port": 20020
io_port": 28668
data_port": 28625
```

### 需要灰度

> 适用场景：保持 1.0 Agent 运行，需要区分安装路径


基于现有接入点克隆为 2.0 接入点，该命令会完成几项工作：

* 标记新接入点使用 2.0 GSE 环境
* 自动调整端口
* 基于原配置路径，映射出新的配置路径，映射规则：`gse` -> `gse2`

```shell
# 查看命令参数说明
python manage.py create_ap_for_gse2 -h
# 克隆接入点
python manage.py create_ap_for_gse2 -r ${ap_id}
```

到页面查看新创建的接入点并进行微调：`{节点管理页面访问地址}/#/global-config/gse-config`

## 打包并上传 Agent 2.0 安装包

### 容器化环境

> 在拥有蓝鲸 k8s 集群 kubectl 执行权限的节点管理执行

假设节点管理所在的 k8s namespace 为 `${NAMESPACE}`

```shell

# 获取第一个存活 POD NAME，后续操作依赖该变量
export FIRST_RUNNING_POD=$(kubectl get pods -n ${NAMESPACE} \
  --selector=app.kubernetes.io/instance=bk-nodeman --field- selector=status.phase=Running \
  -o custom-columns=":metadata.name" | sed '/^$/d' | head -n 1 )

# 删除缓存的包
kubectl exec -n ${NAMESPACE} ${FIRST_RUNNING_POD} -- sh -c 'rm -f /app/official_plugin/gse_agent/* && rm -f /app/official_plugin/gse_proxy/*'

# [Agent] 将 client 包上传到容器指定目录，可以重复该步骤，导入多个版本的 client 包，client 包一般格式为：gse_agent_ce-2.0.0.tgz
kubectl cp ${agent_pkg_path} -n ${NAMESPACE} ${FIRST_RUNNING_POD}:/app/official_plugin/gse_agent/  

# [Proxy] 将 server 包上传到容器指定目录，可以重复该步骤，导入多个版本的 server 包，server 包一般格式为：gse_ce-2.0.0.tgz
# 注意：导入 server 包依赖同版本的 client 包，请确保 client 包已上传或已导入
kubectl cp ${server_pkg_path} -n ${NAMESPACE} ${FIRST_RUNNING_POD}:/app/official_plugin/gse_proxy/

# 解析并导入 Agent/Proxy  
# -o --overwrite_version 版本号，用于覆盖原始制品内的版本信息，`stable` 为内置版本
# 修改内置版本：${BK_NODEMAN_URL}/admin_nodeman/node_man/globalsettings/ 新建或修改 `GSE_AGENT2_VERSION`，默认为 `"stable"`
kubectl exec -n {{ .Release.Namespace }} ${FIRST_RUNNING_POD} -- python manage.py init_agents -o stable
```

### 二进制环境

> 在节点管理后台机器上执行

```shell

# 进入 app 目录
workon bknodeman-nodeman

# 删除缓存的包
rm -f official_plugin/gse_agent/* && rm -f official_plugin/gse_proxy/*

# [Agent] 将 client 包传到指定目录，可以重复该步骤，导入多个版本的 client 包，client 包一般格式为：gse_agent_ce-2.0.0.tgz
cp ${agent_pkg_path} official_plugin/gse_agent/

# [Proxy] 将 server 包传到指定目录，可以重复该步骤，导入多个版本的 server 包，server 包一般格式为：gse_ce-2.0.0.tgz
# 注意：导入 server 包依赖同版本的 client 包，请确保 client 包已上传或已导入
cp ${server_pkg_path} official_plugin/gse_agent/

# 解析并导入 Agent/Proxy  
# -o --overwrite_version 版本号，用于覆盖原始制品内的版本信息，`stable` 为内置版本
# 修改内置版本：${BK_NODEMAN_URL}/admin_nodeman/node_man/globalsettings/ 新建或修改 `GSE_AGENT2_VERSION`，默认为 `"stable"`
python manage.py init_agents -o stable
```

## 开始安装

### 安装 Proxy

编辑/新建云区域 -> 选择新创建的 2.0 接入点 -> 安装/重装 Proxy

### 安装 Agent

选择新创建的 2.0 接入点 -> 安装/重装 Agent

### 指定 Agent 2.0 安装版本（可选）

> 默认取值为：`stable`

进入节点管理管理页：`{节点管理页面访问地址}/admin_nodeman/node_man/globalsettings/`  
设置变量 `GSE_AGENT2_VERSION`
