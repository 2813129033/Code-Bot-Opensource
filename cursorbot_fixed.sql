-- Active: 1769011045674@@127.0.0.1@3306@cursorbot
-- ===============================
-- 钱包表
-- ===============================
CREATE TABLE IF NOT EXISTS wallets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    qq_number VARCHAR(32) NOT NULL UNIQUE COMMENT 'QQ号',
    qq_nickname VARCHAR(100) DEFAULT NULL COMMENT 'QQ昵称',
    balance DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '当前余额（元）',
    total_recharge DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '累计充值金额（元）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_wallets_nickname (qq_nickname)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户钱包';

CREATE TABLE IF NOT EXISTS wallet_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    qq_number VARCHAR(32) NOT NULL COMMENT 'QQ号',
    amount DECIMAL(10,2) NOT NULL COMMENT '交易金额（元）',
    raw_message TEXT COMMENT '原始转账消息',
    remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_wallet_txn_qq (qq_number),
    CONSTRAINT fk_wallet_txn_wallet FOREIGN KEY (qq_number) REFERENCES wallets (qq_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='钱包交易记录';

-- ===============================
-- user_task 表（新增）
-- ===============================
CREATE TABLE IF NOT EXISTS user_task (
    id INT AUTO_INCREMENT PRIMARY KEY,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    user_id VARCHAR(32) NOT NULL COMMENT '用户QQ号',
    task_id VARCHAR(64) NOT NULL UNIQUE COMMENT '任务ID',
    task_description TEXT NOT NULL COMMENT '任务描述',
    task_status VARCHAR(255) NOT NULL DEFAULT 'pending' COMMENT '任务状态：pending/processing/review/user_change/review_change/ready_to_send/sent/failed',
    task_technology VARCHAR(255) DEFAULT NULL COMMENT '技术选型',
    task_type VARCHAR(255) DEFAULT NULL COMMENT '项目类型',
    review_notes TEXT DEFAULT NULL COMMENT '审核批注/回滚原因',
    user_change_request TEXT DEFAULT NULL COMMENT '用户追加修改需求',
    updated_at DATETIME DEFAULT NULL COMMENT '状态更新时间',
    updated_by VARCHAR(64) DEFAULT NULL COMMENT '更新人/服务器标识',
    INDEX idx_user_task_user (user_id),
    INDEX idx_user_task_status (task_status),
    INDEX idx_user_task_create (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户任务表';

-- ===============================
-- user_task 工作流扩展（ALTER 语句改为 CREATE 时已包含）
-- ===============================
-- 注意：由于 user_task 表已在上面创建时包含了所有字段，以下 ALTER 语句可以省略
-- 如果表已存在且需要修改，可以取消注释以下语句：

-- ALTER TABLE user_task
--   MODIFY COLUMN task_status VARCHAR(255) NULL DEFAULT 'pending' COMMENT '任务状态';

-- ALTER TABLE user_task
--   ADD COLUMN IF NOT EXISTS review_notes TEXT NULL COMMENT '审核批注/回滚原因',
--   ADD COLUMN IF NOT EXISTS user_change_request TEXT NULL COMMENT '用户追加修改需求',
--   ADD COLUMN IF NOT EXISTS updated_at DATETIME NULL COMMENT '状态更新时间',
--   ADD COLUMN IF NOT EXISTS updated_by VARCHAR(64) NULL COMMENT '更新人/服务器标识';

-- 可选：把已完成的任务迁移为待审核，防止被自动发送
-- UPDATE user_task
-- SET task_status = 'review', updated_at = NOW(), updated_by = 'migration'
-- WHERE task_status = 'completed';

-- ===============================
-- 邀请码 / 绑定 / 抽奖
-- ===============================
CREATE TABLE IF NOT EXISTS invite_codes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  owner_qq_number VARCHAR(32) NOT NULL UNIQUE COMMENT '邀请码所有者（QQ号）',
  code VARCHAR(32) NOT NULL UNIQUE COMMENT '邀请码',
  max_bindings INT NOT NULL DEFAULT 2 COMMENT '最多绑定次数',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_invite_codes_owner (owner_qq_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='邀请码表';

CREATE TABLE IF NOT EXISTS invite_bindings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(32) NOT NULL COMMENT '被绑定的邀请码',
  inviter_qq_number VARCHAR(32) NOT NULL COMMENT '邀请人QQ号（邀请码所有者）',
  invitee_qq_number VARCHAR(32) NOT NULL UNIQUE COMMENT '被邀请人QQ号（每人只能绑定一次）',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_invite_bindings_code (code),
  INDEX idx_invite_bindings_inviter (inviter_qq_number),
  CONSTRAINT fk_invite_bindings_code FOREIGN KEY (code) REFERENCES invite_codes (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='邀请码绑定关系';

CREATE TABLE IF NOT EXISTS lottery_draws (
  id INT AUTO_INCREMENT PRIMARY KEY,
  qq_number VARCHAR(32) NOT NULL COMMENT '抽奖用户QQ号',
  code VARCHAR(32) NOT NULL COMMENT '绑定的邀请码（用于追溯）',
  prize_amount DECIMAL(10,2) NOT NULL COMMENT '中奖金额（元）',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_lottery_draws_qq (qq_number),
  INDEX idx_lottery_draws_code (code),
  CONSTRAINT fk_lottery_draws_code FOREIGN KEY (code) REFERENCES invite_codes (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抽奖记录';
