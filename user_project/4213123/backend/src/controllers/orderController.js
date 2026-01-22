import { getPool } from '../config/database.js'

const pool = getPool()

export async function createOrder(req, res) {
  try {
    const userId = req.userId
    const { items, address_id } = req.body

    const connection = await pool.getConnection()
    await connection.beginTransaction()

    try {
      let totalAmount = 0

      for (const item of items) {
        const [products] = await connection.query(
          'SELECT price, stock FROM products WHERE id = ? FOR UPDATE',
          [item.product_id]
        )

        if (products.length === 0) {
          throw new Error(`商品 ${item.product_id} 不存在`)
        }

        const product = products[0]

        if (product.stock < item.quantity) {
          throw new Error(`商品 ${item.product_id} 库存不足`)
        }

        await connection.query(
          'UPDATE products SET stock = stock - ?, sales = sales + ? WHERE id = ?',
          [item.quantity, item.quantity, item.product_id]
        )

        totalAmount += product.price * item.quantity
      }

      const [orderResult] = await connection.query(
        'INSERT INTO orders (user_id, address_id, total_amount, status) VALUES (?, ?, ?, ?)',
        [userId, address_id, totalAmount, 'pending']
      )

      const orderId = orderResult.insertId

      for (const item of items) {
        const [products] = await connection.query(
          'SELECT price FROM products WHERE id = ?',
          [item.product_id]
        )
        const price = products[0].price

        await connection.query(
          'INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)',
          [orderId, item.product_id, item.quantity, price]
        )
      }

      await connection.commit()

      res.json({
        code: 200,
        message: '订单创建成功',
        data: { order_id: orderId, total_amount: totalAmount }
      })
    } catch (error) {
      await connection.rollback()
      throw error
    } finally {
      connection.release()
    }
  } catch (error) {
    console.error('Create order error:', error)
    res.status(500).json({
      code: 500,
      message: error.message || '创建订单失败'
    })
  }
}

export async function getOrders(req, res) {
  try {
    const userId = req.userId
    const { page = 1, pageSize = 20, status } = req.query
    const offset = (page - 1) * pageSize

    let sql = 'SELECT * FROM orders WHERE user_id = ?'
    const params = [userId]

    if (status) {
      sql += ' AND status = ?'
      params.push(status)
    }

    sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.push(parseInt(pageSize), offset)

    const [orders] = await pool.query(sql, params)

    res.json({
      code: 200,
      message: 'success',
      data: orders
    })
  } catch (error) {
    console.error('Get orders error:', error)
    res.status(500).json({
      code: 500,
      message: '获取订单列表失败'
    })
  }
}

export async function getOrderDetail(req, res) {
  try {
    const userId = req.userId
    const { id } = req.params

    const [orders] = await pool.query(
      'SELECT * FROM orders WHERE id = ? AND user_id = ?',
      [id, userId]
    )

    if (orders.length === 0) {
      return res.status(404).json({
        code: 404,
        message: '订单不存在'
      })
    }

    const [items] = await pool.query(
      'SELECT oi.*, p.name, p.image FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?',
      [id]
    )

    res.json({
      code: 200,
      message: 'success',
      data: {
        ...orders[0],
        items
      }
    })
  } catch (error) {
    console.error('Get order detail error:', error)
    res.status(500).json({
      code: 500,
      message: '获取订单详情失败'
    })
  }
}
