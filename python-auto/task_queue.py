from typing import List, Dict, Optional
import threading
from db_connector import get_pending_tasks, update_task_status

class TaskQueue:
    """任务队列管理器（支持线程安全的动态添加）"""
    
    def __init__(self):
        self.tasks: List[Dict] = []
        self.current_index = 0
        self.processed_task_ids = set()  # 记录已处理的任务ID，避免重复添加
        self.lock = threading.Lock()  # 线程锁，保证线程安全
    
    def load_tasks(self) -> int:
        """
        从数据库加载待办任务到队列
        返回加载的任务数量
        """
        with self.lock:
            # fetchall() 可能返回 tuple，需要转成 list 以支持后续 append
            fetched = get_pending_tasks()
            self.tasks = list(fetched) if fetched is not None else []
            self.current_index = 0
            # 初始化已处理任务ID集合
            self.processed_task_ids = set()
            return len(self.tasks)
    
    def add_new_tasks(self) -> int:
        """
        从数据库扫描新任务并添加到队列（只添加未处理的任务）
        返回新添加的任务数量
        """
        new_tasks = get_pending_tasks()
        if not new_tasks:
            return 0
        
        with self.lock:
            added_count = 0
            for task in list(new_tasks):  # 确保可迭代为列表
                task_id = task.get('task_id', '')
                # 只添加未处理过的任务
                if task_id and task_id not in self.processed_task_ids:
                    # 检查是否已经在队列中（避免重复添加）
                    if not any(t.get('task_id') == task_id for t in self.tasks):
                        self.tasks.append(task)
                        added_count += 1
            
            if added_count > 0:
                print(f"📥 扫描到 {added_count} 个新任务，已加入队列")
            return added_count
    
    def get_next_task(self) -> Optional[Dict]:
        """
        获取下一个待办任务
        如果队列为空或已处理完所有任务，返回 None
        """
        with self.lock:
            if self.current_index >= len(self.tasks):
                return None
            
            task = self.tasks[self.current_index]
            self.current_index += 1
            # 记录已处理的任务ID
            task_id = task.get('task_id', '')
            if task_id:
                self.processed_task_ids.add(task_id)
            return task
    
    def has_more_tasks(self) -> bool:
        """检查是否还有更多任务"""
        with self.lock:
            return self.current_index < len(self.tasks)
    
    def get_current_task_number(self) -> int:
        """获取当前任务序号（从1开始）"""
        with self.lock:
            return self.current_index
    
    def get_total_tasks(self) -> int:
        """获取总任务数"""
        with self.lock:
            return len(self.tasks)
    
    def get_pending_count(self) -> int:
        """获取队列中待处理的任务数量"""
        with self.lock:
            return max(0, len(self.tasks) - self.current_index)
    
    def mark_task_processing(self, task_id: str) -> bool:
        """标记任务为处理中"""
        return update_task_status(task_id, 'processing')
    
    def mark_task_completed(self, task_id: str) -> bool:
        """标记任务为已完成（保留接口，但当前工作流不再直接使用 completed）"""
        return update_task_status(task_id, 'completed')

    def mark_task_review(self, task_id: str) -> bool:
        """标记任务为待审核"""
        return update_task_status(task_id, 'review')
    
    def mark_task_failed(self, task_id: str) -> bool:
        """标记任务为失败"""
        return update_task_status(task_id, 'failed')

