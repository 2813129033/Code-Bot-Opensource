const mysql = require('mysql2/promise');
const logger = require('../utils/logger');
const config = require('./index');

let pool = null;

const createPool = () => {
  if (pool) {
    return pool;
  }

  pool = mysql.createPool({
    host: config.mysql.host,
    port: config.mysql.port,
    user: config.mysql.user,
    password: config.mysql.password,
    database: config.mysql.database,
    waitForConnections: true,
    connectionLimit: config.mysql.connectionLimit,
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
  // 开发规范提示（写 SQL 时常踩坑）：
  // 1) 建库/建表前如果有外键，先执行：SET FOREIGN_KEY_CHECKS = 0;（创建完成后再改回 1）
  // 2) 外键语法：ON DELETE SET NULL（不要写成 ON SET NULL）
  // 3) 分页 LIMIT/OFFSET：优先把数字 parseInt 后拼接进 SQL，避免用占位符导致驱动/类型问题
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