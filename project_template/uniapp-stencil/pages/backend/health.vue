<template>
  <view class="page">
    <view class="card">
      <view class="title">可选：健康检查</view>
      <view class="desc">对接 express-backend：GET /health</view>
      <button type="primary" @click="run">请求 /health</button>
      <view class="result">{{ result }}</view>
    </view>
  </view>
</template>

<script>
// 可选：只有你在 pages.json 注册了这个页面，才会用到下面的 API
import { api } from '../../common/api';

export default {
  data() {
    return {
      result: ''
    };
  },
  methods: {
    async run() {
      try {
        const res = await api.health();
        this.result = JSON.stringify(res, null, 2);
      } catch (e) {
        this.result = (e && e.message) ? e.message : String(e);
      }
    }
  }
};
</script>

<style>
.page { padding: 24rpx; }
.card { background: #fff; padding: 24rpx; border-radius: 16rpx; }
.title { font-size: 32rpx; font-weight: 600; margin-bottom: 8rpx; }
.desc { color: #666; margin-bottom: 24rpx; }
.result { margin-top: 24rpx; font-family: monospace; white-space: pre-wrap; word-break: break-all; }
</style>

