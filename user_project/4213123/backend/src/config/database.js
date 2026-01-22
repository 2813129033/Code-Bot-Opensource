import mysql from 'mysql2/promise'

let pool

export async function initDB() {
  pool = mysql.createPool({
    host: process.env.DB_HOST || '127.0.0.1',
    port: process.env.DB_PORT || 3306,
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || 'root',
    database: process.env.DB_NAME || 'h5_mall',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
  })

  try {
    const [rows] = await pool.query('SELECT 1')
    console.log('✅ MySQL connected')
    return pool
  } catch (error) {
    console.error('❌ MySQL connection failed:', error)
    throw error
  }
}

export function getPool() {
  return pool
}
