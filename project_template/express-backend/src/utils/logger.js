const winston = require('winston');
const DailyRotateFile = require('winston-daily-rotate-file');
const path = require('path');
const fs = require('fs');

const config = require('../config');

// 确保日志目录存在
const logDir = config.log.dir;
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

// 日志格式
const logFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.errors({ stack: true }),
  winston.format.splat(),
  winston.format.json()
);

// 控制台格式
const consoleFormat = winston.format.combine(
  winston.format.colorize(),
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    let msg = `${timestamp} [${level}]: ${message}`;
    if (Object.keys(meta).length > 0) {
      msg += ` ${JSON.stringify(meta)}`;
    }
    return msg;
  })
);

// 创建logger实例
const logger = winston.createLogger({
  level: config.log.level,
  format: logFormat,
  defaultMeta: { service: 'express-backend' },
  transports: [
    // 错误日志文件
    new DailyRotateFile({
      filename: path.join(logDir, 'error-%DATE%.log'),
      datePattern: 'YYYY-MM-DD',
      level: 'error',
      maxSize: config.log.maxSize,
      maxFiles: config.log.maxFiles,
      format: logFormat
    }),
    // 所有日志文件
    new DailyRotateFile({
      filename: path.join(logDir, 'combined-%DATE%.log'),
      datePattern: 'YYYY-MM-DD',
      maxSize: config.log.maxSize,
      maxFiles: config.log.maxFiles,
      format: logFormat
    })
  ]
});

// 开发环境添加控制台输出
if (config.server.env !== 'production') {
  logger.add(new winston.transports.Console({
    format: consoleFormat
  }));
}

module.exports = logger;