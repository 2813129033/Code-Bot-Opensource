const redis = require('redis');
const logger = require('../utils/logger');

let client = null;

const createClient = () => {
  if (client && client.isOpen) {
    return client;
  }

  client = redis.createClient({
    socket: {
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT) || 6379,
      reconnectStrategy: (retries) => {
        if (retries > 10) {
          logger.error('Redis: Too many reconnection attempts');
          return new Error('Too many retries');
        }
        return Math.min(retries * 50, 1000);
      }
    },
    password: process.env.REDIS_PASSWORD || undefined,
    database: parseInt(process.env.REDIS_DB) || 0
  });

  const keyPrefix = process.env.REDIS_KEY_PREFIX || 'app:';

  // 错误处理
  client.on('error', (err) => {
    logger.error('Redis Client Error:', err);
  });

  client.on('connect', () => {
    logger.info('Redis: Connecting...');
  });

  client.on('ready', () => {
    logger.info('✅ Redis connected successfully');
  });

  client.on('reconnecting', () => {
    logger.warn('Redis: Reconnecting...');
  });

  client.on('end', () => {
    logger.warn('Redis: Connection ended');
  });

  return client;
};

const connectRedis = async () => {
  try {
    const redisClient = createClient();
    await redisClient.connect();
    return redisClient;
  } catch (error) {
    logger.error('❌ Redis connection failed:', error.message);
    // Redis连接失败不应该阻止应用启动，只记录错误
    return null;
  }
};

// 获取Redis客户端
const getClient = () => {
  if (!client || !client.isOpen) {
    createClient();
  }
  return client;
};

// Redis工具方法
const redisUtils = {
  // 设置键值
  async set(key, value, expireSeconds = null) {
    try {
      const client = getClient();
      if (!client || !client.isOpen) {
        logger.warn('Redis client not available');
        return false;
      }
      const fullKey = `${process.env.REDIS_KEY_PREFIX || 'app:'}${key}`;
      if (expireSeconds) {
        await client.setEx(fullKey, expireSeconds, JSON.stringify(value));
      } else {
        await client.set(fullKey, JSON.stringify(value));
      }
      return true;
    } catch (error) {
      logger.error('Redis set error:', error);
      return false;
    }
  },

  // 获取值
  async get(key) {
    try {
      const client = getClient();
      if (!client || !client.isOpen) {
        return null;
      }
      const fullKey = `${process.env.REDIS_KEY_PREFIX || 'app:'}${key}`;
      const value = await client.get(fullKey);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error('Redis get error:', error);
      return null;
    }
  },

  // 删除键
  async del(key) {
    try {
      const client = getClient();
      if (!client || !client.isOpen) {
        return false;
      }
      const fullKey = `${process.env.REDIS_KEY_PREFIX || 'app:'}${key}`;
      await client.del(fullKey);
      return true;
    } catch (error) {
      logger.error('Redis del error:', error);
      return false;
    }
  },

  // 检查键是否存在
  async exists(key) {
    try {
      const client = getClient();
      if (!client || !client.isOpen) {
        return false;
      }
      const fullKey = `${process.env.REDIS_KEY_PREFIX || 'app:'}${key}`;
      const result = await client.exists(fullKey);
      return result === 1;
    } catch (error) {
      logger.error('Redis exists error:', error);
      return false;
    }
  },

  // 设置过期时间
  async expire(key, seconds) {
    try {
      const client = getClient();
      if (!client || !client.isOpen) {
        return false;
      }
      const fullKey = `${process.env.REDIS_KEY_PREFIX || 'app:'}${key}`;
      await client.expire(fullKey, seconds);
      return true;
    } catch (error) {
      logger.error('Redis expire error:', error);
      return false;
    }
  },

  // 获取剩余过期时间
  async ttl(key) {
    try {
      const client = getClient();
      if (!client || !client.isOpen) {
        return -1;
      }
      const fullKey = `${process.env.REDIS_KEY_PREFIX || 'app:'}${key}`;
      return await client.ttl(fullKey);
    } catch (error) {
      logger.error('Redis ttl error:', error);
      return -1;
    }
  }
};

module.exports = {
  connectRedis,
  getClient,
  ...redisUtils
};