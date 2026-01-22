import express from 'express'
import { getProducts, getProductDetail, searchProducts } from '../controllers/productController.js'

const router = express.Router()

router.get('/', getProducts)
router.get('/search', searchProducts)
router.get('/:id', getProductDetail)

export default router
