import axios from 'axios'
import { showToast } from 'vant'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000
})

request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  response => {
    const { code, message, data } = response.data
    if (code === 200) {
      return data
    } else {
      showToast(message || '请求失败')
      return Promise.reject(new Error(message || '请求失败'))
    }
  },
  error => {
    if (error.response) {
      const { status } = error.response
      if (status === 401) {
        showToast('登录已过期，请重新登录')
        localStorage.removeItem('token')
        window.location.href = '/login'
      } else {
        showToast(error.response.data.message || '请求失败')
      }
    } else {
      showToast('网络错误，请检查网络连接')
    }
    return Promise.reject(error)
  }
)

export default request
