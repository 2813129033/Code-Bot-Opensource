const axios = require('axios');
const { cozeConfig } = require('../config/config');

/**
 * 调用 Coze 对话流获取 AI 回复
 * @param {string} message - 用户消息
 * @returns {Promise<string>} AI 回复内容
 */
async function getChatReply(message) {
  try {
    // 直接发送原始消息，不需要包装成 JSON 格式（不做记忆功能）
    // 注意：不使用 validateStatus，让 axios 使用默认行为（4xx/5xx 会抛出异常）
    const response = await axios.post(
      `${cozeConfig.base_url}/v1/workflows/chat`,
      {
        workflow_id: cozeConfig.workflow_id,
        additional_messages: [
          {
            role: 'user',
            content: message,
            content_type: 'text'
          }
        ]
      },
      {
        headers: {
          'Authorization': `Bearer ${cozeConfig.access_token}`,
          'Content-Type': 'application/json'
        },
        responseType: 'stream'
      }
    );

    // 处理流式响应
    let fullReply = '';
    
    return new Promise((resolve, reject) => {
      response.data.on('data', (chunk) => {
        const chunkStr = chunk.toString();
        const lines = chunkStr.split('\n').filter(line => line.trim());
        
        for (const line of lines) {
          if (line.startsWith('data:')) {
            try {
              const jsonStr = line.slice(5).trim();
              const data = JSON.parse(jsonStr);
              
              // 提取 AI 回复内容
              if (data.content && data.role === 'assistant' && data.type === 'answer') {
                fullReply = data.content;
              } else if (data.event === 'Message' && data.message?.content) {
                fullReply += data.message.content;
              } else if (data.event === 'Done' && data.output) {
                fullReply = data.output;
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      });

      response.data.on('end', () => {
        if (fullReply) {
          resolve(fullReply);
        } else {
          resolve('抱歉，我现在有点忙，稍后再聊吧~');
        }
      });

      response.data.on('error', (error) => {
        console.error('❌ 流式响应错误:', error.message);
        reject(error);
      });
    });
  } catch (error) {
    console.error('❌ AI 调用失败:', error.message);
    
    // 处理 axios 错误（流式响应时，401 错误会在 axios 层面抛出）
    if (error.response) {
      // axios 标准错误格式
      const status = error.response.status;
      console.error('❌ 错误状态码:', status);
      
      // 对于流式响应，错误数据可能在 response.data 中，需要读取
      if (error.response.data && typeof error.response.data.on === 'function') {
        // 流式错误响应，读取错误内容
        let errorData = '';
        return new Promise((resolve) => {
          error.response.data.on('data', (chunk) => {
            errorData += chunk.toString();
          });
          error.response.data.on('end', () => {
            console.error('❌ 错误详情:', errorData || '无详细信息');
            console.error('❌ 请求URL:', `${cozeConfig.base_url}/v1/workflows/chat`);
            console.error('❌ 请求头:', {
              'Authorization': `Bearer ${cozeConfig.access_token.substring(0, 20)}...`,
              'Content-Type': 'application/json'
            });
            
            if (status === 401) {
              console.error('⚠️ Coze API 认证失败，可能的原因：');
              console.error('   1. access_token 已过期或无效');
              console.error('   2. access_token 没有调用该 workflow 的权限');
              console.error('   3. API 端点或请求格式不正确');
              console.error('   请检查 sever/config/config.js 中的 cozeConfig 配置');
              console.error('   当前 access_token:', cozeConfig.access_token);
              console.error('   当前 workflow_id:', cozeConfig.workflow_id);
            }
            
            // 返回降级回复
            const msg = message.toLowerCase();
            if (msg.includes('你好') || msg.includes('hi') || msg.includes('hello')) {
              resolve('你好呀！有什么可以帮你的吗？😊');
            } else if (msg.includes('你是谁')) {
              resolve('我是 AI 助手，可以陪你聊天哦~');
            } else {
              resolve('收到你的消息了！有什么想聊的吗？');
            }
          });
        });
      } else {
        // 非流式错误响应
        console.error('❌ 错误详情:', JSON.stringify(error.response.data, null, 2));
        console.error('❌ 请求URL:', `${cozeConfig.base_url}/v1/workflows/chat`);
        
        if (status === 401) {
          console.error('⚠️ Coze API 认证失败，请检查 access_token 是否有效');
          console.error('   当前 access_token:', cozeConfig.access_token);
          console.error('   当前 workflow_id:', cozeConfig.workflow_id);
        }
      }
    } else if (error.request) {
      console.error('❌ 请求已发送但未收到响应:', error.request);
    } else {
      console.error('❌ 请求配置错误:', error.message);
    }
    
    // 降级回复
    const msg = message.toLowerCase();
    if (msg.includes('你好') || msg.includes('hi') || msg.includes('hello')) {
      return '你好呀！有什么可以帮你的吗？😊';
    } else if (msg.includes('你是谁')) {
      return '我是 AI 助手，可以陪你聊天哦~';
    } else {
      return '收到你的消息了！有什么想聊的吗？';
    }
  }
}

module.exports = {
  getChatReply
};

