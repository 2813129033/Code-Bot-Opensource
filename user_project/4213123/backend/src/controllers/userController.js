import { getPool } from '../config/database.js'
import bcrypt from 'bcrypt'
import jwt from 'jsonwebtoken'

const pool = getPool()
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key'

export async function register(req, res) {
  try {
    const { phone, password, nickname } = req.body

    const [existing] = await pool.query('SELECT id FROM users WHERE phone = ?', [phone])
    if (existing.length > 0) {
      return res.status(400).json({
        code: 400,
        message: '手机号已注册'
      })
    }

    const hashedPassword = await bcrypt.hash(password, 10)

    const [result] = await pool.query(
      'INSERT INTO users (phone, password, nickname) VALUES (?, ?, ?)',
      [phone, hashedPassword, nickname || '用户']
    )

    const token = jwt.sign({ userId: result.insertId }, JWT_SECRET, { expiresIn: '7d' })

    res.json({
      code: 200,
      message: '注册成功',
      data: {
        token,
        userId: result.insertId
      }
    })
  } catch (error) {
    console.error('Register error:', error)
    res.status(500).json({
      code: 500,
      message: '注册失败'
    })
  }
}

export async function login(req, res) {
  try {
    const { phone, password } = req.body

    const [users] = await pool.query('SELECT * FROM users WHERE phone = ?', [phone])

    if (users.length === 0) {
      return res.status(400).json({
        code: 400,
        message: '手机号或密码错误'
      })
    }

    const user = users[0]
    const isValid = await bcrypt.compare(password, user.password)

    if (!isValid) {
      return res.status(400).json({
        code: 400,
        message: '手机号或密码错误'
      })
    }

    const token = jwt.sign({ userId: user.id }, JWT_SECRET, { expiresIn: '7d' })

    res.json({
      code: 200,
      message: '登录成功',
      data: {
        token,
        userId: user.id,
        nickname: user.nickname,
        avatar: user.avatar
      }
    })
  } catch (error) {
    console.error('Login error:', error)
    res.status(500).json({
      code: 500,
      message: '登录失败'
    })
  }
}

export async function getUserInfo(req, res) {
  try {
    const userId = req.userId

    const [users] = await pool.query('SELECT id, phone, nickname, avatar FROM users WHERE id = ?', [userId])

    if (users.length === 0) {
      return res.status(404).json({
        code: 404,
        message: '用户不存在'
      })
    }

    res.json({
      code: 200,
      message: 'success',
      data: users[0]
    })
  } catch (error) {
    console.error('Get user info error:', error)
    res.status(500).json({
      code: 500,
      message: '获取用户信息失败'
    })
  }
}
