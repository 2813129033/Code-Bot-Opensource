const express = require('express');
const router = express.Router();
const userController = require('../controllers/userController');
const { authenticate, optionalAuth } = require('../middleware/auth');

// 获取用户列表（可选认证，未认证也能访问）
router.get('/', optionalAuth, userController.getUsers);

// 根据ID获取用户信息（可选认证）
router.get('/:id', optionalAuth, userController.getUserById);

// 更新用户信息（需要认证）
router.put('/:id', authenticate, userController.updateUser);

// 删除用户（需要认证）
router.delete('/:id', authenticate, userController.deleteUser);

module.exports = router;
