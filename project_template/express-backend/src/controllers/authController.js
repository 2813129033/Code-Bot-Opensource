const bcrypt = require('bcryptjs');
const { generateToken } = require('../utils/jwt');
const { query } = require('../config/mysql');
const logger = require('../utils/logger');

/**
 * 用户注册
 */
const register = async (req, res, next) => {
  try {
    const { username, email, password } = req.body;

    // 验证必填字段
    if (!username || !email || !password) {
      return res.error('用户名、邮箱和密码不能为空', 400, 'VALIDATION_ERROR');
    }

    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.error('邮箱格式不正确', 400, 'VALIDATION_ERROR');
    }

    // 验证密码长度
    if (password.length < 6) {
      return res.error('密码长度至少6位', 400, 'VALIDATION_ERROR');
    }

    // 检查用户名是否已存在
    const existingUser = await query(
      'SELECT id FROM users WHERE username = ? OR email = ?',
      [username, email]
    );

    if (existingUser.length > 0) {
      return res.error('用户名或邮箱已存在', 409, 'USER_EXISTS');
    }

    // 加密密码
    // 开发规范提示：数据库里的 password 必须是 bcrypt hash；不要存明文，否则 compare 会一直失败
    const hashedPassword = await bcrypt.hash(password, 10);

    // 创建用户
    const result = await query(
      'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
      [username, email, hashedPassword]
    );

    const userId = result.insertId;

    // 生成 Token
    const token = generateToken({ userId, username, email });

    logger.info(`User registered: ${username} (${email})`);

    res.success({
      user: {
        id: userId,
        username,
        email
      },
      token
    }, '注册成功', 201);
  } catch (error) {
    logger.error('Register error:', error);
    next(error);
  }
};

/**
 * 用户登录
 */
const login = async (req, res, next) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.error('用户名和密码不能为空', 400, 'VALIDATION_ERROR');
    }

    // 查找用户（支持用户名或邮箱登录）
    const users = await query(
      'SELECT id, username, email, password FROM users WHERE username = ? OR email = ?',
      [username, username]
    );

    if (users.length === 0) {
      return res.error('用户名或密码错误', 401, 'INVALID_CREDENTIALS');
    }

    const user = users[0];

    // 验证密码
    const isValidPassword = await bcrypt.compare(password, user.password);
    if (!isValidPassword) {
      return res.error('用户名或密码错误', 401, 'INVALID_CREDENTIALS');
    }

    // 生成 Token
    const token = generateToken({
      userId: user.id,
      username: user.username,
      email: user.email
    });

    logger.info(`User logged in: ${user.username} (${user.email})`);

    res.success({
      user: {
        id: user.id,
        username: user.username,
        email: user.email
      },
      token
    }, '登录成功');
  } catch (error) {
    logger.error('Login error:', error);
    next(error);
  }
};

/**
 * 获取当前用户信息
 */
const getCurrentUser = async (req, res, next) => {
  try {
    const userId = req.user.userId;

    const users = await query(
      'SELECT id, username, email, created_at FROM users WHERE id = ?',
      [userId]
    );

    if (users.length === 0) {
      return res.error('用户不存在', 404, 'USER_NOT_FOUND');
    }

    const user = users[0];
    res.success(user, '获取成功');
  } catch (error) {
    logger.error('Get current user error:', error);
    next(error);
  }
};

/**
 * 刷新 Token（可选功能）
 */
const refreshToken = async (req, res, next) => {
  try {
    const userId = req.user.userId;

    const users = await query(
      'SELECT id, username, email FROM users WHERE id = ?',
      [userId]
    );

    if (users.length === 0) {
      return res.error('用户不存在', 404, 'USER_NOT_FOUND');
    }

    const user = users[0];
    const token = generateToken({
      userId: user.id,
      username: user.username,
      email: user.email
    });

    res.success({ token }, 'Token刷新成功');
  } catch (error) {
    logger.error('Refresh token error:', error);
    next(error);
  }
};

module.exports = {
  register,
  login,
  getCurrentUser,
  refreshToken
};
