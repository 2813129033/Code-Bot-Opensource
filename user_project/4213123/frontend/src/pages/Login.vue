<template>
  <div class="login">
    <div class="login-header">
      <h1>欢迎登录</h1>
      <p>H5商城小程序</p>
    </div>

    <van-form @submit="onSubmit">
      <van-cell-group inset>
        <van-field
          v-model="phone"
          name="phone"
          label="手机号"
          placeholder="请输入手机号"
          :rules="[{ required: true, message: '请填写手机号' }]"
        />
        <van-field
          v-model="code"
          name="code"
          label="验证码"
          placeholder="请输入验证码"
          :rules="[{ required: true, message: '请填写验证码' }]"
        >
          <template #button>
            <van-button size="small" type="primary" @click="sendCode">
              {{ codeText }}
            </van-button>
          </template>
        </van-field>
      </van-cell-group>

      <div style="margin: 16px">
        <van-button round block type="primary" native-type="submit">
          登录
        </van-button>
      </div>
    </van-form>

    <div class="login-footer">
      <van-divider>其他登录方式</van-divider>
      <div class="other-login">
        <van-icon name="wechat" size="40" color="#07c160" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'

const router = useRouter()
const phone = ref('')
const code = ref('')
const codeText = ref('获取验证码')

const sendCode = () => {
  showToast('验证码已发送')
  let count = 60
  codeText.value = `${count}s`
  const timer = setInterval(() => {
    count--
    if (count <= 0) {
      clearInterval(timer)
      codeText.value = '获取验证码'
    } else {
      codeText.value = `${count}s`
    }
  }, 1000)
}

const onSubmit = () => {
  showToast('登录成功')
  router.push('/')
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 40px 20px;
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.login-header h1 {
  font-size: 32px;
  color: #333;
  margin-bottom: 10px;
}

.login-header p {
  font-size: 16px;
  color: #999;
}

.login-footer {
  margin-top: 40px;
}

.other-login {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
