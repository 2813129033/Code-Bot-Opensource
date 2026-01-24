/**
 * API请求封装
 */

const API_BASE_URL = window.API_BASE_URL || 'http://localhost:3000/api';

/**
 * 发送HTTP请求
 * @param {string} url - 请求URL
 * @param {object} options - 请求选项
 */
async function request(url, options = {}) {
    const {
        method = 'GET',
        body = null,
        headers = {},
        showLoading = true,
        showError = true
    } = options;

    // 显示加载动画
    if (showLoading) {
        window.utils?.showLoading();
    }

    // 构建请求头
    const requestHeaders = {
        'Content-Type': 'application/json',
        ...headers
    };

    // 添加token（如果存在）
    const token = window.utils?.storage.get('token');
    if (token) {
        requestHeaders['Authorization'] = `Bearer ${token}`;
    }

    // 构建请求配置
    const config = {
        method,
        headers: requestHeaders
    };

    // 添加请求体
    if (body && method !== 'GET') {
        config.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${url}`, config);
        const data = await response.json();

        // 隐藏加载动画
        if (showLoading) {
            window.utils?.hideLoading();
        }

        // 处理响应
        if (!response.ok) {
            const errorMessage = data.message || `请求失败: ${response.status}`;
            
            // 401未授权，清除token并跳转登录
            if (response.status === 401) {
                window.utils?.storage.remove('token');
                window.location.href = '/login.html';
            }

            if (showError) {
                window.utils?.showToast(errorMessage, 'error');
            }

            throw new Error(errorMessage);
        }

        return data;
    } catch (error) {
        // 隐藏加载动画
        if (showLoading) {
            window.utils?.hideLoading();
        }

        if (showError) {
            window.utils?.showToast(error.message || '网络请求失败', 'error');
        }

        throw error;
    }
}

/**
 * GET请求
 */
function get(url, params = {}, options = {}) {
    // 构建查询字符串
    const queryString = new URLSearchParams(params).toString();
    const fullUrl = queryString ? `${url}?${queryString}` : url;
    
    return request(fullUrl, {
        ...options,
        method: 'GET'
    });
}

/**
 * POST请求
 */
function post(url, body = {}, options = {}) {
    return request(url, {
        ...options,
        method: 'POST',
        body
    });
}

/**
 * PUT请求
 */
function put(url, body = {}, options = {}) {
    return request(url, {
        ...options,
        method: 'PUT',
        body
    });
}

/**
 * DELETE请求
 */
function del(url, options = {}) {
    return request(url, {
        ...options,
        method: 'DELETE'
    });
}

/**
 * 文件上传
 * @param {string} url - 上传URL
 * @param {FormData} formData - 表单数据
 * @param {object} options - 选项
 */
async function upload(url, formData, options = {}) {
    const { showLoading = true, showError = true } = options;

    if (showLoading) {
        window.utils?.showLoading();
    }

    // 添加token
    const token = window.utils?.storage.get('token');
    const headers = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${url}`, {
            method: 'POST',
            headers,
            body: formData
        });

        const data = await response.json();

        if (showLoading) {
            window.utils?.hideLoading();
        }

        if (!response.ok) {
            const errorMessage = data.message || '上传失败';
            if (showError) {
                window.utils?.showToast(errorMessage, 'error');
            }
            throw new Error(errorMessage);
        }

        if (showError) {
            window.utils?.showToast('上传成功', 'success');
        }

        return data;
    } catch (error) {
        if (showLoading) {
            window.utils?.hideLoading();
        }
        throw error;
    }
}

// 导出到全局
window.api = {
    request,
    get,
    post,
    put,
    delete: del,
    upload
};