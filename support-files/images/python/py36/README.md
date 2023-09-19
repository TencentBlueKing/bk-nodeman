## PYTHON 3.6 编译
此文档用于介绍如何编译节点管理``Proxy``服务器上部署的``python``服务二进制

### 前置步骤
编译宿主机需开启路由功能，否则影响容器在编译过程中的依赖下载与编译, 详情请参考: [参考文档](https://stackoverflow.com/questions/41453263/docker-networking-disabled-warning-ipv4-forwarding-is-disabled-networking-wil)

### 编译
1. 同步``Dockerfile``
2. 编译并复制
```bash
docker build -t python36:latest .

# 检查编译步骤无误后
docker_id=$(docker run -d  $(docker build -t python36:latest -q .)  bash -c "while true; do echo hello world; sleep 1; done")
docker cp $docker_id:/tmp/py36.tgz  py36.tgz
```
3. 停止容器
```bash
docker stop $docker_id
 ```

### py36.tgz 替换
替换路径 `/data/bkee/public/bknodeman/download` 中的文件`py36.tgz`
