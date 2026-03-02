const express = require('express');
const { appConfig } = require('./config/config');
const { initDB } = require('./config/mysql');
const messageRoutes = require('./routes/message');
const fileSenderService = require('./services/fileSenderService');
const app = express();

// 定时扫描配置
const SCAN_INTERVAL = 30 * 1000; // 30秒（毫秒）
let scanTimer = null;

/**
 * 启动定时扫描任务
 */
function startFileScanTask() {
  // 立即执行一次
  scanAndSendFiles();
  
  // 设置定时任务：保持 30 秒一次的间隔，但只在每天早上 6:00-7:00 这一小时内真正执行
  scanTimer = setInterval(() => {
    const now = new Date();
    const hour = now.getHours();
    if (hour < 6 || hour >= 7) {
      // 非 6:00-7:00 时段，仅保持心跳，不执行扫描，几乎不占用资源
      return;
    }
    scanAndSendFiles();
  }, SCAN_INTERVAL);
}

/**
 * 停止定时扫描任务
 */
function stopFileScanTask() {
  if (scanTimer) {
    clearInterval(scanTimer);
    scanTimer = null;
  }
}

/**
 * 执行扫描并发送文件
 */
async function scanAndSendFiles() {
  try {
    const result = await fileSenderService.scanAndSendFiles();
  } catch (err) {
    console.error('[fileScan] 扫描任务执行失败:', err);
  }
}

async function start() {
  try {
    const db = await initDB();

	// 解析 JSON 请求体
	app.use(express.json());

	// 健康检查
    app.get('/', (req, res) => {
      res.send('Server running successfully 🚀');
    });

	// 消息路由（接收 NapCat/QQ 机器人事件）
	app.use('/message', messageRoutes);
	// 兼容部分实现使用根路径作为上报地址：POST /
	app.use('/', messageRoutes);

    app.listen(appConfig.port, () => {
    });

    // 启动定时扫描任务
    startFileScanTask();

    // 优雅关闭
    process.on('SIGINT', () => {
      stopFileScanTask();
      process.exit(0);
    });

    process.on('SIGTERM', () => {
      stopFileScanTask();
      process.exit(0);
    });
  } catch (err) {
    console.error('[startup] failed:', err);
  }
}

start();
