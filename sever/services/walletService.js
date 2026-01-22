const { initDB } = require('../config/mysql');

/**
 * 将字符串金额解析为数字（元）
 * @param {string|number|null|undefined} amountStr
 * @returns {number}
 */
function parseAmount(amountStr) {
  if (typeof amountStr === 'number') {
    return amountStr;
  }
  if (!amountStr) return 0;

  const normalized = String(amountStr).replace(/,/g, '');
  const match = normalized.match(/-?\d+(\.\d+)?/);
  return match ? parseFloat(match[0]) : 0;
}

/**
 * 记录一次转账并更新用户钱包
 * @param {Object} options
 * @param {string|number} options.qqNumber
 * @param {string} [options.qqNickname]
 * @param {string|number} options.amount
 * @param {string} [options.rawMessage]
 * @param {string} [options.remark]
 */
async function recordTransfer({ qqNumber, qqNickname, amount, rawMessage, remark }) {
  const numericAmount = parseAmount(amount);
  if (!numericAmount || numericAmount <= 0) {
    throw new Error('INVALID_AMOUNT');
  }

  const db = await initDB();
  const connection = await db.getConnection();

  try {
    await connection.beginTransaction();

    // 创建或更新钱包
    await connection.execute(
      `INSERT INTO wallets (qq_number, qq_nickname, balance, total_recharge)
       VALUES (?, ?, ?, ?)
       ON DUPLICATE KEY UPDATE
         qq_nickname = VALUES(qq_nickname),
         balance = balance + VALUES(balance),
         total_recharge = total_recharge + VALUES(total_recharge)`,
      [String(qqNumber), qqNickname || null, numericAmount, numericAmount]
    );

    // 记录交易
    await connection.execute(
      `INSERT INTO wallet_transactions (qq_number, amount, raw_message, remark)
       VALUES (?, ?, ?, ?)`,
      [String(qqNumber), numericAmount, rawMessage || null, remark || null]
    );

    await connection.commit();

    return { success: true, amount: numericAmount };
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    connection.release();
  }
}

/**
 * 获取钱包信息
 * @param {string|number} qqNumber
 * @returns {Promise<{balance:number,total_recharge:number} | null>}
 */
async function getWallet(qqNumber) {
  const db = await initDB();
  const [rows] = await db.execute(
    'SELECT qq_number, qq_nickname, balance, total_recharge FROM wallets WHERE qq_number = ?',
    [String(qqNumber)]
  );
  if (rows.length === 0) {
    return null;
  }
  return rows[0];
}

/**
 * 扣除余额（项目预付）
 * @param {Object} options
 * @param {string|number} options.qqNumber
 * @param {number} options.amount
 * @param {string} [options.remark]
 * @returns {Promise<{success:boolean,balance:number,required?:number}>}
 */
async function deductBalance({ qqNumber, amount, remark }) {
  const numericAmount = parseFloat(amount);
  if (!numericAmount || numericAmount <= 0) {
    throw new Error('INVALID_DEDUCT_AMOUNT');
  }

  const db = await initDB();
  const connection = await db.getConnection();

  try {
    await connection.beginTransaction();

    // 确保钱包行存在
    await connection.execute(
      `INSERT IGNORE INTO wallets (qq_number, balance, total_recharge)
       VALUES (?, 0, 0)`,
      [String(qqNumber)]
    );

    const [rows] = await connection.execute(
      'SELECT balance FROM wallets WHERE qq_number = ? FOR UPDATE',
      [String(qqNumber)]
    );

    const currentBalance = rows.length ? parseFloat(rows[0].balance) : 0;
    if (currentBalance < numericAmount) {
      await connection.rollback();
      return { success: false, balance: currentBalance, required: numericAmount };
    }

    await connection.execute(
      'UPDATE wallets SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP WHERE qq_number = ?',
      [numericAmount, String(qqNumber)]
    );

    await connection.execute(
      `INSERT INTO wallet_transactions (qq_number, amount, remark)
       VALUES (?, ?, ?)`,
      [String(qqNumber), -numericAmount, remark || '项目预付款']
    );

    await connection.commit();

    return { success: true, balance: currentBalance - numericAmount };
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    connection.release();
  }
}

/**
 * 发放奖励/补贴到钱包（会增加 balance 与 total_recharge，并写入流水）
 * @param {Object} options
 * @param {string|number} options.qqNumber
 * @param {number} options.amount
 * @param {string} [options.remark]
 */
async function grantCredit({ qqNumber, amount, remark }) {
  const numericAmount = parseFloat(amount);
  if (!numericAmount || numericAmount <= 0) {
    throw new Error('INVALID_GRANT_AMOUNT');
  }

  const db = await initDB();
  const connection = await db.getConnection();

  try {
    await connection.beginTransaction();

    await connection.execute(
      `INSERT INTO wallets (qq_number, balance, total_recharge)
       VALUES (?, ?, ?)
       ON DUPLICATE KEY UPDATE
         balance = balance + VALUES(balance),
         total_recharge = total_recharge + VALUES(total_recharge)`,
      [String(qqNumber), numericAmount, numericAmount]
    );

    await connection.execute(
      `INSERT INTO wallet_transactions (qq_number, amount, remark)
       VALUES (?, ?, ?)`,
      [String(qqNumber), numericAmount, remark || '活动奖励']
    );

    await connection.commit();
    return { success: true, amount: numericAmount };
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    connection.release();
  }
}

module.exports = {
  parseAmount,
  recordTransfer,
  getWallet,
  deductBalance,
  grantCredit
};

