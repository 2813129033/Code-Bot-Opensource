// 可选：JWT Token 管理（配套 express-backend 的 /api/auth）
import { BACKEND_CONFIG } from './config';

export function getToken() {
  return uni.getStorageSync(BACKEND_CONFIG.tokenKey) || '';
}

export function setToken(token) {
  uni.setStorageSync(BACKEND_CONFIG.tokenKey, token || '');
}

export function clearToken() {
  uni.removeStorageSync(BACKEND_CONFIG.tokenKey);
}

