const { initDB } = require('../config/mysql');

// 用户状态管理（内存存储）
// key: userId, value: { step, taskId, taskType, taskTechnology, taskDescription }
const userStates = new Map();

// 任务录入步骤
const STEPS = {
  IDLE: 'idle',           // 空闲状态
  WAIT_TYPE: 'wait_type', // 等待选择项目类型
  WAIT_TECH: 'wait_tech', // 等待输入技术选型
  WAIT_DESC: 'wait_desc'  // 等待输入功能描述
};

/**
 * 生成12位随机数字字符串
 */
function generateTaskId() {
  return Math.floor(100000000000 + Math.random() * 900000000000).toString();
}

/**
 * 标准化用户ID为字符串（确保与VARCHAR类型兼容）
 */
function normalizeUserId(userId) {
  return String(userId || '');
}

/**
 * 获取用户当前状态
 */
function getUserState(userId) {
  const normalizedId = normalizeUserId(userId);
  return userStates.get(normalizedId) || { step: STEPS.IDLE };
}

/**
 * 设置用户状态
 */
function setUserState(userId, state) {
  const normalizedId = normalizeUserId(userId);
  userStates.set(normalizedId, { ...getUserState(normalizedId), ...state });
}

/**
 * 清除用户状态
 */
function clearUserState(userId) {
  const normalizedId = normalizeUserId(userId);
  userStates.delete(normalizedId);
}

/**
 * 开始任务录入
 */
function startTask(userId) {
  const taskId = generateTaskId();
  setUserState(userId, {
    step: STEPS.WAIT_TYPE,
    taskId,
    taskType: null,
    taskTechnology: null,
    taskDescription: null
  });
  return taskId;
}

/**
 * 处理项目类型选择
 */
function handleTypeSelection(userId, message) {
  const state = getUserState(userId);
  if (state.step !== STEPS.WAIT_TYPE) {
    return { success: false, error: '当前不在选择项目类型阶段' };
  }

  const typeMap = {
    '1': 'H5开发',
    '2': 'APP开发'
  };

  const selectedType = typeMap[message.trim()];
  if (!selectedType) {
    return { success: false, error: '请选择 1 或 2' };
  }

  setUserState(userId, {
    step: STEPS.WAIT_TECH,
    taskType: selectedType
  });

  return { success: true, nextStep: STEPS.WAIT_TECH };
}

/**
 * 处理技术选型输入
 */
function handleTechSelection(userId, message) {
  const state = getUserState(userId);
  if (state.step !== STEPS.WAIT_TECH) {
    return { success: false, error: '当前不在输入技术选型阶段' };
  }

  setUserState(userId, {
    step: STEPS.WAIT_DESC,
    taskTechnology: message.trim()
  });

  return { success: true, nextStep: STEPS.WAIT_DESC };
}

/**
 * 处理功能描述输入
 */
function handleDescription(userId, message) {
  const state = getUserState(userId);
  if (state.step !== STEPS.WAIT_DESC) {
    return { success: false, error: '当前不在输入功能描述阶段' };
  }

  setUserState(userId, {
    taskDescription: message.trim()
  });

  return { success: true, state: getUserState(userId) };
}

/**
 * 保存任务到数据库
 */
async function saveTaskToDB(userId, taskData) {
  try {
    const db = await initDB();
    // 确保 user_id 作为字符串存储（与 VARCHAR 类型兼容）
    const normalizedUserId = normalizeUserId(userId);
    const [result] = await db.execute(
      `INSERT INTO user_task 
       (create_time, user_id, task_id, task_description, task_status, task_technology, task_type) 
       VALUES (NOW(), ?, ?, ?, 'pending', ?, ?)`,
      [
        normalizedUserId,
        taskData.taskId,
        taskData.taskDescription,
        taskData.taskTechnology,
        taskData.taskType
      ]
    );
    return { success: true, insertId: result.insertId };
  } catch (err) {
    console.error('[taskService][saveTaskToDB]', err);
    return { success: false, error: err.message };
  }
}

/**
 * 完成任务录入并保存
 */
async function completeTask(userId) {
  const state = getUserState(userId);
  if (!state.taskId || !state.taskType || !state.taskTechnology || !state.taskDescription) {
    return { success: false, error: '任务信息不完整' };
  }

  const saveResult = await saveTaskToDB(userId, state);
  if (!saveResult.success) {
    return saveResult;
  }

  clearUserState(userId);
  return { success: true, taskId: state.taskId };
}

/**
 * 查询用户已发送的任务（可以修改的项目）
 */
async function getUserSentTasks(userId) {
  try {
    const db = await initDB();
    const normalizedUserId = normalizeUserId(userId);
    const [tasks] = await db.execute(
      `SELECT task_id, task_type, task_technology, task_description, create_time
       FROM user_task 
       WHERE user_id = ? AND task_status = 'sent'
       ORDER BY create_time DESC
       LIMIT 10`,
      [normalizedUserId]
    );
    return tasks;
  } catch (err) {
    console.error('[taskService][getUserSentTasks]', err);
    return [];
  }
}

/**
 * 保存用户修改需求
 */
async function saveModifyRequest(userId, taskId, modifyRequest) {
  try {
    const db = await initDB();
    const normalizedUserId = normalizeUserId(userId);
    const [result] = await db.execute(
      `UPDATE user_task 
       SET task_status = 'pending_modify', 
           user_change_request = ?,
           updated_at = NOW(),
           updated_by = ?
       WHERE user_id = ? AND task_id = ? AND task_status = 'sent'`,
      [modifyRequest, 'user', normalizedUserId, taskId]
    );
    
    if (result.affectedRows === 0) {
      return { success: false, error: '任务不存在或状态不正确' };
    }
    
    return { success: true, taskId };
  } catch (err) {
    console.error('[taskService][saveModifyRequest]', err);
    return { success: false, error: err.message };
  }
}

module.exports = {
  STEPS,
  getUserState,
  setUserState,
  clearUserState,
  startTask,
  handleTypeSelection,
  handleTechSelection,
  handleDescription,
  completeTask,
  getUserSentTasks,
  saveModifyRequest
};

