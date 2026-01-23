import pymysql
from typing import List, Dict, Optional

# 数据库配置（与 sever/config/config.js 保持一致）
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'cursorbot',
    'charset': 'utf8mb4'
}

def get_pending_tasks() -> List[Dict]:
    """
    从数据库获取所有待处理任务，按优先级与创建时间排序
    返回任务列表
    """
    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG)
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
            connection.close()

def update_task_status(task_id: str, status: str) -> bool:
    """
    更新任务状态
    status: 'pending', 'processing', 'review', 'user_change', 'review_change', 'ready_to_send', 'sent', 'failed'
    """
    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            sql = "UPDATE user_task SET task_status = %s, updated_at = NOW() WHERE task_id = %s"
            cursor.execute(sql, (status, task_id))
            connection.commit()
            print(f"✅ 任务 {task_id} 状态已更新为: {status}")
            return True
    except Exception as e:
        print(f"❌ 更新任务状态失败: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if connection:
            connection.close()

