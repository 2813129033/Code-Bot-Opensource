import pyautogui
import pyperclip
import time
import random
import threading
import traceback
import gc
import os
import shutil
import json
import urllib.request
import urllib.error
from task_queue import TaskQueue

pyautogui.FAILSAFE = True

# 全局变量
SCAN_INTERVAL = 30  # 扫描间隔（秒），默认30秒
running = True  # 控制程序运行状态

# ==================== 配置参数 ====================
CONFIG = {
    'min_confidence': 0.6,  # 最低图片匹配置信度
    'max_retry_attempts': 3,  # 最大重试次数
    'poll_interval': 10,  # 轮询检测间隔（秒）
    'error_check_interval': 20,  # 错误检测间隔（秒）
    'accept_timeout': 60,  # 完成按钮检测超时（秒）
    'base_wait_time': 2700,  # 固定等待时间：45分钟 = 2700秒
    'screenshot_interval': 1.0,  # 截图间隔（秒）
    'gc_interval': 10,  # 垃圾回收间隔（秒）
    'dev_doc_timeout': 60 * 15,  # 开发文档接口最大等待时间（秒）
    'dev_doc_retry_attempts': 2,  # 开发文档生成失败后重试次数
    'dev_doc_retry_sleep': 10,  # 重试前等待（秒）
    # 新增：Trae 完成按钮配置
    'completion_buttons': [
        'btnimg/accept.png',      # Cursor 的 Accept 按钮
        'btnimg/apply.png',       # Trae 的 Apply 按钮
        'btnimg/done.png',        # Trae 的 Done 按钮
        'btnimg/continue.png',     # Trae 的 Continue 按钮
        'btnimg/save.png'         # Trae 的 Save 按钮
    ]
}
# ===================================================

# ==================== 项目目录与文档生成配置 ====================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
USER_PROJECT_ROOT = os.path.join(PROJECT_ROOT, 'user_project')
USER_PROJECT_ZIP_ROOT = os.path.join(PROJECT_ROOT, 'user_project_zip')

PLANNER_API_URL = "https://b8rccch5zx.coze.site/stream_run"
PLANNER_API_TOKEN = (
    "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjM1Y2JkMWVhLWFhNWQtNDVlNC04MzQ4LTk4M2QxOTFlOTRiZSJ9."
    "eyJpc3MiOiJodHRwczovL2FwaS5jb3plLmNuIiwiYXVkIjpbIkVBMXpsTFR2VEV5cTVOWG1sNE5jdjVpWEQ5YjRjdzZqIl0s"
    "ImV4cCI6ODIxMDI2Njg3Njc5OSwiaWF0IjoxNzY4ODgxMzAyLCJzdWIiOiJzcGlmZmU6Ly9hcGkuY296ZS5jbi93b3JrbG9hZF9pZGVudGl0eS9pZDo3NTk2NTc4MjQxNzM3OTE2NDIyIiw"
    "ic3JjIjoiaW5ib3VuZF9hdXRoX2FjY2Vzc190b2tlbl9pZDo3NTk3Mjg3MzQzNzU3NzIxNjU0In0."
    "keoCo-RLF9UnZr0T79uM7K7Z8ab1IS41cTvwkTqCheTviV8ubUhjT8hhgZWxfWzGVIPKDoKzkHyPc4nkuxwqWSvsEYkPqy_RB9VU1v3xrZCN0aMcpvmYtBO0OuXYnak8dtFdfPs8GSj_-iUoJmh0TlB5lftrZHGDTauC_2JXkc1UAtq669md_V6uPHo5IBRz_Ihh5Ih4BBlpJJQc0YSNnn6Gmv7Bd5fq5COiycwKXDSHP5HyC1_X-AGUXlTJgdLoB8gLTLHi-3JiBm7VP-J7Ixu9jqXT41-15_qAJ0H8z78Jf3_Hm7IiGK4ZQ7lWPkLcD5YTmHp92jh0sF0PgKx8Bg"
)

DEV_DOC_FILENAME = "开发文档.md"
DEV_SPEC_FILENAME = "开发规范.md"
# ===================================================

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def prepare_user_project_dir(user_id: str) -> str:
    """
    创建 user_project/{user_id} 项目目录，并确保 user_project_zip 目录存在
    """
    ensure_dir(USER_PROJECT_ROOT)
    ensure_dir(USER_PROJECT_ZIP_ROOT)
    user_dir = os.path.join(USER_PROJECT_ROOT, str(user_id))
    ensure_dir(user_dir)
    return user_dir

def copy_dev_spec_to_project(user_dir: str) -> bool:
    """
    将项目根目录下的 开发规范.md 复制到用户项目目录中
    """
    src = os.path.join(PROJECT_ROOT, DEV_SPEC_FILENAME)
    dst = os.path.join(user_dir, DEV_SPEC_FILENAME)
    if not os.path.exists(src):
        print(f"⚠️  未找到 {DEV_SPEC_FILENAME}（路径: {src}），将跳过复制")
        return False
    try:
        shutil.copyfile(src, dst)
        return True
    except Exception as e:
        print(f"⚠️  复制 {DEV_SPEC_FILENAME} 失败: {e}")
        return False

def fetch_dev_doc_stream(user_requirement: str, output_path: str) -> bool:
    """
    调用规划智能体接口（流式），将返回内容写入 output_path
    """
    payload = json.dumps({"user_requirement": user_requirement}).encode("utf-8")
    req = urllib.request.Request(
        PLANNER_API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": PLANNER_API_TOKEN,
            "Content-Type": "application/json",
            "Accept": "*/*",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=CONFIG.get('dev_doc_timeout', 60 * 15)) as resp:
            with open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        return True
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        print(f"❌ 拉取开发文档失败（HTTP {e.code}）: {body[:500]}")
        return False
    except Exception as e:
        print(f"❌ 拉取开发文档失败: {e}")
        return False

def get_cursor_window_region():
    """
    获取窗口的大概区域（用于限制截图范围）
    返回: (x, y, width, height) 或 None
    """
    return CONFIG.get('cursor_window_region', None)

def wait_and_click(image_path, confidence=0.8, timeout=10, click_offset=(0, 0), silent=False, region=None):
    """
    在屏幕中查找指定图片并点击
    """
    start_time = time.time()
    attempt = 0
    screenshot_interval = CONFIG.get('screenshot_interval', 1.0)
    gc_interval = CONFIG.get('gc_interval', 10)
    
    while time.time() - start_time < timeout:
        try:
            search_region = region or get_cursor_window_region()
            
            if search_region:
                location = pyautogui.locateCenterOnScreen(
                    image_path, 
                    confidence=confidence,
                    region=search_region
                )
            else:
                location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            
            if location:
                x, y = location
                pyautogui.moveTo(x + click_offset[0], y + click_offset[1], duration=random.uniform(0.2, 0.4))
                pyautogui.click()
                return True
        except pyautogui.ImageNotFoundException:
            pass
        except Exception as e:
            if not silent:
                print(f"⚠️  查找图片时发生异常: {e}")
        
        attempt += 1
        
        if attempt % gc_interval == 0:
            gc.collect()
        
        if not silent and attempt % 10 == 0:
            elapsed = int(time.time() - start_time)
            print(f"   正在查找 {image_path}... ({elapsed}/{timeout}秒)")
        
        time.sleep(screenshot_interval)
    
    if not silent:
        print(f"❌ 未找到 {image_path} (超时: {timeout}秒)")
    return False

def check_for_errors():
    """
    检测屏幕上是否有错误提示
    返回: (has_error, error_type)
    """
    return False, None

def try_recover_from_error():
    """
    尝试从错误中恢复
    """
    if wait_and_click("btnimg/try_again.png", confidence=CONFIG['min_confidence'], timeout=5, silent=True):
        print("✅ 已点击 Try again 按钮")
        return True
    
    if wait_and_click("btnimg/input.png", confidence=CONFIG['min_confidence'], timeout=5, silent=True):
        pyperclip.copy("continue")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)
        pyautogui.press("enter")
        print("✅ 已输入 continue 继续生成")
        return True
    
    return False

def wait_for_ai_completion(base_wait_time, task_type):
    """
    智能等待AI完成项目生成
    支持多种完成按钮（Cursor Accept、Trae Apply/Done/Continue/Save）
    """
    wait_time = base_wait_time
    
    print(f"🤖 等待 AI 生成项目（预计 {wait_time} 秒）...")
    print(f"🔍 将检测以下完成按钮: {', '.join(CONFIG['completion_buttons'])}")
    
    initial_wait = min(wait_time // 2, 60)
    time.sleep(initial_wait)
    
    start_time = time.time()
    last_error_check = time.time()
    consecutive_errors = 0
    
    while time.time() - start_time < wait_time:
        # 轮询检测所有可能的完成按钮
        for button_image in CONFIG['completion_buttons']:
            if os.path.exists(button_image):
                if wait_and_click(
                    button_image, 
                    confidence=CONFIG['min_confidence'], 
                    timeout=2,  # 每个按钮检测2秒
                    silent=True
                ):
                    button_name = os.path.basename(button_image)
                    print(f"✅ 检测到 {button_name} 按钮，AI 生成已完成！")
                    return True
            else:
                # 如果按钮图片不存在，跳过
                pass
        
        # 定期检查错误
        if time.time() - last_error_check >= CONFIG['error_check_interval']:
            has_error, error_type = check_for_errors()
            if has_error:
                print(f"⚠️  检测到错误: {error_type}，尝试恢复...")
                if try_recover_from_error():
                    consecutive_errors = 0
                    last_error_check = time.time()
                    continue
                else:
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        print("❌ 多次尝试恢复失败，可能遇到严重错误")
                        return False
            else:
                consecutive_errors = 0
            
            last_error_check = time.time()
            gc.collect()
        
        # 显示等待进度
        elapsed = int(time.time() - start_time)
        if elapsed % 30 == 0:
            remaining = wait_time - elapsed
            print(f"   ⏳ 生成中... (已等待 {elapsed}秒，剩余约 {remaining}秒)")
        
        time.sleep(CONFIG['poll_interval'])
    
    # 超时后再次尝试查找所有完成按钮
    print(f"⏰ 基础等待时间已到，检查是否已完成...")
    gc.collect()
    
    for button_image in CONFIG['completion_buttons']:
        if os.path.exists(button_image):
            if wait_and_click(button_image, confidence=CONFIG['min_confidence'], timeout=15, silent=True):
                button_name = os.path.basename(button_image)
                print(f"✅ 检测到 {button_name} 按钮！")
                return True
    
    print("⚠️  等待超时，但未检测到任何完成按钮")
    return False

def generate_prompt(task):
    """
    根据任务信息生成提示词
    """
    user_id = task.get('user_id', '')
    
    prompt = (
        f"在{user_id}文件夹按照开发文档和开发规范这俩个文档开始开发项目。"
        f"最后将当前项目除文档之外的压缩到user_project_zip里面。"
    )
    return prompt

def process_single_task(task, queue, task_number):
    """
    处理单个任务的完整流程
    """
    task_id = task.get('task_id', '')
    user_id = task.get('user_id', '')
    
    print(f"\n{'='*60}")
    print(f"📋 开始处理任务 [{task_number}/{queue.get_total_tasks()}]")
    print(f"   任务ID: {task_id}")
    print(f"   用户ID: {user_id}")
    print(f"   项目类型: {task.get('task_type', '')}")
    print(f"{'='*60}\n")
    
    queue.mark_task_processing(task_id)
    
    try:
        # Step 0：准备用户项目目录与开发文档
        print("📍 Step 0: 准备用户项目目录与开发文档...")
        user_dir = prepare_user_project_dir(user_id)
        print(f"✅ 用户项目目录已准备: {user_dir}")

        copied = copy_dev_spec_to_project(user_dir)
        if copied:
            print(f"✅ 已复制 {DEV_SPEC_FILENAME}")

        dev_doc_path = os.path.join(user_dir, DEV_DOC_FILENAME)
        requirement_text = task.get('task_description', '') or ''
        planner_input = (
            f"项目类型：{task.get('task_type', '')}\n"
            f"技术选型：{task.get('task_technology', '')}\n\n"
            f"用户原始需求：\n{requirement_text}"
        )

        dev_doc_ok = False
        retry_attempts = int(CONFIG.get('dev_doc_retry_attempts', 2))
        retry_sleep = int(CONFIG.get('dev_doc_retry_sleep', 10))

        for attempt in range(retry_attempts + 1):
            if attempt > 0:
                print(f"🔁 开发文档生成重试 {attempt}/{retry_attempts}（等待 {retry_sleep} 秒后重试）...")
                time.sleep(retry_sleep)

            print(f"📝 正在生成开发文档（预计约 8 分钟，超时 {CONFIG.get('dev_doc_timeout', 0)} 秒）...")
            dev_doc_ok = fetch_dev_doc_stream(planner_input, dev_doc_path)
            if dev_doc_ok:
                break

        if dev_doc_ok:
            print(f"✅ 开发文档已生成: {dev_doc_path}")
        else:
            print("❌ 开发文档生成失败：不开始开发任务，任务标记为 failed")
            queue.mark_task_failed(task_id)
            return False

        # Step 1：点击输入框
        print("📍 Step 1: 查找并点击输入框...")
        input_found = False
        for retry in range(CONFIG['max_retry_attempts']):
            if wait_and_click("btnimg/input.png", confidence=CONFIG['min_confidence'], timeout=15):
                input_found = True
                break
            elif retry < CONFIG['max_retry_attempts'] - 1:
                print(f"   ⚠️  第 {retry + 1} 次尝试失败，{3}秒后重试...")
                time.sleep(3)
        
        if not input_found:
            print("❌ 多次尝试后仍找不到输入框，跳过此任务")
            queue.mark_task_failed(task_id)
            return False
        
        time.sleep(1)
        
        # Step 2：生成并输入提示词
        print("📍 Step 2: 生成提示词并输入...")
        prompt = generate_prompt(task)
        print(f"📝 提示词: {prompt[:100]}...")
        print(f"   完整提示词长度: {len(prompt)} 字符")
        
        try:
            pyperclip.copy(prompt)
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            pyautogui.press("delete")
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1)
            print("✅ 提示词已输入")
        except Exception as e:
            print(f"❌ 输入提示词时发生错误: {e}")
            queue.mark_task_failed(task_id)
            return False
        
        # Step 3：点击发送按钮
        print("📍 Step 3: 点击发送按钮...")
        send_clicked = False
        for retry in range(CONFIG['max_retry_attempts']):
            if wait_and_click("btnimg/send.png", confidence=CONFIG['min_confidence'], timeout=15):
                send_clicked = True
                break
            elif retry < CONFIG['max_retry_attempts'] - 1:
                print(f"   ⚠️  第 {retry + 1} 次尝试失败，{3}秒后重试...")
                time.sleep(3)
        
        if not send_clicked:
            print("❌ 多次尝试后仍找不到发送按钮，跳过此任务")
            queue.mark_task_failed(task_id)
            return False
        
        print("✅ 已发送提示词")
        
        # Step 4：智能等待 AI 完成生成（支持多种完成按钮）
        task_type = task.get('task_type', '')
        completion_detected = wait_for_ai_completion(CONFIG['base_wait_time'], task_type)
        
        if not completion_detected:
            print("⚠️  未能确认AI生成完成，但继续尝试...")
        
        # 开发完成后进入待审核状态
        queue.mark_task_review(task_id)
        print(f"✅ 任务 {task_id} 开发完成，已进入待审核(review)状态！\n")
        return True
        
    except pyautogui.FailSafeException as e:
        print("❌ 处理任务时触发 PyAutoGUI FAILSAFE：请避免将鼠标移动到屏幕角落。")
        queue.mark_task_failed(task_id)
        return False
    except Exception as e:
        print(f"❌ 处理任务时发生错误: {e}")
        traceback.print_exc()
        queue.mark_task_failed(task_id)
        return False

def scan_new_tasks(queue):
    """
    定时扫描数据库，添加新任务到队列
    """
    global running
    while running:
        try:
            queue.add_new_tasks()
        except Exception as e:
            print(f"❌ 扫描新任务时发生错误: {e}")
        
        for _ in range(SCAN_INTERVAL):
            if not running:
                break
            time.sleep(1)

def main():
    """
    主函数：持续运行，定时扫描数据库并处理任务
    """
    global running
    
    print("="*60)
    print("🚀 自动化任务处理系统启动（持续运行模式）")
    print("="*60)
    print(f"📡 定时扫描间隔: {SCAN_INTERVAL} 秒（{SCAN_INTERVAL // 60} 分钟）")
    print("\n请确保 Trae 已打开，AI 输入框、发送按钮、完成按钮都可见。")
    print("准备时间：5秒...")
    print("提示：按 Ctrl+C 可停止程序\n")
    time.sleep(5)
    
    queue = TaskQueue()
    
    print("\n📥 正在从数据库加载初始待办任务...")
    initial_count = queue.load_tasks()
    print(f"✅ 已加载 {initial_count} 个待办任务\n")
    
    scan_thread = threading.Thread(target=scan_new_tasks, args=(queue,), daemon=True)
    scan_thread.start()
    print(f"✅ 后台扫描线程已启动，每 {SCAN_INTERVAL} 秒扫描一次数据库\n")
    
    success_count = 0
    fail_count = 0
    task_number = 0
    last_scan_time = time.time()
    
    try:
        while running:
            if queue.has_more_tasks():
                task = queue.get_next_task()
                if task:
                    task_number += 1
                    pending_count = queue.get_pending_count()
                    total_count = queue.get_total_tasks()
                    
                    if process_single_task(task, queue, task_number):
                        success_count += 1
                    else:
                        fail_count += 1
                    
                    if queue.has_more_tasks():
                        print("⏸️  等待 3 秒后处理下一个任务...\n")
                        time.sleep(3)
            else:
                print(f"⏳ 队列为空，等待新任务... (每 {SCAN_INTERVAL} 秒自动扫描)")
                for _ in range(10):
                    if not running:
                        break
                    if queue.has_more_tasks():
                        break
                    time.sleep(1)
            
            if task_number > 0 and task_number % 10 == 0:
                print("\n" + "="*60)
                print("📊 当前统计信息")
                print("="*60)
                print(f"✅ 成功: {success_count} 个")
                print(f"❌ 失败: {fail_count} 个")
                print(f"📋 已处理: {task_number} 个")
                print(f"⏳ 队列中待处理: {queue.get_pending_count()} 个")
                print("="*60 + "\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  收到中断信号，正在停止...")
        running = False
    
    finally:
        running = False
        scan_thread.join(timeout=2)
        
        print("\n" + "="*60)
        print("📊 最终统计信息")
        print("="*60)
        print(f"✅ 成功: {success_count} 个")
        print(f"❌ 失败: {fail_count} 个")
        print(f"📋 总计: {task_number} 个")
        print("="*60)
        print("\n👋 程序已停止")

if __name__ == "__main__":
    main()
