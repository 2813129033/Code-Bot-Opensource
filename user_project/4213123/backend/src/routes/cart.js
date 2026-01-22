import express from 'express'
import { addToCart, getCart, updateCartItem, removeFromCart } from '../controllers/cartController.js'
import { authenticate } from '../middleware/auth.js'

const router = express.Router()

router.use(authenticate)

router.post('/', addToCart)
router.get('/', getCart)
router.put('/:id', updateCartItem)
router.delete('/:id', removeFromCart)

export default router
