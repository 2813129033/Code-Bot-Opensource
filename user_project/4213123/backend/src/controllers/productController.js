import { getPool } from '../config/database.js'
import { getClient } from '../config/redis.js'

const pool = getPool()
const redis = getClient()

export async function getProducts(req, res) {
  try {
    const { page = 1, pageSize = 20, category_id, sort } = req.query
    const offset = (page - 1) * pageSize

    let sql = 'SELECT * FROM products WHERE 1=1'
    const params = []

    if (category_id) {
      sql += ' AND category_id = ?'
      params.push(category_id)
    }

    if (sort === 'price_asc') {
      sql += ' ORDER BY price ASC'
    } else if (sort === 'price_desc') {
      sql += ' ORDER BY price DESC'
    } else if (sort === 'sales_desc') {
      sql += ' ORDER BY sales DESC'
    } else {
      sql += ' ORDER BY created_at DESC'
    }

    sql += ' LIMIT ? OFFSET ?'
    params.push(parseInt(pageSize), offset)

    const [products] = await pool.query(sql, params)

    const [countResult] = await pool.query('SELECT COUNT(*) as total FROM products WHERE 1=1')
    const total = countResult[0].total

    res.json({
      code: 200,
      message: 'success',
      data: products,
      pagination: {
        page: parseInt(page),
        page_size: parseInt(pageSize),
        total,
        total_pages: Math.ceil(total / pageSize)
      }
    })
  } catch (error) {
    console.error('Get products error:', error)
    res.status(500).json({
      code: 500,
      message: '获取商品列表失败'
    })
  }
}

export async function getProductDetail(req, res) {
  try {
    const { id } = req.params

    const cacheKey = `product:${id}`
    const cached = await redis.get(cacheKey)

    if (cached) {
      return res.json({
        code: 200,
        message: 'success',
        data: JSON.parse(cached)
      })
    }

    const [products] = await pool.query('SELECT * FROM products WHERE id = ?', [id])

    if (products.length === 0) {
      return res.status(404).json({
        code: 404,
        message: '商品不存在'
      })
    }

    await redis.setEx(cacheKey, 3600, JSON.stringify(products[0]))

    res.json({
      code: 200,
      message: 'success',
      data: products[0]
    })
  } catch (error) {
    console.error('Get product detail error:', error)
    res.status(500).json({
      code: 500,
      message: '获取商品详情失败'
    })
  }
}

export async function searchProducts(req, res) {
  try {
    const { keyword, page = 1, pageSize = 20 } = req.query
    const offset = (page - 1) * pageSize

    const sql = `
      SELECT * FROM products 
      WHERE name LIKE ? OR description LIKE ?
      LIMIT ? OFFSET ?
    `
    const params = [`%${keyword}%`, `%${keyword}%`, parseInt(pageSize), offset]

    const [products] = await pool.query(sql, params)

    res.json({
      code: 200,
      message: 'success',
      data: products
    })
  } catch (error) {
    console.error('Search products error:', error)
    res.status(500).json({
      code: 500,
      message: '搜索商品失败'
    })
  }
}
