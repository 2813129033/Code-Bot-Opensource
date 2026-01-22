const crypto = require('crypto');
const { initDB } = require('../config/mysql');

function normalizeQQ(qqNumber) {
  return String(qqNumber || '').trim();
}

function generateCode() {
  // 8 位可读邀请码（不追求加密强度）
  return crypto.randomBytes(6).toString('base64url').slice(0, 8).toUpperCase();
}

async function getOrCreateInviteCode(ownerQq) {
  const qq = normalizeQQ(ownerQq);
  if (!qq) throw new Error('INVALID_QQ');

  const db = await initDB();
  const [rows] = await db.execute(
    'SELECT code, max_bindings FROM invite_codes WHERE owner_qq_number = ?',
    [qq]
  );
  if (rows.length) return rows[0];

  // 创建
  let code = generateCode();
  for (let i = 0; i < 5; i++) {
    try {
      await db.execute(
        'INSERT INTO invite_codes (owner_qq_number, code, max_bindings) VALUES (?, ?, 2)',
        [qq, code]
      );
      return { code, max_bindings: 2 };
    } catch (e) {
      // code 冲突则重试
      code = generateCode();
    }
  }
  throw new Error('CODE_GENERATE_FAILED');
}

/**
 * 仅获取邀请码（不自动创建）
 * @param {string|number} ownerQq
 * @returns {Promise<{code:string,max_bindings:number} | null>}
 */
async function getInviteCode(ownerQq) {
  const qq = normalizeQQ(ownerQq);
  if (!qq) throw new Error('INVALID_QQ');

  const db = await initDB();
  const [rows] = await db.execute(
    'SELECT code, max_bindings FROM invite_codes WHERE owner_qq_number = ?',
    [qq]
  );
  return rows.length ? rows[0] : null;
}

async function bindInviteCode(inviteeQq, codeInput) {
  const invitee = normalizeQQ(inviteeQq);
  const code = String(codeInput || '').trim().toUpperCase();
  if (!invitee || !code) throw new Error('INVALID_PARAMS');

  const db = await initDB();
  const conn = await db.getConnection();

  try {
    await conn.beginTransaction();

    // 已绑定校验（每人只能绑定一次）
    const [existing] = await conn.execute(
      'SELECT id FROM invite_bindings WHERE invitee_qq_number = ? FOR UPDATE',
      [invitee]
    );
    if (existing.length) {
      await conn.rollback();
      return { success: false, error: 'ALREADY_BOUND' };
    }

    // 邀请码存在性
    const [codeRows] = await conn.execute(
      'SELECT owner_qq_number, max_bindings FROM invite_codes WHERE code = ? FOR UPDATE',
      [code]
    );
    if (!codeRows.length) {
      await conn.rollback();
      return { success: false, error: 'CODE_NOT_FOUND' };
    }
    const inviter = String(codeRows[0].owner_qq_number);
    const maxBindings = parseInt(codeRows[0].max_bindings, 10) || 2;

    if (inviter === invitee) {
      await conn.rollback();
      return { success: false, error: 'CANNOT_BIND_SELF' };
    }

    // 绑定次数限制（每个邀请码最多绑定 2 次）
    const [cntRows] = await conn.execute(
      'SELECT COUNT(1) AS cnt FROM invite_bindings WHERE code = ? FOR UPDATE',
      [code]
    );
    const cnt = parseInt(cntRows[0]?.cnt, 10) || 0;
    if (cnt >= maxBindings) {
      await conn.rollback();
      return { success: false, error: 'CODE_BIND_LIMIT' };
    }

    await conn.execute(
      'INSERT INTO invite_bindings (code, inviter_qq_number, invitee_qq_number) VALUES (?, ?, ?)',
      [code, inviter, invitee]
    );

    await conn.commit();
    return { success: true, code, inviter };
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

function pickPrize() {
  // 100:50%, 200:40%, 300:10%
  const r = Math.random() * 100;
  if (r < 50) return 100;
  if (r < 90) return 200;
  return 300;
}

async function drawLottery(qqNumber) {
  const qq = normalizeQQ(qqNumber);
  if (!qq) throw new Error('INVALID_QQ');

  const db = await initDB();
  const conn = await db.getConnection();

  try {
    await conn.beginTransaction();

    // 检查当前用户是否是邀请码所有者（即有人绑定了他的邀请码）
    const [bindingRows] = await conn.execute(
      'SELECT code FROM invite_bindings WHERE inviter_qq_number = ? FOR UPDATE',
      [qq]
    );
    if (!bindingRows.length) {
      await conn.rollback();
      return { success: false, error: 'NOT_BOUND' };
    }
    // 使用第一个绑定的邀请码（如果有多个，使用第一个）
    const code = String(bindingRows[0].code);

    // 邀请码所有者最多抽 2 次（对应最多2个人绑定他的邀请码）
    const [drawCntRows] = await conn.execute(
      'SELECT COUNT(1) AS cnt FROM lottery_draws WHERE qq_number = ? FOR UPDATE',
      [qq]
    );
    const drawCnt = parseInt(drawCntRows[0]?.cnt, 10) || 0;
    if (drawCnt >= 2) {
      await conn.rollback();
      return { success: false, error: 'DRAW_LIMIT' };
    }

    const prize = pickPrize();
    await conn.execute(
      'INSERT INTO lottery_draws (qq_number, code, prize_amount) VALUES (?, ?, ?)',
      [qq, code, prize]
    );

    await conn.commit();
    return { success: true, prize, code, remaining: 1 - drawCnt };
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

async function getUserLotteryInfo(qqNumber) {
  const qq = normalizeQQ(qqNumber);
  if (!qq) throw new Error('INVALID_QQ');

  const db = await initDB();
  const conn = await db.getConnection();
  try {
    await conn.beginTransaction();

    // 检查是否有人绑定了当前用户的邀请码（即当前用户是否是邀请码所有者）
    const [bindingRows] = await conn.execute(
      'SELECT code FROM invite_bindings WHERE inviter_qq_number = ? FOR UPDATE',
      [qq]
    );
    if (!bindingRows.length) {
      await conn.rollback();
      return null; // 没有人绑定他的邀请码
    }

    // 获取抽奖次数
    const [drawCntRows] = await conn.execute(
      'SELECT COUNT(1) AS cnt FROM lottery_draws WHERE qq_number = ? FOR UPDATE',
      [qq]
    );
    const drawCnt = parseInt(drawCntRows[0]?.cnt, 10) || 0;

    await conn.commit();
    return {
      code: bindingRows[0].code,
      remaining: 2 - drawCnt, // 最多2次
      drawCount: drawCnt
    };
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
}

module.exports = {
  getInviteCode,
  getOrCreateInviteCode,
  bindInviteCode,
  drawLottery,
  getUserLotteryInfo,
};

