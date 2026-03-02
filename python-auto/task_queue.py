from typing import List, Dict, Optional
import threading
from db_connector import get_pending_tasks, update_task_status

class TaskQueue:
    """任务队列管理器（支持线程安全的动态添加）"""
    
    def __init__(self, max_processed_ids: int = 1000):
        """
        初始化任务队列
        :param max_processed_ids: 最大保留的已处理任务ID数量，超过此数量会清理最旧的记录
        """
        self.tasks: List[Dict] = []
        self.current_index = 0
        self.processed_task_ids = set()  # 记录已处理的任务ID，避免重复添加
        self.processed_task_ids_list = []  # 用于记录添加顺序，实现FIFO清理
        self.max_processed_ids = max_processed_ids  # 最大保留数量
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
            # 保留已处理任务ID集合（不清空），但清理过大的集合
            self._cleanup_processed_ids_if_needed()
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
            
            return added_count
    
    def top_up_tasks(self, max_total: int = 10) -> int:
        """
        从数据库补充任务到队列
        目标：让「待处理任务数量」最多达到 max_total，多余的不再加入。
        - 如果当前待处理任务 >= max_total，则不做任何事。
        - 否则从数据库获取待处理任务，按需补充，避免重复和已处理过的任务。
        """
        # 先在锁内读一遍当前待处理数量
        with self.lock:
            pending = max(0, len(self.tasks) - self.current_index)
        if pending >= max_total:
            return 0

        # 查询数据库中的待处理任务
        new_tasks = get_pending_tasks()
        if not new_tasks:
            return 0

        with self.lock:
            # 再次计算，避免这段时间队列发生变化
            pending = max(0, len(self.tasks) - self.current_index)
            need = max_total - pending
            if need <= 0:
                return 0

            added_count = 0
            for task in list(new_tasks):
                task_id = task.get('task_id', '')
                if not task_id:
                    continue
                # 跳过已处理过的任务
                if task_id in self.processed_task_ids:
                    continue
                # 跳过已经在队列中的任务，避免重复
                if any(t.get('task_id') == task_id for t in self.tasks):
                    continue

                self.tasks.append(task)
                added_count += 1

                if added_count >= need:
                    break

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
                self._add_processed_task_id(task_id)
            return task
    
    def _add_processed_task_id(self, task_id: str) -> None:
        """
        添加已处理的任务ID，如果超过最大数量则清理最旧的记录
        """
        if task_id not in self.processed_task_ids:
            self.processed_task_ids.add(task_id)
            self.processed_task_ids_list.append(task_id)
            # 如果超过最大数量，清理最旧的记录
            if len(self.processed_task_ids) > self.max_processed_ids:
                # 移除最旧的20%的记录
                remove_count = max(1, self.max_processed_ids // 5)
                for _ in range(remove_count):
                    if self.processed_task_ids_list:
                        old_id = self.processed_task_ids_list.pop(0)
                        self.processed_task_ids.discard(old_id)
    
    def _cleanup_processed_ids_if_needed(self) -> None:
        """
        如果已处理任务ID集合过大，清理最旧的部分
        """
        if len(self.processed_task_ids) > self.max_processed_ids:
            # 移除最旧的记录，保留最新的 max_processed_ids 个
            remove_count = len(self.processed_task_ids) - self.max_processed_ids
            for _ in range(remove_count):
                if self.processed_task_ids_list:
                    old_id = self.processed_task_ids_list.pop(0)
                    self.processed_task_ids.discard(old_id)
    
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

    def mark_task_implementing(self, task_id: str) -> bool:
        """标记任务为代码实现中（GUI 自动化正在写代码）"""
        return update_task_status(task_id, 'implementing')

    def mark_task_completed(self, task_id: str) -> bool:
        """标记任务为已完成（保留接口，但当前工作流不再直接使用 completed）"""
        return update_task_status(task_id, 'completed')

    def mark_task_review(self, task_id: str) -> bool:
        """标记任务为待审核"""
        return update_task_status(task_id, 'review')
    
    def mark_task_failed(self, task_id: str, error_message: str = None) -> bool:
        """标记任务为失败"""
        return update_task_status(task_id, 'failed', error_message=error_message)

    def mark_task_self_check_failed(self, task_id: str, error_message: str = None) -> bool:
        """标记任务为自检未通过（会记录失败原因，自检可多轮进行）"""
        return update_task_status(task_id, 'self_check_failed', error_message=error_message)

    def mark_task_waiting_for_fix(self, task_id: str, error_message: str = None) -> bool:
        """标记任务为等待后续人工/AI 修复（不再依赖《未完成模块汇总》这种静态自检文档）"""
        return update_task_status(task_id, 'waiting_for_fix', error_message=error_message)
    
    def mark_task_retry(self, task_id: str, retry_count: int, error_message: str = None) -> bool:
        """标记任务需要重试，更新重试次数并重置状态为 pending"""
        return update_task_status(task_id, 'pending', retry_count=retry_count, error_message=error_message)

