// 应用配置
module.exports = {
  // 服务器配置
  server: {
    port: 3000,
    env: 'development'
  },

  // MySQL 配置
  mysql: {
    // 开发规范提示（作业环境简化）：建议先按统一默认值启动本地 MySQL，避免“连不上库”
    // 例如：host=localhost port=3306 user=root password=root database=personal_cms
    host: 'localhost',
    port: 3306,
    user: 'root',
    password: '',
    database: 'test',
    connectionLimit: 10
  },

  // Redis 配置
  redis: {
    // 开发规范提示（作业环境简化）：本机没有 Redis 时，建议保持“可选”；启用前先确保本地 Redis 按统一默认值启动
    host: 'localhost',
    port: 6379,
    password: '',
    db: 0,
    keyPrefix: 'app:'
  },

  // CORS 配置
  cors: {
    // 放开所有域名
    // 注意：当 origin 为 '*' 时，不能同时开启 credentials，否则浏览器会拦截
    origin: '*',
    credentials: false,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    // 开发规范提示：前端如果带了自定义请求头（例如 user-id、token 等），必须把字段名加进 allowedHeaders，否则会预检失败
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
  },

  // 限流配置
  rateLimit: {
    windowMs: 15 * 60 * 1000, // 15分钟
    max: 100 // 最多100个请求
  },

  // JWT 配置
  jwt: {
    secret: 'your-secret-key-change-in-production',
    expiresIn: '7d'
  },

  // 日志配置
  log: {
    level: 'info',
    dir: './logs',
    maxSize: '20m',
    maxFiles: '14d'
  }
};
