import request from '@/utils/request'

export const getProducts = (params) => {
  return request.get('/products', { params })
}

export const getProductDetail = (id) => {
  return request.get(`/products/${id}`)
}

export const searchProducts = (keyword) => {
  return request.get('/products/search', { params: { keyword } })
}
