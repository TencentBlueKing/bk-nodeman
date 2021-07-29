### 前端工程指引

#### 新建配置文件

在`frontend`目录下面新建`local_settings.js`，配置如下内容：

```javascript
module.exports = {
  proxyTableTarget: '线下代理地址',
  devHost: '127.0.0.1'
};
```

#### 运行项目

```shell
// 1. 切换到 /frontend 目录
cd frontend
// 2. 安装 npm 依赖包
npm install
// 3. 更新 magicbox 组件库
npm run dll
// 4. 启动服务
npm run dev 
```