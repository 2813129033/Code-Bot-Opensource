const mysql = require('mysql2/promise');
const { dbConfig } = require('./config');

let pool;

async function initDB() {
  if (pool) return pool;
  try {
    pool = mysql.createPool({
      host: dbConfig.host,
      port: dbConfig.port,
      user: dbConfig.user,
      password: dbConfig.password,
      database: dbConfig.database,
      connectionLimit: dbConfig.connectionLimit || 10,
      waitForConnections: true,
      connectTimeout: 10000,
      charset: 'utf8mb4_general_ci',
      enableKeepAlive: true,
      keepAliveInitialDelay: 0
    });

    // 测试连接是否可用
    const [rows] = await pool.query('SELECT 1');
    if (rows) console.log('✅ MySQL connected');

    // 自动重连检测逻辑
    pool.on('error', (err) => {
      console.error('[mysql pool error]', err);
      if (err.code === 'PROTOCOL_CONNECTION_LOST') {
        console.log('🔁 Reconnecting MySQL...');
        initDB();
      } else {
        throw err;
      }
    });

    return pool;
  } catch (err) {
    console.error('❌ MySQL connection failed:', err.message);
    process.exit(1);
  }
}

module.exports = { initDB };
