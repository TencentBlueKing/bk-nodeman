# 如何通过节点管理安装 Agent 2.0


## 部署调整


### 环境变量（二进制）

```shell
BKAPP_ENABLE_DHCP="true"
GSE_VERSION="V2"
# GSE的API网关地址
BKAPP_BK_GSE_APIGATEWAY="https://example.com/api/bk-gse/prod/"
```

### 环境变量（容器部署）

```yaml
config:
  bkAppEnableDHCP: true
  gseVersion: V2
  bkAppBkGseApiGateway: https://example.com/api/bk-gse/prod
```

环境变量说明请参考：[bk-nodman 系统配置](https://github.com/TencentBlueKing/bk-nodeman/blob/V2.2.X/support-files/kubernetes/helm/bk-nodeman/README.md#bk-nodman-%E7%B3%BB%E7%BB%9F%E9%85%8D%E7%BD%AE)



### 接入点

进入节点管理管理页：`{节点管理页面访问地址}/admin_nodeman/node_man/accesspoint/`

修改 `GSE端口配置` 中部分端口配置为：

```yaml
io_port: 28668
data_port: 28625
file_svr_port: 28925
```

### 上传 Agent 2.0 安装包
> 待完善


### 指定 Agent 2.0 安装版本（可选）
> 默认取值为：`stable`

进入节点管理管理页：`{节点管理页面访问地址}/admin_nodeman/node_man/globalsettings/`

设置变量 `GSE_AGENT2_VERSION`
