import pymysql
from typing import List, Dict, Optional
import threading
import time
from queue import Queue, Empty
import atexit

# 数据库配置（与 sever/config/config.js 保持一致）
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'cursorbot',
    'charset': 'utf8mb4',
    'connect_timeout': 10,  # 连接超时
    'read_timeout': 30,     # 读取超时
    'write_timeout': 30,    # 写入超时
    # ✅ 关键修改：开启自动提交，避免长事务导致“看不到新插入的任务”
    # 在 MySQL 的 REPEATABLE-READ 模式下，如果 autocommit=False 且一直复用同一个连接，
    # 那么所有 SELECT 都会在同一个事务快照里，看不到其它会话之后插入的新行。
    # 对于这个任务队列场景，我们不需要跨多条语句的事务，一条语句一提交最合适。
    'autocommit': True,
}

# 连接池配置
_MAX_RETRIES = 3  # 最大重试次数
_RETRY_DELAY = 1  # 重试延迟（秒）
_POOL_SIZE = 5  # 连接池大小
_POOL_TIMEOUT = 10  # 获取连接超时时间（秒）
_MAX_IDLE_TIME = 300  # 连接最大空闲时间（秒），超过此时间会关闭连接

# 连接池：使用 Queue 实现线程安全的连接池
_connection_pool = Queue(maxsize=_POOL_SIZE)
_created_connections = 0  # 已创建的连接数
_pool_lock = threading.Lock()  # 连接池锁

def _create_connection():
    """
    创建新的数据库连接
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        connection.ping(reconnect=True)
        return connection
    except Exception as e:
        print(f"❌ 创建数据库连接失败: {e}")
        raise

def _get_connection_from_pool():
    """
    从连接池获取连接（带重试机制和连接健康检查）
    """
    global _created_connections
    
    # 尝试从池中获取连接（非阻塞，立即返回）
    try:
        connection = _connection_pool.get_nowait()
        # 检查连接是否有效
        try:
            connection.ping(reconnect=False)
            return connection
        except:
            # 连接无效，关闭并创建新连接
            try:
                connection.close()
            except:
                pass
            with _pool_lock:
                _created_connections = max(0, _created_connections - 1)
            connection = _create_connection()
            return connection
    except Empty:
        # 池中没有可用连接，创建新连接
        with _pool_lock:
            if _created_connections < _POOL_SIZE:
                _created_connections += 1
                return _create_connection()
            else:
                # 连接池已满，创建临时连接（不计数）
                return _create_connection()

def _return_connection_to_pool(connection):
    """
    将连接返回到连接池
    """
    global _created_connections
    
    if connection:
        try:
            # 检查连接是否有效
            connection.ping(reconnect=False)
            # 尝试放回池中，如果池已满则关闭连接
            try:
                _connection_pool.put_nowait(connection)
            except:
                # 池已满，关闭连接
                connection.close()
                with _pool_lock:
                    _created_connections = max(0, _created_connections - 1)
        except:
            # 连接无效，直接关闭
            try:
                connection.close()
            except:
                pass
            with _pool_lock:
                _created_connections = max(0, _created_connections - 1)

def _get_connection():
    """
    获取数据库连接（使用连接池）
    """
    for attempt in range(_MAX_RETRIES):
        try:
            return _get_connection_from_pool()
        except Exception as e:
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY)
            else:
                print(f"[ERROR] 获取数据库连接失败（已重试 {_MAX_RETRIES} 次）: {e}")
                raise
    return None

def cleanup_connection_pool():
    """
    清理连接池，关闭所有连接
    """
    global _created_connections
    closed_count = 0
    while not _connection_pool.empty():
        try:
            connection = _connection_pool.get_nowait()
            try:
                connection.close()
                closed_count += 1
            except:
                pass
        except Empty:
            break
    with _pool_lock:
        _created_connections = 0

# 注册退出时清理连接池
atexit.register(cleanup_connection_pool)

def get_pending_tasks() -> List[Dict]:
    """
    从数据库获取所有待处理任务，按优先级与创建时间排序
    返回任务列表
    """
    connection = None
    try:
        connection = _get_connection()
        if not connection:
            print("[ERROR] 无法获取数据库连接")
            return []
            
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
                    user_change_request,
                    COALESCE(retry_count, 0) as retry_count
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
            return tasks if tasks else []
    except Exception as e:
        print(f"[ERROR] 数据库查询失败: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if connection:
            _return_connection_to_pool(connection)

def update_task_status(task_id: str, status: str, retry_count: int = None, error_message: str = None) -> bool:
    """
    更新任务状态
    status: 
      - 基础流转：'pending', 'processing', 'review', 'user_change', 'review_change', 'ready_to_send', 'sent', 'failed'
      - 自检扩展：'implementing', 'self_check_failed', 'waiting_for_fix'
    retry_count: 重试次数（可选）
    error_message: 错误信息（可选，用于记录失败原因）
    """
    connection = None
    try:
        connection = _get_connection()
        with connection.cursor() as cursor:
            if retry_count is not None:
                # 更新状态和重试次数
                sql = "UPDATE user_task SET task_status = %s, retry_count = %s, updated_at = NOW() WHERE task_id = %s"
                cursor.execute(sql, (status, retry_count, task_id))
            else:
                # 只更新状态
                sql = "UPDATE user_task SET task_status = %s, updated_at = NOW() WHERE task_id = %s"
                cursor.execute(sql, (status, task_id))
            
            # 如果有错误信息，记录到备注字段（如果数据库有相关字段）
            if error_message:
                try:
                    # 尝试更新备注字段（如果存在）
                    update_error_sql = "UPDATE user_task SET error_message = %s WHERE task_id = %s"
                    cursor.execute(update_error_sql, (error_message[:500], task_id))  # 限制长度
                except:
                    pass  # 如果字段不存在，忽略
            
            connection.commit()
            return True
    except Exception as e:
        print(f"[ERROR] 更新任务状态失败: {e}")
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass  # 忽略回滚时的异常
        return False
    finally:
        if connection:
            _return_connection_to_pool(connection)

