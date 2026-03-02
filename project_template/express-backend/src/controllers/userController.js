const { query } = require('../config/mysql');
const { paginate, buildPagination } = require('../utils/helpers');
const logger = require('../utils/logger');

/**
 * 获取用户列表（分页）
 */
const getUsers = async (req, res, next) => {
  try {
    const { page = 1, limit = 10 } = req.query;
    const { offset, limit: limitNum, page: pageNum } = paginate(page, limit);

    // 查询总数
    const [countResult] = await query('SELECT COUNT(*) as total FROM users');
    // 开发规范提示：如果这里出现 “Cannot read properties of undefined (reading 'total')”，说明 countResult 为空
    // 处理方式：给 total 做安全兜底，或把 COUNT SQL 单独构建，避免替换/拼接导致空结果
    const total = countResult.total;

    // 查询用户列表
    const users = await query(
      // 开发规范提示：分页 LIMIT/OFFSET 建议不要用占位符；先把数字处理干净再拼接，减少类型导致的 SQL 报错
      'SELECT id, username, email, created_at FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?',
      [limitNum, offset]
    );

    const pagination = buildPagination(total, pageNum, limitNum);

    res.paginated(users, pagination, '获取用户列表成功');
  } catch (error) {
    logger.error('Get users error:', error);
    next(error);
  }
};

/**
 * 根据ID获取用户信息
 */
const getUserById = async (req, res, next) => {
  try {
    const { id } = req.params;

    const users = await query(
      'SELECT id, username, email, created_at FROM users WHERE id = ?',
      [id]
    );

    if (users.length === 0) {
      return res.error('用户不存在', 404, 'USER_NOT_FOUND');
    }

    res.success(users[0], '获取用户信息成功');
  } catch (error) {
    logger.error('Get user by id error:', error);
    next(error);
  }
};

/**
 * 更新用户信息（需要认证）
 */
const updateUser = async (req, res, next) => {
  try {
    const userId = req.user.userId;
    const { username, email } = req.body;

    // 验证必填字段
    if (!username && !email) {
      return res.error('至少提供一个要更新的字段', 400, 'VALIDATION_ERROR');
    }

    // 如果更新邮箱，验证格式
    if (email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        return res.error('邮箱格式不正确', 400, 'VALIDATION_ERROR');
      }

      // 检查邮箱是否已被其他用户使用
      const existingUsers = await query(
        'SELECT id FROM users WHERE email = ? AND id != ?',
        [email, userId]
      );

      if (existingUsers.length > 0) {
        return res.error('邮箱已被使用', 409, 'EMAIL_EXISTS');
      }
    }

    // 如果更新用户名，检查是否已被使用
    if (username) {
      const existingUsers = await query(
        'SELECT id FROM users WHERE username = ? AND id != ?',
        [username, userId]
      );

      if (existingUsers.length > 0) {
        return res.error('用户名已被使用', 409, 'USERNAME_EXISTS');
      }
    }

    // 构建更新SQL
    const updates = [];
    const params = [];

    if (username) {
      updates.push('username = ?');
      params.push(username);
    }

    if (email) {
      updates.push('email = ?');
      params.push(email);
    }

    params.push(userId);

    await query(
      `UPDATE users SET ${updates.join(', ')} WHERE id = ?`,
      params
    );

    // 获取更新后的用户信息
    const users = await query(
      'SELECT id, username, email, created_at FROM users WHERE id = ?',
      [userId]
    );

    logger.info(`User updated: ${userId}`);

    res.success(users[0], '更新用户信息成功');
  } catch (error) {
    logger.error('Update user error:', error);
    next(error);
  }
};

/**
 * 删除用户（需要认证，只能删除自己的账户）
 */
const deleteUser = async (req, res, next) => {
  try {
    const userId = req.user.userId;
    const { id } = req.params;

    // 只能删除自己的账户
    if (parseInt(id) !== userId) {
      return res.error('无权删除其他用户的账户', 403, 'FORBIDDEN');
    }

    await query('DELETE FROM users WHERE id = ?', [id]);

    logger.info(`User deleted: ${id}`);

    res.success(null, '删除用户成功');
  } catch (error) {
    logger.error('Delete user error:', error);
    next(error);
  }
};

module.exports = {
  getUsers,
  getUserById,
  updateUser,
  deleteUser
};
