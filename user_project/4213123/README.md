# H5商城小程序

基于 Vue3 + Node.js + MySQL 的 H5 商城小程序项目。

## 技术栈

### 前端
- Vue 3
- Vite
- Vue Router
- Pinia
- Vant UI
- Axios

### 后端
- Node.js
- Express
- MySQL
- Redis
- JWT
- Winston

## 项目结构

```
4213123/
├── frontend/              # 前端项目
│   ├── src/
│   │   ├── pages/        # 页面组件
│   │   ├── components/   # 公共组件
│   │   ├── api/          # API接口
│   │   ├── store/        # 状态管理
│   │   ├── utils/        # 工具函数
│   │   ├── router/       # 路由配置
│   │   ├── App.vue       # 根组件
│   │   └── main.js      # 入口文件
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── backend/              # 后端项目
│   ├── src/
│   │   ├── config/       # 配置文件
│   │   ├── routes/       # 路由
│   │   ├── controllers/  # 控制器
│   │   ├── middleware/   # 中间件
│   │   ├── utils/        # 工具函数
│   │   └── app.js        # 入口文件
│   ├── package.json
│   └── .env
├── database/             # 数据库脚本
│   └── init.sql
├── 开发文档.md
└── 开发规范.md
```

## 快速开始

### 环境要求

- Node.js >= 16.0.0
- MySQL >= 8.0
- Redis >= 6.0

### 数据库初始化

1. 创建数据库并执行初始化脚本：

```bash
mysql -u root -p < database/init.sql
```

2. 修改后端配置文件 `backend/.env`：

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=h5_mall

REDIS_HOST=127.0.0.1
REDIS_PORT=6379

JWT_SECRET=your-secret-key

PORT=3000
LOG_LEVEL=info
```

### 后端启动

1. 安装依赖：

```bash
cd backend
npm install
```

2. 启动服务：

```bash
npm start
```

后端服务将在 http://localhost:3000 启动

### 前端启动

1. 安装依赖：

```bash
cd frontend
npm install
```

2. 启动开发服务器：

```bash
npm run dev
```

前端服务将在 http://localhost:3001 启动

## API 接口文档

### 基础URL

```
http://localhost:3000/api
```

### 认证

大部分接口需要在请求头中携带 JWT Token：

```
Authorization: Bearer <token>
```

### 商品接口

#### 获取商品列表

```
GET /api/products
```

参数：
- page: 页码（默认1）
- pageSize: 每页数量（默认20）
- category_id: 分类ID
- sort: 排序方式（price_asc/price_desc/sales_desc）

#### 获取商品详情

```
GET /api/products/:id
```

#### 搜索商品

```
GET /api/products/search
```

参数：
- keyword: 搜索关键词

### 用户接口

#### 用户注册

```
POST /api/users/register
```

参数：
- phone: 手机号
- password: 密码
- nickname: 昵称（可选）

#### 用户登录

```
POST /api/users/login
```

参数：
- phone: 手机号
- password: 密码

#### 获取用户信息

```
GET /api/users/info
```

需要认证

### 购物车接口

#### 加入购物车

```
POST /api/cart
```

需要认证

参数：
- product_id: 商品ID
- quantity: 数量

#### 获取购物车

```
GET /api/cart
```

需要认证

#### 更新购物车商品

```
PUT /api/cart/:id
```

需要认证

参数：
- quantity: 数量

#### 删除购物车商品

```
DELETE /api/cart/:id
```

需要认证

### 订单接口

#### 创建订单

```
POST /api/orders
```

需要认证

参数：
- items: 商品列表 [{ product_id, quantity }]
- address_id: 收货地址ID

#### 获取订单列表

```
GET /api/orders
```

需要认证

参数：
- page: 页码
- pageSize: 每页数量
- status: 订单状态

#### 获取订单详情

```
GET /api/orders/:id
```

需要认证

## 功能特性

### 已实现功能

- 用户注册/登录
- 商品浏览
- 商品搜索
- 商品详情
- 购物车管理
- 订单创建
- 订单查询
- 用户信息管理

### 待开发功能

- 收货地址管理
- 商品收藏
- 订单支付
- 订单取消/退款
- 商家后台管理
- 数据统计

## 开发规范

请参考项目根目录下的 `开发规范.md` 文件。

## 测试账号

测试数据已在数据库初始化脚本中包含。

## 常见问题

### 后端启动失败

1. 检查 MySQL 和 Redis 是否正常运行
2. 检查 `backend/.env` 配置是否正确
3. 检查端口 3000 是否被占用

### 前端无法连接后端

1. 检查后端服务是否正常运行
2. 检查 `vite.config.js` 中的代理配置
3. 检查浏览器控制台的网络请求

## 许可证

MIT
