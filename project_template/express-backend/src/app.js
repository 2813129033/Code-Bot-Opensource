const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

const logger = require('./utils/logger');
const connectMySQL = require('./config/mysql');
const connectRedis = require('./config/redis');
const errorHandler = require('./middleware/errorHandler');
const responseHandler = require('./middleware/responseHandler');

const app = express();
const PORT = process.env.PORT || 3000;

// 连接MySQL数据库
connectMySQL();

// 连接Redis
connectRedis();

// 基础中间件
app.use(helmet()); // 安全头
app.use(compression()); // 响应压缩
app.use(morgan('combined', { stream: { write: message => logger.info(message.trim()) } })); // 日志

// CORS配置
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));

// 限流配置
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000,
  max: parseInt(process.env.RATE_LIMIT_MAX) || 100,
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

// 健康检查
app.get('/health', (req, res) => {
  res.success({
    status: 'OK',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
    uptime: process.uptime()
  });
});

// API路由 - 这里可以添加你的业务路由
// app.use('/api/your-module', require('./routes/your-module'));

// 404处理
app.use('*', (req, res) => {
  res.error('接口不存在', 404);
});

// 全局错误处理
app.use(errorHandler);

// 启动服务器
app.listen(PORT, () => {
  logger.info(`🚀 Express server started on port ${PORT}`);
  logger.info(`📊 Environment: ${process.env.NODE_ENV || 'development'}`);
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