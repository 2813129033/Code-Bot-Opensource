const { initDB } = require('../config/mysql');

async function main() {
  try {
    const db = await initDB();
    const [ping] = await db.query('SELECT 1 AS ok');

    const [tables] = await db.query('SHOW TABLES');

    // 检查菜单依赖的核心表是否存在
    const tableNames = new Set(
      tables
        .map(row => Object.values(row)[0])
        .filter(Boolean)
        .map(String)
    );

    const required = [
      'wallets',
      'invite_codes',
      'invite_bindings',
      'lottery_draws',
      'wallet_transactions',
    ];

    const missing = required.filter(t => !tableNames.has(t));
    if (missing.length) {
      console.error('[db_check] missing tables:', missing);
      process.exitCode = 2;
      return;
    }
  } catch (e) {
    console.error('[db_check] failed:', e && (e.stack || e.message || e));
    process.exitCode = 1;
  }
}

main();

