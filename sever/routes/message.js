const express = require('express');
const router = express.Router();
const taskService = require('../services/taskService');
const cozeService = require('../services/cozeService');
const axios = require('axios');
const { onebotConfig } = require('../config/config');
const walletService = require('../services/walletService');
const inviteService = require('../services/inviteService');

// 项目类型及定价配置
const PROJECT_PRODUCTS = {
  '网站开发': { price: 688 },
  '小程序开发': { price: 788 },
  'APP开发': { price: 888 }
};

function decodeHtmlEntities(text = '') {
  return text.replace(/&#(\d+);/g, (_, dec) => String.fromCharCode(dec));
}

function extractTransferFromRawMessage(rawMessage = '') {
  if (!rawMessage) return null;
  const decoded = decodeHtmlEntities(rawMessage);
  if (!decoded.includes('转账')) return null;
  if (!decoded.includes('成功')) return null;

  const amountMatch = decoded.match(/([0-9]+(?:\.[0-9]+)?)\s*元/);
  if (!amountMatch) return null;

  return {
    type: 'text_transfer',
    amount: amountMatch[1],
    pay_msg: decoded
  };
}

function normalizeEvent(body) {
  const eventType = body.post_type || body.event_type || body.type || 'message';
  const messageType = body.message_type || body.sub_type || body.detail_type || 'private';
  const userId = body.user_id || body.sender_id || (body.sender && body.sender.user_id) || null;
  const groupId = body.group_id || null;
  const rawMessage = body.raw_message || body.message || body.text || '';
  const timestamp = body.time || Date.now();

  return {
    eventType,
    messageType,
    userId,
    groupId,
    rawMessage,
    timestamp,
    original: body
  };
}

router.post('/', async (req, res) => {
  try {
    const body = req.body || {};
    const normalized = normalizeEvent(body);

    if (normalized.eventType !== 'message') {
      return res.json({});
    }

    if (normalized.messageType !== 'private' && !normalized.groupId) {
      return res.json({});
    }

    const userId = normalized.userId;
    const message = typeof normalized.rawMessage === 'string' ? normalized.rawMessage.trim() : '';

    if (!userId) {
      return res.json({});
    }

    // ==================== 菜单系统 ====================
    if (normalized.messageType === 'private' && message) {
      const lower = message.toLowerCase();

      if (message === '菜单') {
        try {
          const wallet = await walletService.getWallet(userId);
          const inviteInfo = await inviteService.getInviteCode(String(userId));
          const lotteryInfo = await inviteService.getUserLotteryInfo(String(userId));
          
          return res.json({
            reply:
              `📋 功能菜单\n` +
              `═══════════════════\n` +
              `1️⃣ 我的邀请码\n` +
              `2️⃣ 绑定别人邀请码\n` +
              `3️⃣ 开始构建项目\n` +
              `4️⃣ 余额查询\n` +
              `5️⃣ 论文小助手\n` +
              `6️⃣ 开始抽奖\n` +
              `7️⃣ 加盟赚钱\n` +
              `8️⃣ 修改我的项目\n` +
              `9️⃣ 提现\n` +
              `🔟 充值\n` +
              `1️⃣1️⃣ 咸鱼购买\n` +
              `═════════════════════\n` +
              `💰 当前余额：¥${wallet ? Number(wallet.balance).toFixed(2) : '0.00'}\n` +
              `🎫 邀请码：${inviteInfo ? inviteInfo.code : '未生成'}\n` +
              `🎲 抽奖次数：${lotteryInfo ? lotteryInfo.remaining : 0}/2\n` +
              `📌 系统仅供学习使用`
          });
        } catch (e) {
          console.error('[menu] 获取菜单信息失败:', e && (e.stack || e.message || e));
          return res.json({ reply: '❌ 获取菜单信息失败，请稍后再试。' });
        }
      }

      if (message === '我的邀请码' || message === '邀请码') {
        try {
          const info = await inviteService.getOrCreateInviteCode(String(userId));
          const wallet = await walletService.getWallet(userId);
          return res.json({
            reply:
              `🎟️ 您的邀请码：${info.code}\n` +
              `规则：每个邀请码最多可被绑定 2 次；别人绑定您的邀请码后，您可获得抽奖机会（最多2次）。\n` +
              `当前余额：¥${wallet ? Number(wallet.balance).toFixed(2) : '0.00'}`
          });
        } catch (e) {
          return res.json({ reply: '❌ 获取邀请码失败，请稍后再试。' });
        }
      }

      if (message === '绑定别人邀请码' || message === '绑定邀请码') {
        taskService.setUserState(userId, {
          step: 'WAIT_INVITE_CODE',
          action: 'bind_invite'
        });
        return res.json({
          reply: '请输入对方的邀请码（例如：INVITE2026）'
        });
      }

      if (message.match(/^[A-Z0-9]{4,32}$/)) {
        const userState = taskService.getUserState(userId);
        if (userState.step === 'WAIT_INVITE_CODE') {
          const code = message.trim();
          try {
            const result = await inviteService.bindInviteCode(String(userId), code);
            if (!result.success) {
              const map = {
                CODE_NOT_FOUND: '邀请码不存在，请检查是否输入正确。',
                ALREADY_BOUND: '您已绑定过邀请码，不能重复绑定。',
                CODE_BIND_LIMIT: '该邀请码已达到最多绑定次数（2次）。',
                CANNOT_BIND_SELF: '不能绑定自己的邀请码。',
              };
              return res.json({ reply: `❌ 绑定失败：${map[result.error] || '未知原因'}` });
            }
            taskService.clearUserState(userId);
            return res.json({
              reply:
                `✅ 绑定成功！\n` +
                `已绑定邀请码：${result.code}\n`
            });
          } catch (e) {
            return res.json({ reply: '❌ 绑定失败，请稍后再试。' });
          }
        }
      }

      if (message === '开始构建项目' || message === '构建项目') {
        const userState = taskService.getUserState(userId);
        if (userState.step !== taskService.STEPS.IDLE) {
          return res.json({ reply: '您已有任务在进行中，请先完成当前任务或等待完成。' });
        }
        const taskId = taskService.startTask(userId);
        return res.json({ 
          reply: 
            '📌 项目都是独一无二的，不用担心版权问题。\n\n' +
            '请选择项目类型并确保余额充足：\n' +
            '1：网站开发（¥688）\n' +
            '2：小程序开发（¥788）\n' +
            '3：APP开发（¥888）\n\n' +
            '🤖 给项目定制 AI 功能，联系微信：Tangle-01'
        });
      }

      if (message === '余额查询' || message === '查询余额') {
        try {
          const wallet = await walletService.getWallet(userId);
          return res.json({
            reply: `💰 当前余额：¥${wallet ? Number(wallet.balance).toFixed(2) : '0.00'}`
          });
        } catch (e) {
          return res.json({ reply: '❌ 查询余额失败，请稍后再试。' });
        }
      }

      if (message === '充值') {
        return res.json({
          reply: '充值直接给我转账即可，如需系统实名信息，姓：张'
        });
      }

      if (message === '提现') {
        return res.json({
          reply: '构建项目以后可以提现，请截图构建项目转账记录，添加微信 Tangle-01'
        });
      }

      if (message === '论文小助手') {
        return res.json({
          reply: '📚 论文小助手QQ：88410801'
        });
      }

      if (message === '开始抽奖' || message === '抽奖') {
        try {
          const draw = await inviteService.drawLottery(String(userId));
          if (!draw.success) {
            const map = {
              NOT_BOUND: '还没有人绑定您的邀请码，无法抽奖。',
              DRAW_LIMIT: '您已达到最多抽奖次数（2次）。',
            };
            return res.json({ reply: `❌ 抽奖失败：${map[draw.error] || '未知原因'}` });
          }

          await walletService.grantCredit({
            qqNumber: userId,
            amount: draw.prize,
            remark: `抽奖奖励（邀请码 ${draw.code}）`
          });

          const wallet = await walletService.getWallet(userId);
          return res.json({
            reply:
              `🎉 抽奖成功！恭喜获得 ¥${Number(draw.prize).toFixed(2)}\n` +
              `已自动加入余额用于项目抵扣。\n` +
              `剩余抽奖次数：${draw.remaining}\n` +
              `当前余额：¥${wallet ? Number(wallet.balance).toFixed(2) : '0.00'}`
          });
        } catch (e) {
          return res.json({ reply: '❌ 抽奖失败，请稍后再试。' });
        }
      }

      if (message === '加盟赚钱' || message === '加盟') {
        return res.json({
          reply: '💼 加盟QQ：2813129033'
        });
      }

      if (message === '修改我的项目' || message === '修改项目') {
        try {
          const tasks = await taskService.getUserSentTasks(String(userId));
          if (tasks.length === 0) {
            return res.json({
              reply: '❌ 您还没有已发送的项目，无法修改。\n请先完成一个项目构建。'
            });
          }

          // 显示任务列表，让用户选择
          let taskList = '📋 请选择要修改的项目（发送任务ID）：\n\n';
          tasks.forEach((task, index) => {
            taskList += `${index + 1}. 任务ID: ${task.task_id}\n`;
            taskList += `   类型: ${task.task_type}\n`;
            taskList += `   技术: ${task.task_technology}\n`;
            taskList += `   创建时间: ${task.create_time}\n\n`;
          });

          taskService.setUserState(userId, {
            step: 'WAIT_MODIFY_TASK_ID',
            action: 'modify_project'
          });

          return res.json({ reply: taskList });
        } catch (e) {
          return res.json({ reply: '❌ 查询项目失败，请稍后再试。' });
        }
      }

      if (message === '咸鱼购买' || message === '闲鱼购买') {
        return res.json({
          reply: '【闲鱼】https://m.tb.cn/h.iZdNzGs?tk=7yjSUqJKOOE CZ005 「我在闲鱼发布了【APP网站小程序开发包更新】」\n\n点击链接直接打开\n\n⚠️ 注：咸鱼购买的用户参加不了抽奖活动'
        });
      }

      // 处理修改项目：选择任务ID
      const userState = taskService.getUserState(userId);
      if (userState.step === 'WAIT_MODIFY_TASK_ID' && userState.action === 'modify_project') {
        const taskId = message.trim();
        try {
          const tasks = await taskService.getUserSentTasks(String(userId));
          const selectedTask = tasks.find(t => t.task_id === taskId);
          
          if (!selectedTask) {
            return res.json({
              reply: '❌ 任务ID不存在，请重新发送正确的任务ID。'
            });
          }

          taskService.setUserState(userId, {
            step: 'WAIT_MODIFY_REQUEST',
            action: 'modify_project',
            modifyTaskId: taskId
          });

          return res.json({
            reply: `✅ 已选择任务：${taskId}\n\n请详细描述您需要修改的内容：\n（例如：添加登录功能、修改界面样式、增加数据导出功能等）`
          });
        } catch (e) {
          return res.json({ reply: '❌ 处理失败，请稍后再试。' });
        }
      }

      // 处理修改项目：输入修改需求
      if (userState.step === 'WAIT_MODIFY_REQUEST' && userState.action === 'modify_project') {
        const modifyRequest = message.trim();
        const taskId = userState.modifyTaskId;

        if (!modifyRequest || modifyRequest.length < 5) {
          return res.json({
            reply: '❌ 修改需求描述太短，请详细描述需要修改的内容（至少5个字符）。'
          });
        }

        try {
          const result = await taskService.saveModifyRequest(String(userId), taskId, modifyRequest);
          
          if (!result.success) {
            return res.json({
              reply: `❌ 保存修改需求失败：${result.error || '未知错误'}`
            });
          }

          taskService.clearUserState(userId);
          return res.json({
            reply: `✅ 修改需求已提交！\n\n任务ID：${taskId}\n修改需求：${modifyRequest}\n\n系统将自动处理您的修改请求，完成后会通知您。`
          });
        } catch (e) {
          return res.json({ reply: '❌ 保存失败，请稍后再试。' });
        }
      }
    }
    // ==================== 菜单系统 END ====================

    // 转账事件
    const transferPayload = normalized.original.transfer_info || extractTransferFromRawMessage(normalized.rawMessage);
    if (transferPayload) {
      const transfer = transferPayload;
      const senderNickname = normalized.original.sender?.nickname || '';
      const amountSource = transfer.amount || transfer.pay_msg || normalized.rawMessage;
      const amount = walletService.parseAmount(amountSource);

      if (!amount || amount <= 0) {
        return res.json({});
      }

      try {
        await walletService.recordTransfer({
          qqNumber: String(userId),
          qqNickname: senderNickname,
          amount,
          rawMessage: normalized.rawMessage,
          remark: transfer.type || transfer.pay_msg || 'QQ转账'
        });
        const napcatUrl = onebotConfig.defaultUrl;
        const reply = `💰 收到您的转账 ${amount.toFixed(2)} 元\n` +
          `当前余额已更新，请发送 "菜单" 查看功能。`;

        axios.post(`${napcatUrl}/send_private_msg`, {
          user_id: userId,
          message: reply
        }).catch(err => {
          console.error('[payment] ❌ 发送转账提醒失败:', err.message);
        });
      } catch (error) {
        console.error('[payment] ❌ 转账记录异常:', error);
      }

      return res.json({});
    }

    // 获取用户当前状态
    const userState = taskService.getUserState(userId);


    // 处理任务录入流程
    if (userState.step === taskService.STEPS.WAIT_TYPE) {
      const result = taskService.handleTypeSelection(userId, message);
      if (!result.success) {
        return res.json({ reply: result.error || '请选择 1、2 或 3' });
      }

      const currentState = taskService.getUserState(userId);
      const product = PROJECT_PRODUCTS[currentState.taskType];

      if (!product) {
        taskService.clearUserState(userId);
        return res.json({ reply: '暂不支持该项目类型，请重新输入 "开始构建项目" 选择 1-3。' });
      }

      try {
        const deductResult = await walletService.deductBalance({
          qqNumber: userId,
          amount: product.price,
          remark: `项目预付款-${currentState.taskType}`
        });

        if (!deductResult.success) {
          taskService.clearUserState(userId);
          const currentBalance = deductResult.balance || 0;
          const need = product.price - currentBalance;
          return res.json({
            reply: `余额不足：${currentState.taskType} 需要 ¥${product.price.toFixed(2)}。\n当前余额 ¥${currentBalance.toFixed(2)}，还需充值 ¥${need.toFixed(2)}。\n请转账充值后再次发送 "开始构建项目"。`
          });
        }

        taskService.setUserState(userId, {
          paidAmount: product.price
        });

        return res.json({ 
          reply: `✅ 已扣款 ¥${product.price.toFixed(2)}（${currentState.taskType}），当前余额 ¥${deductResult.balance.toFixed(2)}。\n\n请说出您的技术选型，语言，数据库等必须要使用的技术，如果没有请回复“无”。` 
        });
      } catch (error) {
        console.error('[payment] ❌ 扣款错误:', error);
        taskService.clearUserState(userId);
        return res.json({ reply: '扣款失败，请稍后重新发送 "开始构建项目"。' });
      }
    }

    if (userState.step === taskService.STEPS.WAIT_TECH) {
      const result = taskService.handleTechSelection(userId, message);
      if (!result.success) {
        return res.json({ reply: result.error || '请说出您的技术选型，语言，数据库等必须要使用的技术，如果没有请回复“无”。' });
      }
      return res.json({ 
        reply: '请描述项目是什么样子的，哪些功能是必须有的，如果没有描述到的地方系统也会按照正常逻辑写完整。' 
      });
    }

    if (userState.step === taskService.STEPS.WAIT_DESC) {
      const result = taskService.handleDescription(userId, message);
      if (!result.success) {
        return res.json({ reply: result.error || '请输入功能描述' });
      }

      const completeResult = await taskService.completeTask(userId);
      if (completeResult.success) {
        return res.json({
          reply: `✅ 任务录入成功！\n任务ID：${completeResult.taskId}\n项目类型：${result.state.taskType}\n技术选型：${result.state.taskTechnology}\n功能描述：${result.state.taskDescription}`,
        });
      } else {
        return res.json({
          reply: `❌ 任务保存失败：${completeResult.error || '未知错误'}`,
        });
      }
    }

    // 示例：ping -> pong（保留原有功能）
    if (message.toLowerCase() === 'ping') {
      return res.json({ reply: 'pong' });
    }

    // 默认：调用 Coze AI 对话（只处理私聊消息）
    if (normalized.messageType === 'private' && message) {
      res.status(200).json({});
      
      const napcatUrl = onebotConfig.defaultUrl;
      
      cozeService.getChatReply(message)
        .then(reply => {
          return axios.post(`${napcatUrl}/send_private_msg`, {
            user_id: userId,
            message: reply + '\n（发送"菜单"查看AI助手选项）'
          });
        })
        .catch(error => {
          console.error('[message] ❌ AI调用或发送失败:', error.message);
          if (error.response) {
            console.error('[message] 错误详情:', error.response.status, error.response.data);
          }
          axios.post(`${napcatUrl}/send_private_msg`, {
            user_id: userId,
            message: '抱歉，我现在有点问题，稍后再聊~'
          }).catch(err => {
            console.error('[message] ❌ 发送降级回复失败:', err.message);
          });
        });
      
      return;
    }

    return res.json({});
  } catch (err) {
    console.error('[message][error]', err);
    try {
      return res.json({});
    } catch {
      return;
    }
  }
});

router.get('/health', (req, res) => {
  res.json({ ok: true, service: 'message' });
});

module.exports = router;
