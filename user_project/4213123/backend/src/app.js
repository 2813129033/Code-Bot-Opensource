import express from 'express'
import cors from 'cors'
import { createServer } from 'http'
import { initDB } from './config/database.js'
import { initRedis } from './config/redis.js'
import logger from './utils/logger.js'
import routes from './routes/index.js'
import errorHandler from './middleware/errorHandler.js'

const app = express()
const server = createServer(app)

app.use(cors())
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

app.use('/api', routes)

app.use(errorHandler)

app.use((req, res) => {
  res.status(404).json({
    code: 404,
    message: '接口不存在'
  })
})

const PORT = process.env.PORT || 3000

async function start() {
  try {
    await initDB()
    await initRedis()
    
    server.listen(PORT, () => {
      logger.info(`Server running on port ${PORT}`)
    })
  } catch (error) {
    logger.error('Failed to start server:', error)
    process.exit(1)
  }
}

start()

process.on('SIGINT', () => {
  logger.info('Shutting down gracefully...')
  server.close(() => {
    process.exit(0)
  })
})
