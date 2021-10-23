# 接口管理



## ESB yaml
> 命名：nodeman.yaml
> 
> 作用：用于注册到 ESB

### 格式

```yaml
- api_type: operate
  comp_codename: generic.v2.nodeman.nodeman_component
  name: subscription_delete
  label: test
  label_en: null
  dest_path: /backend/api/subscription/delete/
  path: /v2/nodeman/backend/api/subscription/delete/
  dest_http_method: POST
  suggest_method: POST
  is_hidden: true
```

### 新增方式

* 1⃣️ 在 [nodeman.yaml](nodeman.yaml) 加入新增的接口，
* 2⃣️ 将该 yaml 文件的同步到 ESB 仓库



## apigw yaml
> 命名：apigw.yaml
> 
> 作用：注册到 APIGW

### 格式

```yaml
  /core/api/encrypt_rsa/fetch_public_keys/:
    post:
      description: 获取公钥列表
      operationId: rsa_fetch_public_keys
      tags:
      - rsa
      x-bk-apigateway-resource:
        allowApplyPermission: true
        authConfig:
          userVerifiedRequired: false
        backend:
          matchSubpath: false
          method: post
          path: /core/api/encrypt_rsa/fetch_public_keys/
          timeout: 30
          transformHeaders: {}
          type: HTTP
          upstreams: {}
        disabledStages: []
        isPublic: true
        matchSubpath: false
```

### 新增方式

自动生成 apigw.yaml
```shell
python manage.py generate_api_js --is_apigw_yaml -f docs/workflows/release/api/apigw.yaml
```

导入到 APIGW

## 前端 API modules
> 作用：用于前端请求后台

### 格式

```js
import { request } from '../base';

export const fetchPublicKeys = request('POST', 'encrypt_rsa/fetch_public_keys/');

export default {
  fetchPublicKeys,
};
```

### 新增方式

* 后台定义好接口后，执行 `python manage.py generate_api_js`，该命名会生成代码到 `frontend/src/api/modules`

* 和后台代码一并提交，前端基于该分支进行开发联调


