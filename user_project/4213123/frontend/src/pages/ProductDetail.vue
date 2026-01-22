<template>
  <div class="product-detail">
    <van-nav-bar title="商品详情" left-arrow @click-left="goBack" />

    <van-swipe :autoplay="3000" class="product-images">
      <van-swipe-item v-for="(image, index) in product.images" :key="index">
        <img :src="image" alt="product" />
      </van-swipe-item>
    </van-swipe>

    <div class="product-info">
      <div class="price">¥{{ product.price }}</div>
      <div class="name">{{ product.name }}</div>
      <div class="description">{{ product.description }}</div>
    </div>

    <van-action-bar>
      <van-action-bar-icon icon="cart-o" text="购物车" badge="5" />
      <van-action-bar-button type="warning" text="加入购物车" @click="addToCart" />
      <van-action-bar-button type="danger" text="立即购买" @click="buyNow" />
    </van-action-bar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showToast } from 'vant'

const router = useRouter()
const route = useRoute()

const product = ref({
  id: 1,
  name: '智能手机 Pro',
  price: 2999,
  description: '高性能智能手机，搭载最新处理器，支持5G网络',
  images: [
    'https://via.placeholder.com/750x750/FF6B6B/FFFFFF?text=Product1',
    'https://via.placeholder.com/750x750/4ECDC4/FFFFFF?text=Product2',
    'https://via.placeholder.com/750x750/45B7D1/FFFFFF?text=Product3'
  ]
})

const goBack = () => {
  router.back()
}

const addToCart = () => {
  showToast('已加入购物车')
}

const buyNow = () => {
  showToast('立即购买')
}
</script>

<style scoped>
.product-images {
  height: 375px;
}

.product-images img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-info {
  padding: 15px;
  background: white;
  margin-bottom: 10px;
}

.price {
  color: #ff4444;
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 10px;
}

.name {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 10px;
}

.description {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
}
</style>
