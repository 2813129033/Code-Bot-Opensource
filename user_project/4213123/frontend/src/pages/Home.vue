<template>
  <div class="home">
    <van-search v-model="searchValue" placeholder="搜索商品" />
    
    <van-swipe :autoplay="3000" indicator-color="white" class="banner">
      <van-swipe-item v-for="(item, index) in banners" :key="index">
        <img :src="item.image" alt="banner" />
      </van-swipe-item>
    </van-swipe>

    <van-grid :column-num="4" class="categories">
      <van-grid-item v-for="(item, index) in categories" :key="index" :icon="item.icon" :text="item.name" />
    </van-grid>

    <div class="section">
      <div class="section-title">热门商品</div>
      <van-grid :column-num="2" :gutter="10">
        <van-grid-item v-for="product in products" :key="product.id" @click="goToProduct(product.id)">
          <van-image :src="product.image" fit="cover" />
          <div class="product-name">{{ product.name }}</div>
          <div class="product-price">¥{{ product.price }}</div>
        </van-grid-item>
      </van-grid>
    </div>

    <van-tabbar v-model="activeTab" class="tabbar">
      <van-tabbar-item icon="home-o">首页</van-tabbar-item>
      <van-tabbar-item icon="cart-o">购物车</van-tabbar-item>
      <van-tabbar-item icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const searchValue = ref('')
const activeTab = ref(0)

const banners = [
  { image: 'https://via.placeholder.com/750x300/FF6B6B/FFFFFF?text=Banner1' },
  { image: 'https://via.placeholder.com/750x300/4ECDC4/FFFFFF?text=Banner2' },
  { image: 'https://via.placeholder.com/750x300/45B7D1/FFFFFF?text=Banner3' }
]

const categories = [
  { name: '手机', icon: 'phone-o' },
  { name: '电脑', icon: 'desktop-o' },
  { name: '服饰', icon: 'bag-o' },
  { name: '食品', icon: 'cart-o' }
]

const products = [
  { id: 1, name: '智能手机 Pro', price: 2999, image: 'https://via.placeholder.com/200x200/FF6B6B/FFFFFF?text=Phone' },
  { id: 2, name: '笔记本电脑', price: 5999, image: 'https://via.placeholder.com/200x200/4ECDC4/FFFFFF?text=Laptop' },
  { id: 3, name: '无线耳机', price: 299, image: 'https://via.placeholder.com/200x200/45B7D1/FFFFFF?text=Headphone' },
  { id: 4, name: '智能手表', price: 899, image: 'https://via.placeholder.com/200x200/96CEB4/FFFFFF?text=Watch' }
]

const goToProduct = (id) => {
  router.push(`/product/${id}`)
}
</script>

<style scoped>
.home {
  padding-bottom: 50px;
}

.banner {
  height: 200px;
}

.banner img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.categories {
  margin: 10px 0;
}

.section {
  padding: 15px;
}

.section-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 10px;
}

.product-name {
  font-size: 14px;
  margin: 5px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-price {
  color: #ff4444;
  font-size: 16px;
  font-weight: bold;
}

.tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
}
</style>
