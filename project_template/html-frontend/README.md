# HTML前端框架模板

通用的传统HTML前端开发模板，包含常用功能和组件。

## 功能特性

- ✅ Bootstrap 5 响应式框架
- ✅ 现代化UI设计
- ✅ 完整的工具函数库
- ✅ Axios HTTP请求封装
- ✅ 表单验证和处理
- ✅ 消息提示系统
- ✅ 本地存储工具
- ✅ 常用工具函数（日期格式化、防抖、节流等）

## 项目结构

```
html-frontend/
├── index.html              # 主页面
├── assets/
│   ├── css/
│   │   └── style.css      # 自定义样式
│   └── js/
│       ├── utils.js        # 工具函数库
│       └── main.js         # 主脚本
├── about.html              # 关于页面（示例）
├── contact.html            # 联系页面（示例）
└── README.md
```

## 快速开始

1. 直接在浏览器中打开 `index.html`
2. 或使用本地服务器：
   ```bash
   # 使用Python
   python -m http.server 8000
   
   # 使用Node.js
   npx http-server
   ```

## 使用说明

### API配置

在 `assets/js/utils.js` 中修改API配置：

```javascript
const API_CONFIG = {
    baseURL: 'http://localhost:3000/api', // 修改为你的后端地址
    timeout: 10000
};
```

### 使用工具函数

```javascript
// 显示消息
Utils.showMessage('操作成功', 'success');

// 格式化日期
const dateStr = Utils.formatDate(new Date(), 'YYYY-MM-DD');

// 验证邮箱
if (Utils.isValidEmail('test@example.com')) {
    // ...
}

// 本地存储
Utils.Storage.set('key', { data: 'value' });
const data = Utils.Storage.get('key');
```

### 发送HTTP请求

```javascript
// GET请求
const response = await axios.get('/users');
console.log(response.data);

// POST请求
const response = await axios.post('/users', {
    name: 'John',
    email: 'john@example.com'
});

// 请求会自动添加token（如果存在）
```

### 表单处理

表单提交会自动验证，示例：

```html
<form id="myForm">
    <input type="email" id="email" required>
    <button type="submit">提交</button>
</form>

<script>
document.getElementById('myForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = {
        email: document.getElementById('email').value
    };
    
    try {
        const response = await axios.post('/api/submit', formData);
        Utils.showMessage('提交成功', 'success');
    } catch (error) {
        Utils.showMessage('提交失败', 'danger');
    }
});
</script>
```

### （可选）对接 express-backend 模板（JWT / 用户 / 上传 / 健康检查）

本模板提供一个**可选**的配套模块：`assets/js/backend.js`（默认不启用）。

- 启用方式：在页面底部取消注释下面这一行即可（以 `index.html` 为例）：

```html
<!-- <script src="assets/js/backend.js"></script> -->
```

- 可用方法（挂在 `window.Backend`）：
  - `Backend.health()`：GET `/health`
  - `Backend.register({ username, email, password })`
  - `Backend.login({ username, password })`（成功会把 `token` 存到 `localStorage`）
  - `Backend.me()`
  - `Backend.listUsers({ page, limit })`
  - `Backend.uploadImage(file)`
  - `Backend.uploadVideo(file)`

## 包含的组件

- 响应式导航栏
- 卡片组件
- 表单组件
- 数据表格
- 页脚
- 消息提示
- 加载状态

## 浏览器支持

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

## License

MIT