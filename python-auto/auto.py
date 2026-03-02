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
import sys
import urllib.request
import urllib.error
import http.client
from task_queue import TaskQueue
from db_connector import cleanup_connection_pool
from task_checker import (
    load_task_tree, save_task_tree, find_next_unfinished_task,
    mark_task_completed, all_tasks_completed, generate_task_check_prompt,
    generate_final_check_prompt, get_all_tasks_status
)

# Windows 控制台常见为 GBK，遇到 emoji 会触发 UnicodeEncodeError；这里统一改为 UTF-8 并替换不可编码字符
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

pyautogui.FAILSAFE = True

# 全局变量
# 数据库任务扫描间隔（秒）：改为每 8 小时执行一次
SCAN_INTERVAL = 60 * 60 * 8
running = True  # 控制程序运行状态

# ==================== 配置参数 ====================
CONFIG = {
    'min_confidence': 0.6,          # 最低图片匹配置信度
    'max_retry_attempts': 5,        # 最大重试次数（图片识别等操作）- 增加到5次，给界面更多加载时间
    # 初次代码生成等待时间：建议 20~30 分钟，而不是 1.5 小时，避免长时间干等
    'project_wait_time': 60 * 30,   # 新建项目首次生成等待时间：30 分钟
    'modify_project_wait_time': 60 * 20,  # 修改项目默认等待：20 分钟
    # 2-3万字文档，接口整体可能较慢，这里给到 20 分钟超时
    'dev_doc_timeout': 60 * 20,     # 开发文档接口最大等待时间（秒）
    'dev_doc_retry_attempts': 2,    # 开发文档生成失败后重试次数
    'dev_doc_retry_sleep': 10,      # 重试前等待（秒）
    'token_check_interval': 60 * 5, # Token 检测间隔：5分钟 = 300秒
    'task_max_retries': 3,          # 任务最大重试次数（整个任务失败后）
    'task_retry_delay': 60,         # 任务重试前等待时间（秒）
    'resource_cleanup_interval': 3600,  # 资源清理间隔（秒），1小时
    # 任务轮次相关配置（用于 Step 5 / Step 6 等待 AI 修复代码的间隔）
    'self_check_max_rounds': 3,              # 每个任务最多等待轮数（含首轮）
    # 每一轮任务修复后的等待时间：默认 5 分钟（原来是 15 分钟 = 900 秒）
    'self_check_round_wait_time': 300,
    'debug_logs': False,            # 普通运行时关闭信息级日志，只打印异常/错误
}
# ===================================================


def log_info(message: str) -> None:
    """仅在 debug_logs 为 True 时输出的信息级日志"""
    if CONFIG.get('debug_logs'):
        print(message)

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
# 任务清单文件名：统一在各模块中使用固定字符串，不再依赖 doc_state_model.py
TASK_TREE_FILENAME = "task_tree.json"
# ===================================================

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def prepare_user_project_dir(user_id: str, task_id: str) -> str:
    """
    创建 user_project/{user_id}/{task_id} 项目目录，并确保 user_project_zip 目录存在
    """
    if not task_id:
        raise ValueError("task_id is required for prepare_user_project_dir")
    ensure_dir(USER_PROJECT_ROOT)
    ensure_dir(USER_PROJECT_ZIP_ROOT)
    user_dir = os.path.join(USER_PROJECT_ROOT, str(user_id))
    ensure_dir(user_dir)
    project_dir = os.path.join(user_dir, str(task_id))
    ensure_dir(project_dir)
    return project_dir

def copy_dev_spec_to_project(user_dir: str) -> bool:
    """
    将项目根目录下的 开发规范.md 复制到用户项目目录中
    """
    src = os.path.join(PROJECT_ROOT, DEV_SPEC_FILENAME)
    dst = os.path.join(user_dir, DEV_SPEC_FILENAME)
    if not os.path.exists(src):
        return False
    try:
        shutil.copyfile(src, dst)
        return True
    except Exception as e:
        print(f"⚠️  复制 {DEV_SPEC_FILENAME} 失败: {e}")
        return False

def fetch_dev_doc_stream(user_requirement: str, output_path: str, user_id: str = None) -> bool:
    """
    调用规划智能体接口（流式），将返回内容写入 output_path，生成完成后立即上传

    扣子当前要求的参数格式（仅文本需求）为：
    {
        "original_requirement": "开发一个在线考试系统，支持用户注册登录、查看考试列表、参加考试、查看成绩等功能"
    }

    如果后续需要支持带文档的形式：
    {
        "original_requirement": "开发一个在线考试系统",
        "requirement_file": {
            "url": "https://example.com/requirement.pdf",
            "file_type": "document"
        }
    }
    可以在这里按需扩展 payload。
    
    @param user_requirement: 用户需求文本
    @param output_path: 输出文件路径
    @param user_id: 用户ID，用于上传（可选，如果提供则生成完成后立即上传）
    """
    # 目前仅传文本需求，按扣子最新接口要求使用 original_requirement 字段
    payload = json.dumps({"original_requirement": user_requirement}).encode("utf-8")
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

    total_written = 0  # 实际写入的字节数

    try:
        with urllib.request.urlopen(req, timeout=CONFIG.get('dev_doc_timeout', 60 * 20)) as resp:
            with open(output_path, "wb") as f:
                while True:
                    try:
                        chunk = resp.read(8192)
                    except http.client.IncompleteRead as e:
                        # Coze 端有时会在内容已基本发送完成时提前关闭连接
                        # IncompleteRead.partial 中通常已经包含剩余内容
                        partial = e.partial or b""
                        if partial:
                            f.write(partial)
                            total_written += len(partial)

                        # 如果一个字节都没写入，就认为失败，不继续后续步骤
                        if total_written == 0:
                            print("❌ 开发文档生成失败：IncompleteRead 且无有效内容写入")
                            return False

                        # 扣子生成完成后立即上传
                        if user_id:
                            upload_success = upload_dev_document(output_path, user_id)
                        return True

                    if not chunk:
                        break

                    f.write(chunk)
                    total_written += len(chunk)

        # 如果正常结束但一个字节都没写入，也视为失败
        if total_written == 0:
            print("❌ 开发文档生成失败：接口返回空内容")
            return False

        # 扣子生成完成后立即上传
        if user_id:
            upload_success = upload_dev_document(output_path, user_id)

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

def upload_dev_document(file_path: str, user_id: str) -> bool:
    """
    上传开发文档到指定接口
    @param file_path: 文档文件路径
    @param user_id: 用户QQ号
    @return: 是否上传成功
    """
    upload_url = "http://192.168.5.6:3000/save-md"
    
    # 重试机制
    max_retries = 3
    base_retry_delay = 2  # 秒
    
    for attempt in range(max_retries):
        try:
            # 使用 multipart/form-data 格式上传文件（按照 curl 的格式）
            import mimetypes
            
            # 读取文件内容
            with open(file_path, 'rb') as file:
                file_content = file.read()
            
            # 使用 curl 风格的 boundary 格式（-------------------------- 开头）
            boundary = '--------------------------' + ''.join(random.choices('0123456789', k=24))
            content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            filename = os.path.basename(file_path)
            
            # 构建请求体（按照 curl 的格式：先 fileName，后 file）
            body_parts = []
            
            # fileName 字段（第一个字段）
            body_parts.append(f'--{boundary}\r\n'.encode('utf-8'))
            body_parts.append(f'Content-Disposition: form-data; name="fileName"\r\n'.encode('utf-8'))
            body_parts.append(b'\r\n')
            body_parts.append(str(user_id).encode('utf-8'))
            body_parts.append(b'\r\n')
            
            # file 字段（第二个字段）
            body_parts.append(f'--{boundary}\r\n'.encode('utf-8'))
            body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode('utf-8'))
            body_parts.append(f'Content-Type: {content_type}\r\n'.encode('utf-8'))
            body_parts.append(b'\r\n')
            body_parts.append(file_content)
            body_parts.append(b'\r\n')
            
            # 结束 boundary
            body_parts.append(f'--{boundary}--\r\n'.encode('utf-8'))
            
            body = b''.join(body_parts)
            
            # 创建请求（添加 curl 类似的头部）
            req = urllib.request.Request(
                upload_url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Content-Length": str(len(body)),
                    "User-Agent": "Python-urllib/3.x",
                    "Accept": "*/*",
                    "Connection": "keep-alive",
                },
            )
            
            # 发送请求
            with urllib.request.urlopen(req, timeout=60) as resp:
                response_data = resp.read().decode('utf-8', errors='ignore')
                # urllib.request.urlopen 成功时状态码为 200，否则会抛出 HTTPError
                return True
                    
        except (urllib.error.HTTPError, ConnectionResetError, OSError) as e:
            if attempt < max_retries - 1:
                retry_delay = base_retry_delay * (2 ** attempt)  # 指数退避：2秒、4秒、8秒
                time.sleep(retry_delay)
                continue
            else:
                # 最后一次尝试失败
                if isinstance(e, urllib.error.HTTPError):
                    try:
                        body = e.read().decode("utf-8", errors="ignore")
                    except Exception:
                        body = ""
                    print(f"❌ 上传开发文档失败（HTTP {e.code}）: {body[:500]}")
                else:
                    print(f"❌ 上传开发文档失败: {e}")
                return False
        except Exception as e:
            print(f"❌ 上传开发文档失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return False

def wait_and_click(image_path, confidence=0.8, timeout=10, click_offset=(0, 0), silent=False, click_times=2):
    """
    在屏幕中查找指定图片并点击
    使用动态扫描间隔：初始间隔较短，随着时间推移逐渐增加，减少CPU占用
    """
    start_time = time.time()
    attempt = 0
    # 动态扫描间隔配置：初始0.3秒，逐渐增加到最大2秒
    initial_interval = 0.3
    max_interval = 2.0
    interval_increase_threshold = 3.0  # 每3秒增加一次间隔
    
    current_interval = initial_interval
    last_interval_increase_time = start_time
    
    while time.time() - start_time < timeout:
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
            
            if location:
                x, y = location
                # 移动到目标位置
                pyautogui.moveTo(x + click_offset[0], y + click_offset[1], duration=random.uniform(0.2, 0.4))
                time.sleep(0.2)  # 等待鼠标移动完成
                # 点击前先确保鼠标在正确位置
                current_x, current_y = pyautogui.position()
                if abs(current_x - (x + click_offset[0])) > 5 or abs(current_y - (y + click_offset[1])) > 5:
                    # 如果位置偏差太大，重新移动
                    pyautogui.moveTo(x + click_offset[0], y + click_offset[1], duration=0.1)
                    time.sleep(0.1)
                # 执行点击（默认双击；部分按钮需要单击避免二次点击副作用）
                safe_click_times = int(click_times) if click_times is not None else 2
                if safe_click_times < 1:
                    safe_click_times = 1
                for i in range(safe_click_times):
                    pyautogui.click()
                    # 单击/双击之间留一点时间，提升成功率
                    time.sleep(0.25 if i == 0 else 0.15)
                return True
        except pyautogui.ImageNotFoundException:
            # 识别不到图片本身不算致命错误，这里不打印堆栈，但可以按需输出一次日志
            if not silent:
                print(f"⚠️ 未在屏幕上找到图像: {image_path}")
        except Exception as e:
            # 其他异常必须打印出来，方便排查
            print(f"❌ wait_and_click 调用出错，image={image_path}: {e}")
            traceback.print_exc()
        
        attempt += 1
        
        # 动态调整扫描间隔：每3秒增加0.2秒，最多到2秒
        current_time = time.time()
        elapsed = current_time - start_time
        time_since_last_increase = current_time - last_interval_increase_time
        
        if time_since_last_increase >= interval_increase_threshold:
            if current_interval < max_interval:
                current_interval = min(current_interval + 0.2, max_interval)
                last_interval_increase_time = current_time
        
        time.sleep(current_interval)
    
    if not silent:
        print(f"❌ 未找到 {image_path} (超时: {timeout}秒)")
    return False

def click_send_with_confirm(
    send_button_image="btnimg/send.png",
    success_image="btnimg/send-success.png",
    confidence=None,
    click_timeout=15,
    success_timeout=6,
    max_attempts=None,
):
    """
    发送按钮只能点击一次（双击可能导致停止/异常）。
    流程：单击 send.png -> 鼠标移开避免遮挡 -> 识别 send-success.png 判断是否发送成功 -> 否则重试。
    """
    try:
        if confidence is None:
            confidence = CONFIG.get("min_confidence", 0.8)
        if max_attempts is None:
            max_attempts = int(CONFIG.get("max_retry_attempts", 3))

        for attempt in range(max_attempts):
            # 单击发送按钮（禁止双击）
            clicked = wait_and_click(
                send_button_image,
                confidence=confidence,
                timeout=click_timeout,
                silent=False,
                click_times=1,
            )
            if not clicked:
                print(f"⚠️ 第 {attempt + 1}/{max_attempts} 次点击发送按钮失败: {send_button_image}")
                continue

            # 移开鼠标，避免遮挡“发送成功”标识（避免移动到屏幕角落触发 failsafe）
            try:
                cur_x, cur_y = pyautogui.position()
                pyautogui.moveTo(cur_x + 180, cur_y + 120, duration=0.2)
            except Exception as move_err:
                print(f"⚠️ 移动鼠标避免遮挡时出错: {move_err}")

            # 等待“发送成功”标识出现
            start = time.time()
            while time.time() - start < success_timeout:
                try:
                    ok = pyautogui.locateCenterOnScreen(success_image, confidence=confidence)
                    if ok:
                        print(f"✅ 检测到发送成功标识: {success_image}")
                        return True
                except pyautogui.ImageNotFoundException:
                    # 没识别到成功标识属正常情况，不打印堆栈
                    pass
                except Exception as loc_err:
                    print(f"⚠️ 检测发送成功标识时出错: {loc_err}")
                    traceback.print_exc()
                time.sleep(0.4)

            # 没看到成功标识，重试发送
            print(f"⚠️ 在 {success_timeout} 秒内未检测到发送成功标识，将进行重试")

        print("❌ 多次尝试后仍未成功点击发送按钮")
        return False
    except Exception as e:
        print(f"❌ click_send_with_confirm 发生异常: {e}")
        traceback.print_exc()
        return False

def send_continue_prompt(custom_prompt: str):
    """
    根据传入的提示词，自动聚焦输入框并发送。
    该函数现仅作为通用"继续构建/检查"提示词发送工具使用，与任何静态自检文档（如《未完成模块汇总》）无直接关系。
    """
    try:
        if not custom_prompt:
            raise ValueError("custom_prompt is required for send_continue_prompt")

        # 先等待一下，确保界面稳定
        time.sleep(2)
        
        # 查找并点击输入框（使用 wait_and_click 函数，有更好的等待机制）
        input_found = False
        input_location = None
        
        # 增加超时时间，从默认的15秒增加到30秒，给界面更多加载时间
        input_timeout = 30
        
        for retry in range(CONFIG['max_retry_attempts']):
            # 先尝试 input.png（使用 wait_and_click，有动态等待机制）
            if wait_and_click("btnimg/input.png", confidence=CONFIG['min_confidence'], timeout=input_timeout, silent=True):
                # 获取输入框位置（用于后续点击）
                try:
                    location = pyautogui.locateCenterOnScreen("btnimg/input.png", confidence=CONFIG['min_confidence'])
                    if location:
                        input_location = location
                        input_found = True
                        break
                except:
                    # 如果获取位置失败，但已经点击了，继续执行
                    input_found = True
                    break
            
            # 如果 input.png 没找到，尝试 input2.png
            if not input_found:
                if wait_and_click("btnimg/input2.png", confidence=CONFIG['min_confidence'], timeout=input_timeout, silent=True):
                    # 获取输入框位置（用于后续点击）
                    try:
                        location = pyautogui.locateCenterOnScreen("btnimg/input2.png", confidence=CONFIG['min_confidence'])
                        if location:
                            input_location = location
                            input_found = True
                            break
                    except:
                        # 如果获取位置失败，但已经点击了，继续执行
                        input_found = True
                        break
            
            if not input_found and retry < CONFIG['max_retry_attempts'] - 1:
                time.sleep(5)
        
        if not input_found:
            print("⚠️  输入框未找到，无法发送提示词")
            return False
        
        # 等待输入框获得焦点
        time.sleep(2)
        
        # 如果获取到了输入框位置，再次点击确保焦点
        if input_location:
            try:
                x, y = input_location
                pyautogui.moveTo(x, y, duration=0.2)
                pyautogui.click()
                time.sleep(1)
                # 再次点击确保焦点
                pyautogui.click()
                time.sleep(0.5)
            except Exception as e:
                pass
        else:
            # 如果没有位置信息，尝试再次查找并点击
            if wait_and_click("btnimg/input.png", confidence=CONFIG['min_confidence'], timeout=10, silent=True) or \
               wait_and_click("btnimg/input2.png", confidence=CONFIG['min_confidence'], timeout=10, silent=True):
                time.sleep(1)
        
        # 输入提示词
        follow_up_prompt = custom_prompt
        
        try:
            # 复制到剪贴板
            pyperclip.copy(follow_up_prompt)
            time.sleep(0.5)
            
            # 清空输入框：全选并删除
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.3)
            pyautogui.press("backspace")  # 使用 backspace 而不是 delete
            time.sleep(0.2)
            pyautogui.press("delete")  # 双重保险
            time.sleep(0.3)
            
            # 粘贴内容
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1)
            
            # 再次确保：如果粘贴失败，尝试直接输入
            # 检查剪贴板内容
            clipboard_check = pyperclip.paste()
            if clipboard_check != follow_up_prompt:
                pyperclip.copy(follow_up_prompt)
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.2)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(1)
            
        except Exception as input_err:
            import traceback
            traceback.print_exc()
            # 备用方法：直接输入文本（逐字符输入）
            try:
                # 先清空
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.2)
                pyautogui.press("delete")
                time.sleep(0.3)
                # 直接输入
                pyautogui.write(follow_up_prompt, interval=0.05)
                time.sleep(1)
            except Exception as write_err:
                return False
        
        # 点击发送按钮（单击 + 成功标识检测）
        send_clicked = False
        for retry in range(CONFIG['max_retry_attempts']):
            if click_send_with_confirm(
                send_button_image="btnimg/send.png",
                success_image="btnimg/send-success.png",
                confidence=CONFIG['min_confidence'],
                click_timeout=15,
                success_timeout=6,
                max_attempts=1,  # 外层循环已重试
            ):
                send_clicked = True
                break
            elif retry < CONFIG['max_retry_attempts'] - 1:
                time.sleep(3)
        
        if send_clicked:
            return True
        else:
            return False
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False

def wait_for_project_completion(wait_time=None, is_modify_task=False, task=None, project_dir=None, queue=None, round_index=0):
    """
    等待项目生成，并在等待期间定期检测输入框。
    当前实现中，如果检测到输入框（说明 AI 可能停下了），**只记录日志，不再触发任何自检或基于《未完成模块汇总》的额外流程**。

    参数：
    - wait_time: 最大等待时间（秒），None 则使用默认配置
    - is_modify_task: 是否为修改任务
    - task: 任务对象（保留参数，仅用于日志）
    - project_dir: 项目目录（保留参数）
    - queue: TaskQueue 实例（保留参数）
    - round_index: 当前轮次（用于日志区分不同等待阶段）
    """
    # 根据任务类型决定等待时间
    if wait_time is None:
        if is_modify_task:
            wait_time = int(CONFIG.get('modify_project_wait_time', 60 * 20))
        else:
            wait_time = int(CONFIG.get('project_wait_time', 60 * 30))
    
    # 输入框检测间隔：每 5 分钟检测一次
    input_check_interval = 60 * 5
    wait_hours = wait_time / 3600
    
    start_time = time.time()
    last_input_check_time = start_time
    
    while time.time() - start_time < wait_time:
        elapsed = int(time.time() - start_time)
        remaining = wait_time - elapsed
        current_time = time.time()
        
        # 定期检测输入框（如果提供了 task 和 project_dir，说明需要主动检测）
        if task and project_dir and (current_time - last_input_check_time) >= input_check_interval:
            last_input_check_time = current_time
            
            input_found = False
            # 先尝试检测 input.png
            try:
                input_path = "btnimg/input.png"
                if os.path.exists(input_path):
                    location = pyautogui.locateCenterOnScreen(input_path, confidence=CONFIG['min_confidence'])
                    if location:
                        input_found = True
            except pyautogui.ImageNotFoundException:
                pass
            except Exception as e:
                pass
            
            # 如果 input.png 没找到，再尝试 input2.png
            if not input_found:
                try:
                    input2_path = "btnimg/input2.png"
                    if os.path.exists(input2_path):
                        location = pyautogui.locateCenterOnScreen(input2_path, confidence=CONFIG['min_confidence'])
                        if location:
                            input_found = True
                except pyautogui.ImageNotFoundException:
                    pass
                except Exception as e:
                    pass
        
        time.sleep(10)  # 每10秒检查一次
    
    return True

def _generate_task_tree_with_ai(task, project_dir: str) -> bool:
    """
    让 AI 根据《开发文档.md》生成任务清单（task_tree.json）
    
    流程：
    1. 找到输入框
    2. 输入提示词：让 AI 读取开发文档，按照指定格式生成 task_tree.json
    3. 发送
    4. 等待 AI 生成（给足够时间）
    5. 检查 task_tree.json 是否生成成功
    """
    # 直接使用当前模块中定义的常量，而不是依赖 doc_state_model.py
    dev_doc_path = os.path.join(project_dir, DEV_DOC_FILENAME)
    task_tree_path = os.path.join(project_dir, TASK_TREE_FILENAME)
    
    if not os.path.exists(dev_doc_path):
        return False
    
    # 生成提示词
    prompt = """请仔细阅读 user_project 文件夹下的《开发文档.md》文件，然后按照以下 JSON 格式生成任务清单，保存为 task_tree.json 文件：

格式要求：
{{
  "modules": [
    {{
      "name": "模块名称",
      "description": "模块描述",
      "tasks": [
        {{
          "name": "任务名称（如：用户登录接口）",
          "type": "任务类型（只允许：api/page/function/ui_review，不要使用 db_table）",
          "description": "任务详细描述",
          "status": "pending",
          "file_path": "相关文件路径（可选，例如前端页面或后端控制器路径）"
        }}
      ]
    }}
  ]
}

要求：
1. 仔细阅读《开发文档.md》，提取所有需要实现的模块和任务，但【不要单独生成任何数据库设计或建表相关任务】，即不要出现 type 为 "db_table" 的任务。
2. 每个模块下的 tasks 数组只包含「接口（api）」「页面（page）」「通用功能/服务（function）」和「UI 审核与美化（ui_review）」这几类任务。
3. 所有任务的 status 初始值都设为 "pending"。
4. 任务要具体、可验证（比如"实现用户登录接口 POST /api/login"，而不是"实现用户模块"）。
5. 必须额外增加一个“页面 UI 审核与美化”相关的模块，例如“前端 UI 视觉与交互优化”，其中包含对每个主要页面进行 UI 设计优化的任务（type 为 "ui_review"，描述中强调：让页面更加现代化、美观、布局合理、交互友好、兼容移动端或小程序视觉规范）。
6. 生成后保存为 task_tree.json 文件。
1. 仔细阅读《开发文档.md》，提取所有需要实现的模块和任务，但【不要单独生成任何数据库设计或建表相关任务】，即不要出现 type 为 "db_table" 的任务。
2. 每个模块下的 tasks 数组只包含「接口（api）」「页面（page）」「通用功能/服务（function）」和「UI 审核与美化（ui_review）」这几类任务。
3. 所有任务的 status 初始值都设为 "pending"。
4. 任务要具体、可验证（比如"实现用户登录接口 POST /api/login"，而不是"实现用户模块"）。
5. 必须额外增加一个“页面 UI 审核与美化”相关的模块，例如“前端 UI 视觉与交互优化”，其中包含对每个主要页面进行 UI 设计优化的任务（type 为 "ui_review"，描述中强调：让页面更加现代化、美观、布局合理、交互友好、兼容移动端或小程序视觉规范）。
6. 生成后保存为 task_tree.json 文件。

现在开始生成任务清单。"""
    
    # 找到输入框并发送
    input_found = False
    for retry in range(CONFIG['max_retry_attempts']):
        if wait_and_click("btnimg/input.png", confidence=CONFIG['min_confidence'], timeout=15):
            input_found = True
            break
        if wait_and_click("btnimg/input2.png", confidence=CONFIG['min_confidence'], timeout=15):
            input_found = True
            break
        if retry < CONFIG['max_retry_attempts'] - 1:
            time.sleep(3)
    
    if not input_found:
        return False
    
    time.sleep(1)
    
    # 输入提示词
    try:
        pyperclip.copy(prompt)
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.2)
        pyautogui.press("delete")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1)
    except Exception as e:
        return False
    
    # 发送
    send_clicked = False
    for retry in range(CONFIG['max_retry_attempts']):
        if click_send_with_confirm(
            send_button_image="btnimg/send.png",
            success_image="btnimg/send-success.png",
            confidence=CONFIG['min_confidence'],
            click_timeout=15,
            success_timeout=6,
            max_attempts=1,
        ):
            send_clicked = True
            break
        elif retry < CONFIG['max_retry_attempts'] - 1:
            time.sleep(3)
    
    if not send_clicked:
        return False
    
    # 等待 AI 生成（最多 10 分钟）
    max_wait = 60 * 10
    check_interval = 30  # 每 30 秒检查一次文件是否生成
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if os.path.exists(task_tree_path):
            # 检查文件内容是否有效
            try:
                tree = load_task_tree(project_dir)
                if tree.get("modules") and len(tree.get("modules", [])) > 0:
                    return True
            except Exception as e:
                pass
        
        time.sleep(check_interval)
    
    return False


def generate_prompt(task):
    """
    根据任务信息生成提示词
    区分新建项目和修改项目
    """
    user_id = task.get('user_id', '')
    task_status = task.get('task_status', 'pending')
    user_change_request = (task.get('user_change_request') or '').strip()
    review_notes = (task.get('review_notes') or '').strip()
    
    # 如果是修改任务：pending_modify / user_change / review_change + 有修改依据
    is_modify_status = task_status in ('pending_modify', 'user_change', 'review_change')
    has_change_source = bool(user_change_request or review_notes)

    if is_modify_status and has_change_source:
        # 把用户原始修改需求和审核回滚原因拼在一起，作为本轮修改依据
        change_text_parts = []
        if user_change_request:
            change_text_parts.append(f"用户的修改需求是：{user_change_request}")
        if review_notes:
            change_text_parts.append(f"上一次审核给出的回滚原因是：{review_notes}")

        change_text = "；".join(change_text_parts)

        task_id = task.get('task_id', '')
        prompt = (
            f"找到user_project文件夹下面的{user_id}/{task_id}项目，先完整理解下面这些修改依据：{change_text}。"
            f"然后在当前项目基础上进行修改并彻底解决上述所有问题，保持原有功能正常可用。"
            f"修改完成后将当前项目除文档之外的压缩到user_project_zip里面，压缩包文件名必须是{task_id}.zip，如果覆盖不了就先删除之前的{task_id}.zip文件，然后再压缩进去。"
        )
    else:
        # 新建项目
        task_id = task.get('task_id', '')
        prompt = (
            f"在user_project文件夹下面的{user_id}/{task_id}文件夹按照开发文档和开发规范这俩个文档开始开发项目。要着重注意开发规范里面的代码规范，避免出现里面的问题。务必要将开发文档里面的功能和页面全部实现。一次性实现全部，永远不要问我要不要继续，直接完成全部功能。"
            f"最后将当前项目除文档之外的压缩到user_project_zip里面，压缩包文件名必须是{task_id}.zip。"
        )
    return prompt


def is_retryable_error(error: Exception) -> bool:
    """
    判断错误是否可重试
    可重试的错误：网络超时、图片未找到、临时性错误
    不可重试的错误：配置错误、权限错误、数据错误等
    """
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # 可重试的错误类型
    retryable_types = [
        'TimeoutError', 'ConnectionError', 'ImageNotFoundException',
        'HTTPError', 'URLError', 'IncompleteRead'
    ]
    
    # 可重试的错误关键词
    retryable_keywords = [
        'timeout', 'connection', 'network', 'not found', 'image',
        'temporary', 'retry', 'unavailable'
    ]
    
    # 不可重试的错误关键词
    non_retryable_keywords = [
        'permission', 'authentication', 'authorization', 'invalid',
        'syntax error', 'configuration', 'not implemented'
    ]
    
    # 检查不可重试错误
    for keyword in non_retryable_keywords:
        if keyword in error_str:
            return False
    
    # 检查错误类型
    if error_type in retryable_types:
        return True
    
    # 检查可重试关键词
    for keyword in retryable_keywords:
        if keyword in error_str:
            return True
    
    # 默认：未知错误视为可重试（保守策略）
    return True

def process_single_task(task, queue, task_number):
    """
    处理单个任务的完整流程（带重试机制）
    """
    task_id = task.get('task_id', '')
    user_id = task.get('user_id', '')
    task_status = task.get('task_status', 'pending')
    user_change_request = (task.get('user_change_request') or '').strip()
    review_notes = (task.get('review_notes') or '').strip()
    retry_count = task.get('retry_count', 0) or 0  # 获取当前重试次数

    # 修改任务：pending_modify / user_change / review_change，只要有 user_change_request 或 review_notes 就认为是"修改项目"
    is_modify_status = task_status in ('pending_modify', 'user_change', 'review_change')
    is_modify_task = is_modify_status and bool(user_change_request or review_notes)
    
    queue.mark_task_processing(task_id)
    
    try:
        # Step 0：准备用户项目目录与文档
        project_dir = prepare_user_project_dir(user_id, task_id)

        copied = copy_dev_spec_to_project(project_dir)

        # 对于"修改项目"任务（pending_modify），不再重新拉取开发文档，
        # 直接根据 user_change_request 进行修改；只有新建任务才需要调用规划接口生成开发文档。
        if not is_modify_task:
            dev_doc_path = os.path.join(project_dir, DEV_DOC_FILENAME)
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
                    time.sleep(retry_sleep)

                # 扣子生成完成后会自动上传，无需再次上传
                dev_doc_ok = fetch_dev_doc_stream(planner_input, dev_doc_path, user_id)
                if dev_doc_ok:
                    break

            if dev_doc_ok:
                # 强制最少等待一段时间，确保文档内容稳定
                min_wait_seconds = 60 * 2  # 最少等待 2 分钟
                time.sleep(min_wait_seconds)
            else:
                error_msg = "开发文档生成失败：已达到最大重试次数"
                print(f"❌ {error_msg}")
                # 开发文档生成失败通常不可重试（可能是需求问题）
                queue.mark_task_failed(task_id, error_msg=error_msg)
                return False

        # 在开始构建前先点击 newpro.png 并等待1分钟（新建项目和修改项目都需要）
        newpro_clicked = False
        
        # 检查图片文件是否存在
        newpro_path = "btnimg/newpro.png"
        if os.path.exists(newpro_path):
            # 新项目按钮使用更高的匹配度，确保准确识别
            newpro_confidence = 0.8  # 比其他按钮的 0.6 更高
            for retry in range(CONFIG['max_retry_attempts']):
                if wait_and_click(newpro_path, confidence=newpro_confidence, timeout=20, silent=True):
                    newpro_clicked = True
                    # 点击后等待一下，确保界面响应
                    time.sleep(1)
                    # 验证点击是否成功（可以尝试再次查找按钮，如果按钮消失了说明点击成功）
                    try:
                        # 等待0.5秒后检查按钮是否还在（如果点击成功，按钮可能会消失或变化）
                        time.sleep(0.5)
                        check_location = pyautogui.locateCenterOnScreen(newpro_path, confidence=newpro_confidence)
                        if check_location:
                            # 再次点击
                            x, y = check_location
                            pyautogui.moveTo(x, y, duration=0.2)
                            time.sleep(0.2)
                            pyautogui.click()
                            time.sleep(0.3)
                            pyautogui.click()  # 双击确保
                            time.sleep(0.5)
                    except:
                        pass
                    break
                if retry < CONFIG['max_retry_attempts'] - 1:
                    time.sleep(3)
        
        if newpro_clicked:
            time.sleep(60)  # 等待1分钟

        # Step 1：点击输入框
        input_found = False
        for retry in range(CONFIG['max_retry_attempts']):
            # 先尝试 input.png，如果找不到再尝试 input2.png
            if wait_and_click("btnimg/input.png", confidence=CONFIG['min_confidence'], timeout=15):
                input_found = True
                break
            if wait_and_click("btnimg/input2.png", confidence=CONFIG['min_confidence'], timeout=15):
                input_found = True
                break

            if retry < CONFIG['max_retry_attempts'] - 1:
                time.sleep(3)
        
        if not input_found:
            error_msg = "多次尝试后仍找不到输入框"
            print(f"❌ {error_msg}")
            # 这是可重试错误
            if retry_count < CONFIG.get('task_max_retries', 3):
                queue.mark_task_retry(task_id, retry_count + 1, error_msg)
                return False
            else:
                queue.mark_task_failed(task_id, error_msg=f"{error_msg}（已达最大重试次数）")
                return False
        
        time.sleep(1)
        
        # Step 2：生成并输入初始构建提示词（让 AI 先写基础项目）
        prompt = generate_prompt(task)
        
        try:
            pyperclip.copy(prompt)
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            pyautogui.press("delete")
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1)
        except Exception as e:
            error_msg = f"输入提示词时发生错误: {str(e)}"
            print(f"❌ {error_msg}")
            # 判断是否可重试
            if is_retryable_error(e) and retry_count < CONFIG.get('task_max_retries', 3):
                queue.mark_task_retry(task_id, retry_count + 1, error_msg)
                return False
            else:
                queue.mark_task_failed(task_id, error_msg=error_msg)
                return False
        
        # Step 3：点击发送按钮（单击 + 成功标识检测）
        send_clicked = False
        for retry in range(CONFIG['max_retry_attempts']):
            if click_send_with_confirm(
                send_button_image="btnimg/send.png",
                success_image="btnimg/send-success.png",
                confidence=CONFIG['min_confidence'],
                click_timeout=15,
                success_timeout=6,
                max_attempts=1,  # 外层循环已重试
            ):
                send_clicked = True
                break
            elif retry < CONFIG['max_retry_attempts'] - 1:
                time.sleep(3)
        
        if not send_clicked:
            error_msg = "多次尝试后仍找不到发送按钮"
            print(f"❌ {error_msg}")
            # 这是可重试错误
            if retry_count < CONFIG.get('task_max_retries', 3):
                print(f"🔄 任务将在 {CONFIG.get('task_retry_delay', 60)} 秒后重试...")
                queue.mark_task_retry(task_id, retry_count + 1, error_msg)
                return False
            else:
                queue.mark_task_failed(task_id, error_msg=f"{error_msg}（已达最大重试次数）")
                return False

        # 将任务标记为"实现中"
        queue.mark_task_implementing(task_id)

        # Step 4：等待初始项目构建完成
        initial_wait_time = int(CONFIG.get('project_wait_time', 60 * 30)) if not is_modify_task else int(CONFIG.get('modify_project_wait_time', 60 * 20))
        wait_for_project_completion(wait_time=initial_wait_time, is_modify_task=is_modify_task)
        
        # Step 5：逐个任务检查循环
        # 检查任务清单是否存在
        task_tree = load_task_tree(project_dir)
        if not task_tree.get("modules") or len(task_tree.get("modules", [])) == 0:
            if not _generate_task_tree_with_ai(task, project_dir):
                error_msg = "无法生成任务清单"
                print(f"❌ {error_msg}")
                queue.mark_task_failed(task_id, error_msg=error_msg)
                return False
            task_tree = load_task_tree(project_dir)
        
        max_task_rounds = 50  # 最多检查 50 个任务（防止无限循环）
        max_total_rounds = 100  # 总轮次上限（包括 Step 5 和 Step 6 的多次循环）
        total_rounds = 0
        task_round = 0
        
        # 外层循环：允许 Step 5 和 Step 6 互相跳转
        while total_rounds < max_total_rounds:
            total_rounds += 1
            
            # Step 5：逐个任务检查循环
            while task_round < max_task_rounds:
                task_round += 1
                task_tree = load_task_tree(project_dir)  # 重新加载，获取最新状态
                
                # 检查是否所有任务都完成了
                if all_tasks_completed(task_tree):
                    break  # 跳出 Step 5 循环，进入 Step 6
                
                # 找出下一个未完成的任务
                next_task = find_next_unfinished_task(task_tree)
                if not next_task:
                    # 重新检查一次
                    task_tree = load_task_tree(project_dir)
                    if all_tasks_completed(task_tree):
                        break
                    else:
                        continue
                
                # 生成检查提示词
                check_prompt = generate_task_check_prompt(next_task, project_dir)
                
                # 发送检查提示词
                queue.mark_task_implementing(task_id)
                
                # 在发送之前，等待一下确保界面稳定
                time.sleep(3)
                
                send_ok = send_continue_prompt(check_prompt)
                if not send_ok:
                    error_msg = "发送任务检查提示词失败：无法找到输入框或发送按钮"
                    print(f"❌ {error_msg}")
                    queue.mark_task_failed(task_id, error_message=error_msg)
                    return False
                
                # 等待 AI 完成检查和实现
                task_wait_time = int(CONFIG.get('self_check_round_wait_time', 60 * 15))
                wait_for_project_completion(
                    wait_time=task_wait_time,
                    is_modify_task=is_modify_task,
                    task=task,
                    project_dir=project_dir,
                    queue=queue,
                    round_index=task_round
                )
                
                # 检查任务是否被标记为完成
                task_tree_after = load_task_tree(project_dir)
                module_idx = next_task.get("module_index")
                task_idx = next_task.get("task_index")
                
                if module_idx is not None and task_idx is not None:
                    modules_after = task_tree_after.get("modules", [])
                    if module_idx < len(modules_after):
                        tasks_after = modules_after[module_idx].get("tasks", [])
                        if task_idx < len(tasks_after):
                            status_after = tasks_after[task_idx].get("status", "pending")
            
            if task_round >= max_task_rounds:
                error_msg = f"任务检查轮次达到上限（{max_task_rounds}），可能存在问题"
                print(f"❌ {error_msg}")
                queue.mark_task_failed(task_id, error_message=error_msg)
                return False
            
            # Step 6：最终检查（只有从 Step 5 正常完成才执行）
            max_final_rounds = 5
            final_round = 0
            
            while final_round < max_final_rounds:
                final_round += 1
                
                # 在最终检查前先点击新项目按钮，创建全新上下文
                newpro_clicked = False
                newpro_path = "btnimg/newpro.png"
                if os.path.exists(newpro_path):
                    newpro_confidence = 0.8  # 使用更高的匹配度
                    for retry in range(CONFIG['max_retry_attempts']):
                        if wait_and_click(newpro_path, confidence=newpro_confidence, timeout=20, silent=True):
                            newpro_clicked = True
                            # 点击后等待一下，确保界面响应
                            time.sleep(1)
                            # 验证点击是否成功
                            try:
                                time.sleep(0.5)
                                check_location = pyautogui.locateCenterOnScreen(newpro_path, confidence=newpro_confidence)
                                if check_location:
                                    x, y = check_location
                                    pyautogui.moveTo(x, y, duration=0.2)
                                    time.sleep(0.2)
                                    pyautogui.click()
                                    time.sleep(0.3)
                                    pyautogui.click()  # 双击确保
                                    time.sleep(0.5)
                            except:
                                pass
                            break
                        if retry < CONFIG['max_retry_attempts'] - 1:
                            time.sleep(3)
                
                if newpro_clicked:
                    time.sleep(2)  # 等待界面响应，不需要像Step 0.5那样等1分钟
                
                # 生成最终检查提示词
                final_check_prompt = generate_final_check_prompt(project_dir)
                
                # 发送最终检查提示词
                send_ok = send_continue_prompt(final_check_prompt)
                if not send_ok:
                    error_msg = "发送最终检查提示词失败"
                    print(f"❌ {error_msg}")
                    queue.mark_task_failed(task_id, error_message=error_msg)
                    return False
                
                # 等待 AI 完成检查
                wait_for_project_completion(
                    wait_time=int(CONFIG.get('self_check_round_wait_time', 60 * 15)),
                    is_modify_task=is_modify_task,
                    task=task,
                    project_dir=project_dir,
                    queue=queue,
                    round_index=1000 + final_round  # 用大数字区分最终检查轮次
                )
                
                # 检查任务清单状态（包含最终检查次数）
                task_tree_final = load_task_tree(project_dir)
                final_check_count = task_tree_final.get("final_check_count", 0)

                if all_tasks_completed(task_tree_final) and final_check_count >= 1:
                    queue.mark_task_review(task_id)
                    return True
                else:
                    stats_final = get_all_tasks_status(task_tree_final)
                    if final_round < max_final_rounds:
                        # 重置 task_round，重新开始 Step 5 循环
                        task_round = 0
                        break  # 跳出 Step 6 循环，回到外层 while 循环，重新进入 Step 5
                    else:
                        error_msg = f"最终检查多轮后仍有未完成任务或 final_check_count 始终小于 1"
                        print(f"❌ {error_msg}")
                        queue.mark_task_failed(task_id, error_message=error_msg)
                        return False
            
            # 如果从 Step 6 正常完成（所有任务都 completed），会 return True，不会到这里
            # 如果从 Step 6 break（发现遗漏），会继续外层 while 循环，重新进入 Step 5
            # task_round 已被重置为 0，所以会重新开始 Step 5 的循环
        
        if total_rounds >= max_total_rounds:
            error_msg = f"总轮次达到上限（{max_total_rounds}），可能存在问题"
            print(f"❌ {error_msg}")
            queue.mark_task_failed(task_id, error_message=error_msg)
            return False
        
    except pyautogui.FailSafeException as e:
        error_msg = "处理任务时触发 PyAutoGUI FAILSAFE：请避免将鼠标移动到屏幕角落"
        print(f"❌ {error_msg}")
        # FailSafe 异常不可重试（用户操作导致）
        queue.mark_task_failed(task_id, error_msg=error_msg)
        return False
    except Exception as e:
        error_msg = f"处理任务时发生错误: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        # 判断是否可重试
        if is_retryable_error(e) and retry_count < CONFIG.get('task_max_retries', 3):
            print(f"🔄 任务将在 {CONFIG.get('task_retry_delay', 60)} 秒后重试...")
            queue.mark_task_retry(task_id, retry_count + 1, error_msg)
            return False
        else:
            queue.mark_task_failed(task_id, error_msg=error_msg)
            return False

def handle_token_exhausted():
    """
    处理 Token 耗尽，自动切换账号
    流程：
    1. 检测 Token 耗尽提示
    2. 点击切换账号按钮
    3. 等待2秒后点击确认切换
    4. 等待5秒后点击切换完成
    5. 检测输入框，输入"继续构建代码"并发送
    """
    try:
        # Step 1: 点击切换账号按钮
        if not wait_and_click("btnimg/Switchaccount.png", confidence=CONFIG['min_confidence'], timeout=10):
            return False
        
        time.sleep(2)  # 等待2秒
        
        # Step 2: 点击确认切换按钮
        if not wait_and_click("btnimg/Confirmswitch.png", confidence=CONFIG['min_confidence'], timeout=10):
            return False
        
        time.sleep(5)  # 等待5秒
        
        # Step 3: 点击切换完成按钮
        if not wait_and_click("btnimg/Switchingcomplete.png", confidence=CONFIG['min_confidence'], timeout=10):
            return False
        
        time.sleep(2)  # 等待界面稳定
        
        # Step 4: 检测输入框并输入"继续构建代码"
        input_found = False
        input_location = None
        
        # 先尝试 input.png
        for retry in range(CONFIG['max_retry_attempts']):
            try:
                location = pyautogui.locateCenterOnScreen("btnimg/input.png", confidence=CONFIG['min_confidence'])
                if location:
                    x, y = location
                    pyautogui.moveTo(x, y, duration=random.uniform(0.2, 0.4))
                    pyautogui.click()
                    input_location = (x, y)
                    input_found = True
                    break
            except pyautogui.ImageNotFoundException:
                pass
            except Exception as e:
                pass
            
            # 如果 input.png 没找到，尝试 input2.png
            if not input_found:
                try:
                    location = pyautogui.locateCenterOnScreen("btnimg/input2.png", confidence=CONFIG['min_confidence'])
                    if location:
                        x, y = location
                        pyautogui.moveTo(x, y, duration=random.uniform(0.2, 0.4))
                        pyautogui.click()
                        input_location = (x, y)
                        input_found = True
                        break
                except pyautogui.ImageNotFoundException:
                    pass
                except Exception as e:
                    pass
            
            if not input_found and retry < CONFIG['max_retry_attempts'] - 1:
                time.sleep(3)
        
        if not input_found:
            return False
        
        # 等待输入框获得焦点
        time.sleep(2)
        
        # 再次点击输入框确保焦点（在找到的位置）
        x, y = input_location
        pyautogui.moveTo(x, y, duration=0.2)
        pyautogui.click()
        time.sleep(1)
        
        # 再次点击确保焦点
        pyautogui.click()
        time.sleep(0.5)
        
        # 输入"继续构建代码"
        follow_up_prompt = "继续执行任务，不要执行一半然后停止，要直接完成全部任务，我会审查所有文档里面提到的功能模块，你要是不给我写完整我就一直让你写"
        
        try:
            # 复制到剪贴板
            pyperclip.copy(follow_up_prompt)
            time.sleep(0.5)
            
            # 清空输入框：全选并删除
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.3)
            pyautogui.press("backspace")  # 使用 backspace 而不是 delete
            time.sleep(0.2)
            pyautogui.press("delete")  # 双重保险
            time.sleep(0.3)
            
            # 粘贴内容
            pyautogui.hotkey("ctrl", "v")
            time.sleep(2)  # 增加等待时间，确保粘贴完成
            
            # 再次确保：如果粘贴失败，尝试直接输入
            # 检查剪贴板内容
            clipboard_check = pyperclip.paste()
            if clipboard_check != follow_up_prompt:
                pyperclip.copy(follow_up_prompt)
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.2)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(2)
            
        except Exception as input_err:
            import traceback
            traceback.print_exc()
            # 备用方法：直接输入文本（逐字符输入）
            try:
                # 先清空
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.2)
                pyautogui.press("delete")
                time.sleep(0.3)
                # 直接输入
                pyautogui.write(follow_up_prompt, interval=0.05)
                time.sleep(2)  # 增加等待时间
            except Exception as write_err:
                return False
        
        # Step 5: 点击发送按钮（单击 + 成功标识检测）
        # 等待一下，确保输入框内容已完全输入
        time.sleep(1)
        
        send_clicked = False
        for retry in range(CONFIG['max_retry_attempts']):
            if click_send_with_confirm(
                send_button_image="btnimg/send.png",
                success_image="btnimg/send-success.png",
                confidence=CONFIG['min_confidence'],
                click_timeout=15,
                success_timeout=6,
                max_attempts=1,  # 外层循环已重试
            ):
                send_clicked = True
                # 点击后等待一下，确保发送生效
                time.sleep(1)
                break
            elif retry < CONFIG['max_retry_attempts'] - 1:
                time.sleep(3)
        
        if not send_clicked:
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 处理 Token 切换时发生错误: {e}")
        traceback.print_exc()
        return False

def check_token_exhausted():
    """
    检测屏幕上是否有 Token 耗尽提示
    返回 True 如果检测到，False 如果未检测到
    """
    try:
        location = pyautogui.locateCenterOnScreen(
            "btnimg/Tokensexhausted.png", 
            confidence=CONFIG['min_confidence']
        )
        return location is not None
    except pyautogui.ImageNotFoundException:
        return False
    except Exception:
        return False

def monitor_token_exhaustion():
    """
    后台线程：定期检测 Token 耗尽并自动切换账号
    每5分钟检测一次
    """
    global running
    while running:
        try:
            # 检测是否有 Token 耗尽提示（只检测，不点击）
            if check_token_exhausted():
                # 如果检测到 Token 耗尽提示，执行切换流程
                handle_token_exhausted()
        except Exception as e:
            print(f"❌ Token 检测线程发生错误: {e}")
            traceback.print_exc()
        
        # 等待检测间隔
        for _ in range(CONFIG['token_check_interval']):
            if not running:
                break
            time.sleep(1)
    
    print("🛑 Token 检测线程已停止")

def scan_new_tasks(queue):
    """
    定时扫描数据库，刷新任务队列
    为了避免“有任务但扫描不到”的问题，这里采用【全量刷新】策略：
    - 每次扫描直接调用 queue.load_tasks() 从数据库重新加载待处理任务
    - 具体是否需要再次处理，由数据库中的 task_status 决定（pending/user_change/review_change/pending_modify）
    这样可以保证：只要数据库里有待处理任务，本进程一定能在下一次扫描时看到
    """
    global running
    while running:
        try:
            # 每次只补充到「待处理任务最多 10 个」
            added = queue.top_up_tasks(max_total=10)
            pending = queue.get_pending_count()
            log_info(f"📥 本次扫描数据库，新增 {added} 个任务，当前待处理: {pending} 个（上限 10）")
        except Exception as e:
            print(f"❌ 扫描新任务时发生错误: {e}")
            traceback.print_exc()  # 打印完整错误堆栈，便于调试
        except Exception:
            # 捕获所有异常，确保线程不会因为意外错误而退出
            print(f"❌ 扫描新任务时发生未知错误")
            traceback.print_exc()
        
        # 使用单次 sleep，在循环开始检查 running 状态
        if not running:
            break

        # 每 8 小时执行一次：拆成每秒检查 running，避免无法优雅退出
        for _ in range(SCAN_INTERVAL):
            if not running:
                break
            time.sleep(1)

def cleanup_resources():
    """
    定期清理资源：内存清理、连接池清理等
    """
    global running
    cleanup_interval = CONFIG.get('resource_cleanup_interval', 3600)  # 默认1小时
    
    while running:
        try:
            time.sleep(cleanup_interval)
            
            if not running:
                break
            
            # 1. 强制垃圾回收
            gc.collect()
            
            # 2. 清理连接池（关闭空闲连接）
            try:
                cleanup_connection_pool()
            except Exception as e:
                pass
            
        except Exception as e:
            print(f"⚠️  资源清理时发生错误: {e}")
            traceback.print_exc()

def main():
    """
    主函数：持续运行，定时扫描数据库并处理任务
    """
    global running
    
    log_info("="*60)
    log_info("🚀 自动化任务处理系统启动（持续运行模式）")
    log_info("="*60)
    log_info(f"⏰ 每个项目固定等待时间: {CONFIG['project_wait_time']} 秒（{CONFIG['project_wait_time']/3600} 小时）")
    log_info(f"📡 定时扫描间隔: {SCAN_INTERVAL} 秒（{SCAN_INTERVAL // 60} 分钟）")
    log_info("\n请确保 Cursor 已打开，AI 输入框、发送按钮都可见。")
    log_info("准备时间：5秒...")
    log_info("提示：按 Ctrl+C 可停止程序\n")
    time.sleep(5)
    
    queue = TaskQueue()
    
    log_info("\n📥 正在从数据库加载初始待办任务...")
    initial_count = queue.load_tasks()
    log_info(f"✅ 已加载 {initial_count} 个待办任务\n")
    
    scan_thread = threading.Thread(target=scan_new_tasks, args=(queue,), daemon=True)
    scan_thread.start()
    log_info(f"✅ 后台扫描线程已启动，每 {SCAN_INTERVAL} 秒扫描一次数据库\n")
    
    # 启动 Token 检测线程
    token_monitor_thread = threading.Thread(target=monitor_token_exhaustion, daemon=True)
    token_monitor_thread.start()
    log_info(f"✅ Token 检测线程已启动，每 {CONFIG['token_check_interval']} 秒检测一次 Token 状态\n")
    
    # 启动资源清理线程
    cleanup_thread = threading.Thread(target=cleanup_resources, daemon=True)
    cleanup_thread.start()
    cleanup_interval_hours = CONFIG.get('resource_cleanup_interval', 3600) / 3600
    log_info(f"✅ 资源清理线程已启动，每 {cleanup_interval_hours} 小时清理一次资源\n")
    
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
                        time.sleep(60)
            else:
                log_info(f"⏳ 队列为空，等待新任务... (每 {SCAN_INTERVAL} 秒自动扫描)")
                for _ in range(10):
                    if not running:
                        break
                    if queue.has_more_tasks():
                        break
                    time.sleep(1)
            
    
    except KeyboardInterrupt:
        running = False
    except Exception as e:
        # 捕获所有未预期的异常，确保程序不会意外退出
        print(f"\n\n❌ 主循环发生未预期的错误: {e}")
        traceback.print_exc()
        running = False
    
    finally:
        running = False
        
        # 清理资源
        try:
            cleanup_connection_pool()
            gc.collect()
        except Exception as e:
            pass
        
        # 等待所有线程结束
        scan_thread.join(timeout=5)
        token_monitor_thread.join(timeout=2)
        cleanup_thread.join(timeout=2)
        
        print("\n" + "="*60)
        print("📊 最终统计信息")
        print("="*60)
        print(f"❌ 失败: {fail_count} 个")
        print("="*60)

if __name__ == "__main__":
    main()
