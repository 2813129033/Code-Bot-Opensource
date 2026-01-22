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
  console.log(`[fileScan] 定时扫描任务已启动，间隔: ${SCAN_INTERVAL / 1000} 秒`);
  
  // 立即执行一次
  scanAndSendFiles();
  
  // 设置定时任务
  scanTimer = setInterval(() => {
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
    console.log('[fileScan] 定时扫描任务已停止');
  }
}

/**
 * 执行扫描并发送文件
 */
async function scanAndSendFiles() {
  try {
    const result = await fileSenderService.scanAndSendFiles();
    if (result.scanned > 0) {
      console.log(`[fileScan] 扫描结果: 扫描 ${result.scanned} 个任务，发送 ${result.sent} 个，失败 ${result.failed} 个`);
    }
  } catch (err) {
    console.error('[fileScan] 扫描任务执行失败:', err);
  }
}

async function start() {
  try {
    console.log(`[server] starting in ${appConfig.env}...`);

    const db = await initDB();
    console.log('[db] ready:', { ok: true });

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
      console.log(`🚀 Server running on port ${appConfig.port}`);
    });

    // 启动定时扫描任务
    startFileScanTask();

    // 优雅关闭
    process.on('SIGINT', () => {
      console.log('\n[server] 收到退出信号，正在关闭...');
      stopFileScanTask();
      process.exit(0);
    });

    process.on('SIGTERM', () => {
      console.log('\n[server] 收到终止信号，正在关闭...');
      stopFileScanTask();
      process.exit(0);
    });
  } catch (err) {
    console.error('[startup] failed:', err);
  }
}

start();
