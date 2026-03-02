const express = require('express');
const path = require('path');
const router = express.Router();

const { imageUploadSingle, videoUploadSingle } = require('../utils/upload');

// 统一处理 multer 错误（大小超限/类型不对等）
const runUpload = (uploadMiddleware) => (req, res, next) => {
  uploadMiddleware(req, res, (err) => {
    if (err) {
      // Multer 的错误会带 code，如 LIMIT_FILE_SIZE
      const message =
        err.code === 'LIMIT_FILE_SIZE' ? '文件过大' : (err.message || '上传失败');
      return res.error(message, 400, err.code || 'UPLOAD_ERROR');
    }
    next();
  });
};

/**
 * 图片上传
 * POST /api/upload/image
 * form-data: image=<file>
 */
router.post('/image', runUpload(imageUploadSingle('image')), (req, res) => {
  if (!req.file) {
    return res.error('未收到图片文件', 400, 'NO_FILE');
  }

  res.success(
    {
      filename: req.file.filename,
      mimetype: req.file.mimetype,
      size: req.file.size,
      // 静态访问路径（配合 app.js 的 /uploads）
      url: `/uploads/images/${req.file.filename}`,
      // 服务器本地路径（可选）
      path: path.normalize(req.file.path)
    },
    '图片上传成功',
    201
  );
});

/**
 * 视频上传
 * POST /api/upload/video
 * form-data: video=<file>
 */
router.post('/video', runUpload(videoUploadSingle('video')), (req, res) => {
  if (!req.file) {
    return res.error('未收到视频文件', 400, 'NO_FILE');
  }

  res.success(
    {
      filename: req.file.filename,
      mimetype: req.file.mimetype,
      size: req.file.size,
      url: `/uploads/videos/${req.file.filename}`,
      path: path.normalize(req.file.path)
    },
    '视频上传成功',
    201
  );
});

module.exports = router;

