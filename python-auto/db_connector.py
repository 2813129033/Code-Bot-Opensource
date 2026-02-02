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
    'read_timeout': 30,  # 读取超时
    'write_timeout': 30,  # 写入超时
    'autocommit': False,  # 手动提交事务
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
                print(f"⚠️  获取数据库连接失败（尝试 {attempt + 1}/{_MAX_RETRIES}）: {e}，{_RETRY_DELAY}秒后重试...")
                time.sleep(_RETRY_DELAY)
            else:
                print(f"❌ 获取数据库连接失败（已重试 {_MAX_RETRIES} 次）: {e}")
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
    print(f"✅ 连接池已清理，关闭了 {closed_count} 个连接")

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
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # 优先级：pending_modify > user_change > review_change > pending
            # 尝试查询 retry_count 字段，如果不存在则使用 0
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
            print(f"✅ 查询到 {len(tasks)} 个待处理任务（user_change/review_change/pending）")
            return tasks
    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")
        return []
    finally:
        if connection:
            _return_connection_to_pool(connection)

def update_task_status(task_id: str, status: str, retry_count: int = None, error_message: str = None) -> bool:
    """
    更新任务状态
    status: 'pending', 'processing', 'review', 'user_change', 'review_change', 'ready_to_send', 'sent', 'failed'
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
            print(f"✅ 任务 {task_id} 状态已更新为: {status}" + (f", 重试次数: {retry_count}" if retry_count is not None else ""))
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
            _return_connection_to_pool(connection)

