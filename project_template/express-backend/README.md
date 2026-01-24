# Express Backend Framework

通用的 Express.js 后端框架模板，包含基础配置和常用功能。

## 功能特性

- ✅ Express.js 基础配置
- ✅ MySQL 数据库连接池
- ✅ Redis 缓存支持
- ✅ 日志系统（Winston + 日志轮转）
- ✅ 统一错误处理
- ✅ 统一响应格式
- ✅ CORS 配置
- ✅ 请求限流
- ✅ 安全中间件（Helmet）
- ✅ 通用工具函数

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 3. 启动服务

开发环境：
```bash
npm run dev
```

生产环境：
```bash
npm start
```

## 项目结构

```
express-backend/
├── src/
│   ├── app.js                 # 应用入口
│   ├── config/                # 配置文件
│   │   ├── mysql.js          # MySQL配置
│   │   └── redis.js          # Redis配置
│   ├── middleware/            # 中间件
│   │   ├── errorHandler.js   # 错误处理
│   │   └── responseHandler.js # 响应处理
│   ├── routes/                # 路由（业务路由放这里）
│   └── utils/                 # 工具函数
│       ├── logger.js          # 日志工具
│       └── helpers.js         # 通用工具
├── logs/                      # 日志文件目录
├── package.json
└── .env.example
```

## 使用示例

### 使用MySQL

```javascript
const { query, transaction } = require('./config/mysql');

// 简单查询
const users = await query('SELECT * FROM users WHERE id = ?', [1]);

// 事务
await transaction(async (connection) => {
  await connection.execute('INSERT INTO users (name) VALUES (?)', ['John']);
  await connection.execute('INSERT INTO logs (action) VALUES (?)', ['create_user']);
});
```

### 使用Redis

```javascript
const redis = require('./config/redis');

// 设置缓存
await redis.set('user:1', { name: 'John' }, 3600);

// 获取缓存
const user = await redis.get('user:1');

// 删除缓存
await redis.del('user:1');
```

### 使用日志

```javascript
const logger = require('./utils/logger');

logger.info('Info message');
logger.error('Error message', { error: err });
logger.warn('Warning message');
```

### 统一响应格式

```javascript
// 成功响应
res.success({ id: 1, name: 'John' }, '获取成功');

// 错误响应
res.error('操作失败', 400);

// 分页响应
res.paginated(data, pagination, '获取成功');
```

## 环境变量说明

- `PORT`: 服务端口（默认: 3000）
- `NODE_ENV`: 环境（development/production）
- `MYSQL_*`: MySQL数据库配置
- `REDIS_*`: Redis配置
- `ALLOWED_ORIGINS`: CORS允许的源
- `RATE_LIMIT_*`: 限流配置
- `LOG_*`: 日志配置

## License

MIT