// config/config.js
const appConfig = {
	port: 3000,
	env: 'development'
  };
  
  const dbConfig = {
	host: '127.0.0.1',
	port: 3306,
	user: 'root',
	password: 'root',
	database: 'cursorbot',
	waitForConnections: true,
	connectionLimit: 10,
	queueLimit: 0,
	charset: 'utf8mb4'
  };
  
  const redisConfig = {
	host: '127.0.0.1',
	port: 6379,
	password: 'root', // 通常不需要 username，Redis 6.x 以后才引入 ACL 用户
	db: 0
  };

  // Coze 对话流配置
  const cozeConfig = {
	access_token: 'testtoken',
	base_url: 'https://api.coze.cn',
	workflow_id: '7560718083158065178' // 对话流 ID
  };

  // NapCat/OneBot HTTP API 配置
  const onebotConfig = {
	// 根据 self_id 映射到对应的端口
	urls: {
	  '2543404224': 'http://127.0.0.1:5700',
	  '2370463692': 'http://127.0.0.1:5701'
	},
	// 默认端口
	defaultUrl: 'http://127.0.0.1:5700'
  };

  // 压缩包查找路径配置（按优先级从高到低）
  const zipSearchPaths = [
	// 主要路径：Python 自动化脚本输出的压缩包目录（项目根目录下）
	'C:\\AI-project\\cursor_bot\\user_project_zip',
	// 备用路径：桌面 test 目录（兼容旧流程/手动测试）
	'C:\\AI-project\\cursor_bot\\user_project_zip',
	// 可以添加更多备用路径，例如：
	// 'D:\\projects\\output',
  ];
  
  module.exports = {
	appConfig,
	dbConfig,
	redisConfig,
	cozeConfig,
	onebotConfig,
	zipSearchPaths
  };
  