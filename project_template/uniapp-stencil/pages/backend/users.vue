<template>
  <view class="page">
    <view class="card">
      <view class="title">可选：用户列表</view>
      <view class="desc">对接 express-backend：GET /api/users</view>
      <button type="primary" @click="load">加载用户</button>

      <view v-if="users.length" class="list">
        <view v-for="u in users" :key="u.id" class="item">
          <view class="name">{{ u.username }}</view>
          <view class="meta">{{ u.email }}</view>
        </view>
      </view>

      <view class="result" v-else>{{ result }}</view>
    </view>
  </view>
</template>

<script>
// 可选：只有你在 pages.json 注册了这个页面，才会用到下面的 API
import { api } from '../../common/api';

export default {
  data() {
    return {
      users: [],
      result: '点击“加载用户”'
    };
  },
  methods: {
    async load() {
      try {
        const res = await api.listUsers({ page: 1, limit: 20 });
        // express-backend 的 paginated 会把数据放在 data
        const list = (res && res.data) ? res.data : [];
        this.users = Array.isArray(list) ? list : [];
        this.result = this.users.length ? '' : '暂无数据';
      } catch (e) {
        this.users = [];
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
.list { margin-top: 24rpx; }
.item { padding: 16rpx 0; border-bottom: 1px solid #eee; }
.name { font-weight: 600; }
.meta { color: #666; font-size: 24rpx; }
.result { margin-top: 24rpx; color: #666; }
</style>

