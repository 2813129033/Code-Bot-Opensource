const axios = require('axios');
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');

// 项目根目录：从 sever/services/ 向上两级到项目根目录 (D:\work\Code-bot)
// __dirname = D:\work\Code-bot\sever\services
// ../.. = D:\work\Code-bot
const PROJECT_ROOT = path.resolve(__dirname, '../..');
const USER_PROJECT_ROOT = path.join(PROJECT_ROOT, 'user_project');

// 智能体规划接口配置
const PLANNER_API_URL = 'https://b8rccch5zx.coze.site/stream_run';
// TODO: 如果后续需要更安全的方式，可以将 token 挪到环境变量中
const PLANNER_API_TOKEN =
  'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjM1Y2JkMWVhLWFhNWQtNDVlNC04MzQ4LTk4M2QxOTFlOTRiZSJ9.eyJpc3MiOiJodHRwczovL2FwaS5jb3plLmNuIiwiYXVkIjpbIkVBMXpsTFR2VEV5cTVOWG1sNE5jdjVpWEQ5YjRjdzZqIl0sImV4cCI6ODIxMDI2Njg3Njc5OSwiaWF0IjoxNzY4ODgxMzAyLCJzdWIiOiJzcGlmZmU6Ly9hcGkuY296ZS5jbi93b3JrbG9hZF9pZGVudGl0eS9pZDo3NTk2NTc4MjQxNzM3OTE2NDIyIiwic3JjIjoiaW5ib3VuZF9hdXRoX2FjY2Vzc190b2tlbl9pZDo3NTk3Mjg3MzQzNzU3NzIxNjU0In0.keoCo-RLF9UnZr0T79uM7K7Z8ab1IS41cTvwkTqCheTviV8ubUhjT8hhgZWxfWzGVIPKDoKzkHyPc4nkuxwqWSvsEYkPqy_RB9VU1v3xrZCN0aMcpvmYtBO0OuXYnak8dtFdfPs8GSj_-iUoJmh0TlB5lftrZHGDTauC_2JXkc1UAtq669md_V6uPHo5IBRz_Ihh5Ih4BBlpJJQc0YSNnn6Gmv7Bd5fq5COiycwKXDSHP5HyC1_X-AGUXlTJgdLoB8gLTLHi-3JiBm7VP-J7Ixu9jqXT41-15_qAJ0H8z78Jf3_Hm7IiGK4ZQ7lWPkLcD5YTmHp92jh0sF0PgKx8Bg';

/**
 * 确保用户项目根目录存在
 * userId 建议使用 QQ 号字符串
 */
function ensureUserProjectDir(userId) {
  const userDir = path.join(USER_PROJECT_ROOT, String(userId));
  if (!fs.existsSync(USER_PROJECT_ROOT)) {
    fs.mkdirSync(USER_PROJECT_ROOT, { recursive: true });
  }
  if (!fs.existsSync(userDir)) {
    fs.mkdirSync(userDir, { recursive: true });
  }
  return userDir;
}

/**
 * 将规划文档写入用户项目根目录
 * 默认文件名：project_plan.md
 */
async function writePlanToFile({ userId, taskId, originalRequirement, content }) {
  const userDir = ensureUserProjectDir(userId);
  const filePath = path.join(userDir, 'project_plan.md');

  const headerLines = [
    '# 项目规划文档',
    '',
    `- 任务ID：${taskId || 'N/A'}`,
    `- 用户ID：${userId}`,
    '- 说明：本文件由规划智能体自动生成，用于指导项目开发。',
    '',
    '## 用户原始需求',
    '',
    originalRequirement || '（无）',
    '',
    '---',
    '',
    '## 智能体规划内容',
    '',
  ];

  return new Promise((resolve, reject) => {
    const stream = fs.createWriteStream(filePath, { encoding: 'utf8' });
    stream.on('error', (err) => reject(err));
    stream.on('finish', () => resolve(filePath));

    stream.write(headerLines.join('\n'));
    if (content) {
      stream.write(content);
    }
    stream.end();
  });
}

/**
 * 通过流式接口拉取规划文档，并写入文件
 * 由于 /stream_run 为流式接口，这里使用 axios 的 stream 响应
 */
async function generateProjectPlan({ userId, taskId, userRequirement }) {
  if (!userRequirement || !String(userRequirement).trim()) {
    console.warn('[planningService] 空的用户需求，跳过规划文档生成');
    return null;
  }

  try {
    console.log('[planningService] 开始为用户生成项目规划文档', {
      userId,
      taskId,
    });

    // 先创建用户目录，准备输出文件路径
    const userDir = ensureUserProjectDir(userId);
    const filePath = path.join(userDir, 'project_plan.md');

    // 打开写入流，并先写入头部信息
    const headerLines = [
      '# 项目规划文档',
      '',
      `- 任务ID：${taskId || 'N/A'}`,
      `- 用户ID：${userId}`,
      '- 说明：本文件由规划智能体自动生成，用于指导项目开发。',
      '',
      '## 用户原始需求',
      '',
      userRequirement,
      '',
      '---',
      '',
      '## 智能体规划内容',
      '',
    ];

    const outStream = fs.createWriteStream(filePath, { encoding: 'utf8' });

    // 确保流错误能够被捕获
    outStream.on('error', (err) => {
      console.error('[planningService] 写入规划文档失败:', err);
    });

    // 先写入头部
    outStream.write(headerLines.join('\n'));

    // 组装扣子规划接口参数
    // 目前只使用「文本需求」格式：
    // {
    //   "original_requirement": "开发一个在线考试系统，支持用户注册登录、查看考试列表、参加考试、查看成绩等功能"
    // }
    // 如果后续需要带文档，可在此处增加 requirement_file 字段：
    // {
    //   original_requirement: String(userRequirement),
    //   requirement_file: {
    //     url: 'https://example.com/requirement.pdf',
    //     file_type: 'document'
    //   }
    // }
    const payload = {
      original_requirement: String(userRequirement),
    };

    // 调用流式接口
    const response = await axios.post(PLANNER_API_URL, payload, {
      headers: {
        Authorization: PLANNER_API_TOKEN,
        'Content-Type': 'application/json',
      },
      responseType: 'stream',
      timeout: 1000 * 60 * 10, // 最长 10 分钟
    });

    return await new Promise((resolve, reject) => {
      const stream = response.data;

      stream.on('data', (chunk) => {
        // 直接将流式内容写入文件，不做额外处理
        outStream.write(chunk.toString('utf8'));
      });

      stream.on('end', () => {
        outStream.end(async () => {
          console.log('[planningService] 项目规划文档生成完成:', filePath);
          
          // 注意：文档上传已在 Python 自动化脚本中完成（python-auto/auto.py 的 upload_dev_document 函数）
          // 此处不再重复上传，避免二次传输
          
          resolve(filePath);
        });
      });

      stream.on('error', (err) => {
        console.error('[planningService] 读取规划接口流失败:', err);
        outStream.end(() => reject(err));
      });
    });
  } catch (err) {
    console.error('[planningService] 生成项目规划文档失败:', err.message || err);
    return null;
  }
}

/**
 * 上传规划文档到指定接口
 * @param {string} filePath - 文档文件路径
 * @param {string} userId - 用户QQ号
 * 
 * 注意：此函数已不再使用。实际文档上传在 Python 自动化脚本中完成
 * （python-auto/auto.py 的 upload_dev_document 函数），避免重复上传。
 * 保留此函数仅作为参考，如需使用请取消注释。
 */
async function uploadPlanDocument(filePath, userId) {
  try {
    const form = new FormData();
    
    // 添加文件字段
    form.append('file', fs.createReadStream(filePath), {
      filename: path.basename(filePath),
      contentType: 'text/markdown'
    });
    
    // 添加用户QQ号字段（可选）
    if (userId) {
      form.append('fileName', String(userId));
    }
    
    // 发送POST请求
    const response = await axios.post('http://192.168.5.5:3000/save-md', form, {
      headers: form.getHeaders(),
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
      timeout: 30000 // 30秒超时
    });
    
    console.log('[planningService] 规划文档上传成功:', {
      userId,
      status: response.status,
      data: response.data
    });
    
    return response.data;
  } catch (err) {
    console.error('[planningService] 上传规划文档异常:', {
      userId,
      error: err.message || err,
      response: err.response?.data
    });
    throw err;
  }
}

module.exports = {
  generateProjectPlan,
  ensureUserProjectDir,
};

