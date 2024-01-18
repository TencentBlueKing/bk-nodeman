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
// 3.  @blueking/notice-component-vue2 安装不成功时请使用如下命令单独安装
npm install @blueking/notice-component-vue2@2.0.1 --legacy-peer-deps
// 4. 更新 magicbox 组件库
npm run dll
// 5. 启动服务
npm run dev 
```

### eslint 
前端文件不处于根目录时, eslint不生效。 根目录新建 `vetur.config.js` 文件。引导正确js、ts检查配置文件路径, 同下：
```javascript
module.exports = {
  projects: [
    './frontend',
    {
      root: './frontend',
      package: './package.json',
      tsconfig: './tsconfig.json',
      snippetFolder: './.vscode/vetur/snippets',
      globalComponents: [
        './src/components/**/*.vue'
      ]
    }
  ]
}
```