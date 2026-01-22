const { initDB } = require('../config/mysql');
const { zipSearchPaths } = require('../config/config');
const path = require('path');
const fs = require('fs');
const axios = require('axios');

// NapCat HTTP API 配置
const NAPCAT_API_BASE = 'http://127.0.0.1:5700';
// 项目根目录：从 sever/services/ 向上两级到项目根目录 (D:\work\Code-bot)
// __dirname = D:\work\Code-bot\sever\services
// ../.. = D:\work\Code-bot
const PROJECT_ROOT = path.resolve(__dirname, '../..');

// 压缩包查找目录（优先级从高到低）
// 从配置文件读取，如果没有配置则使用默认路径
const ZIP_SEARCH_PATHS = zipSearchPaths && zipSearchPaths.length > 0 
  ? zipSearchPaths 
  : [
      'C:\\Users\\28131\\Desktop\\test',  // 默认：桌面test目录
      path.join(PROJECT_ROOT, 'test'),     // 备用：项目根目录下的test文件夹
      PROJECT_ROOT                         // 备用：项目根目录
    ];

// 已发送的任务ID集合（避免重复发送）
const sentTaskIds = new Set();

/**
 * 获取已审核通过、待发送的任务
 */
async function getCompletedTasks() {
  try {
    const db = await initDB();
    const [tasks] = await db.execute(
      `SELECT id, user_id, task_id, task_description, task_type, task_technology
       FROM user_task 
       WHERE task_status = 'ready_to_send'
       ORDER BY create_time ASC`
    );
    return tasks;
  } catch (err) {
    console.error('[fileSenderService][getCompletedTasks]', err);
    return [];
  }
}

/**
 * 检查压缩包文件是否存在
 * 支持多个查找路径，按优先级查找
 */
function checkZipFileExists(userId) {
  const zipFileName = `${userId}.zip`;
  
  // 添加调试信息
  console.log(`[fileSenderService] 检查压缩包文件:`);
  console.log(`  userId: ${userId}`);
  console.log(`  查找文件名: ${zipFileName}`);
  console.log(`  查找路径列表: ${ZIP_SEARCH_PATHS.join(', ')}`);
  
  // 按优先级在多个路径中查找
  for (const searchPath of ZIP_SEARCH_PATHS) {
    const zipFilePath = path.join(searchPath, zipFileName);
    
    console.log(`  🔍 尝试路径: ${zipFilePath}`);
    
    if (fs.existsSync(zipFilePath)) {
      console.log(`  ✅ 找到压缩包: ${zipFilePath}`);
      return zipFilePath;
    } else {
      console.log(`  ❌ 文件不存在`);
      
      // 如果目录存在，列出目录下的文件（帮助调试）
      if (fs.existsSync(searchPath)) {
        try {
          const dirFiles = fs.readdirSync(searchPath);
          const zipFiles = dirFiles.filter(f => f.endsWith('.zip'));
          if (zipFiles.length > 0) {
            console.log(`  📦 该目录下的zip文件: ${zipFiles.join(', ')}`);
          }
        } catch (err) {
          console.log(`  ⚠️  无法读取目录: ${err.message}`);
        }
      } else {
        console.log(`  ⚠️  目录不存在: ${searchPath}`);
      }
    }
  }
  
  // 所有路径都找不到，尝试模糊匹配（查找包含userId的zip文件）
  console.log(`  🔍 尝试模糊匹配（查找包含 ${userId} 的zip文件）...`);
  for (const searchPath of ZIP_SEARCH_PATHS) {
    if (!fs.existsSync(searchPath)) continue;
    
    try {
      const dirFiles = fs.readdirSync(searchPath);
      const matchingZips = dirFiles.filter(f => 
        f.endsWith('.zip') && f.includes(userId)
      );
      
      if (matchingZips.length > 0) {
        const matchedFile = matchingZips[0];
        const matchedPath = path.join(searchPath, matchedFile);
        console.log(`  ✅ 模糊匹配找到: ${matchedPath}`);
        return matchedPath;
      }
    } catch (err) {
      // 忽略读取错误，继续下一个路径
    }
  }
  
  console.log(`  ❌ 在所有路径中都未找到压缩包`);
  return null;
}

/**
 * 上传文件到NapCat（如果需要）
 * NapCat支持本地文件路径，可以直接使用
 */
function normalizeFilePath(filePath) {
  // Windows路径转换为Unix风格，并确保是绝对路径
  const normalizedPath = path.resolve(filePath).replace(/\\/g, '/');
  return normalizedPath;
}

/**
 * 发送文件给用户
 */
async function sendFileToUser(userId, filePath, taskInfo) {
  try {
    const normalizedPath = normalizeFilePath(filePath);
    
    // 构建消息内容
    const textMessage = `✅ 您的项目已完成！\n\n` +
      `任务ID：${taskInfo.task_id}\n` +
      `项目类型：${taskInfo.task_type}\n` +
      `技术选型：${taskInfo.task_technology}\n` +
      `功能描述：${taskInfo.task_description}\n\n` +
      `正在发送项目压缩包...`;

    // 先发送文本消息
    try {
      await axios.post(`${NAPCAT_API_BASE}/send_private_msg`, {
        user_id: parseInt(userId) || userId,
        message: textMessage
      });
    } catch (textErr) {
      console.warn('[fileSenderService] 发送文本消息失败:', textErr.message);
    }

    // 尝试方式1：使用CQ码发送本地文件（NapCat可能支持）
    try {
      const fileName = path.basename(filePath);
      // 尝试使用file://协议
      const fileMessage = `[CQ:file,file=file:///${normalizedPath},name=${fileName}]`;
      const response = await axios.post(`${NAPCAT_API_BASE}/send_private_msg`, {
        user_id: parseInt(userId) || userId,
        message: fileMessage
      });
      
      if (response.data && (response.data.retcode === 0 || response.data.status === 'ok')) {
        console.log(`[fileSenderService] 文件通过CQ码发送成功: ${fileName}`);
        return { success: true };
      }
    } catch (cqErr) {
      console.warn('[fileSenderService] CQ码方式发送失败，尝试上传方式:', cqErr.message);
    }

    // 尝试方式2：上传文件到NapCat（如果支持upload_private_file API）
    try {
      const FormData = require('form-data');
      const form = new FormData();
      form.append('user_id', userId);
      form.append('file', fs.createReadStream(filePath), {
        filename: path.basename(filePath),
        contentType: 'application/zip'
      });

      const uploadResponse = await axios.post(`${NAPCAT_API_BASE}/upload_private_file`, form, {
        headers: form.getHeaders(),
        maxContentLength: Infinity,
        maxBodyLength: Infinity
      });

      if (uploadResponse.data && (uploadResponse.data.retcode === 0 || uploadResponse.data.status === 'ok')) {
        const fileId = uploadResponse.data.data?.file_id || uploadResponse.data.data?.file;
        if (fileId) {
          // 使用返回的file_id发送文件
          await axios.post(`${NAPCAT_API_BASE}/send_private_msg`, {
            user_id: parseInt(userId) || userId,
            message: `[CQ:file,file=${fileId}]`
          });
          console.log(`[fileSenderService] 文件上传并发送成功: ${path.basename(filePath)}`);
          return { success: true };
        }
      }
    } catch (uploadErr) {
      console.warn('[fileSenderService] 文件上传方式失败:', uploadErr.message);
    }

    // 方式3：如果都失败，发送文件路径信息（备用方案）
    const fallbackMessage = `📦 项目压缩包已生成！\n\n` +
      `文件名：${path.basename(filePath)}\n` +
      `文件路径：${normalizedPath}\n\n` +
      `⚠️ 由于技术限制，无法直接发送文件。\n` +
      `请通过文件路径访问或联系管理员获取。`;
    
    try {
      await axios.post(`${NAPCAT_API_BASE}/send_private_msg`, {
        user_id: parseInt(userId) || userId,
        message: fallbackMessage
      });
      return { success: true, warning: '使用备用方式发送文件路径' };
    } catch (fallbackErr) {
      // 如果连备用方案都失败，说明 NapCat 确实没有启动
      throw new Error(`NapCat API 连接失败: ${fallbackErr.message}。请确保 NapCat 已启动且 HTTP 服务器端口 ${NAPCAT_API_BASE.split(':').pop()} 已启用。`);
    }
  } catch (err) {
    console.error('[fileSenderService][sendFileToUser]', err);
    return { success: false, error: err.message };
  }
}

/**
 * 标记任务为已发送
 */
async function markTaskAsSent(taskId) {
  try {
    const db = await initDB();
    await db.execute(
      `UPDATE user_task 
       SET task_status = 'sent' 
       WHERE task_id = ?`,
      [taskId]
    );
    sentTaskIds.add(taskId);
    return true;
  } catch (err) {
    console.error('[fileSenderService][markTaskAsSent]', err);
    return false;
  }
}

/**
 * 检查 NapCat API 是否可用
 */
async function checkNapCatConnection() {
  try {
    const response = await axios.get(`${NAPCAT_API_BASE}/get_status`, {
      timeout: 3000
    });
    return { available: true, response: response.data };
  } catch (err) {
    if (err.code === 'ECONNREFUSED') {
      return { 
        available: false, 
        error: `无法连接到 NapCat API (${NAPCAT_API_BASE})，请确保 NapCat 已启动且 HTTP 服务器已启用` 
      };
    }
    return { available: false, error: err.message };
  }
}

/**
 * 扫描并发送已完成项目的压缩包
 */
async function scanAndSendFiles() {
  try {
    console.log('[fileSenderService] 开始扫描已完成的任务...');
    
    // 检查 NapCat 连接
    const connectionCheck = await checkNapCatConnection();
    if (!connectionCheck.available) {
      console.warn(`[fileSenderService] ⚠️ ${connectionCheck.error}`);
      console.warn(`[fileSenderService] 跳过本次扫描，等待 NapCat 启动...`);
      return { scanned: 0, sent: 0, failed: 0, warning: connectionCheck.error };
    }
    
    const completedTasks = await getCompletedTasks();
    
    if (completedTasks.length === 0) {
      console.log('[fileSenderService] 没有已完成的任务');
      return { scanned: 0, sent: 0, failed: 0 };
    }

    let sentCount = 0;
    let failedCount = 0;

    for (const task of completedTasks) {
      const taskId = task.task_id;
      const userId = String(task.user_id);

      // 跳过已发送的任务
      if (sentTaskIds.has(taskId)) {
        continue;
      }

      // 检查压缩包是否存在
      const zipFilePath = checkZipFileExists(userId);
      if (!zipFilePath) {
        console.log(`[fileSenderService] 任务 ${taskId} 的压缩包不存在`);
        console.log(`  期望文件名: ${userId}.zip`);
        console.log(`  查找路径: ${ZIP_SEARCH_PATHS.join(', ')}`);
        continue;
      }

      // 发送文件
      console.log(`[fileSenderService] 正在发送任务 ${taskId} 的压缩包给用户 ${userId}...`);
      const result = await sendFileToUser(userId, zipFilePath, task);
      
      if (result.success) {
        await markTaskAsSent(taskId);
        sentCount++;
        console.log(`[fileSenderService] ✅ 任务 ${taskId} 的压缩包已发送给用户 ${userId}`);
      } else {
        failedCount++;
        // 如果是连接错误，给出更友好的提示
        if (result.error && result.error.includes('ECONNREFUSED')) {
          console.error(`[fileSenderService] ❌ 任务 ${taskId} 发送失败: NapCat API 未启动，请启动 NapCat 后再试`);
        } else {
          console.error(`[fileSenderService] ❌ 任务 ${taskId} 发送失败: ${result.error}`);
        }
      }

      // 避免发送过快，每个任务间隔1秒
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    console.log(`[fileSenderService] 扫描完成: 已发送 ${sentCount} 个，失败 ${failedCount} 个`);
    return { scanned: completedTasks.length, sent: sentCount, failed: failedCount };
  } catch (err) {
    console.error('[fileSenderService][scanAndSendFiles]', err);
    return { scanned: 0, sent: 0, failed: 0, error: err.message };
  }
}

module.exports = {
  scanAndSendFiles,
  checkZipFileExists,
  sendFileToUser
};

