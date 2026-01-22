export default function errorHandler(err, req, res, next) {
  console.error('Error:', err)

  if (err.name === 'ValidationError') {
    return res.status(400).json({
      code: 400,
      message: '参数验证失败',
      errors: err.errors
    })
  }

  if (err.name === 'UnauthorizedError') {
    return res.status(401).json({
      code: 401,
      message: '未授权'
    })
  }

  res.status(500).json({
    code: 500,
    message: err.message || '服务器内部错误'
  })
}
