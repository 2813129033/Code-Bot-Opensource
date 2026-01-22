<template>
  <div class="user">
    <div class="user-header">
      <div class="avatar">
        <van-image round width="60" height="60" src="https://via.placeholder.com/60x60/FF6B6B/FFFFFF?text=User" />
      </div>
      <div class="user-info">
        <div class="nickname">{{ userInfo.nickname || '未登录' }}</div>
        <div class="phone">{{ userInfo.phone || '' }}</div>
      </div>
    </div>

    <van-cell-group class="user-menu">
      <van-cell title="我的订单" is-link @click="goToOrders" />
      <van-cell title="我的收藏" is-link @click="goToFavorites" />
      <van-cell title="收货地址" is-link @click="goToAddresses" />
      <van-cell title="设置" is-link @click="goToSettings" />
    </van-cell-group>

    <van-button type="danger" block @click="logout" class="logout-btn">退出登录</van-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'

const router = useRouter()

const userInfo = ref({
  nickname: '测试用户',
  phone: '138****8888'
})

const goToOrders = () => {
  showToast('我的订单')
}

const goToFavorites = () => {
  showToast('我的收藏')
}

const goToAddresses = () => {
  showToast('收货地址')
}

const goToSettings = () => {
  showToast('设置')
}

const logout = () => {
  showToast('退出登录')
  router.push('/login')
}
</script>

<style scoped>
.user-header {
  display: flex;
  align-items: center;
  padding: 30px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.avatar {
  margin-right: 15px;
}

.nickname {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 5px;
}

.phone {
  font-size: 14px;
  opacity: 0.9;
}

.user-menu {
  margin-top: 20px;
}

.logout-btn {
  margin-top: 20px;
  margin-left: 20px;
  margin-right: 20px;
}
</style>
