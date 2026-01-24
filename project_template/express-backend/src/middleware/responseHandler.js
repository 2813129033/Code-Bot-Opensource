// 统一响应处理中间件
const responseHandler = (req, res, next) => {
  // 成功响应
  res.success = (data, message = '操作成功', statusCode = 200) => {
    res.status(statusCode).json({
      success: true,
      message,
      data,
      timestamp: new Date().toISOString()
    });
  };

  // 错误响应
  res.error = (message = '操作失败', statusCode = 400, code = null) => {
    res.status(statusCode).json({
      success: false,
      message,
      code: code || `ERROR_${statusCode}`,
      timestamp: new Date().toISOString()
    });
  };

  // 分页响应
  res.paginated = (data, pagination, message = '获取成功') => {
    res.json({
      success: true,
      message,
      data,
      pagination: {
        currentPage: pagination.currentPage || 1,
        totalPages: pagination.totalPages || 1,
        totalItems: pagination.totalItems || 0,
        itemsPerPage: pagination.itemsPerPage || 10,
        hasNext: pagination.hasNext || false,
        hasPrev: pagination.hasPrev || false
      },
      timestamp: new Date().toISOString()
    });
  };

  next();
};

module.exports = responseHandler;