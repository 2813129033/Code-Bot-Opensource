import express from 'express'
import productRoutes from './product.js'
import userRoutes from './user.js'
import orderRoutes from './order.js'
import cartRoutes from './cart.js'

const router = express.Router()

router.use('/products', productRoutes)
router.use('/users', userRoutes)
router.use('/orders', orderRoutes)
router.use('/cart', cartRoutes)

router.get('/health', (req, res) => {
  res.json({
    code: 200,
    message: 'success',
    data: { status: 'ok' }
  })
})

export default router
