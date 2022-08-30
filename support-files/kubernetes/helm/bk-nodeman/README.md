# BK-NODEMAN

此 Chart 用于在 Kubernetes 集群中通过 helm 部署 bk-nodeman

## 环境要求

- Kubernetes 1.12+
- Helm 3+
- PV provisioner

## 安装Chart

使用以下命令安装名称为 `bk-nodeman` 的 release

* `<bk-nodeman helm repo url>` 代表 helm 仓库地址
* `<bk-nodeman namespace>` 代表 `bk-nodeman`  部署后的 k8s 名字空间，不填默认 `default`

```shell
$ helm repo add bkee <bk-nodeman helm repo url>
$ helm install bkrepo bkee/bk-nodeman -n <bk-nodeman namespace> --create-namespace
```

上述命令将使用**默认配置**在 Kubernetes 集群中部署 bk-nodeman, 并输出访问指引。

## 卸载Chart

使用以下命令卸载 `bk-nodeman`:

```shell
$ helm uninstall bk-nodeman -n <bk-nodeman namespace>
```

上述命令将移除所有和 `bk-nodeman` 相关的 Kubernetes 组件，并删除 release。

## Chart依赖

- [bitnami/common](https://github.com/bitnami/charts/blob/master/bitnami/common/)
- [bitnami/mysql](https://github.com/bitnami/charts/blob/master/bitnami/mysql/)
- [bitnami/redis](https://github.com/bitnami/charts/blob/master/bitnami/redis/)
- [bitnami/rabbitmq](https://github.com/bitnami/charts/blob/master/bitnami/rabbitmq/)
- [bitnami/nginx-ingress-controller](https://github.com/bitnami/charts/tree/master/bitnami/nginx-ingress-controller)

## 配置说明

下面展示了可配置的参数列表以及默认值

### Charts 全局设置

| 参数                      | 描述                                            | 默认值                                                  |
| ------------------------- | ----------------------------------------------- | ------------------------------------------------------- |
| `global.imageRegistry`    | Global Docker image registry                    | `""`                                                    |
| `global.imagePullSecrets` | Global Docker registry secret names as an array | `[]` (does not add image pull secrets to deployed pods) |
| `global.storageClass`     | Global storage class for dynamic provisioning   | `""`                                                    |
| `global.bkDomain`         | 蓝鲸主域名                                      | `example.com`                                           |
| `global.bkDomain`         | 蓝鲸主域名访问协议                              | `http`                                                  |

### Kubernetes 组件公共配置

下列参数用于配置 Kubernetes 组件的公共属性，一份配置作用到每个组件

| 参数                 | 描述                                                         | 默认值 |
| -------------------- | ------------------------------------------------------------ | ------ |
| `nameOverride`       | String to partially override common.names.fullname template (will maintain the release name) | `""`   |
| `fullnameOverride`   | String to fully override common.names.fullname template      | `""`   |
| `podAnnotations`     | Pod annotations                                              | `{}`   |
| `commonLabels`       | Common labels to add to all bk-nodeman resources. Evaluated as a template | `{}`   |
| `commonAnnotations`  | Common annotations to add to all bk-nodeman resources . Evaluated as a template | `{}`   |
| `podSecurityContext` | A security context defines privilege and access control settings for a Pod or Container. | `{}`   |
| `securityContext`    | A security context defines privilege and access control settings for a Pod or Container. | `{}`   |
| `nodeSelector`       | Node labels for all pods assignment                          | `{}`   |
| `tolerations`        | Tolerations for all pods assignment                          | `[]`   |
| `volumes`            | Optionally specify extra list of additional volumes to the  bk-nodeman pod(s) | `[]`   |
| `volumeMounts`       | Optionally specify extra list of additional volumeMounts for the bk-nodeman secondary container(s) | `[]`   |
| `affinity`           | Affinity for pod assignment (evaluated as a template)        | `{}`   |

### ServiceAccount 配置

| 参数                         | 描述                                                         | 默认值 |
| ---------------------------- | ------------------------------------------------------------ | ------ |
| `serviceAccount.annotations` | Annotations for service account                              | `{}`   |
| `serviceAccount.create`      | If true, create a service account                            | `true` |
| `serviceAccount.name`        | The name of the service account to use. If not set and create is true, a name is generated using the fullname template. | `""`   |

### 镜像通用配置

下列参数表示 `images.<image name>` 的通用配置，能够配置的 `<image name>`：

* `saas`
* `backend`
* `busybox`
* `k8sWaitFor`
* `nginx`

| 参数                             | 描述         | 默认值                                |
| -------------------------------- | ------------ | ------------------------------------- |
| `images.<image name>.registry`   | 镜像仓库     | 详见 `values.yaml` 中各个镜像的默认值 |
| `images.<image name>.repository` | 镜像名称     | 详见 `values.yaml` 中各个镜像的默认值 |
| `images.<image name>.pullPolicy` | 镜像拉取策略 | 详见 `values.yaml` 中各个镜像的默认值 |
| ``images.<image name>.tag``      | 镜像 tag     | 详见 `values.yaml` 中各个镜像的默认值 |

### nginx-ingress-controller 配置

相关配置请参考 [bitnami/nginx-ingress-controller](https://github.com/bitnami/charts/tree/master/bitnami/)

| 参数                                              | 描述                                                         | 默认值      |
| ------------------------------------------------- | ------------------------------------------------------------ | ----------- |
| `nginx-ingress-controller.enabled`                | 是否部署 nginx ingress controller                            | `false`     |
| `nginx-ingress-controller.kind`                   | Install as Deployment or DaemonSet                           | `DaemonSet` |
| `nginx-ingress-controller.daemonset.useHostPort`  | If `kind` is `DaemonSet`, this will enable `hostPort` for `TCP/80` and `TCP/443` | `true`      |
| `nginx-ingress-controller.defaultBackend.enabled` | nginx ingress controller 默认 backend                        | `false`     |

### ingress 配置

| 参数                  | 描述                                                         | 默认值                  |
| --------------------- | ------------------------------------------------------------ | ----------------------- |
| `ingress.enabled`     | 是否创建 ingress                                             | `true`                  |
| `ingress.className`   | ingress 类                                                   | `nginx`                 |
| `ingress.annotations` | ingress 标注                                                 | 详见 `values.yaml`      |
| `ingress.hostname`    | 访问域名                                                     | `bknodeman.example.com` |
| `ingress.paths`       | 转发规则                                                     | 详见 `values.yaml`      |
| `ingress.selfSigned`  | Create a TLS secret for this ingress record using self-signed certificates generated by Helm | `false`                 |
| `ingress.tls`         | Enable TLS configuration for the host defined at `ingress.hostname` parameter | `false`                 |
| `ingress.extraPaths`  | An array with additional arbitrary paths that may need to be added to the ingress under the main host | `[]`                    |
| `ingress.extraTls`    | TLS configuration for additional hostname(s) to be covered with this ingress record | `[]`                    |
| `ingress.secrets`     | Custom TLS certificates as secrets                           | `[]`                    |

### 模块配置

| 参数                 | 描述                                                         | 默认值  |
| -------------------- | ------------------------------------------------------------ | ------- |
| `saas.enabled`       | 是否启用 SaaS                                                | `true`  |
| `backend.enabled`    | 是否启用后台                                                 | `true`  |
| `backend.miniDeploy` | 是否启用后台最小化部署<br />如果管理规模较大，建议该值为 `true`，以保证可用性<br />不同取值所启动的 worker 服务：<br />**`true`**： `backend.commonWorker` `commonPipelineWorker`<br />**`false`**:<br />`backend.dworker`<br />`backend.bworker`<br />`backend.baworker`<br />`backend.pworker`<br />`backend.psworker`<br />`backend.paworker` | `false` |

### 服务通用配置

下列参数表示 bk-nodeman 服务通用配置，每个服务进行单独配置。能够配置的服务有:

- `saas.api`
- `saas.web`
- `backend.api`
- `backend.celeryBeat`
- `backend.commonWorker`
- `backend.commonPipelineWorker`
- `backend.dworker`
- `backend.bworker`
- `backend.baworker`
- `backend.pworker`
- `backend.psworker`
- `backend.paworker`
- `backend.syncHost`
- `backend.syncHostRe`
- `backend.syncProcess`
- `backend.resourceWatch`

| 参数                 | 描述                                   | 默认值             |
| -------------------- | -------------------------------------- | ------------------ |
| `enabled`            | 是否启用服务                           | `true`             |
| `resources.limits`   | The resources limits for containers    | `{}`               |
| `resources.requests` | The requested resources for containers | `{}`               |
| `replicaCount`       | 服务实例数量                           | `1`                |
| `command`            | 启动命令                               | 详见 `values.yaml` |

### 服务配置

下列参数表示 bk-nodeman 服务除去 `服务通用配置` 的其他配置

| 参数                           | 描述                         | 默认值      |
| ------------------------------ | ---------------------------- | ----------- |
| `saas.api.service.type`        | SaaS API Service Type        | `ClusterIP` |
| `saas.api.service.port`        | SaaS API Service Port        | `10300`     |
| `saas.web.service.type`        | SaaS Web Service Type        | `ClusterIP` |
| `saas.web.service.port`        | SaaS Web Service Port        | `80`        |
| `backend.api.service.type`     | Backend API Service Type     | `NodePort`  |
| `backend.api.service.port`     | Backend API Service Port     | `10300`     |
| `backend.api.service.nodePort` | Backend API Service NodePort | `30300`     |

### Redis 配置

默认将部署 Redis，如果不需要可以关闭。 相关配置请参考 [bitnami/redis](https://github.com/bitnami/charts/blob/master/bitnami/redis)

| 参数                  | 描述                                                         | 默认值       |
| --------------------- | ------------------------------------------------------------ | ------------ |
| `redis.enabled`       | 是否部署 Redis。如果需要使用外部 Redis，设置为 `false` 并配置 `externalRedis` | `true`       |
| `redis.auth.enabled`  | 是否开启认证                                                 | `true`       |
| `redis.auth.password` | Redis 密码                                                   | `bk-nodeman` |

> 如果需要持久化 redis 数据，请参考 [bitnami/redis](https://github.com/bitnami/charts/blob/master/bitnami/redis) 配置存储卷

#### externalRedis 配置示例

```yaml
## External Redis configuration
##
externalRedis:
  architecture: "standalone"
  host: "bk-nodeman"
  port: 6379
  password: "bk-nodeman"
```

### MySQL 配置

默认将部署 MySQL，如果不需要可以关闭。 相关配置请参考 [bitnami/mysql](https://github.com/bitnami/charts/blob/master/bitnami/mysql)

| 参数                                     | 描述                                                         | 默认值             |
| ---------------------------------------- | ------------------------------------------------------------ | ------------------ |
| `mysql.enabled`                          | 是否部署 MySQL。如果需要使用外部数据库，设置为 `false` 并配置 `externalMySQL` | `true`             |
| `mysql.auth.rootPassword`                | `root` 密码                                                  | `bk-nodeman`       |
| `mysql.auth.database`                    | 数据库名称                                                   | `bk-nodeman`       |
| `mysql.auth.username`                    | 数据库用户名                                                 | `bk-nodeman`       |
| `mysql.auth.password`                    | 数据库密码                                                   | `bk-nodeman`       |
| `mysql.initdbScripts.grant_user_pms.sql` | 为 `mysql.auth.username` 授权                                | 详见 `values.yaml` |
| `primary.configuration`                  | 在默认配置的基础上，调整字符集及 `max_allowed_packet`        | 详见 `values.yaml` |

> 如果需要持久化数据库数据，请参考 [bitnami/mysql](https://github.com/bitnami/charts/blob/master/bitnami/mysql) 配置存储卷

#### externalMySQL 配置示例

```yaml
## External MySQL configuration
##
externalMySQL:
  host: "host.docker.internal"
  port: 3306
  username: "bk-nodeman"
  password: "bk-nodeman"
  database: "bk-nodeman"
```

### RabbitMQ 配置

默认将部署 RabbitMQ，如果不需要可以关闭。 相关配置请参考 [bitnami/rabbitmq](https://github.com/bitnami/charts/blob/master/bitnami/rabbitmq)

| 参数                          | 描述                                                         | 默认值             |
| ----------------------------- | ------------------------------------------------------------ | ------------------ |
| `rabbitmq.enabled`            | 是否部署 RabbitMQ。如果需要使用外部 RabbitMQ，设置为 `false` 并配置 `externalRabbitMQ` | `true`             |
| `rabbitmq.auth.username`      | 用户名                                                       | `bk-nodeman`       |
| `rabbitmq.auth.password`      | 密码                                                         | `bk-nodeman`       |
| `rabbitmq.extraConfiguration` | 为 `vhost=bk-nodeman`授权                                    | 详见 `values.yaml` |

> 如果需要持久化 RabbitMQ 数据，请参考 [bitnami/rabbitmq](https://github.com/bitnami/charts/blob/master/bitnami/rabbitmq) 配置存储卷

#### externalRabbitMQ 配置示例

```yaml
## External RabbitMQ configuration
##
externalRabbitMQ:
  host: "host.docker.internal"
  port: 5672
  vhost: "bk-nodeman"
  username: "bk-nodeman"
  password: "bk-nodeman"
```

### 第三方依赖配置

| 参数                | 描述                                                         | 默认值                          |
| ------------------- | ------------------------------------------------------------ | ------------------------------- |
| `bkPaasUrl`         | 蓝鲸 PaaS url（浏览器访问蓝鲸入口）                          | `http://example.com`            |
| `bkLoginUrl`        | 蓝鲸 Login url（浏览器跳转登录用的URL前缀）                  | `http://example.com/login`      |
| `bkComponentApiUrl` | 蓝鲸 ESB url，注意集群内外都是统一域名。集群内可以配置域名解析到内网ip | `http://bkapi.example.com`      |
| `bkNodemanUrl`      | 节点管理浏览器访问地址                                       | `http://bknodeman.example.com`  |
| `bkNodemanApiUrl`   | 节点管理后台访问地址                                         | `http://bk-nodeman-backend-api` |
| `bkJobUrl`          | 蓝鲸作业平台浏览器访问地址                                   | `http://job.example.com`        |
| `bkIamUrl`          | 蓝鲸权限中心 SaaS 地址                                       | `http://bkiam.example.com`      |
| `bkIamApiUrl`       | 蓝鲸权限中心后台 API 地址                                    | `http://bkiam-api.example.com`  |
| `bkRepoUrl`         | 蓝鲸制品库浏览器访问域名和后台 API http://bkiam-api.example.com 域名同一个 | `http://bkrepo.example.com`     |

### bk-nodman 系统配置

用于生成运行环境变量，具体参考：`support-files/kubernetes/helm/bk-nodeman/templates/configmaps/env-configmap.yaml`

| 参数                                  | 描述                                                         | 默认值                         |
| ------------------------------------- | ------------------------------------------------------------ | ------------------------------ |
| `config.appCode`                      | app code                                                     | `bk_nodeman`                   |
| `config.appSecret`                    | app secret                                                   | `""`                           |
| `config.bkAppRunEnv`                  | 运行环境，ce / ee / ieod，影响 gse 端口等配置                | `ce`                           |
| `config.bkAppEnableDHCP`              | 是否开启动态主机配置协议适配                                 | `false`                        |
| `config.bkPaasMajorVersion`           | 开发框架 PaaS 版本适配，目前仅支持 `3`                       | `3`                            |
| `config.bkPaaSEnvironment`            | 开发框架 PaaS 环境适配，目前仅支持 `prod`                    | `prod`                         |
| `config.logType`                      | 日志类别，`DEFAULT`-   `STDOUT`                              | `STDOUT`                       |
| `config.logLevel`                     | 日志级别                                                     | `INFO`                         |
| `config.bkLogDir`                     | 日志所在目录，`config.logType=DEFAULT` 时有效                | `/data/bkee/logs/bknodeman`    |
| `config.bkCmdbResourcePoolBizId`      | 蓝鲸配置平台相关配置，资源池 ID                              | `1`                            |
| `config.defaultSupplierAccount`       | 蓝鲸配置平台相关配置，企业账户                               | `0`                            |
| `config.jobVersion`                   | 蓝鲸作业平台相关配置，API 版本，可选项 `V2` `V3`             | `V3`                           |
| `config.bluekingBizId`                | 蓝鲸作业平台相关配置，调用作业平台 API 所使用的业务集 ID     | `9991001`                      |
| `config.bkAppUseIam`                  | 蓝鲸权限中心相关配置，是否启用权限中心                       | `true`                         |
| `config.bkIamV3AppCode`               | 蓝鲸权限中心相关配置，权限中心 AppCode                       | `bk_iam`                       |
| `config.bkAppIamResourceApiHost`      | 蓝鲸权限中心相关配置，权限中心拉取权限相关资源的访问地址，默认取 `{{ .Values.bkNodemanUrl }}` | `""`                           |
| `config.bkAppBkNodeApiGateway`        | 组件 API 接入地址，节点管理网关地址，用于覆盖  `bkComponentApiUrl` 访问节点管理<br />⚠️ 配置为 `{{ .Values.bkNodemanApiUrl }`} 由于 JWT 校验问题，会导致 Agent 安装步骤中「安装预制插件」失败 | `""`                           |
| `config.bkAppBkGseApiGateway`         | 管控平台 API 访问地址，用于覆盖 `bkComponentApiUrl` 访问管控平台 API | `""`                           |
| `config.bkAppBackendHost`             | 节点管理自身模块依赖，后台访问地址，渲染时为空默认取 `{{ .Values.bkNodemanApiUrl }}` | `""`                           |
| `config.bkAppNodemanCallbackUrl`      | 节点管理自身模块依赖，后台内网回调地址，渲染时为空取 `{{ .Values.bkNodemanUrl }}/backend` | `""`                           |
| `config.bkAppNodemanOuterCallbackUrl` | 节点管理自身模块依赖，后台外网回调地址，渲染时为空取 `{{ .Values.bkNodemanUrl }}/backend` | `""`                           |
| `config.gseVersion`                   | 蓝鲸管控平台版本，默认为 `V1`,可选：`V1` `V2`                | `V1`                           |
| `config.gseEnableSvrDisCovery`        | 蓝鲸管控平台 Agent，AgentXXDir 仅在初次部署有效，后续可以在页面「全局配置」维护。是否启用 GSE 服务探测，默认为 `true` | `true`                         |
| `config.bkAppGseZkHost`               | 蓝鲸管控平台 Agent，zk hosts 信息，host:port，多个 hosts 以 `,` 分隔<br />⚠️ ZK hosts 将作为 Agent 配置，需要保证 Agent 可访问，所以不能使用 k8s service 信息 进行配置<br />如果 zk 通过 k8s 部署，建议通过 NodePort 等方式暴露服务，使用 NodeIP:NodePort 进行配置 | `127.0.0.1:2181`               |
| `config.bkAppGseZkAuth`               | 蓝鲸管控平台 Agent，ZK 认证信息，用户名:密码                 | `bkzk:zkpass`                  |
| `config.bkAppGseAgentHome`            | 蓝鲸管控平台 Agent，AgentXXDir 仅在初次部署有效，后续可以在页面「全局配置」维护。Linux Agent 安装目录 | `/usr/local/gse`               |
| `config.bkAppGseAgentLogDir`          | 蓝鲸管控平台 Agent，AgentXXDir 仅在初次部署有效，后续可以在页面「全局配置」维护。Linux Agent 日志目录 | `/usr/log/gse`                 |
| `config.bkAppGseAgentRunDir`          | 蓝鲸管控平台 Agent，AgentXXDir 仅在初次部署有效，后续可以在页面「全局配置」维护。Linux Agent 运行目录 | `/usr/run/gse`                 |
| `config.bkAppGseAgentDataDir`         | 蓝鲸管控平台 Agent，AgentXXDir 仅在初次部署有效，后续可以在页面「全局配置」维护。Linux Agent 数据目录 | `/usr/data/gse`                |
| `config.bkAppGseWinAgentHome`         | 蓝鲸管控平台 Agent，AgentXXDir 仅在初次部署有效，后续可以在页面「全局配置」维护。Windows Agent 安装目录 | `C:\\\\gse`                    |
| `config.bkAppGseWinAgentLogDir`       | 蓝鲸管控平台 Agent，AgentXXDir 仅在初次部署有效，后续可以在页面「全局配置」维护。Windows Agent 日志目录 | `C:\\\\gse\\\\logs`            |
| `config.bkAppGseWinAgentRunDir`       | 蓝鲸管控平台 Agent，AgentXXDir 仅在初次部署有效，后续可以在页面「全局配置」维护。Windows Agent 运行目录 | `C:\\\\gse\\\\data`            |
| `config.bkAppGseWinAgentDataDir`      | 蓝鲸管控平台 Agent，AgentXXDir 仅在初次部署有效，后续可以在页面「全局配置」维护。Windows Agent 数据目录 | `C:\\\\gse\\\\data`            |
| `config.storageType`                  | 存储，存储类型`FILE_SYSTEM` `BLUEKING_ARTIFACTORY`           | `BLUEKING_ARTIFACTORY`         |
| `config.lanIp`                        | 存储，文件服务器内网IP，用于物理机文件分发，在 `storageType=FILE_SYSTEM` 时必须设置为有效中 | `127.0.0.1`                    |
| `config.bkAppPublicPath`              | 存储，文件存储目录                                           | `/data/bkee/public/bknodeman/` |
| `config.bkRepoProject`                | 存储，蓝鲸制品库项目                                         | `""`                           |
| `config.bkRepoPassword`               | 存储，蓝鲸制品库密码                                         | `""`                           |
| `config.bkRepoUsername`               | 存储，蓝鲸制品库用户                                         | `""`                           |
| `config.bkRepoBucket`                 | 存储，蓝鲸制品库仓库                                         | `""`                           |
| `config.bkRepoPublicBucket`           | 存储，蓝鲸制品库公共仓库                                     | `""`                           |
| `config.bkRepoPrivateBucket`          | 存储，蓝鲸制品库私有仓库                                     | `""`                           |
| `config.bkAppEnableOtelTrace`         | 可观测，是否开启 Trace                                       | `false`                        |
| `config.bkAppOtelInstrumentDbApi`     | 可观测，是否开启 DB 访问 trace（开启后 span 数量会明显增多） | `false`                        |
| `config.bkAppOtelSampler`             | 可观测，配置采样策略，可选值 `always_on`，`always_off`, `parentbased_always_on`,`parentbased_always_off`, `traceidratio`, `parentbased_traceidratio` | `parentbased_always_off`       |
| `config.bkAppOtelBkDataToken`         | 可观测，监控上报配置项                                       | `""`                           |
| `config.bkAppOtelGrpcHost`            | 可观测，监控上报配置项                                       | `""`                           |
| `config.concurrentNumber`             | 线程最大并发数                                               | `50`                           |

## 额外的环境变量

> 额外的环境变量，可用于覆盖或新增环境变量
>
> 环境变量可参考：`support-files/kubernetes/helm/bk-nodeman/templates/configmaps/*.yaml`
>
> 优先级：内置环境变量 < extraEnvVarsCM < extraEnvVarsSecret < extraEnvVars < backendExtraEnvVars (仅后台)

| 参数                  | 描述               | 默认值 |
| --------------------- | ------------------ | ------ |
| `extraEnvVarsCM`      | 额外的 ConfigMap   | `""`   |
| `extraEnvVarsSecret`  | 额外的 Secret      | `""`   |
| `extraEnvVars`        | 额外的环境变量     | `[]`   |
| `backendExtraEnvVars` | 额外的后台环境变量 | `[]`   |

## 配置案例 & 建议

### 1. 使用 ingress-controller

#### 使用内置的 ingress-controller

内置 `ingress-controller ` 默认不开启，如需使用，请自行开启，例如：

```shell
helm install bkrepo bkee/bk-nodeman -n <bk-nodeman namespace> --set nginx-ingress-controller.enabled=true --create-namespace
```

#### 安装 `ingress-controller`

```shell
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install nginx-ingress-controller bitnami/nginx-ingress-controller --set kind=DaemonSet --set daemonset.useHostPort=true --set defaultBackend.enabled=false
```

### 2. 推荐不修改默认的 NodePort 暴露 bk-nodeman backend API Service

backend API 主要用于以下场景

* 作为 蓝鲸 APIGW 的 EndPoints
* 为 bk-nodeman SaaS 提供 API 服务
* Agent、Proxy 安装回调地址

考虑到部分安装目标机器不一定具备 **域名解析** 的能力，backend API 在这种场景下必须提供 `IP:PORT` 的方式形式

当然也可以考虑通过 `ingress` 的方式暴露服务或配置访问域名

### 3. 最小化配置

这是一个最小化的 `private_values.yaml`，最大限度使用默认值和内建存储部署 bk-nodeman

```yaml
## --------------------------------------
## 第三方依赖，可被 config 中的同名变量覆盖
## --------------------------------------
## 蓝鲸 PaaS url（浏览器访问蓝鲸入口）
bkPaasUrl: "http://example.com"

## 蓝鲸 Login url（浏览器跳转登录用的URL前缀）
bkLoginUrl: "http://example.com/login"

## 蓝鲸 ESB url，注意集群内外都是统一域名。集群内可以配置域名解析到内网ip
bkComponentApiUrl: "http://bkapi.example.com"

## 节点管理浏览器访问地址
bkNodemanUrl: "http://bknodeman.example.com"
## 节点管理后台访问地址
bkNodemanApiUrl: "http://bk-nodeman-backend-api"

## 蓝鲸作业平台浏览器访问地址
bkJobUrl: "http://job.example.com"

## 蓝鲸权限中心 SaaS 地址
bkIamUrl: "http://bkiam.example.com"
## 蓝鲸权限中心后台 API 地址
bkIamApiUrl: "http://bkiam-api.example.com"

## 蓝鲸制品库浏览器访问域名和后台 API http://bkiam-api.example.com 域名同一个
bkRepoUrl: "http://bkrepo.example.com"

config:
  appCode: "bk_nodeman"
  appSecret: "xxxxx"
  bkNodemanApiUrl: "http://bk-nodeman-backend-api:10300"
  bkRepoProject: "xxxx"
  bkRepoPassword: "xxxx"
  bkRepoUsername: "xxxx"
  bkRepoPublicBucket: "xxxx"
```

### 4. SaaS 调用 bk-nodeman-backend-api

SaaS 默认通过 `bkComponentApiUrl` 访问 bk-nodeman 后台，若需要直接调用自身服务或其他可用的后台服务，可以设置 `config.bkAppBkNodeApiGateway` 覆盖默认配置

## 常见问题

**1. 首次启动失败，是 bk-nodeman Chart有问题吗**

* bk-nodeman Chart 部分 `bitnami` 依赖默认从 `docker.io` 拉镜像，如果网络不通或被 `docker hub` 限制，将导致镜像拉取失败
* 参考配置列表修改镜像地址。

**2. 如何查看日志？**

* kubectl logs pod 查看实时日志
* 日志默认为标准输出（`config.logType=STDOUT`），可以通过设置 `config.logType=DEFAULT` ，在容器中的 `config.bkLogDir` 路径下查看日志
