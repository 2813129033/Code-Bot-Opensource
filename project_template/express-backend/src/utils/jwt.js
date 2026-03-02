const jwt = require('jsonwebtoken');
const config = require('../config');

/**
 * 生成 JWT Token
 * @param {object} payload - 载荷数据
 * @param {string} expiresIn - 过期时间，默认使用配置
 * @returns {string} JWT Token
 */
const generateToken = (payload, expiresIn = null) => {
  const options = {};
  if (expiresIn) {
    options.expiresIn = expiresIn;
  } else {
    options.expiresIn = config.jwt.expiresIn;
  }

  return jwt.sign(payload, config.jwt.secret, options);
};

/**
 * 验证 JWT Token
 * @param {string} token - JWT Token
 * @returns {object} 解码后的载荷数据
 */
const verifyToken = (token) => {
  try {
    return jwt.verify(token, config.jwt.secret);
  } catch (error) {
    if (error.name === 'TokenExpiredError') {
      throw new Error('Token已过期');
    } else if (error.name === 'JsonWebTokenError') {
      throw new Error('无效的Token');
    } else {
      throw new Error('Token验证失败');
    }
  }
};

/**
 * 从请求头中提取 Token
 * @param {object} req - Express 请求对象
 * @returns {string|null} Token 或 null
 */
const extractToken = (req) => {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    return authHeader.substring(7);
  }
  return null;
};

module.exports = {
  generateToken,
  verifyToken,
  extractToken
};
