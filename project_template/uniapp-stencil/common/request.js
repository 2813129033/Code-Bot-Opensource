// 可选：请求封装（对齐 express-backend 的统一响应格式）
// - 自动拼接 baseURL + apiPrefix
// - 自动附加 Authorization: Bearer <token>（如果已设置）
import { BACKEND_CONFIG } from './config';
import { getToken } from './auth';

function buildUrl(path) {
  const base = BACKEND_CONFIG.baseURL.replace(/\/+$/, '');
  const prefix = (BACKEND_CONFIG.apiPrefix || '').replace(/\/+$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${base}${prefix}${p}`;
}

export function request(path, options = {}) {
  const {
    method = 'GET',
    data = undefined,
    header = {},
    timeout = 10000
  } = options;

  const token = getToken();
  const finalHeader = {
    'Content-Type': 'application/json',
    ...header
  };
  if (token) {
    // 开发规范提示：Authorization 属于自定义头；跨域/代理时，后端需在 CORS allowedHeaders 中声明 Authorization
    finalHeader.Authorization = `Bearer ${token}`;
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: buildUrl(path),
      method,
      data,
      header: finalHeader,
      timeout,
      success: (res) => {
        const body = res.data;

        // 兼容后端 responseHandler：{ success, message, data }
        if (body && typeof body === 'object' && 'success' in body) {
          if (body.success) {
            return resolve(body);
          }
          const err = new Error(body.message || '请求失败');
          err.code = body.code || 'REQUEST_FAILED';
          err.statusCode = res.statusCode;
          return reject(err);
        }

        // 若后端不是统一格式，则直接返回
        return resolve(body);
      },
      fail: (err) => reject(err)
    });
  });
}

export const get = (path, options = {}) => request(path, { ...options, method: 'GET' });
export const post = (path, data, options = {}) => request(path, { ...options, method: 'POST', data });
export const put = (path, data, options = {}) => request(path, { ...options, method: 'PUT', data });
export const del = (path, options = {}) => request(path, { ...options, method: 'DELETE' });

