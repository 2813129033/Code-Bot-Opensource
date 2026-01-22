import { createClient } from 'redis'

let client

export async function initRedis() {
  client = createClient({
    url: `redis://${process.env.REDIS_HOST || '127.0.0.1'}:${process.env.REDIS_PORT || 6379}`
  })

  client.on('error', (err) => console.error('Redis Client Error:', err))

  await client.connect()
  console.log('✅ Redis connected')
  return client
}

export function getClient() {
  return client
}
