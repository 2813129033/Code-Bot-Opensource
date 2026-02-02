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
import http.client
from task_queue import TaskQueue
from db_connector import cleanup_connection_pool

pyautogui.FAILSAFE = True

# 全局变量
SCAN_INTERVAL = 30  # 扫描间隔（秒），默认30秒
running = True  # 控制程序运行状态

# ==================== 配置参数 ====================
CONFIG = {
    'min_confidence': 0.6,  # 最低图片匹配置信度
    'max_retry_attempts': 3,  # 最大重试次数（图片识别等操作）
    'project_wait_time': 5400,  # 每个项目固定等待时间：1.5小时 = 5400秒
    # 2-3万字文档，接口整体可能较慢，这里给到 20 分钟超时
    'dev_doc_timeout': 60 * 20,  # 开发文档接口最大等待时间（秒）
    'dev_doc_retry_attempts': 2,  # 开发文档生成失败后重试次数
    'dev_doc_retry_sleep': 10,  # 重试前等待（秒）
    'token_check_interval': 60 * 5,  # Token 检测间隔：5分钟 = 300秒
    'task_max_retries': 3,  # 任务最大重试次数（整个任务失败后）
    'task_retry_delay': 60,  # 任务重试前等待时间（秒）
    'resource_cleanup_interval': 3600,  # 资源清理间隔（秒），1小时
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

                        print("⚠️ 检测到 IncompleteRead，但已写入所有可用内容，视为开发文档生成成功。")
                        # 扣子生成完成后立即上传
                        if user_id:
                            print(f"📤 扣子生成完成，立即上传开发文档到 192.168.5.5:3000/save-md...")
                            upload_success = upload_dev_document(output_path, user_id)
                            if not upload_success:
                                print("⚠️ 开发文档上传失败，但继续后续流程")
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
            print(f"📤 扣子生成完成，立即上传开发文档到 192.168.5.5:3000/save-md...")
            upload_success = upload_dev_document(output_path, user_id)
            if not upload_success:
                print("⚠️ 开发文档上传失败，但继续后续流程")

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
                print(f"✅ 开发文档上传成功: {upload_url} (用户ID: {user_id})")
                if response_data:
                    print(f"   响应: {response_data[:200]}")
                return True
                    
        except (urllib.error.HTTPError, ConnectionResetError, OSError) as e:
            if attempt < max_retries - 1:
                retry_delay = base_retry_delay * (2 ** attempt)  # 指数退避：2秒、4秒、8秒
                print(f"⚠️ 上传开发文档失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                print(f"   等待 {retry_delay} 秒后重试...")
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

def wait_and_click(image_path, confidence=0.8, timeout=10, click_offset=(0, 0), silent=False):
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
                pyautogui.moveTo(x + click_offset[0], y + click_offset[1], duration=random.uniform(0.2, 0.4))
                pyautogui.click()
                return True
        except pyautogui.ImageNotFoundException:
            pass
        except Exception as e:
            if not silent:
                print(f"⚠️  查找图片时发生异常: {e}")
        
        attempt += 1
        
        # 动态调整扫描间隔：每3秒增加0.2秒，最多到2秒
        current_time = time.time()
        elapsed = current_time - start_time
        time_since_last_increase = current_time - last_interval_increase_time
        
        if time_since_last_increase >= interval_increase_threshold:
            if current_interval < max_interval:
                current_interval = min(current_interval + 0.2, max_interval)
                last_interval_increase_time = current_time
        
        if not silent and attempt % 10 == 0:
            elapsed_int = int(elapsed)
            print(f"   正在查找 {image_path}... ({elapsed_int}/{timeout}秒, 扫描间隔: {current_interval:.1f}秒)")
        
        time.sleep(current_interval)
    
    if not silent:
        print(f"❌ 未找到 {image_path} (超时: {timeout}秒)")
    return False

def wait_for_project_completion(wait_time=None, is_modify_task=False):
    """
    固定等待项目完成（不检测任何按钮）
    新建项目默认等待 1.5 小时，修改项目可缩短为 30 分钟
    对于新建项目，在等待1小时后会自动输入提示词继续推进项目
    """
    # 根据任务类型决定等待时间
    if wait_time is None:
        if is_modify_task:
            # 修改任务：可配置，默认 30 分钟
            wait_time = int(CONFIG.get('modify_project_wait_time', 60 * 30))
        else:
            # 新建任务：1.5 小时配置
            wait_time = int(CONFIG.get('project_wait_time', 60 * 90))

    wait_hours = wait_time / 3600
    one_hour_seconds = 60 * 60  # 1小时 = 3600秒
    
    print(f"⏰ 等待项目完成...")
    print(f"   固定等待时间: {wait_hours} 小时（{wait_time} 秒）")
    print(f"   开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   预计完成: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + wait_time))}")
    if not is_modify_task:
        print(f"   ⚠️  将在1小时后自动输入提示词继续推进项目")
    print()
    
    start_time = time.time()
    one_hour_triggered = False  # 标记是否已经触发1小时后的操作
    
    while time.time() - start_time < wait_time:
        elapsed = int(time.time() - start_time)
        remaining = wait_time - elapsed
        
        # 对于新建项目，在等待1小时后自动输入提示词
        if not is_modify_task and not one_hour_triggered and elapsed >= one_hour_seconds:
            one_hour_triggered = True
            print(f"\n⏰ 已等待1小时，开始输入提示词继续推进项目...")
            
            try:
                # 查找并点击输入框（使用与初始输入相同的方法）
                input_found = False
                input_location = None
                
                for retry in range(CONFIG['max_retry_attempts']):
                    # 先尝试 input.png
                    try:
                        location = pyautogui.locateCenterOnScreen("btnimg/input.png", confidence=CONFIG['min_confidence'])
                        if location:
                            x, y = location
                            pyautogui.moveTo(x, y, duration=random.uniform(0.2, 0.4))
                            pyautogui.click()
                            input_location = (x, y)
                            input_found = True
                            print(f"   ✅ 找到输入框 (input.png) 位置: ({x}, {y})")
                            break
                    except pyautogui.ImageNotFoundException:
                        pass
                    except Exception as e:
                        print(f"   ⚠️  查找 input.png 时发生异常: {e}")
                    
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
                                print(f"   ✅ 找到输入框 (input2.png) 位置: ({x}, {y})")
                                break
                        except pyautogui.ImageNotFoundException:
                            pass
                        except Exception as e:
                            print(f"   ⚠️  查找 input2.png 时发生异常: {e}")
                    
                    if not input_found and retry < CONFIG['max_retry_attempts'] - 1:
                        print(f"   ⚠️  第 {retry + 1} 次尝试失败，{3}秒后重试...")
                        time.sleep(3)
                
                if input_found and input_location:
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
                    
                    # 输入提示词
                    follow_up_prompt = "将项目实现完整，完全按照文档实现，功能全部都要实现，不要问我任何问题，直接开始写，数据库文件中写一些基础假数据"
                    print(f"📝 输入提示词: {follow_up_prompt}")
                    
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
                            print(f"   ⚠️  剪贴板内容不匹配，重新复制...")
                            pyperclip.copy(follow_up_prompt)
                            time.sleep(0.3)
                            pyautogui.hotkey("ctrl", "a")
                            time.sleep(0.2)
                            pyautogui.hotkey("ctrl", "v")
                            time.sleep(1)
                        
                        print("✅ 提示词已输入")
                        
                    except Exception as input_err:
                        print(f"⚠️  输入提示词时发生错误: {input_err}，尝试备用方法...")
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
                            print("✅ 提示词已输入（使用备用方法：直接输入）")
                        except Exception as write_err:
                            print(f"⚠️  备用输入方法也失败: {write_err}")
                            print("⚠️  但继续执行后续流程...")
                    
                    # 点击发送按钮
                    send_clicked = False
                    for retry in range(CONFIG['max_retry_attempts']):
                        if wait_and_click("btnimg/send.png", confidence=CONFIG['min_confidence'], timeout=15):
                            send_clicked = True
                            break
                        elif retry < CONFIG['max_retry_attempts'] - 1:
                            print(f"   ⚠️  第 {retry + 1} 次尝试失败，{3}秒后重试...")
                            time.sleep(3)
                    
                    if send_clicked:
                        print("✅ 提示词已发送，继续等待项目完成...")
                    else:
                        print("⚠️  发送按钮未找到，但继续等待项目完成...")
                else:
                    print("⚠️  输入框未找到，但继续等待项目完成...")
                    
            except Exception as e:
                print(f"⚠️  1小时后输入提示词时发生错误: {e}，但继续等待项目完成...")
        
        # 每5分钟显示一次进度
        if elapsed % 300 == 0 and elapsed > 0:
            progress = (elapsed / wait_time) * 100
            print(f"   ⏳ 项目生成中... 进度: {progress:.1f}% ({elapsed}秒 / {wait_time}秒，剩余 {remaining}秒)")
        
        time.sleep(10)  # 每10秒检查一次
    
    print(f"\n✅ 等待时间已到（{wait_hours} 小时），认为项目已完成")
    return True

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

        prompt = (
            f"找到user_project文件夹下面的{user_id}项目，先完整理解下面这些修改依据：{change_text}。"
            f"然后在当前项目基础上进行修改并彻底解决上述所有问题，保持原有功能正常可用。"
            f"修改完成后将当前项目除文档之外的压缩到user_project_zip里面，如果覆盖不了就先删除之前的{user_id}.zip文件，然后再压缩进去。"
        )
    else:
        # 新建项目
        prompt = (
            f"在{user_id}文件夹按照开发文档和开发规范这俩个文档开始开发项目。要着重注意开发规范里面的代码规范，避免出现里面的问题。务必要将开发文档里面的功能和页面全部实现。一次性实现全部，永远不要问我要不要继续，直接完成全部功能。"
            f"最后将当前项目除文档之外的压缩到user_project_zip里面。"
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
    
    print(f"\n{'='*60}")
    print(f"📋 开始处理任务 [{task_number}/{queue.get_total_tasks()}]")
    print(f"   任务ID: {task_id}")
    print(f"   用户ID: {user_id}")
    print(f"   项目类型: {task.get('task_type', '')}")
    if retry_count > 0:
        print(f"   ⚠️  这是第 {retry_count + 1} 次尝试（已重试 {retry_count} 次）")
    print(f"{'='*60}\n")
    
    queue.mark_task_processing(task_id)
    
    try:
        # Step 0：准备用户项目目录与文档
        print("📍 Step 0: 准备用户项目目录与文档...")
        user_dir = prepare_user_project_dir(user_id)
        print(f"✅ 用户项目目录已准备: {user_dir}")

        copied = copy_dev_spec_to_project(user_dir)
        if copied:
            print(f"✅ 已复制 {DEV_SPEC_FILENAME}")

        # 对于“修改项目”任务（pending_modify），不再重新拉取开发文档，
        # 直接根据 user_change_request 进行修改；只有新建任务才需要调用规划接口生成开发文档。
        if not is_modify_task:
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

                print(f"📝 正在生成开发文档（预计约 20 分钟，超时 {CONFIG.get('dev_doc_timeout', 0)} 秒）...")
                # 扣子生成完成后会自动上传，无需再次上传
                dev_doc_ok = fetch_dev_doc_stream(planner_input, dev_doc_path, user_id)
                if dev_doc_ok:
                    break

            if dev_doc_ok:
                print(f"✅ 开发文档已生成并已上传: {dev_doc_path}")
                
                # 强制最少等待一段时间，确保文档内容稳定
                min_wait_seconds = 60 * 2  # 最少等待 2 分钟
                print(f"⏳ 为确保开发文档内容稳定，额外等待 {min_wait_seconds // 60} 分钟...")
                time.sleep(min_wait_seconds)
                print("✅ 最少等待时间已结束，开始后续开发流程")
            else:
                error_msg = "开发文档生成失败：已达到最大重试次数"
                print(f"❌ {error_msg}")
                # 开发文档生成失败通常不可重试（可能是需求问题）
                queue.mark_task_failed(task_id, error_msg=error_msg)
                return False

        # 在开始构建前先点击 newpro.png 并等待1分钟（新建项目和修改项目都需要）
        print("📍 Step 0.5: 点击新项目按钮...")
        newpro_clicked = False
        for retry in range(CONFIG['max_retry_attempts']):
            if wait_and_click("btnimg/newpro.png", confidence=CONFIG['min_confidence'], timeout=15):
                newpro_clicked = True
                break
            if retry < CONFIG['max_retry_attempts'] - 1:
                print(f"   ⚠️  第 {retry + 1} 次尝试失败，{3}秒后重试...")
                time.sleep(3)
        
        if newpro_clicked:
            task_type_text = "修改项目" if is_modify_task else "新建项目"
            print(f"✅ 已点击新项目按钮，等待1分钟后开始{task_type_text}构建...")
            time.sleep(60)  # 等待1分钟
            print("✅ 等待时间已到，开始构建项目")
        else:
            print("⚠️  未找到新项目按钮，但继续执行后续流程...")

        # Step 1：点击输入框
        print("📍 Step 1: 查找并点击输入框...")
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
                print(f"   ⚠️  第 {retry + 1} 次尝试失败，{3}秒后重试...")
                time.sleep(3)
        
        if not input_found:
            error_msg = "多次尝试后仍找不到输入框"
            print(f"❌ {error_msg}")
            # 这是可重试错误
            if retry_count < CONFIG.get('task_max_retries', 3):
                print(f"🔄 任务将在 {CONFIG.get('task_retry_delay', 60)} 秒后重试...")
                queue.mark_task_retry(task_id, retry_count + 1, error_msg)
                return False
            else:
                queue.mark_task_failed(task_id, error_msg=f"{error_msg}（已达最大重试次数）")
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
            error_msg = f"输入提示词时发生错误: {str(e)}"
            print(f"❌ {error_msg}")
            # 判断是否可重试
            if is_retryable_error(e) and retry_count < CONFIG.get('task_max_retries', 3):
                print(f"🔄 任务将在 {CONFIG.get('task_retry_delay', 60)} 秒后重试...")
                queue.mark_task_retry(task_id, retry_count + 1, error_msg)
                return False
            else:
                queue.mark_task_failed(task_id, error_msg=error_msg)
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
        
        print("✅ 已发送提示词")
        
        # Step 4：固定等待项目完成
        # 新建项目一般需要完整生成时间（默认 1 小时），
        # 修改项目可以适当缩短（默认 30 分钟，可通过 CONFIG['modify_project_wait_time'] 调整）
        print("\n📍 Step 4: 等待项目完成...")
        wait_for_project_completion(is_modify_task=is_modify_task)
        
        # 开发完成后进入待审核状态
        queue.mark_task_review(task_id)
        print(f"\n✅ 任务 {task_id} 开发完成，已进入待审核(review)状态！\n")
        return True
        
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
        print("\n🔄 检测到 Token 耗尽，开始自动切换账号...")
        
        # Step 1: 点击切换账号按钮
        print("📍 Step 1: 点击切换账号按钮...")
        if not wait_and_click("btnimg/Switchaccount.png", confidence=CONFIG['min_confidence'], timeout=10):
            print("⚠️  未找到切换账号按钮，可能 Token 提示已消失")
            return False
        
        print("✅ 已点击切换账号按钮")
        time.sleep(2)  # 等待2秒
        
        # Step 2: 点击确认切换按钮
        print("📍 Step 2: 点击确认切换按钮...")
        if not wait_and_click("btnimg/Confirmswitch.png", confidence=CONFIG['min_confidence'], timeout=10):
            print("⚠️  未找到确认切换按钮")
            return False
        
        print("✅ 已点击确认切换按钮")
        time.sleep(5)  # 等待5秒
        
        # Step 3: 点击切换完成按钮
        print("📍 Step 3: 点击切换完成按钮...")
        if not wait_and_click("btnimg/Switchingcomplete.png", confidence=CONFIG['min_confidence'], timeout=10):
            print("⚠️  未找到切换完成按钮")
            return False
        
        print("✅ 已点击切换完成按钮")
        time.sleep(2)  # 等待界面稳定
        
        # Step 4: 检测输入框并输入"继续构建代码"
        print("📍 Step 4: 检测输入框并输入'继续构建代码'...")
        if not wait_and_click("btnimg/input.png", confidence=CONFIG['min_confidence'], timeout=15):
            print("⚠️  未找到输入框")
            return False
        
        # 输入"继续构建代码"
        try:
            pyperclip.copy("继续构建代码")
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.2)
            pyautogui.press("delete")
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1)
            print("✅ 已输入'继续构建代码'")
        except Exception as e:
            print(f"❌ 输入文本时发生错误: {e}")
            return False
        
        # Step 5: 点击发送按钮
        print("📍 Step 5: 点击发送按钮...")
        if not wait_and_click("btnimg/send.png", confidence=CONFIG['min_confidence'], timeout=15):
            print("⚠️  未找到发送按钮")
            return False
        
        print("✅ 已点击发送按钮")
        print("🎉 Token 切换完成，已发送'继续构建代码'指令\n")
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
    定时扫描数据库，添加新任务到队列
    优化：使用单次 sleep 而不是循环，减少 CPU 占用
    """
    global running
    while running:
        try:
            queue.add_new_tasks()
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
        time.sleep(SCAN_INTERVAL)

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
            
            print("\n🧹 开始资源清理...")
            
            # 1. 强制垃圾回收
            collected = gc.collect()
            print(f"   ✅ 垃圾回收完成，回收了 {collected} 个对象")
            
            # 2. 清理连接池（关闭空闲连接）
            try:
                cleanup_connection_pool()
                print("   ✅ 连接池清理完成")
            except Exception as e:
                print(f"   ⚠️  连接池清理失败: {e}")
            
            print("✅ 资源清理完成\n")
            
        except Exception as e:
            print(f"⚠️  资源清理时发生错误: {e}")
            traceback.print_exc()

def main():
    """
    主函数：持续运行，定时扫描数据库并处理任务
    """
    global running
    
    print("="*60)
    print("🚀 自动化任务处理系统启动（持续运行模式）")
    print("="*60)
    print(f"⏰ 每个项目固定等待时间: {CONFIG['project_wait_time']} 秒（{CONFIG['project_wait_time']/3600} 小时）")
    print(f"📡 定时扫描间隔: {SCAN_INTERVAL} 秒（{SCAN_INTERVAL // 60} 分钟）")
    print("\n请确保 Cursor 已打开，AI 输入框、发送按钮都可见。")
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
    
    # 启动 Token 检测线程
    token_monitor_thread = threading.Thread(target=monitor_token_exhaustion, daemon=True)
    token_monitor_thread.start()
    print(f"✅ Token 检测线程已启动，每 {CONFIG['token_check_interval']} 秒检测一次 Token 状态\n")
    
    # 启动资源清理线程
    cleanup_thread = threading.Thread(target=cleanup_resources, daemon=True)
    cleanup_thread.start()
    cleanup_interval_hours = CONFIG.get('resource_cleanup_interval', 3600) / 3600
    print(f"✅ 资源清理线程已启动，每 {cleanup_interval_hours} 小时清理一次资源\n")
    
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
    except Exception as e:
        # 捕获所有未预期的异常，确保程序不会意外退出
        print(f"\n\n❌ 主循环发生未预期的错误: {e}")
        traceback.print_exc()
        running = False
    
    finally:
        running = False
        
        # 清理资源
        print("\n🧹 正在清理资源...")
        try:
            cleanup_connection_pool()
            gc.collect()
            print("✅ 资源清理完成")
        except Exception as e:
            print(f"⚠️  资源清理失败: {e}")
        
        # 等待所有线程结束
        scan_thread.join(timeout=5)
        if scan_thread.is_alive():
            print("⚠️  扫描线程未能在超时时间内结束")
        
        token_monitor_thread.join(timeout=2)
        cleanup_thread.join(timeout=2)
        
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
