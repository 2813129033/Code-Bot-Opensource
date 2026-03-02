<template>
  <view class="page">
    <view class="card">
      <view class="title">可选：上传（图片 / 视频）</view>
      <view class="desc">对接 express-backend：/api/upload/image /video</view>

      <view class="row">
        <button type="primary" @click="pickImage">选择图片并上传</button>
        <button type="default" @click="pickVideo">选择视频并上传</button>
      </view>

      <view class="result">{{ result }}</view>
    </view>
  </view>
</template>

<script>
// 可选：只有你在 pages.json 注册了这个页面，才会用到下面的 API
import { api } from '../../common/api';

export default {
  data() {
    return { result: '' };
  },
  methods: {
    async pickImage() {
      try {
        const { tempFilePaths } = await uni.chooseImage({ count: 1 });
        const filePath = tempFilePaths && tempFilePaths[0];
        const res = await api.uploadImage(filePath);
        this.result = JSON.stringify(res, null, 2);
      } catch (e) {
        this.result = (e && e.message) ? e.message : String(e);
      }
    },
    async pickVideo() {
      try {
        const resChoose = await uni.chooseVideo({});
        const filePath = resChoose && resChoose.tempFilePath;
        const res = await api.uploadVideo(filePath);
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
.row { display: flex; gap: 16rpx; }
.result { margin-top: 24rpx; font-family: monospace; white-space: pre-wrap; word-break: break-all; }
</style>

