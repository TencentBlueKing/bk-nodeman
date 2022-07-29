## Nginx 编译
此文档用于介绍如何编译节点管理``Proxy``服务器上部署的``nginx``服务二进制

### 前置步骤
编译宿主机需开启路由功能，否则影响容器在编译过程中的依赖下载与编译, 详情请参考: [参考文档](https://stackoverflow.com/questions/41453263/docker-networking-disabled-warning-ipv4-forwarding-is-disabled-networking-wil)

### 编译
1. 同步``Dockerfile``
2. 编译并复制
```bash
docker build -t nginx:latest .

# 检查编译步骤无误后
docker_id=$(docker run -d  $(docker build -t nginx:latest -q .)  bash -c "while true; do echo hello world; sleep 1; done")
docker cp $docker_id:/opt/nginx-portable/bin/nginx nginx 
```
3. 停止容器
```bash
docker stop $docker_id
 ```

### 修改编译版本
```bash
容器构建命令可调整为: docker build --build-arg NGINX_VERSION=1.20.2 --build-arg OPENSSL_VERSION=1.1.2 -t nginx:latest .
```

### nginx-portable.tgz 替换
> 该压缩包包含相关的操作脚本、配置文件、与``MIME-type``媒体类型区分文件
1. 解压原来``script_tools``目录下的``nginx-portable.tgz``
```bash
tar xvf script_tools/nginx-portable.tgz -C .
```
2. 替换``nginx-portable/bin/``目录下的``nginx``二进制文件
3. 重新打包``nginx-portable.tgz``
```bash
tar czf script_tools/nginx-portable.tgz nginx-portable
```