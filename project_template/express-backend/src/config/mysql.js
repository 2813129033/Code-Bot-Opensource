const mysql = require('mysql2/promise');
const logger = require('../utils/logger');

let pool = null;

const createPool = () => {
  if (pool) {
    return pool;
  }

  pool = mysql.createPool({
    host: process.env.MYSQL_HOST || 'localhost',
    port: parseInt(process.env.MYSQL_PORT) || 3306,
    user: process.env.MYSQL_USER || 'root',
    password: process.env.MYSQL_PASSWORD || '',
    database: process.env.MYSQL_DATABASE || 'test',
    waitForConnections: true,
    connectionLimit: parseInt(process.env.MYSQL_CONNECTION_LIMIT) || 10,
    queueLimit: 0,
    enableKeepAlive: true,
    keepAliveInitialDelay: 0,
    charset: 'utf8mb4',
    timezone: '+00:00'
  });

  // 监听连接事件
  pool.on('connection', (connection) => {
    logger.info(`MySQL: New connection established as id ${connection.threadId}`);
  });

  pool.on('error', (err) => {
    logger.error('MySQL pool error:', err);
    if (err.code === 'PROTOCOL_CONNECTION_LOST') {
      logger.warn('MySQL connection lost, attempting to reconnect...');
      pool = null;
      createPool();
    } else {
      throw err;
    }
  });

  return pool;
};

const connectMySQL = async () => {
  try {
    const connectionPool = createPool();
    const connection = await connectionPool.getConnection();
    
    // 测试连接
    await connection.ping();
    logger.info('✅ MySQL connected successfully');
    
    connection.release();
    return connectionPool;
  } catch (error) {
    logger.error('❌ MySQL connection failed:', error.message);
    throw error;
  }
};

// 获取连接池
const getPool = () => {
  if (!pool) {
    createPool();
  }
  return pool;
};

// 执行查询
const query = async (sql, params = []) => {
  try {
    const connectionPool = getPool();
    const [results] = await connectionPool.execute(sql, params);
    return results;
  } catch (error) {
    logger.error('MySQL query error:', error);
    throw error;
  }
};

// 执行事务
const transaction = async (callback) => {
  const connectionPool = getPool();
  const connection = await connectionPool.getConnection();
  
  try {
    await connection.beginTransaction();
    const result = await callback(connection);
    await connection.commit();
    return result;
  } catch (error) {
    await connection.rollback();
    logger.error('MySQL transaction error:', error);
    throw error;
  } finally {
    connection.release();
  }
};

module.exports = {
  connectMySQL,
  getPool,
  query,
  transaction
};