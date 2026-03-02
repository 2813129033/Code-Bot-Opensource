# uniapp-stencil

这是一个最小的 uni-app 脚手架模板。

## 可选：对接 express-backend 模板（JWT / 用户 / 上传 / 健康检查）

本模板已提供 **可选** 的后端配套模块，但不会强制启用：

- `common/config.js`：后端地址配置
- `common/request.js`：`uni.request` 封装（自动带 Bearer Token）
- `common/auth.js`：token 存取
- `common/api.js`：对接接口（`/auth`、`/users`、`/upload`、`/health`）
- `pages/backend/*`：示例页面（**默认未注册**，需要你手动加到 `pages.json`）

### 1) 配置后端地址

修改 `common/config.js`：

- `baseURL`：例如 `http://localhost:3000`

### 2) （可选）注册示例页面

把下面页面加到 `pages.json` 的 `pages` 数组中即可：

```json
{
  "path": "pages/backend/health",
  "style": { "navigationBarTitleText": "Health（可选）" }
}
```

可用页面路径：

- `pages/backend/health`
- `pages/backend/auth`
- `pages/backend/users`
- `pages/backend/upload`

如果你不需要这些功能：**不要注册这些页面即可**。

