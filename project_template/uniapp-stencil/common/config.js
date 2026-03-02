// 可选：后端配套配置（用于对接 express-backend 模板）
// 不需要后端/接口时，这个文件可以保留但不必被任何页面引用。

export const BACKEND_CONFIG = {
  // 后端地址（对应 express-backend：例如 http://localhost:3000 ）
  baseURL: 'http://localhost:3000',

  // API 前缀（express-backend 默认 /api）
  apiPrefix: '/api',

  // Token 本地存储 key
  tokenKey: 'token'
};

