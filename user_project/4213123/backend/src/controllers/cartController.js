import { getPool } from '../config/database.js'

const pool = getPool()

export async function addToCart(req, res) {
  try {
    const userId = req.userId
    const { product_id, quantity } = req.body

    const [existing] = await pool.query(
      'SELECT * FROM cart WHERE user_id = ? AND product_id = ?',
      [userId, product_id]
    )

    if (existing.length > 0) {
      await pool.query(
        'UPDATE cart SET quantity = quantity + ? WHERE user_id = ? AND product_id = ?',
        [quantity, userId, product_id]
      )
    } else {
      await pool.query(
        'INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
        [userId, product_id, quantity]
      )
    }

    res.json({
      code: 200,
      message: '加入购物车成功'
    })
  } catch (error) {
    console.error('Add to cart error:', error)
    res.status(500).json({
      code: 500,
      message: '加入购物车失败'
    })
  }
}

export async function getCart(req, res) {
  try {
    const userId = req.userId

    const [cartItems] = await pool.query(`
      SELECT 
        c.id,
        c.quantity,
        p.id as product_id,
        p.name,
        p.price,
        p.image,
        p.stock
      FROM cart c
      JOIN products p ON c.product_id = p.id
      WHERE c.user_id = ?
    `, [userId])

    res.json({
      code: 200,
      message: 'success',
      data: cartItems
    })
  } catch (error) {
    console.error('Get cart error:', error)
    res.status(500).json({
      code: 500,
      message: '获取购物车失败'
    })
  }
}

export async function updateCartItem(req, res) {
  try {
    const userId = req.userId
    const { id } = req.params
    const { quantity } = req.body

    await pool.query(
      'UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?',
      [quantity, id, userId]
    )

    res.json({
      code: 200,
      message: '更新购物车成功'
    })
  } catch (error) {
    console.error('Update cart item error:', error)
    res.status(500).json({
      code: 500,
      message: '更新购物车失败'
    })
  }
}

export async function removeFromCart(req, res) {
  try {
    const userId = req.userId
    const { id } = req.params

    await pool.query(
      'DELETE FROM cart WHERE id = ? AND user_id = ?',
      [id, userId]
    )

    res.json({
      code: 200,
      message: '删除购物车商品成功'
    })
  } catch (error) {
    console.error('Remove from cart error:', error)
    res.status(500).json({
      code: 500,
      message: '删除购物车商品失败'
    })
  }
}
