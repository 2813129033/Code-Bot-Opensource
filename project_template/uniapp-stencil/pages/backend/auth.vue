<template>
  <view class="page">
    <view class="card">
      <view class="title">可选：JWT 登录 / 注册</view>
      <view class="desc">对接 express-backend：/api/auth/login /register</view>

      <view class="field">
        <text class="label">用户名/邮箱</text>
        <input class="input" v-model="username" placeholder="username 或 email" />
      </view>
      <view class="field">
        <text class="label">密码</text>
        <input class="input" v-model="password" password placeholder="至少 6 位" />
      </view>

      <view class="row">
        <button type="primary" @click="login">登录</button>
        <button type="default" @click="register">注册</button>
      </view>

      <view class="row">
        <button type="default" @click="me">请求 /me</button>
        <button type="warn" @click="logout">清除 token</button>
      </view>

      <view class="result">{{ result }}</view>
    </view>
  </view>
</template>

<script>
// 可选：只有你在 pages.json 注册了这个页面，才会用到下面的 API/Token
import { api } from '../../common/api';
import { setToken, clearToken, getToken } from '../../common/auth';

export default {
  data() {
    return {
      username: '',
      password: '',
      result: ''
    };
  },
  methods: {
    async login() {
      try {
        const res = await api.login({ username: this.username, password: this.password });
        if (res && res.data && res.data.token) {
          setToken(res.data.token);
        }
        this.result = JSON.stringify({ token: getToken(), response: res }, null, 2);
      } catch (e) {
        this.result = (e && e.message) ? e.message : String(e);
      }
    },
    async register() {
      try {
        // 后端示例：需要 username/email/password
        const email = this.username.includes('@') ? this.username : `${this.username}@example.com`;
        const res = await api.register({ username: this.username, email, password: this.password });
        if (res && res.data && res.data.token) {
          setToken(res.data.token);
        }
        this.result = JSON.stringify({ token: getToken(), response: res }, null, 2);
      } catch (e) {
        this.result = (e && e.message) ? e.message : String(e);
      }
    },
    async me() {
      try {
        const res = await api.me();
        this.result = JSON.stringify(res, null, 2);
      } catch (e) {
        this.result = (e && e.message) ? e.message : String(e);
      }
    },
    logout() {
      clearToken();
      this.result = 'token 已清除';
    }
  }
};
</script>

<style>
.page { padding: 24rpx; }
.card { background: #fff; padding: 24rpx; border-radius: 16rpx; }
.title { font-size: 32rpx; font-weight: 600; margin-bottom: 8rpx; }
.desc { color: #666; margin-bottom: 24rpx; }
.field { margin-bottom: 16rpx; }
.label { display: block; margin-bottom: 8rpx; color: #333; }
.input { border: 1px solid #ddd; border-radius: 12rpx; padding: 16rpx; background: #fafafa; }
.row { display: flex; gap: 16rpx; margin-top: 16rpx; }
.result { margin-top: 24rpx; font-family: monospace; white-space: pre-wrap; word-break: break-all; }
</style>

