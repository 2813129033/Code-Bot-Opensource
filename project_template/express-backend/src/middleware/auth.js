const { verifyToken, extractToken } = require('../utils/jwt');

/**
 * JWT 认证中间件
 * 验证请求中的 JWT Token，并将用户信息附加到 req.user
 */
const authenticate = (req, res, next) => {
  try {
    const token = extractToken(req);

    if (!token) {
      return res.error('未提供认证Token', 401, 'UNAUTHORIZED');
    }

    const decoded = verifyToken(token);
    req.user = decoded; // 将解码后的用户信息附加到请求对象
    next();
  } catch (error) {
    return res.error(error.message, 401, 'UNAUTHORIZED');
  }
};

/**
 * 可选的认证中间件
 * 如果提供了 Token 则验证，否则继续执行（不要求必须认证）
 */
const optionalAuth = (req, res, next) => {
  try {
    const token = extractToken(req);
    if (token) {
      const decoded = verifyToken(token);
      req.user = decoded;
    }
    next();
  } catch (error) {
    // 可选认证失败时继续执行，但不设置 req.user
    next();
  }
};

module.exports = {
  authenticate,
  optionalAuth
};
