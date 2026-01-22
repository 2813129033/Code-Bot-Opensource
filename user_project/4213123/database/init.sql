-- H5商城数据库初始化脚本
-- 数据库名: h5_mall

CREATE DATABASE IF NOT EXISTS h5_mall DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE h5_mall;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  phone VARCHAR(11) NOT NULL UNIQUE COMMENT '手机号',
  password VARCHAR(255) NOT NULL COMMENT '密码（加密）',
  nickname VARCHAR(50) DEFAULT '用户' COMMENT '昵称',
  avatar VARCHAR(255) DEFAULT NULL COMMENT '头像URL',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 商品分类表
CREATE TABLE IF NOT EXISTS categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL COMMENT '分类名称',
  parent_id INT DEFAULT 0 COMMENT '父分类ID',
  icon VARCHAR(255) DEFAULT NULL COMMENT '图标URL',
  sort_order INT DEFAULT 0 COMMENT '排序',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';

-- 商品表
CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL COMMENT '商品名称',
  description TEXT COMMENT '商品描述',
  price DECIMAL(10,2) NOT NULL COMMENT '价格',
  original_price DECIMAL(10,2) DEFAULT NULL COMMENT '原价',
  stock INT DEFAULT 0 COMMENT '库存',
  sales INT DEFAULT 0 COMMENT '销量',
  category_id INT DEFAULT NULL COMMENT '分类ID',
  images JSON COMMENT '商品图片数组',
  status TINYINT DEFAULT 1 COMMENT '状态：1-上架，0-下架',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_category_id (category_id),
  INDEX idx_status (status),
  INDEX idx_sales (sales),
  INDEX idx_created_at (created_at),
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- 收货地址表
CREATE TABLE IF NOT EXISTS addresses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL COMMENT '用户ID',
  consignee VARCHAR(50) NOT NULL COMMENT '收货人',
  phone VARCHAR(11) NOT NULL COMMENT '手机号',
  province VARCHAR(50) NOT NULL COMMENT '省份',
  city VARCHAR(50) NOT NULL COMMENT '城市',
  district VARCHAR(50) NOT NULL COMMENT '区县',
  detail_address VARCHAR(255) NOT NULL COMMENT '详细地址',
  is_default TINYINT DEFAULT 0 COMMENT '是否默认：1-是，0-否',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收货地址表';

-- 购物车表
CREATE TABLE IF NOT EXISTS cart (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL COMMENT '用户ID',
  product_id INT NOT NULL COMMENT '商品ID',
  quantity INT DEFAULT 1 COMMENT '数量',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_product (user_id, product_id),
  INDEX idx_user_id (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购物车表';

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_no VARCHAR(32) NOT NULL UNIQUE COMMENT '订单号',
  user_id INT NOT NULL COMMENT '用户ID',
  address_id INT NOT NULL COMMENT '收货地址ID',
  total_amount DECIMAL(10,2) NOT NULL COMMENT '订单总金额',
  status VARCHAR(20) DEFAULT 'pending' COMMENT '订单状态：pending-待付款，paid-已付款，shipped-已发货，completed-已完成，cancelled-已取消',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user_id (user_id),
  INDEX idx_order_no (order_no),
  INDEX idx_status (status),
  INDEX idx_created_at (created_at),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- 订单商品表
CREATE TABLE IF NOT EXISTS order_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_id INT NOT NULL COMMENT '订单ID',
  product_id INT NOT NULL COMMENT '商品ID',
  quantity INT NOT NULL COMMENT '数量',
  price DECIMAL(10,2) NOT NULL COMMENT '单价',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_order_id (order_id),
  INDEX idx_product_id (product_id),
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单商品表';

-- 商品收藏表
CREATE TABLE IF NOT EXISTS favorites (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL COMMENT '用户ID',
  product_id INT NOT NULL COMMENT '商品ID',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_user_product (user_id, product_id),
  INDEX idx_user_id (user_id),
  INDEX idx_product_id (product_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品收藏表';

-- 插入测试数据
-- 商品分类
INSERT INTO categories (name, parent_id, icon, sort_order) VALUES
('手机数码', 0, 'phone-o', 1),
('电脑办公', 0, 'desktop-o', 2),
('服饰鞋包', 0, 'bag-o', 3),
('食品生鲜', 0, 'cart-o', 4),
('智能手机', 1, 'phone-o', 1),
('笔记本电脑', 2, 'desktop-o', 1);

-- 商品
INSERT INTO products (name, description, price, original_price, stock, sales, category_id, images, status) VALUES
('智能手机 Pro', '高性能智能手机，搭载最新处理器，支持5G网络', 2999.00, 3299.00, 100, 50, 5, '["https://via.placeholder.com/400x400/FF6B6B/FFFFFF?text=Phone1", "https://via.placeholder.com/400x400/4ECDC4/FFFFFF?text=Phone2"]', 1),
('笔记本电脑 Ultra', '轻薄本，16GB内存，512GB固态硬盘', 5999.00, 6999.00, 50, 30, 6, '["https://via.placeholder.com/400x400/45B7D1/FFFFFF?text=Laptop1", "https://via.placeholder.com/400x400/96CEB4/FFFFFF?text=Laptop2"]', 1),
('无线耳机', '主动降噪，30小时续航', 299.00, 399.00, 200, 100, 1, '["https://via.placeholder.com/400x400/FFEAA7/FFFFFF?text=Headphone1"]', 1),
('智能手表', '健康监测，运动追踪', 899.00, 999.00, 80, 40, 1, '["https://via.placeholder.com/400x400/DFE6E9/FFFFFF?text=Watch1"]', 1),
('机械键盘', 'RGB背光，青轴', 399.00, 499.00, 150, 60, 2, '["https://via.placeholder.com/400x400/A29BFE/FFFFFF?text=Keyboard1"]', 1),
('游戏鼠标', '16000DPI，可编程按键', 199.00, 299.00, 300, 120, 2, '["https://via.placeholder.com/400x400/FD79A8/FFFFFF?text=Mouse1"]', 1);
