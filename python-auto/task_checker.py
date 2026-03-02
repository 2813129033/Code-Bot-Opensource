"""
任务检查器：基于 AI 生成的任务清单，逐个检查完成状态

核心流程：
1. 读取 task_tree.json（AI 生成的任务清单）
2. 找出第一个未完成的任务
3. 让 AI 检查/实现该任务
4. AI 标记完成状态
5. 循环直到所有任务完成
6. 最终检查：让 AI 做结构完整度检查
"""

import os
import json
from typing import Dict, Any, List, Optional


# 任务清单文件名，原先从 doc_state_model.py 引用，这里直接固定为统一常量
TASK_TREE_FILENAME = "task_tree.json"


def load_task_tree(project_dir: str) -> Dict[str, Any]:
    """加载任务树 JSON"""
    path = os.path.join(project_dir, TASK_TREE_FILENAME)
    if not os.path.exists(path):
        return {"modules": []}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 读取任务树失败: {e}")
        return {"modules": []}


def save_task_tree(project_dir: str, tree: Dict[str, Any]) -> bool:
    """保存任务树 JSON"""
    path = os.path.join(project_dir, TASK_TREE_FILENAME)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ 保存任务树失败: {e}")
        return False


def find_next_unfinished_task(tree: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    找出第一个未完成的任务
    
    返回格式：
    {
        "module_index": 0,
        "task_index": 1,
        "module": {...},
        "task": {...},
        "path": "modules[0].tasks[1]"
    }
    """
    modules = tree.get("modules", [])
    
    for module_idx, module in enumerate(modules):
        tasks = module.get("tasks", [])
        for task_idx, task in enumerate(tasks):
            status = task.get("status", "pending")
            if status in ("pending", "in_progress", "failed"):
                return {
                    "module_index": module_idx,
                    "task_index": task_idx,
                    "module": module,
                    "task": task,
                    "path": f"modules[{module_idx}].tasks[{task_idx}]"
                }
    
    return None


def mark_task_completed(tree: Dict[str, Any], module_index: int, task_index: int) -> bool:
    """标记任务为已完成"""
    try:
        modules = tree.get("modules", [])
        if module_index < len(modules):
            tasks = modules[module_index].get("tasks", [])
            if task_index < len(tasks):
                tasks[task_index]["status"] = "completed"
                tasks[task_index]["completed_at"] = "auto_checked"
                return True
    except Exception as e:
        print(f"❌ 标记任务完成失败: {e}")
    return False


def mark_task_failed(tree: Dict[str, Any], module_index: int, task_index: int, reason: str = "") -> bool:
    """标记任务为失败"""
    try:
        modules = tree.get("modules", [])
        if module_index < len(modules):
            tasks = modules[module_index].get("tasks", [])
            if task_index < len(tasks):
                tasks[task_index]["status"] = "failed"
                if reason:
                    tasks[task_index]["failure_reason"] = reason
                return True
    except Exception as e:
        print(f"❌ 标记任务失败状态失败: {e}")
    return False


def get_all_tasks_status(tree: Dict[str, Any]) -> Dict[str, int]:
    """获取所有任务的状态统计"""
    modules = tree.get("modules", [])
    stats = {
        "total": 0,
        "completed": 0,
        "pending": 0,
        "in_progress": 0,
        "failed": 0
    }
    
    for module in modules:
        tasks = module.get("tasks", [])
        for task in tasks:
            stats["total"] += 1
            status = task.get("status", "pending")
            if status in stats:
                stats[status] += 1
    
    return stats


def all_tasks_completed(tree: Dict[str, Any]) -> bool:
    """检查是否所有任务都已完成"""
    stats = get_all_tasks_status(tree)
    return stats["total"] > 0 and stats["completed"] == stats["total"]


def generate_task_check_prompt(task_info: Dict[str, Any], project_dir: str) -> str:
    """
    生成检查单个任务的提示词
    
    格式：
    检查任务：[模块名] - [任务名]
    任务描述：[描述]
    请检查这个任务是否已经在代码中完整实现。如果已完成，请在 task_tree.json 中将该任务的 status 字段改为 "completed"。
    如果未完成，请立即实现这个任务，实现完成后标记为 completed。
    """
    module = task_info.get("module", {})
    task = task_info.get("task", {})
    
    module_name = module.get("name", "未知模块")
    task_name = task.get("name", "未知任务")
    task_desc = task.get("description", "")
    task_type = task.get("type", "")
    
    prompt = f"""检查并完成以下任务：

**模块：** {module_name}
**任务：** {task_name}
**类型：** {task_type}
**描述：** {task_desc}

**要求：**
1. 首先检查这个任务是否已经在代码中完整实现
2. 如果已完成，请打开 task_tree.json 文件，找到对应的任务（路径：{task_info.get('path', '')}），将 status 字段改为 "completed"
3. 如果未完成或实现不完整，请立即实现这个任务，实现完成后同样标记为 completed
4. 禁止使用 TODO/FIXME/占位符，必须实现完整功能

**重要：** 完成或检查后，必须修改 task_tree.json 文件中的 status 字段，否则系统无法识别任务已完成。"""
    
    return prompt


def generate_final_check_prompt(project_dir: str) -> str:
    """生成最终检查的提示词"""
    prompt = f"""你现在是结构完整度检查专家。

**任务：** 检查 task_tree.json 文件中的所有模块和任务，对照当前项目的代码实现，确保每个任务都真正完成了。

**检查步骤：**
1. 打开 task_tree.json 文件，查看所有模块和任务
2. 对照代码，检查每个任务的实现情况
3. 如果发现代码中没有实现或实现不完整的地方，在 task_tree.json 中将对应任务的 status 改为 "pending" 或 "failed"，并为该任务新增或更新字段 "final_check_notes"，用简洁明确的中文一句话说明“具体少了什么 / 哪一部分实现不完整”（例如：\"接口 /api/users/login 只有路由没有参数校验和数据库查询\"）
4. 如果某个任务经过你检查后确认已经完全实现，请保持 status 为 "completed"，并将该任务的 "final_check_notes" 字段清空或设置为 ""（空字符串），表示最终检查未发现问题
5. 在 task_tree.json 顶层增加或更新字段 "final_check_count"：如果不存在则创建并置为 1；如果已存在则在原有数值基础上加 1（例如从 0 加到 1）

**检查重点：**
- 接口是否有实际的路由和处理逻辑（不能只是空函数）
- 页面是否有实际的文件和内容（不能只是占位符）
- 数据库表是否有建表语句或迁移文件
- 功能是否完整可用（不能有 TODO/FIXME）

**完成后：** 保存 task_tree.json 文件。

**特别要求：**
- 一定要执行第 5 步，正确维护顶层的 "final_check_count" 字段，避免遗漏。
- 在为任务写入 "final_check_notes" 时，务必写清楚是哪一个接口/页面/功能点不完整，便于后续精确修复；已经确认完整的任务请将该字段留空。"""
    
    return prompt
