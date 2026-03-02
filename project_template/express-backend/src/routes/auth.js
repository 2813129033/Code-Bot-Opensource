const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const { authenticate } = require('../middleware/auth');

// 注册
router.post('/register', authController.register);

// 登录
router.post('/login', authController.login);

// 获取当前用户信息（需要认证）
router.get('/me', authenticate, authController.getCurrentUser);

// 刷新Token（需要认证）
router.post('/refresh', authenticate, authController.refreshToken);

module.exports = router;
