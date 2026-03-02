/**
 * 工具函数库
 */

// API配置
const API_CONFIG = {
    baseURL: 'http://localhost:3000/api', // 根据实际后端地址修改
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
};

// 配置Axios
if (typeof axios !== 'undefined') {
    axios.defaults.baseURL = API_CONFIG.baseURL;
    axios.defaults.timeout = API_CONFIG.timeout;
    axios.defaults.headers.common['Content-Type'] = API_CONFIG.headers['Content-Type'];

    // 请求拦截器
    axios.interceptors.request.use(
        config => {
            // 开发规范提示：如果你在跨域请求里加了自定义请求头（包括 Authorization），后端必须在 CORS allowedHeaders 里声明，否则预检会失败
            // 可以在这里添加 token 等认证信息
            const token = localStorage.getItem('token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        },
        error => {
            return Promise.reject(error);
        }
    );

    // 响应拦截器
    axios.interceptors.response.use(
        response => {
            return response.data;
        },
        error => {
            if (error.response) {
                const { status, data } = error.response;
                switch (status) {
                    case 401:
                        showMessage('未授权，请重新登录', 'danger');
                        // 可以跳转到登录页
                        break;
                    case 403:
                        showMessage('没有权限访问', 'danger');
                        break;
                    case 404:
                        showMessage('请求的资源不存在', 'warning');
                        break;
                    case 500:
                        showMessage('服务器错误', 'danger');
                        break;
                    default:
                        showMessage(data?.message || '请求失败', 'danger');
                }
            } else {
                showMessage('网络错误，请检查网络连接', 'danger');
            }
            return Promise.reject(error);
        }
    );
}

/**
 * 显示消息提示
 * @param {string} message - 消息内容
 * @param {string} type - 消息类型 (success, danger, warning, info)
 * @param {number} duration - 显示时长（毫秒）
 */
function showMessage(message, type = 'info', duration = 3000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, duration);
}

/**
 * 格式化日期
 * @param {Date|string|number} date - 日期
 * @param {string} format - 格式，默认 'YYYY-MM-DD HH:mm:ss'
 * @returns {string}
 */
function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
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
}

/**
 * 防抖函数
 * @param {Function} func - 要执行的函数
 * @param {number} wait - 等待时间（毫秒）
 * @returns {Function}
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 * @param {Function} func - 要执行的函数
 * @param {number} limit - 时间限制（毫秒）
 * @returns {Function}
 */
function throttle(func, limit = 300) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * 验证邮箱格式
 * @param {string} email - 邮箱地址
 * @returns {boolean}
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * 验证手机号（中国）
 * @param {string} phone - 手机号
 * @returns {boolean}
 */
function isValidPhone(phone) {
    const phoneRegex = /^1[3-9]\d{9}$/;
    return phoneRegex.test(phone);
}

/**
 * 获取URL参数
 * @param {string} name - 参数名
 * @returns {string|null}
 */
function getUrlParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

/**
 * 设置URL参数
 * @param {string} name - 参数名
 * @param {string} value - 参数值
 */
function setUrlParam(name, value) {
    const url = new URL(window.location);
    url.searchParams.set(name, value);
    window.history.pushState({}, '', url);
}

/**
 * 深拷贝对象
 * @param {any} obj - 要拷贝的对象
 * @returns {any}
 */
function deepClone(obj) {
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
}

/**
 * 加载中状态
 * @param {HTMLElement} element - 元素
 * @param {boolean} isLoading - 是否加载中
 */
function setLoading(element, isLoading) {
    if (isLoading) {
        element.disabled = true;
        const originalHTML = element.innerHTML;
        element.dataset.originalHTML = originalHTML;
        element.innerHTML = '<span class="loading"></span> 加载中...';
    } else {
        element.disabled = false;
        if (element.dataset.originalHTML) {
            element.innerHTML = element.dataset.originalHTML;
            delete element.dataset.originalHTML;
        }
    }
}

/**
 * 本地存储工具
 */
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.error('Storage set error:', e);
        }
    },
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Storage get error:', e);
            return defaultValue;
        }
    },
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.error('Storage remove error:', e);
        }
    },
    clear() {
        try {
            localStorage.clear();
        } catch (e) {
            console.error('Storage clear error:', e);
        }
    }
};

// 导出到全局
window.Utils = {
    showMessage,
    formatDate,
    debounce,
    throttle,
    isValidEmail,
    isValidPhone,
    getUrlParam,
    setUrlParam,
    deepClone,
    setLoading,
    Storage
};