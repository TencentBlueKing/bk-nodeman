### windows检查脚本编译步骤

```bash
1. 安装rust，构建编译环境
2. rustup toolchain install stable-x86_64-pc-windows-gnu
3. rustup target add x86_64-pc-windows-gnu --toolchain=stable
4. brew install mingw-w64  #  安装linker
5. 在项目根目录创建.cargo目录，然后创建.cargo/config文件
cat > .cargo/config << EOF
[target.x86_64-pc-windows-gnu]

linker= "x86_64-w64-mingw32-gcc"
ar= "x86_64-w64-mingw32-gcc-ar"
EOF
6. cargo build --release --target=x86_64-pc-windows-gnu # 在target目录里有x86_64-pc-windows-gnu目录里有release目录可以找到对应可执行文件

```

### windows检查脚本使用说明

##### 用途

* 开启登陆相关服务（TODO: 没有当前服务状态检测逻辑，直接启动）
* 开启相关端口入站防火墙策略

##### 参数


```bash
win_check.exe -s service  # 开启相关服务
win_check.exe -s port # 开启相关端口防火墙
```

