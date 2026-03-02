const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const path = require('path');

const config = require('./config');
const logger = require('./utils/logger');
// 开发规范提示：mysql.js/redis.js 导出的是对象（module.exports = { connectMySQL, ... }），这里必须解构导入
const { connectMySQL } = require('./config/mysql');
const { connectRedis } = require('./config/redis');
const errorHandler = require('./middleware/errorHandler');
const responseHandler = require('./middleware/responseHandler');

const app = express();
const PORT = config.server.port;

// 可选：MySQL（如果不需要数据库，可以移除/注释掉这一段）
// 连接MySQL数据库
connectMySQL();

// 可选：Redis（如果不需要缓存/队列，可以移除/注释掉这一段）
// 连接Redis
connectRedis();

// 基础中间件
app.use(helmet()); // 安全头
app.use(compression()); // 响应压缩
app.use(morgan('combined', { stream: { write: message => logger.info(message.trim()) } })); // 日志

// CORS配置
app.use(cors(config.cors));

// 可选：限流（如果不需要限流，可以移除/注释掉这一段）
// 限流配置
const limiter = rateLimit({
  // 开发规范提示：如果你在代理/反代后运行（或本地用了开发代理），可能遇到：
  // - ERR_ERL_UNEXPECTED_X_FORWARDED_FOR
  // - ERR_ERL_PERMISSIVE_TRUST_PROXY
  // 处理方式：设置 app.set('trust proxy', 1)；开发环境必要时可参考规范禁用严格 validate
  windowMs: config.rateLimit.windowMs,
  max: config.rateLimit.max,
  message: {
    success: false,
    message: '请求过于频繁，请稍后再试',
    code: 'RATE_LIMIT_EXCEEDED'
  }
});
app.use('/api/', limiter);

// 解析请求体
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// 响应处理中间件
app.use(responseHandler);

// 可选：上传静态目录（如果不做上传/静态资源，可以移除/注释掉这一段）
// 静态资源：上传文件访问
app.use('/uploads', express.static(path.join(process.cwd(), 'uploads')));

// 可选：健康检查（不需要可移除）
// 健康检查
app.get('/health', async (req, res) => {
  const { getPool } = require('./config/mysql');
  const { getClient } = require('./config/redis');
  
  const health = {
    status: 'OK',
    timestamp: new Date().toISOString(),
    environment: config.server.env,
    uptime: process.uptime(),
    services: {
      mysql: 'unknown',
      redis: 'unknown'
    }
  };

  // 检查 MySQL 连接
  try {
    const pool = getPool();
    if (pool) {
      const connection = await pool.getConnection();
      await connection.ping();
      connection.release();
      health.services.mysql = 'connected';
    }
  } catch (error) {
    health.services.mysql = 'disconnected';
    health.status = 'DEGRADED';
  }

  // 检查 Redis 连接
  try {
    const redisClient = getClient();
    if (redisClient && redisClient.isOpen) {
      await redisClient.ping();
      health.services.redis = 'connected';
    } else {
      health.services.redis = 'disconnected';
    }
  } catch (error) {
    health.services.redis = 'disconnected';
    if (health.status === 'OK') {
      health.status = 'DEGRADED';
    }
  }

  const statusCode = health.status === 'OK' ? 200 : 503;
  res.status(statusCode).json({
    success: health.status === 'OK',
    message: health.status === 'OK' ? '服务正常' : '服务降级',
    data: health,
    timestamp: health.timestamp
  });
});

// 可选：示例 API 路由（不需要可移除/注释掉）
// API路由
app.use('/api/auth', require('./routes/auth'));
app.use('/api/users', require('./routes/users'));
app.use('/api/upload', require('./routes/upload'));

// 404处理
app.use('*', (req, res) => {
  res.error('接口不存在', 404);
});

// 全局错误处理
app.use(errorHandler);

// 启动服务器
app.listen(PORT, () => {
  logger.info(`🚀 Express server started on port ${PORT}`);
  logger.info(`📊 Environment: ${config.server.env}`);
});

// 优雅关闭
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  process.exit(0);
});

module.exports = app;