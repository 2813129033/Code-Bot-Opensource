import express from 'express'
import { register, login, getUserInfo } from '../controllers/userController.js'
import { authenticate } from '../middleware/auth.js'

const router = express.Router()

router.post('/register', register)
router.post('/login', login)
router.get('/info', authenticate, getUserInfo)

export default router
