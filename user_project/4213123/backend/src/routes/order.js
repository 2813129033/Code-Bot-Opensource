import express from 'express'
import { createOrder, getOrders, getOrderDetail } from '../controllers/orderController.js'
import { authenticate } from '../middleware/auth.js'

const router = express.Router()

router.use(authenticate)

router.post('/', createOrder)
router.get('/', getOrders)
router.get('/:id', getOrderDetail)

export default router
