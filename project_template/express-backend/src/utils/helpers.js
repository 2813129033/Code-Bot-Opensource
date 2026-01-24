// 通用工具函数

/**
 * 生成随机字符串
 * @param {number} length - 字符串长度
 * @returns {string}
 */
const generateRandomString = (length = 32) => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
};

/**
 * 格式化日期
 * @param {Date|string} date - 日期对象或字符串
 * @param {string} format - 格式，默认 'YYYY-MM-DD HH:mm:ss'
 * @returns {string}
 */
const formatDate = (date, format = 'YYYY-MM-DD HH:mm:ss') => {
  const d = new Date(date);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const seconds = String(d.getSeconds()).padStart(2, '0');

  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
};

/**
 * 分页计算
 * @param {number} page - 当前页
 * @param {number} limit - 每页数量
 * @returns {{offset: number, limit: number}}
 */
const paginate = (page = 1, limit = 10) => {
  const pageNum = Math.max(1, parseInt(page) || 1);
  const limitNum = Math.max(1, Math.min(100, parseInt(limit) || 10));
  const offset = (pageNum - 1) * limitNum;

  return {
    offset,
    limit: limitNum,
    page: pageNum
  };
};

/**
 * 构建分页信息
 * @param {number} total - 总数
 * @param {number} page - 当前页
 * @param {number} limit - 每页数量
 * @returns {object}
 */
const buildPagination = (total, page = 1, limit = 10) => {
  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.max(1, Math.min(page, totalPages));

  return {
    currentPage,
    totalPages,
    totalItems: total,
    itemsPerPage: limit,
    hasNext: currentPage < totalPages,
    hasPrev: currentPage > 1
  };
};

/**
 * 深度克隆对象
 * @param {any} obj - 要克隆的对象
 * @returns {any}
 */
const deepClone = (obj) => {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  if (obj instanceof Date) {
    return new Date(obj.getTime());
  }
  if (obj instanceof Array) {
    return obj.map(item => deepClone(item));
  }
  if (typeof obj === 'object') {
    const clonedObj = {};
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key]);
      }
    }
    return clonedObj;
  }
};

/**
 * 验证邮箱格式
 * @param {string} email - 邮箱地址
 * @returns {boolean}
 */
const isValidEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * 验证手机号格式（中国）
 * @param {string} phone - 手机号
 * @returns {boolean}
 */
const isValidPhone = (phone) => {
  const phoneRegex = /^1[3-9]\d{9}$/;
  return phoneRegex.test(phone);
};

/**
 * 延迟执行
 * @param {number} ms - 延迟毫秒数
 * @returns {Promise}
 */
const sleep = (ms) => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * 安全获取对象属性
 * @param {object} obj - 对象
 * @param {string} path - 属性路径，如 'user.profile.name'
 * @param {any} defaultValue - 默认值
 * @returns {any}
 */
const get = (obj, path, defaultValue = undefined) => {
  const keys = path.split('.');
  let result = obj;
  
  for (const key of keys) {
    if (result === null || result === undefined) {
      return defaultValue;
    }
    result = result[key];
  }
  
  return result !== undefined ? result : defaultValue;
};

module.exports = {
  generateRandomString,
  formatDate,
  paginate,
  buildPagination,
  deepClone,
  isValidEmail,
  isValidPhone,
  sleep,
  get
};