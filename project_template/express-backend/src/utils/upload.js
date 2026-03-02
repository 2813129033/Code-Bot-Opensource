const multer = require('multer');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const UPLOAD_ROOT = path.join(process.cwd(), 'uploads');
const IMAGE_UPLOAD_DIR = path.join(UPLOAD_ROOT, 'images');
const VIDEO_UPLOAD_DIR = path.join(UPLOAD_ROOT, 'videos');

const ensureDir = (dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
};

const safeExt = (originalname) => {
  const ext = path.extname(originalname || '').toLowerCase();
  return ext && ext.length <= 10 ? ext : '';
};

const randomName = (originalname) => {
  const id = crypto.randomBytes(16).toString('hex');
  return `${Date.now()}-${id}${safeExt(originalname)}`;
};

const createStorage = (baseDir) =>
  multer.diskStorage({
    destination: (req, file, cb) => {
      ensureDir(baseDir);
      cb(null, baseDir);
    },
    filename: (req, file, cb) => {
      cb(null, randomName(file.originalname));
    }
  });

const imageFileFilter = (req, file, cb) => {
  if (file.mimetype && file.mimetype.startsWith('image/')) {
    return cb(null, true);
  }
  return cb(new Error('只允许上传图片文件'), false);
};

const videoFileFilter = (req, file, cb) => {
  const allowed = new Set([
    'video/mp4',
    'video/webm',
    'video/quicktime', // mov
    'video/x-matroska' // mkv
  ]);
  if (allowed.has(file.mimetype)) {
    return cb(null, true);
  }
  return cb(new Error('只允许上传视频文件（mp4/webm/mov/mkv）'), false);
};

/**
 * 图片上传（单文件）
 * - field 默认 image
 * - 最大 5MB
 */
const imageUploadSingle = (field = 'image') =>
  multer({
    storage: createStorage(IMAGE_UPLOAD_DIR),
    fileFilter: imageFileFilter,
    limits: {
      fileSize: 5 * 1024 * 1024
    }
  }).single(field);

/**
 * 视频上传（单文件）
 * - field 默认 video
 * - 最大 200MB
 */
const videoUploadSingle = (field = 'video') =>
  multer({
    storage: createStorage(VIDEO_UPLOAD_DIR),
    fileFilter: videoFileFilter,
    limits: {
      fileSize: 200 * 1024 * 1024
    }
  }).single(field);

module.exports = {
  UPLOAD_ROOT,
  IMAGE_UPLOAD_DIR,
  VIDEO_UPLOAD_DIR,
  imageUploadSingle,
  videoUploadSingle
};

