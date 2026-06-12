"""
固定区域截图工具
使用方法：
1. 运行脚本
2. 用鼠标框选截图区域
3. 按 N 截图
4. 按 Y 自动循环截图（检测媒体播放器窗口）
5. 按 ESC 退出
"""

import pyautogui
import pygetwindow as gw
import tkinter as tk
from pynput import keyboard
import time
import os
import threading

# 全局变量保存截图区域
region = None
# 截图保存目录
save_dir = r"E:\CozyHome\temp\scot"
# 自动截图循环控制
auto_screenshot_running = False
# 鼠标初始位置（用于检测移动）
mouse_start_pos = None

def select_region():
    """让用户框选区域，按住 SHIFT 强制正方形"""
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.3)
    root.attributes('-topmost', True)

    canvas = tk.Canvas(root, cursor="cross")
    canvas.pack(fill=tk.BOTH, expand=True)

    start_x = start_y = 0
    rect = None

    def on_press(event):
        nonlocal start_x, start_y, rect
        start_x = event.x
        start_y = event.y
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

    def on_drag(event):
        nonlocal rect
        dx = event.x - start_x
        dy = event.y - start_y
        # 按住 SHIFT 强制正方形
        if event.state & 0x0001:  # SHIFT
            size = max(abs(dx), abs(dy))
            end_x = start_x + size if dx >= 0 else start_x - size
            end_y = start_y + size if dy >= 0 else start_y - size
        else:
            end_x = event.x
            end_y = event.y
        canvas.coords(rect, start_x, start_y, end_x, end_y)

    def on_release(event):
        global region
        dx = event.x - start_x
        dy = event.y - start_y
        # 按住 SHIFT 强制正方形
        if event.state & 0x0001:  # SHIFT
            size = max(abs(dx), abs(dy))
            end_x = start_x + size if dx >= 0 else start_x - size
            end_y = start_y + size if dy >= 0 else start_y - size
        else:
            end_x = event.x
            end_y = event.y
        x1 = min(start_x, end_x)
        y1 = min(start_y, end_y)
        x2 = max(start_x, end_x)
        y2 = max(start_y, end_y)
        region = (x1, y1, x2-x1, y2-y1)
        root.destroy()

    canvas.bind('<ButtonPress-1>', on_press)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<ButtonRelease-1>', on_release)

    root.mainloop()

def take_screenshot():
    """截取之前框选的区域"""
    if region:
        # 创建保存目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        screenshot = pyautogui.screenshot(region=region)
        timestamp = int(time.time() * 1000)
        filename = f'{save_dir}/screenshot_{timestamp}.png'
        screenshot.save(filename)
        print(f'截图已保存: {filename}')
    else:
        print('请先框选截图区域！')

def find_media_player_window():
    """查找媒体播放器窗口"""
    try:
        windows = gw.getWindowsWithTitle('媒体播放器')
        if windows:
            return windows[0]
    except Exception as e:
        print(f"查找窗口失败: {e}")
    return None

def auto_screenshot_loop():
    """自动循环截图"""
    global auto_screenshot_running, mouse_start_pos

    # 查找媒体播放器窗口
    win = find_media_player_window()
    if not win:
        print("未找到媒体播放器窗口")
        auto_screenshot_running = False
        return

    print(f"找到窗口: {win.title}")
    print("开始自动截图循环...")

    # 激活窗口
    try:
        win.activate()
        time.sleep(0.5)
    except Exception as e:
        print(f"激活窗口失败: {e}")

    # 记录鼠标初始位置
    mouse_start_pos = pyautogui.position()
    print(f"记录鼠标初始位置: {mouse_start_pos}")

    # 等待4秒
    print("等待2秒...")
    time.sleep(2)

    # 循环截图
    loop_count = 0
    while auto_screenshot_running:
        # 检测鼠标是否移动
        current_pos = pyautogui.position()
        if mouse_start_pos and (abs(current_pos[0] - mouse_start_pos[0]) > 10 or
                                abs(current_pos[1] - mouse_start_pos[1]) > 10):
            print("检测到鼠标移动，停止截图")
            break

        loop_count += 1
        print(f"第 {loop_count} 次截图...")

        # 按N截图
        pyautogui.press('n')
        time.sleep(0.05)

        # 按End键结束截图选择（精确单次按键）
        pyautogui.keyDown('right')
        time.sleep(0.05)

        # 等待1.5秒
        time.sleep(0.05)

    auto_screenshot_running = False
    print(f"自动截图结束，共截图 {loop_count} 次")

def start_auto_screenshot():
    """启动自动截图线程"""
    global auto_screenshot_running

    if not region:
        print("请先框选截图区域！")
        return

    if auto_screenshot_running:
        print("自动截图已在运行中")
        return

    auto_screenshot_running = True
    thread = threading.Thread(target=auto_screenshot_loop, daemon=True)
    thread.start()
    print("自动截图已启动，移动鼠标可停止")

def on_press(key):
    """按键监听"""
    global auto_screenshot_running

    try:
        if key.char == 'n' or key.char == 'N':
            take_screenshot()
        elif key.char == 'y' or key.char == 'Y':
            start_auto_screenshot()
    except AttributeError:
        pass
    if key == keyboard.Key.esc:
        # 停止自动截图
        auto_screenshot_running = False
        print('退出程序')
        return False

# 主程序
print("=" * 50)
print("固定区域截图工具")
print("=" * 50)
print("1. 请用鼠标框选截图区域...")
select_region()
print(f"已选择区域: {region}")
print("2. 按 N 截图，按 Y 自动循环截图，按 ESC 退出")
print("   自动截图时移动鼠标可停止")
print("=" * 50)

# 启动按键监听
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
