/**
 * 可选：对接 express-backend 模板的“配套功能”
 *
 * 适配接口：
 * - GET    /health
 * - POST   /api/auth/register
 * - POST   /api/auth/login
 * - GET    /api/auth/me
 * - GET    /api/users
 * - POST   /api/upload/image   (form-data: image=<file>)
 * - POST   /api/upload/video   (form-data: video=<file>)
 *
 * 使用方式（可选）：
 * 1) 在页面中引入本文件（例如 index.html 末尾加一行 script）
 * 2) 确保已经引入 axios + assets/js/utils.js（里面配置了 baseURL 和 token 注入）
 * 3) 调用 window.Backend.xxx()
 */

(function () {
  if (typeof axios === 'undefined') {
    // 不强行依赖：如果页面没引入 axios，本文件什么都不做
    return;
  }

  async function health() {
    // 注意：/health 不在 /api 下，需要临时拼 baseURL（utils.js 里 baseURL 是 /api）
    const apiBase = (axios.defaults.baseURL || '').replace(/\/+$/, '');
    const base = apiBase.replace(/\/api$/, '');
    const res = await axios.get(`${base}/health`);
    return res; // { success, message, data, ... } 或后端返回体
  }

  async function register(payload) {
    return axios.post('/auth/register', payload);
  }

  async function login(payload) {
    const res = await axios.post('/auth/login', payload);
    // 可选：如果返回 token，就保存到 localStorage（utils.js 的拦截器会自动带上）
    if (res && res.data && res.data.token) {
      localStorage.setItem('token', res.data.token);
    }
    return res;
  }

  async function me() {
    return axios.get('/auth/me');
  }

  async function listUsers(params) {
    return axios.get('/users', { params: params || {} });
  }

  async function uploadImage(file, fieldName = 'image') {
    const fd = new FormData();
    fd.append(fieldName, file);
    // axios 会自动设置 multipart boundary；这里不要设置 Content-Type
    return axios.post('/upload/image', fd);
  }

  async function uploadVideo(file, fieldName = 'video') {
    const fd = new FormData();
    fd.append(fieldName, file);
    return axios.post('/upload/video', fd);
  }

  // 导出（可选模块）
  window.Backend = {
    health,
    register,
    login,
    me,
    listUsers,
    uploadImage,
    uploadVideo
  };
})();

