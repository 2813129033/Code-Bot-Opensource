<template>
  <div class="cart">
    <van-nav-bar title="购物车" />

    <van-checkbox-group v-model="checkedItems">
      <div v-for="item in cartItems" :key="item.id" class="cart-item">
        <van-checkbox :name="item.id" />
        <van-image :src="item.image" width="80" height="80" />
        <div class="item-info">
          <div class="item-name">{{ item.name }}</div>
          <div class="item-price">¥{{ item.price }}</div>
          <van-stepper v-model="item.quantity" min="1" />
        </div>
      </div>
    </van-checkbox-group>

    <van-submit-bar :price="totalPrice" button-text="结算" @submit="checkout" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { showToast } from 'vant'

const checkedItems = ref([1, 2])

const cartItems = ref([
  { id: 1, name: '智能手机 Pro', price: 2999, quantity: 1, image: 'https://via.placeholder.com/80x80/FF6B6B/FFFFFF?text=P1' },
  { id: 2, name: '无线耳机', price: 299, quantity: 2, image: 'https://via.placeholder.com/80x80/4ECDC4/FFFFFF?text=P2' },
  { id: 3, name: '智能手表', price: 899, quantity: 1, image: 'https://via.placeholder.com/80x80/45B7D1/FFFFFF?text=P3' }
])

const totalPrice = computed(() => {
  return cartItems.value
    .filter(item => checkedItems.value.includes(item.id))
    .reduce((sum, item) => sum + item.price * item.quantity, 0)
})

const checkout = () => {
  showToast('结算成功')
}
</script>

<style scoped>
.cart-item {
  display: flex;
  align-items: center;
  padding: 15px;
  background: white;
  margin-bottom: 10px;
}

.item-info {
  flex: 1;
  margin-left: 10px;
}

.item-name {
  font-size: 16px;
  margin-bottom: 5px;
}

.item-price {
  color: #ff4444;
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 10px;
}
</style>
