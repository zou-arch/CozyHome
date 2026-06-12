#!/usr/bin/env python3
"""模拟点击测试作物检测 - 完整调试"""
import subprocess
import time
import pyautogui
import sys

# 启动游戏
print("启动游戏...")
proc = subprocess.Popen([sys.executable, "main.py"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, bufsize=1)

time.sleep(6)

# 获取游戏窗口
import pygetwindow as gw
windows = gw.getWindowsWithTitle("2.5D")
if not windows:
    print("未找到游戏窗口")
    proc.terminate()
    sys.exit(1)

win = windows[0]
win.activate()
time.sleep(1)

# 点击窗口中心
center_x = win.left + win.width // 2
center_y = win.top + win.height // 2
print(f"点击: ({center_x}, {center_y}) 相对: ({center_x - win.left}, {center_y - win.top})")

# 点击
pyautogui.click(center_x, center_y)
time.sleep(3)

# 读取输出
print("\n--- 输出 ---")
count = 0
while True:
    try:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if line:
            count += 1
            if count > 30:  # 只打印最后30行
                print(line)
    except:
        break

proc.terminate()
