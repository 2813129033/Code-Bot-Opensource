// 可选：后端 API（配套 express-backend 模板）
import { get, post, put, del } from './request';
import { BACKEND_CONFIG } from './config';
import { getToken } from './auth';

export const api = {
  // 健康检查：注意这个接口不在 /api 下（express-backend: GET /health）
  async health() {
    const base = BACKEND_CONFIG.baseURL.replace(/\/+$/, '');
    return new Promise((resolve, reject) => {
      uni.request({
        url: `${base}/health`,
        method: 'GET',
        header: { 'Content-Type': 'application/json' },
        success: (res) => resolve(res.data),
        fail: (err) => reject(err)
      });
    });
  },

  // =====================
  // 认证（JWT）
  // =====================
  register(payload) {
    return post('/auth/register', payload);
  },
  login(payload) {
    return post('/auth/login', payload);
  },
  me() {
    return get('/auth/me');
  },
  refresh() {
    return post('/auth/refresh', {});
  },

  // =====================
  // 用户
  // =====================
  listUsers(params = {}) {
    return get('/users', { data: params });
  },
  getUser(id) {
    return get(`/users/${id}`);
  },
  updateMe(payload) {
    // 后端示例里是 PUT /api/users/:id，需要 token 中的 userId 才能对齐权限
    // 这里不解析 token，仅提供最小示例：调用者自行传 id
    return put(`/users/${payload.id}`, payload);
  },

  // =====================
  // 上传（图片/视频）
  // =====================
  uploadImage(filePath, name = 'image') {
    return uploadFile('/upload/image', filePath, name);
  },
  uploadVideo(filePath, name = 'video') {
    return uploadFile('/upload/video', filePath, name);
  }
};

function uploadFile(apiPath, filePath, name) {
  const base = BACKEND_CONFIG.baseURL.replace(/\/+$/, '');
  const prefix = (BACKEND_CONFIG.apiPrefix || '').replace(/\/+$/, '');
  const token = getToken();

  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: `${base}${prefix}${apiPath}`,
      filePath,
      name,
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        try {
          const body = JSON.parse(res.data);
          if (body && typeof body === 'object' && 'success' in body) {
            if (body.success) return resolve(body);
            const err = new Error(body.message || '上传失败');
            err.code = body.code || 'UPLOAD_FAILED';
            return reject(err);
          }
          return resolve(body);
        } catch (e) {
          return resolve(res.data);
        }
      },
      fail: (err) => reject(err)
    });
  });
}

