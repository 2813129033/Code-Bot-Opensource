import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/pages/Home.vue')
  },
  {
    path: '/product/:id',
    name: 'product',
    component: () => import('@/pages/ProductDetail.vue')
  },
  {
    path: '/cart',
    name: 'cart',
    component: () => import('@/pages/Cart.vue')
  },
  {
    path: '/user',
    name: 'user',
    component: () => import('@/pages/User.vue')
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/Login.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
