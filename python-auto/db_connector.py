import pymysql
from typing import List, Dict, Optional
import threading
import time

# 数据库配置（与 sever/config/config.js 保持一致）
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'cursorbot',
    'charset': 'utf8mb4',
    'connect_timeout': 10,  # 连接超时
    'read_timeout': 30,  # 读取超时
    'write_timeout': 30,  # 写入超时
    'autocommit': False,  # 手动提交事务
}

# 连接池配置
_pool = None
_pool_lock = threading.Lock()
_MAX_RETRIES = 3  # 最大重试次数
_RETRY_DELAY = 1  # 重试延迟（秒）

def _get_connection():
    """
    获取数据库连接（带重试机制）
    """
    for attempt in range(_MAX_RETRIES):
        try:
            connection = pymysql.connect(**DB_CONFIG)
            # 测试连接是否有效
            connection.ping(reconnect=True)
            return connection
        except Exception as e:
            if attempt < _MAX_RETRIES - 1:
                print(f"⚠️  数据库连接失败（尝试 {attempt + 1}/{_MAX_RETRIES}）: {e}，{_RETRY_DELAY}秒后重试...")
                time.sleep(_RETRY_DELAY)
            else:
                print(f"❌ 数据库连接失败（已重试 {_MAX_RETRIES} 次）: {e}")
                raise
    return None

def get_pending_tasks() -> List[Dict]:
    """
    从数据库获取所有待处理任务，按优先级与创建时间排序
    返回任务列表
    """
    connection = None
    try:
        connection = _get_connection()
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # 优先级：pending_modify > user_change > review_change > pending
            sql = """
                SELECT 
                    id, 
                    create_time, 
                    user_id, 
                    task_id, 
                    task_description, 
                    task_status, 
                    task_technology, 
                    task_type,
                    review_notes,
                    user_change_request
                FROM user_task 
                WHERE task_status IN ('pending', 'user_change', 'review_change', 'pending_modify')
                ORDER BY 
                  CASE task_status
                    WHEN 'pending_modify' THEN 1
                    WHEN 'user_change' THEN 2
                    WHEN 'review_change' THEN 3
                    WHEN 'pending' THEN 4
                    ELSE 9
                  END,
                  create_time ASC
            """
            cursor.execute(sql)
            tasks = cursor.fetchall()
            print(f"✅ 查询到 {len(tasks)} 个待处理任务（user_change/review_change/pending）")
            return tasks
    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")
        return []
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass  # 忽略关闭连接时的异常

def update_task_status(task_id: str, status: str) -> bool:
    """
    更新任务状态
    status: 'pending', 'processing', 'review', 'user_change', 'review_change', 'ready_to_send', 'sent', 'failed'
    """
    connection = None
    try:
        connection = _get_connection()
        with connection.cursor() as cursor:
            sql = "UPDATE user_task SET task_status = %s, updated_at = NOW() WHERE task_id = %s"
            cursor.execute(sql, (status, task_id))
            connection.commit()
            print(f"✅ 任务 {task_id} 状态已更新为: {status}")
            return True
    except Exception as e:
        print(f"❌ 更新任务状态失败: {e}")
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass  # 忽略回滚时的异常
        return False
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass  # 忽略关闭连接时的异常

