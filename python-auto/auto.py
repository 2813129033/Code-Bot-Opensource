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

pyautogui.FAILSAFE = True  # 移到角落可强制中止

# 全局变量
SCAN_INTERVAL = 30  # 扫描间隔（秒），默认30秒
running = True  # 控制程序运行状态

# ==================== 配置参数 ====================
# 可以根据实际情况调整这些参数
CONFIG = {
    'min_confidence': 0.6,  # 最低图片匹配置信度（0.0-1.0，越低越容易匹配但可能误匹配）
    'max_retry_attempts': 3,  # 最大重试次数（输入框、发送按钮等关键步骤）
    'poll_interval': 10,  # 轮询检测间隔（秒）- 检测Accept按钮的频率（降低频率减少截图）
    'error_check_interval': 20,  # 错误检测间隔（秒）- 检查网络错误等的频率（降低频率）
    'accept_timeout': 60,  # Accept按钮检测超时（秒）- 在基础等待时间后额外等待的时间
    # 固定等待时间：45 分钟 = 2700 秒
    'base_wait_time': 2700,
    'screenshot_interval': 1.0,  # 截图间隔（秒）- 降低截图频率，减少内存占用
    'gc_interval': 10,  # 垃圾回收间隔（秒）- 每N次截图后强制GC
    # 'cursor_window_region': (100, 100, 1600, 900),  # Cursor窗口区域 (x, y, width, height)，取消注释并设置实际值可大幅减少内存占用
    # 开发文档生成等待配置
    'dev_doc_timeout': 60 * 15,  # 开发文档接口最大等待时间（秒），默认 15 分钟
    'dev_doc_retry_attempts': 2,  # 开发文档生成失败后重试次数
    'dev_doc_retry_sleep': 10,  # 重试前等待（秒）
}
# ===================================================

# ==================== 项目目录与文档生成配置 ====================
# 项目会统一生成在 user_project/{user_id} 下
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
USER_PROJECT_ROOT = os.path.join(PROJECT_ROOT, 'user_project')
USER_PROJECT_ZIP_ROOT = os.path.join(PROJECT_ROOT, 'user_project_zip')

# 规划智能体接口（流式返回开发文档）
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
        # 这里是“整个请求”的超时时间；接口通常 ~8 分钟返回完成
        with urllib.request.urlopen(req, timeout=CONFIG.get('dev_doc_timeout', 60 * 15)) as resp:
            # 直接流式写入文件，避免内存占用
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
    获取Cursor窗口的大概区域（用于限制截图范围）
    返回: (x, y, width, height) 或 None
    如果无法确定，返回None，将使用全屏截图
    """
    # 方法1：尝试通过查找Cursor特有的元素来确定窗口位置
    # 这里可以添加更智能的窗口检测逻辑
    
    # 方法2：使用配置的窗口位置（如果用户知道Cursor窗口位置）
    # 可以在CONFIG中添加 'cursor_window_region' 配置
    
    # 暂时返回None，使用全屏截图
    # 后续可以扩展为自动检测或配置
    return CONFIG.get('cursor_window_region', None)

def wait_and_click(image_path, confidence=0.8, timeout=10, click_offset=(0, 0), silent=False, region=None):
    """
    在屏幕中查找指定图片并点击
    silent: 如果为True，找不到时不打印错误信息
    region: (x, y, width, height) 限制截图区域，减少内存占用
    """
    start_time = time.time()
    attempt = 0
    screenshot_interval = CONFIG.get('screenshot_interval', 1.0)
    gc_interval = CONFIG.get('gc_interval', 10)
    
    while time.time() - start_time < timeout:
        try:
            # 优先使用传入的region，否则尝试使用配置的Cursor窗口区域
            search_region = region or get_cursor_window_region()
            
            # 如果指定了区域，只在该区域截图（大幅减少内存占用）
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
            # 图片未找到，继续尝试
            pass
        except Exception as e:
            # 其他异常（如截图失败等）
            if not silent:
                print(f"⚠️  查找图片时发生异常: {e}")
        
        attempt += 1
        
        # 定期强制垃圾回收，释放截图内存
        if attempt % gc_interval == 0:
            gc.collect()
        
        # 每10次尝试打印一次进度（仅在非silent模式下）
        if not silent and attempt % 10 == 0:
            elapsed = int(time.time() - start_time)
            print(f"   正在查找 {image_path}... ({elapsed}/{timeout}秒)")
        
        # 使用配置的截图间隔，而不是固定的0.5秒
        time.sleep(screenshot_interval)
    
    if not silent:
        print(f"❌ 未找到 {image_path} (超时: {timeout}秒)")
    return False

def check_for_errors():
    """
    检测屏幕上是否有错误提示（如网络错误、Token用完等）
    返回: (has_error, error_type)
    """
    # 这里可以添加OCR识别错误信息的逻辑
    # 目前先返回False，后续可以扩展
    return False, None

def try_recover_from_error():
    """
    尝试从错误中恢复（点击Try again或输入continue）
    """
    # 尝试查找并点击 "Try again" 按钮
    if wait_and_click("btnimg/try_again.png", confidence=CONFIG['min_confidence'], timeout=5, silent=True):
        print("✅ 已点击 Try again 按钮")
        return True
    
    # 如果找不到按钮，尝试在输入框输入 "continue"
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
    使用轮询方式检测Accept按钮，而不是固定等待
    """
    # 统一使用固定等待时间（例如 45 分钟）
    wait_time = base_wait_time
    
    print(f"🤖 等待 AI 生成项目（预计 {wait_time} 秒）...")
    
    # 先等待基础时间的一半，让AI开始生成
    initial_wait = min(wait_time // 2, 60)
    time.sleep(initial_wait)
    
    # 然后开始轮询检测
    start_time = time.time()
    last_error_check = time.time()
    consecutive_errors = 0
    
    while time.time() - start_time < wait_time:
        # 检查是否有Accept按钮（说明生成完成）
        # 使用更短的超时时间，减少无效截图次数
        # 可以指定region参数，只截取Cursor窗口区域（需要先获取窗口位置）
        if wait_and_click(
            "btnimg/accept.png", 
            confidence=CONFIG['min_confidence'], 
            timeout=3,  # 稍微增加超时，但减少截图频率
            silent=True
        ):
            print("✅ 检测到 Accept 按钮，AI 生成已完成！")
            return True
        
        # 定期检查是否有错误需要恢复（降低频率）
        if time.time() - last_error_check >= CONFIG['error_check_interval']:
            has_error, error_type = check_for_errors()
            if has_error:
                print(f"⚠️  检测到错误: {error_type}，尝试恢复...")
                if try_recover_from_error():
                    consecutive_errors = 0
                    last_error_check = time.time()
                    # 恢复后继续等待
                    continue
                else:
                    consecutive_errors += 1
                    if consecutive_errors >= 3:
                        print("❌ 多次尝试恢复失败，可能遇到严重错误")
                        return False
            else:
                consecutive_errors = 0
            
            last_error_check = time.time()
            # 错误检查后强制GC，释放可能的内存占用
            gc.collect()
        
        # 显示等待进度
        elapsed = int(time.time() - start_time)
        if elapsed % 30 == 0:  # 每30秒显示一次进度
            remaining = wait_time - elapsed
            print(f"   ⏳ 生成中... (已等待 {elapsed}秒，剩余约 {remaining}秒)")
        
        # 使用配置的轮询间隔（已从5秒增加到10秒）
        time.sleep(CONFIG['poll_interval'])
    
    # 超时后再次尝试查找Accept按钮
    print(f"⏰ 基础等待时间已到，检查是否已完成...")
    # 强制GC一次，清理等待期间的内存
    gc.collect()
    
    if wait_and_click("btnimg/accept.png", confidence=CONFIG['min_confidence'], timeout=15, silent=True):
        print("✅ 检测到 Accept 按钮！")
        return True
    
    print("⚠️  等待超时，但未检测到 Accept 按钮")
    return False

def generate_prompt(task):
    """
    根据任务信息生成提示词
    格式：创建一个名字为user_id文件夹，写一个规模为task_type的项目，技术选型为task_technology,项目描述为task_description，不要乱写文档，只需要最后写一个运行文档就可以，然后将这个项目压缩到这个项目的根目录中
    """
    user_id = task.get('user_id', '')
    task_type = task.get('task_type', '')
    task_technology = task.get('task_technology', '')
    task_description = task.get('task_description', '')
    
    # 注意：目录和文档由脚本提前准备好，这里只负责“让 Cursor 按文档开发，并在最后输出压缩包”
    prompt = (
        f"在{user_id}文件夹按照开发文档和开发规范这俩个文档开始开发项目。"
        f"最后将当前项目除文档之外的压缩到user_project_zip里面。"
    )
    return prompt

def process_single_task(task, queue, task_number):
    """
    处理单个任务的完整流程
    task_number: 当前任务序号（从1开始）
    """
    task_id = task.get('task_id', '')
    
    user_id = task.get('user_id', '')
    
    print(f"\n{'='*60}")
    print(f"📋 开始处理任务 [{task_number}/{queue.get_total_tasks()}]")
    print(f"   任务ID: {task_id}")
    print(f"   用户ID: {user_id}")
    print(f"   项目类型: {task.get('task_type', '')}")
    print(f"{'='*60}\n")
    
    # 标记任务为处理中
    queue.mark_task_processing(task_id)
    
    try:
        # Step 0：创建用户项目目录，准备开发文档与开发规范
        print("📍 Step 0: 准备用户项目目录与开发文档...")
        user_dir = prepare_user_project_dir(user_id)
        print(f"✅ 用户项目目录已准备: {user_dir}")

        # 复制开发规范
        copied = copy_dev_spec_to_project(user_dir)
        if copied:
            print(f"✅ 已复制 {DEV_SPEC_FILENAME}")

        # 拉取开发文档（流式写入）
        dev_doc_path = os.path.join(user_dir, DEV_DOC_FILENAME)
        # 将用户的原始描述 + 类型 + 技术选型发给规划智能体
        requirement_text = task.get('task_description', '') or ''
        planner_input = (
            f"项目类型：{task.get('task_type', '')}\n"
            f"技术选型：{task.get('task_technology', '')}\n\n"
            f"用户原始需求：\n{requirement_text}"
        )

        # 开发文档必须生成成功才开始开发任务（接口通常需要 ~8 分钟）
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

        # Step 1：点击输入框（带重试机制）
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
            print("   提示：请确保 Cursor 窗口可见且输入框在屏幕上")
            queue.mark_task_failed(task_id)
            return False
        
        time.sleep(1)
        
        # Step 2：生成并输入提示词
        print("📍 Step 2: 生成提示词并输入...")
        prompt = generate_prompt(task)
        print(f"📝 提示词: {prompt[:100]}...")  # 只显示前100个字符
        print(f"   完整提示词长度: {len(prompt)} 字符")
        
        # 确保剪贴板内容正确
        try:
            pyperclip.copy(prompt)
            time.sleep(0.5)
            # 清空输入框（全选+删除）
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            pyautogui.press("delete")
            time.sleep(0.3)
            # 粘贴提示词
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1)
            print("✅ 提示词已输入")
        except Exception as e:
            print(f"❌ 输入提示词时发生错误: {e}")
            queue.mark_task_failed(task_id)
            return False
        
        # Step 3：点击发送按钮（带重试机制）
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
        
        # Step 4：智能等待 AI 完成生成
        task_type = task.get('task_type', '')
        completion_detected = wait_for_ai_completion(CONFIG['base_wait_time'], task_type)
        
        if not completion_detected:
            print("⚠️  未能确认AI生成完成，但继续尝试点击Accept...")
        
        # Step 5：点击 Accept 按钮（使用更宽松的参数）
        print("📍 Step 5: 点击 Accept 按钮...")
        accept_clicked = False
        
        # 尝试多次点击Accept，使用不同的置信度
        for attempt in range(3):
            confidence_levels = [0.7, 0.6, 0.5]
            if wait_and_click("btnimg/accept.png", 
                            confidence=confidence_levels[attempt], 
                            timeout=CONFIG['accept_timeout'] // 3,
                            silent=(attempt > 0)):
                print("✅ 已点击 Accept")
                accept_clicked = True
                break
            elif attempt < 2:
                print(f"   尝试 {attempt + 1}/3 未找到，降低置信度继续尝试...")
        
        if not accept_clicked:
            print("⚠️  未找到 Accept 按钮，可能的原因：")
            print("   1. AI 还未生成完成，需要更多时间")
            print("   2. Accept 按钮样式已变化，需要更新图片")
            print("   3. 项目生成失败或中断")
            print("   任务将标记为完成，但建议手动检查")
        
        # 开发完成后进入待审核状态（不压缩、不发送）
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
    在后台线程中运行
    """
    global running
    while running:
        try:
            queue.add_new_tasks()
        except Exception as e:
            print(f"❌ 扫描新任务时发生错误: {e}")
        
        # 等待指定间隔后再次扫描
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
    print("\n请确保 Cursor 已打开，AI 输入框、发送按钮、Accept 按钮都可见。")
    print("准备时间：5秒...")
    print("提示：按 Ctrl+C 可停止程序\n")
    time.sleep(5)
    
    # 初始化任务队列
    queue = TaskQueue()
    
    # 从数据库加载初始待办任务
    print("\n📥 正在从数据库加载初始待办任务...")
    initial_count = queue.load_tasks()
    print(f"✅ 已加载 {initial_count} 个待办任务\n")
    
    # 启动后台扫描线程
    scan_thread = threading.Thread(target=scan_new_tasks, args=(queue,), daemon=True)
    scan_thread.start()
    print(f"✅ 后台扫描线程已启动，每 {SCAN_INTERVAL} 秒扫描一次数据库\n")
    
    # 统计信息
    success_count = 0
    fail_count = 0
    task_number = 0
    last_scan_time = time.time()
    
    try:
        # 主循环：持续处理任务
        while running:
            # 检查是否有待处理任务
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
                    
                    # 任务之间的间隔，避免操作过快
                    if queue.has_more_tasks():
                        print("⏸️  等待 3 秒后处理下一个任务...\n")
                        time.sleep(3)
            else:
                # 队列为空，等待新任务
                print(f"⏳ 队列为空，等待新任务... (每 {SCAN_INTERVAL} 秒自动扫描)")
                # 每10秒检查一次队列，避免长时间阻塞
                for _ in range(10):
                    if not running:
                        break
                    if queue.has_more_tasks():
                        break
                    time.sleep(1)
            
            # 定期显示统计信息（每处理10个任务）
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
        # 等待扫描线程结束
        scan_thread.join(timeout=2)
        
        # 输出最终统计信息
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
