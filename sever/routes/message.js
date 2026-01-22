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
  'H5开发': { price: 200 },
  'APP开发': { price: 400 }
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

    console.log('[message][incoming]', {
      from: normalized.groupId ? 'group' : 'private',
      userId: normalized.userId,
      groupId: normalized.groupId,
      text: normalized.rawMessage
    });

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
              `═════════════════════\n` +
              `💰 当前余额：¥${wallet ? Number(wallet.balance).toFixed(2) : '0.00'}\n` +
              `🎫 邀请码：${inviteInfo ? inviteInfo.code : '未生成'}\n` +
              `🎲 抽奖次数：${lotteryInfo ? lotteryInfo.remaining : 0}/2`
          });
        } catch (e) {
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
                `邀请码：${result.code}\n` +
                `现在可发送 "开始抽奖" 开始抽奖（最多 2 次）。`
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
        console.log(`[task] 用户 ${userId} 开始任务录入，任务ID: ${taskId}`);
        return res.json({ 
          reply: '请选择项目类型并确保余额充足：\n1：H5 开发（¥200）\n2：APP 开发（¥400）' 
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
    }
    // ==================== 菜单系统 END ====================

    // 转账事件
    const transferPayload = normalized.original.transfer_info || extractTransferFromRawMessage(normalized.rawMessage);
    if (transferPayload) {
      const transfer = transferPayload;
      const senderNickname = normalized.original.sender?.nickname || '';
      const amountSource = transfer.amount || transfer.pay_msg || normalized.rawMessage;
      const amount = walletService.parseAmount(amountSource);

      console.log('[payment][transfer]', {
        userId,
        amount,
        raw: transfer
      });

      if (!amount || amount <= 0) {
        console.warn('[payment] ⚠️ 无法解析转账金额，忽略此次事件');
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

        console.log('[payment] ✅ 转账记录成功');
      } catch (error) {
        console.error('[payment] ❌ 转账记录异常:', error);
      }

      return res.json({});
    }

    // 获取用户当前状态
    const userState = taskService.getUserState(userId);

    // 处理 start 命令（保留兼容性）
    if (message.toLowerCase() === 'start') {
      if (userState.step !== taskService.STEPS.IDLE) {
        return res.json({ reply: '您已有任务在进行中，请先完成当前任务或等待完成。' });
      }
      const taskId = taskService.startTask(userId);
      console.log(`[task] 用户 ${userId} 开始任务录入，任务ID: ${taskId}`);
      return res.json({ 
        reply: '请选择项目类型并确保余额充足：\n1：H5 开发（¥200）\n2：APP 开发（¥400）' 
      });
    }

    // 处理任务录入流程
    if (userState.step === taskService.STEPS.WAIT_TYPE) {
      const result = taskService.handleTypeSelection(userId, message);
      if (!result.success) {
        return res.json({ reply: result.error || '请选择1、2或3' });
      }

      const currentState = taskService.getUserState(userId);
      const product = PROJECT_PRODUCTS[currentState.taskType];

      if (!product) {
        taskService.clearUserState(userId);
        return res.json({ reply: '暂不支持该项目类型，请重新输入 "开始构建项目" 选择 1-2。' });
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
          reply: `✅ 已扣款 ¥${product.price.toFixed(2)}（${currentState.taskType}），当前余额 ¥${deductResult.balance.toFixed(2)}。\n技术选型是什么？请输入项目语言和数据库（例如：Node.js + MySQL）。` 
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
        return res.json({ reply: result.error || '请输入技术选型' });
      }
      return res.json({ 
        reply: '请说出您项目的功能描述，也可以在此处补充技术选型' 
      });
    }

    if (userState.step === taskService.STEPS.WAIT_DESC) {
      const result = taskService.handleDescription(userId, message);
      if (!result.success) {
        return res.json({ reply: result.error || '请输入功能描述' });
      }

      const completeResult = await taskService.completeTask(userId);
      if (completeResult.success) {
        console.log(`[task] 用户 ${userId} 任务录入完成，任务ID: ${completeResult.taskId}`);

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
            message: reply
          });
        })
        .then(() => {
          console.log(`[message] ✅ AI回复已发送给用户 ${userId}`);
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
