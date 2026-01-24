const errorHandler = (err, req, res, next) => {
  const logger = require('../utils/logger');
  
  // 记录错误日志
  logger.error('Error occurred:', {
    message: err.message,
    stack: err.stack,
    url: req.originalUrl,
    method: req.method,
    ip: req.ip,
    body: req.body
  });

  // 默认错误信息
  let statusCode = err.statusCode || err.status || 500;
  let message = err.message || '服务器内部错误';

  // 处理不同类型的错误
  if (err.name === 'ValidationError') {
    statusCode = 400;
    message = '数据验证失败';
  } else if (err.name === 'UnauthorizedError') {
    statusCode = 401;
    message = '未授权访问';
  } else if (err.name === 'CastError') {
    statusCode = 400;
    message = '无效的参数格式';
  }

  // 返回错误响应
  res.status(statusCode).json({
    success: false,
    message: message,
    code: err.code || 'INTERNAL_ERROR',
    ...(process.env.NODE_ENV === 'development' && {
      stack: err.stack,
      error: err
    })
  });
};

module.exports = errorHandler;