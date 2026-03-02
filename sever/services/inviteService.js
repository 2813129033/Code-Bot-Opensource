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
  // 每次随机金额：70 ~ 100（含），均匀分布
  const min = 70;
  const max = 100;
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

async function drawLottery(qqNumber) {
  const qq = normalizeQQ(qqNumber);
  if (!qq) throw new Error('INVALID_QQ');

  const db = await initDB();
  const conn = await db.getConnection();

  try {
    await conn.beginTransaction();

    // 检查当前用户是否是邀请码所有者，并统计被绑定次数
    const [bindingRows] = await conn.execute(
      'SELECT code, COUNT(*) AS bind_cnt FROM invite_bindings WHERE inviter_qq_number = ? GROUP BY code FOR UPDATE',
      [qq]
    );
    if (!bindingRows.length || !bindingRows[0].bind_cnt) {
      await conn.rollback();
      return { success: false, error: 'NOT_BOUND' };
    }
    // 取绑定次数最多的那条（兼容 ONLY_FULL_GROUP_BY）
    const best = bindingRows
      .map(r => ({ code: r.code, bind_cnt: parseInt(r.bind_cnt, 10) || 0 }))
      .sort((a, b) => b.bind_cnt - a.bind_cnt)[0];

    const code = String(best.code);
    const bindCnt = best.bind_cnt;

    // 每被绑定 1 次获得 1 次抽奖机会，总机会数 = min(绑定人数, 2)
    // 例如：
    //  - 绑定 1 人 → 总共 1 次机会
    //  - 绑定 2 人及以上 → 总共最多 2 次机会
    const maxDrawTimes = Math.min(bindCnt, 2);

    // 查询当前已抽奖次数
    const [drawCntRows] = await conn.execute(
      'SELECT COUNT(1) AS cnt FROM lottery_draws WHERE qq_number = ? FOR UPDATE',
      [qq]
    );
    const drawCnt = parseInt(drawCntRows[0]?.cnt, 10) || 0;
    if (drawCnt >= maxDrawTimes) {
      await conn.rollback();
      return { success: false, error: 'DRAW_LIMIT' };
    }

    const prize = pickPrize();
    await conn.execute(
      'INSERT INTO lottery_draws (qq_number, code, prize_amount) VALUES (?, ?, ?)',
      [qq, code, prize]
    );

    await conn.commit();
    return {
      success: true,
      prize,
      code,
      remaining: Math.max(0, maxDrawTimes - drawCnt - 1)
    };
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

    // 检查是否有人绑定了当前用户的邀请码，并统计绑定次数
    const [bindingRows] = await conn.execute(
      'SELECT code, COUNT(*) AS bind_cnt FROM invite_bindings WHERE inviter_qq_number = ? GROUP BY code FOR UPDATE',
      [qq]
    );
    if (!bindingRows.length || !bindingRows[0].bind_cnt) {
      await conn.rollback();
      return null; // 没有人绑定他的邀请码
    }
    const best = bindingRows
      .map(r => ({ code: r.code, bind_cnt: parseInt(r.bind_cnt, 10) || 0 }))
      .sort((a, b) => b.bind_cnt - a.bind_cnt)[0];
    const bindCnt = best.bind_cnt;

    // 获取抽奖次数
    const [drawCntRows] = await conn.execute(
      'SELECT COUNT(1) AS cnt FROM lottery_draws WHERE qq_number = ? FOR UPDATE',
      [qq]
    );
    const drawCnt = parseInt(drawCntRows[0]?.cnt, 10) || 0;

    const maxDrawTimes = Math.min(bindCnt, 2);
    const remaining = Math.max(0, maxDrawTimes - drawCnt);

    await conn.commit();
    return {
      code: best.code,
      // 每被绑定一次获得一次机会，总机会不超过 2 次
      remaining,
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

