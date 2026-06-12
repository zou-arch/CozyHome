#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯元宝 - 自动化生图脚本
使用 PyAutoGUI 控制元宝桌面应用自动生成图片
"""

import pyautogui
import pyperclip
import time
import os
import sys
import io
import json
from pathlib import Path
from datetime import datetime

# Windows DPI 缩放修复 - 让 pyautogui 坐标和实际屏幕一致
if sys.platform == 'win32':
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# 设置标准输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 安全设置
pyautogui.FAILSAFE = True  # 鼠标移到左上角可中断
pyautogui.PAUSE = 0.3  # 操作间隔

# 配置
OUTPUT_DIR = Path("E:/CozyHome/temp")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
COORDS_FILE = Path("E:/CozyHome/yuanbao_coords.json")
COORDS_FILE2 = Path("E:/CozyHome/yuanbao_coords2.json")

# ==================== 工具函数 ====================

def log(msg):
    """打印日志"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def load_coords():
    """加载校准坐标"""
    if COORDS_FILE.exists():
        with open(COORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_coords(positions):
    """保存校准坐标"""
    with open(COORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, ensure_ascii=False, indent=2)
    log(f"💾 坐标已保存到 {COORDS_FILE}")

def find_yuanbao(window_index=0):
    """查找并激活元宝窗口
    window_index: 0=第一个窗口, 1=第二个窗口
    窗口按位置排序（从左到右），确保顺序稳定
    """
    import pygetwindow as gw

    # 尝试多个可能的窗口标题
    keywords = ['腾讯元宝', '元宝', 'Yuanbao', 'yuanbao', 'Tauri App', 'tauri app']
    all_yuanbao_windows = []
    for kw in keywords:
        windows = gw.getWindowsWithTitle(kw)
        all_yuanbao_windows.extend(windows)

    if not all_yuanbao_windows:
        log("❌ 未找到元宝窗口，当前所有窗口：")
        all_windows = gw.getAllWindows()
        for w in all_windows:
            if w.title.strip():
                log(f"   - {w.title}")
        log("请确认元宝窗口标题，或手动切换到元宝窗口")
        return False

    # 去重
    unique_windows = []
    seen_titles = set()
    for win in all_yuanbao_windows:
        if win.title not in seen_titles:
            unique_windows.append(win)
            seen_titles.add(win.title)

    # 按位置排序（从左到右，从上到下），确保窗口顺序稳定
    unique_windows.sort(key=lambda w: (w.left, w.top))

    if window_index >= len(unique_windows):
        log(f"⚠️ 只找到 {len(unique_windows)} 个元宝窗口，无法激活第 {window_index + 1} 个")
        return False

    win = unique_windows[window_index]
    try:
        win.activate()
        time.sleep(0.5)
    except Exception:
        win.minimize()
        time.sleep(0.3)
        win.restore()
        time.sleep(0.5)
    log(f"✅ 已激活元宝窗口 [{win.title}] (窗口 {window_index + 1}, 位置: {win.left},{win.top})")
    return True

def find_all_yuanbao_windows():
    """查找所有元宝窗口，按位置排序（从左到右，从上到下）"""
    import pygetwindow as gw

    keywords = ['腾讯元宝', '元宝', 'Yuanbao', 'yuanbao', 'Tauri App', 'tauri app']
    all_yuanbao_windows = []
    for kw in keywords:
        windows = gw.getWindowsWithTitle(kw)
        all_yuanbao_windows.extend(windows)

    # 去重
    unique_windows = []
    seen_titles = set()
    for win in all_yuanbao_windows:
        if win.title not in seen_titles:
            unique_windows.append(win)
            seen_titles.add(win.title)

    # 按位置排序（从左到右，从上到下），确保窗口顺序稳定
    unique_windows.sort(key=lambda w: (w.left, w.top))

    return unique_windows

def input_text(text, coords=None):
    """输入文本（使用剪贴板避免中文输入法问题）"""
    # 如果有校准的输入框位置，先点击它
    if coords and "输入框位置" in coords:
        pos = coords["输入框位置"]
        pyautogui.click(pos[0], pos[1])
        time.sleep(0.3)

    pyperclip.copy(text)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)

def click_upload_button(coords):
    """点击发送按钮"""
    pos = coords.get("发送按钮")
    if not pos:
        log("❌ 未找到[发送按钮]坐标，请先校准")
        return False
    log("[...] 点击发送按钮...")
    pyautogui.click(pos[0], pos[1])
    return True

def wait_for_image(coords, timeout=180):
    """等待图片生成完成 - 使用校准的检测区域"""
    log("[等待] 检测图片是否生成...")
    start_time = time.time()

    # 使用校准的检测区域
    region = coords.get("检测区域", [380, 541, 332, 199])

    # 等待18秒让图片开始生成
    log("[等待] 等待18秒让图片开始生成...")
    time.sleep(18)

    # 取第一张基准截图
    last_screenshot = pyautogui.screenshot(region=region)
    log("[检测] 已获取基准截图，开始检测...")

    while time.time() - start_time < timeout:
        # 每1.5秒检测一次
        time.sleep(1.5)

        current_screenshot = pyautogui.screenshot(region=region)
        diff = compare_images(last_screenshot, current_screenshot)

        if diff == 0:
            # 两次图片完全无异，判定生成完成
            log("[检测] 两次图片完全一致，图片生成完成")
            time.sleep(0.5)  # 检测到成功后等0.5秒
            return True
        else:
            # 有变化，更新基准截图
            last_screenshot = current_screenshot
            log(f"[检测] 检测到变化 (diff={diff:.4f})，继续等待...")

        elapsed = int(time.time() - start_time)
        if elapsed % 15 == 0 and elapsed > 0:
            log(f"[等待] 已等待 {elapsed} 秒...")

    log("[超时] 等待超时")
    return False

def compare_images(img1, img2):
    """比较两张图片的差异 - 像素级别无变化检测"""
    # 直接比较原始像素，不进行缩放
    img1_gray = img1.convert('L')
    img2_gray = img2.convert('L')

    pixels1 = list(img1_gray.getdata())
    pixels2 = list(img2_gray.getdata())

    # 确保像素数量一致
    if len(pixels1) != len(pixels2):
        return 1.0  # 像素数量不一致，返回最大差异

    diff_count = sum(1 for p1, p2 in zip(pixels1, pixels2) if p1 != p2)
    diff_ratio = diff_count / len(pixels1)

    return diff_ratio

def save_screenshot(name):
    """截图保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"
    filepath = OUTPUT_DIR / filename

    screenshot = pyautogui.screenshot()
    screenshot.save(str(filepath))
    log(f"[截图] {filepath}")
    return filepath

def right_click_image(coords):
    """右键点击图片打开工具栏"""
    pos = coords.get("右键位置")
    if not pos:
        log("❌ 未找到[右键位置]坐标，请先校准")
        return False
    log("[...] 右键点击图片...")
    pyautogui.rightClick(pos[0], pos[1])
    return True

def click_download_option(coords):
    """点击右键菜单中的下载选项"""
    pos = coords.get("下载选项")
    if not pos:
        log("❌ 未找到[下载选项]坐标，请先校准")
        return False
    log("[...] 点击下载选项...")
    time.sleep(0.8)  # 等右键菜单弹出
    pyautogui.click(pos[0], pos[1])
    return True

def save_file(name):
    """等待保存对话框并输入文件名"""
    time.sleep(2)  # 等保存对话框弹出
    log("[...] 输入文件名...")
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyperclip.copy(name)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)
    pyautogui.press('enter')
    time.sleep(1)  # 等保存完成

def upload_reference_image(coords, reference_name):
    """上传参考图（仅宠物图片使用）"""
    log("[上传参考图] 开始上传参考图...")

    # 1. 点击+号
    plus_pos = coords.get("加号按钮")
    if not plus_pos:
        log("❌ 未找到[加号按钮]坐标，请先校准")
        return False
    log("[1/4] 点击+号...")
    pyautogui.click(plus_pos[0], plus_pos[1])
    time.sleep(1)

    # 2. 点击上传图片
    upload_pos = coords.get("上传图片按钮")
    if not upload_pos:
        log("❌ 未找到[上传图片按钮]坐标，请先校准")
        return False
    log("[2/4] 点击上传图片...")
    pyautogui.click(upload_pos[0], upload_pos[1])
    time.sleep(2)

    # 3. 输入参考图名称（添加 .png 后缀）
    log("[3/4] 输入参考图名称...")
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    # 添加 .png 后缀
    if not reference_name.endswith(".png"):
        reference_name = reference_name + ".png"
    pyperclip.copy(reference_name)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)

    # 4. 确认选择（按Enter）
    pyautogui.press('enter')
    time.sleep(0.5)

    log("[上传参考图] 完成")
    return True

def is_pet_prompt(prompts_file):
    """检查是否是宠物提示词文件"""
    return "pets" in prompts_file.lower()

def is_idle_frame(name):
    """检查是否是 idle_0 帧（初始帧，不需要参考图）"""
    # 只有 idle_0 是初始帧，不需要参考图
    # idle_1、idle_2 等都需要参考图
    # 先移除 .png 后缀（如果有）
    name = name.replace(".png", "")
    return name.endswith("_idle_0")

def get_reference_name(name):
    """获取参考图名称（上一帧）"""
    # 例如：
    # golden_retriever_idle_1 → golden_retriever_idle_0
    # golden_retriever_idle_2 → golden_retriever_idle_1
    # golden_retriever_walk_0 → golden_retriever_idle_0
    # golden_retriever_walk_1 → golden_retriever_walk_0
    # golden_retriever_walk_2 → golden_retriever_walk_1
    # 先移除 .png 后缀（如果有）
    name = name.replace(".png", "")
    parts = name.rsplit("_", 2)  # 分割成 ["golden_retriever", "walk", "0"]
    if len(parts) == 3:
        pet_name = parts[0]
        state = parts[1]
        frame = int(parts[2])

        if frame == 0:
            # 第0帧参考 idle_0
            return f"{pet_name}_idle_0"
        else:
            # 第N帧参考同状态的第N-1帧
            return f"{pet_name}_{state}_{frame - 1}"
    return None

# ==================== 主流程 ====================

def generate_one(prompt, name, coords, max_retries=3, prompts_file="prompts_crops.txt"):
    """生成单张图片 - 匹配元宝实际流程，带重试功能"""
    for attempt in range(max_retries):
        log(f"\n{'='*50}")
        log(f"[生成] {name} (尝试 {attempt + 1}/{max_retries})")
        log(f"[Prompt] {prompt[:50]}...")

        # 1. 激活元宝窗口
        if not find_yuanbao():
            return False

        # 如果是重试，先点击发送按钮重置状态
        if attempt > 0:
            log("[重试] 点击发送按钮重置状态...")
            click_upload_button(coords)
            time.sleep(3)

        # 2. 判断是否需要上传参考图（仅宠物图片且非 idle_0 帧）
        need_upload = is_pet_prompt(prompts_file) and not is_idle_frame(name)
        if need_upload:
            reference_name = get_reference_name(name)
            if reference_name:
                log(f"[上传参考图] {reference_name}")
                if not upload_reference_image(coords, reference_name):
                    log("[警告] 上传参考图失败，继续尝试...")

        # 3. 输入 Prompt
        log("[1/5] 输入 Prompt...")
        pyautogui.hotkey('ctrl', 'a')  # 全选
        time.sleep(0.1)
        input_text(prompt, coords)

        # 4. 等1秒再点发送
        log("[2/5] 等待1秒...")
        time.sleep(1)

        # 5. 点击发送按钮
        log("[3/5] 点击发送按钮...")
        if not click_upload_button(coords):
            continue

        # 6. 等待图片生成完成（8秒检测）
        log("[4/5] 等待图片生成（8秒检测）...")
        if not wait_for_image(coords):
            log(f"[警告] 图片生成超时，准备重试...")
            save_screenshot(f"timeout_{name}_attempt{attempt + 1}")
            continue

        # 7. 下载图片（自适应判断左键或右键下载）
        log("[5/5] 下载图片...")
        if "下载按钮" in coords:
            # 左键下载模式
            pos = coords.get("下载按钮")
            if pos:
                pyautogui.moveTo(pos[0], pos[1])
                time.sleep(1)  # 鼠标先挪到下载按钮等待1秒
                pyautogui.click(pos[0], pos[1])
                time.sleep(1)  # 点击下载等1秒
            else:
                log("[错误] 未找到下载按钮位置")
                continue
        elif "右键位置" in coords and "下载选项" in coords:
            # 右键下载模式
            if not right_click_image(coords):
                continue
            time.sleep(1)  # 等待1秒
            if not click_download_option(coords):
                continue
            time.sleep(1)  # 等待1秒
        else:
            log("[错误] 未找到下载相关按钮")
            continue
        save_file(name)

        log(f"✅ [完成] {name}")
        return True

    log(f"❌ [失败] {name} 达到最大重试次数 ({max_retries})")
    return False

def check_image_generated(coords):
    """检查图片是否真的生成了"""
    # 使用校准的检测区域
    region = coords.get("检测区域", [380, 541, 332, 199])

    try:
        screenshot = pyautogui.screenshot(region=region)

        # 检查是否有非空白内容
        pixels = list(screenshot.getdata())
        # 检查是否有足够多的不同颜色（不是纯色背景）
        unique_colors = len(set(pixels))
        if unique_colors > 100:  # 有足够多的不同颜色，说明有内容
            log("[检测] 图片已生成")
            return True
        else:
            log("[检测] 图片区域可能为空白")
            return False
    except Exception as e:
        log(f"[检测] 检测失败: {e}")
        return False

def batch_generate(prompts, coords, prompts_file="prompts_crops.txt"):
    """批量生成，自动跳过已生成的，带验证功能"""
    # 过滤掉已生成的（检查 temp 目录）
    pending = []
    skipped = []
    for name, prompt in prompts:
        # name 可能已经包含 .png 后缀，检查两种情况
        if (OUTPUT_DIR / f"{name}.png").exists() or (OUTPUT_DIR / name).exists():
            skipped.append(name)
        else:
            pending.append((name, prompt))

    if skipped:
        log(f"[跳过] {len(skipped)} 张已生成: {', '.join(skipped)}")

    if not pending:
        log("[完成] 所有素材已生成！")
        return

    log(f"\n[批量生成] 还剩 {len(pending)} 张需要生成")
    log("[提示] 请确保：")
    log("   1. 腾讯元宝已打开")
    log("   2. 元宝窗口在前台")
    log("   3. 鼠标不要移动（自动化会控制鼠标）")
    log("   4. 每张图片生成后会自动验证")
    log("   5. 如果生成失败会自动重试（最多3次）")
    if is_pet_prompt(prompts_file):
        log("   6. 宠物图片需要上传参考图（idle_0 除外）")
    print(f"\n即将生成 {len(pending)} 张：")
    for i, (name, prompt) in enumerate(pending, 1):
        print(f"  {i}. {name}")
    print()
    confirm = input("按 Enter 开始，输入 q 取消: ").strip()
    if confirm == 'q':
        log("[取消] 用户取消批量生成")
        return

    success_count = 0
    fail_count = 0
    verified_count = 0
    for i, (name, prompt) in enumerate(pending, 1):
        log(f"\n[{i}/{len(pending)}] {name}")

        if generate_one(prompt, name, coords, prompts_file=prompts_file):
            success_count += 1
            # 验证生成的图片
            if verify_generated_image(name):
                verified_count += 1
                log(f"[验证] ✓ {name} 图片已验证")
            else:
                log(f"[验证] ✗ {name} 图片验证失败")
        else:
            fail_count += 1

        time.sleep(3)

    log(f"\n{'='*50}")
    log(f"🎉 完成!")
    log(f"   成功: {success_count}")
    log(f"   已验证: {verified_count}")
    log(f"   失败: {fail_count}")
    log(f"   跳过: {len(skipped)}")
    log(f"📁 输出目录: {OUTPUT_DIR}")

def verify_generated_image(name):
    """验证生成的图片是否存在且有效"""
    # name 可能已经包含 .png 后缀，检查两种情况
    if name.endswith(".png"):
        file_path = OUTPUT_DIR / name
    else:
        file_path = OUTPUT_DIR / f"{name}.png"
    if not file_path.exists():
        log(f"[验证] 图片文件不存在: {file_path}")
        return False

    # 检查文件大小
    file_size = file_path.stat().st_size
    if file_size < 1000:  # 小于1KB可能是空文件
        log(f"[验证] 图片文件太小: {file_size} bytes")
        return False

    # 尝试加载图片
    try:
        from PIL import Image
        img = Image.open(file_path)
        img.verify()  # 验证图片完整性
        log(f"[验证] 图片格式正确: {img.size}")
        return True
    except Exception as e:
        log(f"[验证] 图片加载失败: {e}")
        return False

def batch_generate_parallel(prompts, coords1, coords2, prompts_file="prompts_crops.txt"):
    """双窗口独立并行生成 - 按照宠物分组处理"""
    import threading

    # 过滤掉已生成的
    pending = []
    skipped = []
    for name, prompt in prompts:
        # name 可能已经包含 .png 后缀，检查两种情况
        if (OUTPUT_DIR / f"{name}.png").exists() or (OUTPUT_DIR / name).exists():
            skipped.append(name)
        else:
            pending.append((name, prompt))

    if skipped:
        log(f"[跳过] {len(skipped)} 张已生成")

    if not pending:
        log("[完成] 所有素材已生成！")
        return

    # 如果是宠物图片，按照宠物分组处理
    if is_pet_prompt(prompts_file):
        log(f"\n[宠物图片模式] 按照宠物分组处理")
        log("[说明] 提前按宠物分组，每个窗口处理不同的宠物")

        # 按照宠物分组
        pets = {}
        for name, prompt in pending:
            pet_name = name.rsplit("_", 2)[0]  # 例如：golden_retriever_idle_0 → golden_retriever
            if pet_name not in pets:
                pets[pet_name] = []
            pets[pet_name].append((name, prompt))

        # 按照宠物的帧数排序（从多到少）
        pet_list = sorted(pets.items(), key=lambda x: len(x[1]), reverse=True)

        # 使用贪心算法分配宠物给两个窗口，尽量均衡
        group1 = []
        group2 = []
        group1_count = 0
        group2_count = 0

        for pet_name, pet_prompts in pet_list:
            if group1_count <= group2_count:
                group1.extend(pet_prompts)
                group1_count += len(pet_prompts)
            else:
                group2.extend(pet_prompts)
                group2_count += len(pet_prompts)

        # 显示分组结果
        log(f"\n[分组结果]")
        log(f"  窗口1: {group1_count} 张 ({', '.join([name.rsplit('_', 2)[0] for name, _ in group1 if '_' in name])})")
        log(f"  窗口2: {group2_count} 张 ({', '.join([name.rsplit('_', 2)[0] for name, _ in group2 if '_' in name])})")
        log(f"  总计: {len(pending)} 张")

        print(f"\n窗口1 生成列表:")
        for i, (name, prompt) in enumerate(group1, 1):
            print(f"  {i}. {name}")

        print(f"\n窗口2 生成列表:")
        for i, (name, prompt) in enumerate(group2, 1):
            print(f"  {i}. {name}")

        print()
        confirm = input("按 Enter 开始，输入 q 取消: ").strip()
        if confirm == 'q':
            log("[取消] 用户取消批量生成")
            return

        # 并行生成
        _parallel_generate(group1, group2, coords1, coords2, prompts_file)

    else:
        # 非宠物图片，直接分成两组并行生成
        log(f"\n[双窗口独立并行生成]")
        half = len(pending) // 2
        group1 = pending[:half]
        group2 = pending[half:]

        log(f"  窗口1: {len(group1)} 张")
        log(f"  窗口2: {len(group2)} 张")
        log(f"  总计: {len(pending)} 张")
        log("[提示] 请确保两个元宝窗口都已打开")
        log("[说明] 每个窗口完成一个立即开始下一个，最大化利用等待时间")
        print(f"\n即将生成 {len(pending)} 张：")
        for i, (name, prompt) in enumerate(pending, 1):
            print(f"  {i}. {name}")
        print()
        confirm = input("按 Enter 开始，输入 q 取消: ").strip()
        if confirm == 'q':
            log("[取消] 用户取消批量生成")
            return

        _parallel_generate(group1, group2, coords1, coords2, prompts_file)

def _parallel_generate(group1, group2, coords1, coords2, prompts_file):
    """并行生成辅助函数 - 支持中断和恢复"""
    import threading

    # 鼠标键盘操作锁
    input_lock = threading.Lock()
    results = {"success": 0, "fail": 0}
    results_lock = threading.Lock()

    def worker(group, coords, window_index):
        i = 0
        while i < len(group):
            name, prompt = group[i]
            log(f"[窗口{window_index+1}] 开始处理: {name}")

            # 1. 上传参考图 + 输入提示词 + 发送（需要锁）
            with input_lock:
                find_yuanbao(window_index)

                # 1.1 上传参考图（如果需要）
                need_upload = is_pet_prompt(prompts_file) and not is_idle_frame(name)
                if need_upload:
                    reference_name = get_reference_name(name)
                    if reference_name:
                        log(f"[窗口{window_index+1}] 上传参考图: {reference_name}")
                        upload_reference_image(coords, reference_name)

                # 1.2 输入提示词并发送
                log(f"[窗口{window_index+1}] 输入并发送: {name}")
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.1)
                input_text(prompt, coords)
                time.sleep(1)
                click_upload_button(coords)

            # 2. 等待图片生成（不需要锁）
            log(f"[窗口{window_index+1}] 等待图片生成: {name}")
            wait_for_image(coords)

            # 3. 下载 + 保存 + 下一个图片的上传+输入+发送（需要锁）
            with input_lock:
                # 3.1 下载图片
                log(f"[窗口{window_index+1}] 下载: {name}")
                if "下载按钮" in coords:
                    pos = coords.get("下载按钮")
                    if pos:
                        pyautogui.moveTo(pos[0], pos[1])
                        time.sleep(1)
                        pyautogui.click(pos[0], pos[1])
                        time.sleep(1)
                    else:
                        log(f"[窗口{window_index+1}] [错误] 未找到下载按钮位置")
                        i += 1
                        continue
                elif "右键位置" in coords and "下载选项" in coords:
                    if not right_click_image(coords):
                        i += 1
                        continue
                    time.sleep(1)
                    if not click_download_option(coords):
                        i += 1
                        continue
                    time.sleep(1)
                else:
                    log(f"[窗口{window_index+1}] [错误] 未找到下载相关按钮")
                    i += 1
                    continue

                # 3.2 保存文件
                log(f"[窗口{window_index+1}] 保存: {name}")
                save_file(name)

                # 3.3 验证
                if verify_generated_image(name):
                    with results_lock:
                        results["success"] += 1
                        log(f"[窗口{window_index+1}] ✓ 完成: {name} (成功: {results['success']})")
                else:
                    with results_lock:
                        results["fail"] += 1
                        log(f"[窗口{window_index+1}] ✗ 失败: {name}")

                # 3.4 如果还有下一个图片，继续上传+输入+发送
                if i + 1 < len(group):
                    next_name, next_prompt = group[i + 1]
                    log(f"[窗口{window_index+1}] 开始下一个图片: {next_name}")

                    # 上传参考图（如果需要）
                    need_upload = is_pet_prompt(prompts_file) and not is_idle_frame(next_name)
                    if need_upload:
                        reference_name = get_reference_name(next_name)
                        if reference_name:
                            log(f"[窗口{window_index+1}] 上传参考图: {reference_name}")
                            upload_reference_image(coords, reference_name)

                    # 输入提示词并发送
                    log(f"[窗口{window_index+1}] 输入并发送: {next_name}")
                    pyautogui.hotkey('ctrl', 'a')
                    time.sleep(0.1)
                    input_text(next_prompt, coords)
                    time.sleep(1)
                    click_upload_button(coords)

            i += 1

    # 启动两个线程
    t1 = threading.Thread(target=worker, args=(group1, coords1, 0))
    t2 = threading.Thread(target=worker, args=(group2, coords2, 1))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    log(f"\n{'='*50}")
    log(f"🎉 双窗口并行完成!")
    log(f"   成功: {results['success']}")
    log(f"   失败: {results['fail']}")
    log(f"📁 输出目录: {OUTPUT_DIR}")

# ==================== 测试工具 ====================

def get_mouse_position():
    """获取鼠标当前位置（用于调试）"""
    print("\n[鼠标位置工具]")
    print("将鼠标移动到目标位置，按 Enter 记录坐标")
    print("输入 q 退出\n")

    positions = []
    while True:
        pos = pyautogui.position()
        print(f"当前坐标: x={pos.x}, y={pos.y}")

        cmd = input("按 Enter 记录 / 输入 q 退出: ").strip()
        if cmd == 'q':
            break
        positions.append(pos)
        print(f"[已记录] ({pos.x}, {pos.y})")

    if positions:
        print("\n[记录的坐标]")
        for i, pos in enumerate(positions, 1):
            print(f"  {i}. x={pos.x}, y={pos.y}")

def calibrate():
    """校准工具 - 窗口1（右键下载模式）"""
    print("\n[校准工具 - 窗口1]")
    print("流程：点击输入框 → 输入提示词 → 发送 → 检测图片 → 右键 → 下载 → 保存")
    print("\n请依次将鼠标移动到以下位置并按 Enter：")
    print("  1. 输入框位置（点击后输入提示词）")
    print("  2. 发送按钮位置")
    print("  3. 图片检测区域左上角")
    print("  4. 图片检测区域右下角")
    print("  5. 右键图片位置")
    print("  6. 右键菜单中的下载选项位置")
    print("\n按 Enter 开始...")
    input()

    positions = {}
    for name in ["输入框位置", "发送按钮", "检测区域左上角", "检测区域右下角", "右键位置", "下载选项"]:
        print(f"\n请将鼠标移动到 [{name}] 位置，然后按 Enter...")
        input()
        pos = pyautogui.position()
        positions[name] = (pos.x, pos.y)
        print(f"[OK] {name}: x={pos.x}, y={pos.y}")

    # 计算检测区域
    x1, y1 = positions["检测区域左上角"]
    x2, y2 = positions["检测区域右下角"]
    positions["检测区域"] = [x1, y1, x2 - x1, y2 - y1]  # (x, y, width, height)

    print("\n[校准完成] 坐标如下：")
    for name, pos in positions.items():
        print(f"  {name}: {pos}")

    save_coords(positions)
    return positions

def calibrate_with_pet():
    """校准工具 - 窗口1（支持宠物图片上传参考图）"""
    print("\n[校准工具 - 窗口1（支持宠物图片）]")
    print("流程：")
    print("  非宠物图片：点击输入框 → 输入提示词 → 发送 → 检测图片 → 右键 → 下载 → 保存")
    print("  宠物图片(idle_0)：点击输入框 → 输入提示词 → 发送 → 检测图片 → 右键 → 下载 → 保存")
    print("  宠物图片(其他帧)：点击+号 → 点击上传图片 → 输入参考图名称 → 点击输入框 → 输入提示词 → 发送 → 检测图片 → 右键 → 下载 → 保存")
    print("\n请依次将鼠标移动到以下位置并按 Enter：")
    print("  1. 输入框位置（点击后输入提示词）")
    print("  2. 发送按钮位置")
    print("  3. 图片检测区域左上角")
    print("  4. 图片检测区域右下角")
    print("  5. 右键图片位置")
    print("  6. 右键菜单中的下载选项位置")
    print("  7. 加号按钮位置（用于上传参考图）")
    print("  8. 上传图片按钮位置")
    print("\n按 Enter 开始...")
    input()

    positions = {}
    for name in ["输入框位置", "发送按钮", "检测区域左上角", "检测区域右下角", "右键位置", "下载选项", "加号按钮", "上传图片按钮"]:
        print(f"\n请将鼠标移动到 [{name}] 位置，然后按 Enter...")
        input()
        pos = pyautogui.position()
        positions[name] = (pos.x, pos.y)
        print(f"[OK] {name}: x={pos.x}, y={pos.y}")

    # 计算检测区域
    x1, y1 = positions["检测区域左上角"]
    x2, y2 = positions["检测区域右下角"]
    positions["检测区域"] = [x1, y1, x2 - x1, y2 - y1]  # (x, y, width, height)

    print("\n[校准完成] 坐标如下：")
    for name, pos in positions.items():
        print(f"  {name}: {pos}")

    save_coords(positions)
    return positions

def calibrate_left_click():
    """校准工具 - 窗口1（左键下载模式）"""
    print("\n[校准工具 - 窗口1（左键下载）]")
    print("流程：点击输入框 → 输入提示词 → 发送 → 检测图片 → 左键下载 → 保存")
    print("\n请依次将鼠标移动到以下位置并按 Enter：")
    print("  1. 输入框位置（点击后输入提示词）")
    print("  2. 发送按钮位置")
    print("  3. 图片检测区域左上角")
    print("  4. 图片检测区域右下角")
    print("  5. 下载按钮位置")
    print("\n按 Enter 开始...")
    input()

    positions = {}
    for name in ["输入框位置", "发送按钮", "检测区域左上角", "检测区域右下角", "下载按钮"]:
        print(f"\n请将鼠标移动到 [{name}] 位置，然后按 Enter...")
        input()
        pos = pyautogui.position()
        positions[name] = (pos.x, pos.y)
        print(f"[OK] {name}: x={pos.x}, y={pos.y}")

    # 计算检测区域
    x1, y1 = positions["检测区域左上角"]
    x2, y2 = positions["检测区域右下角"]
    positions["检测区域"] = [x1, y1, x2 - x1, y2 - y1]  # (x, y, width, height)

    print("\n[校准完成] 坐标如下：")
    for name, pos in positions.items():
        print(f"  {name}: {pos}")

    save_coords(positions)
    return positions

def calibrate_left_click_with_pet():
    """校准工具 - 窗口1（左键下载模式，支持宠物图片）"""
    print("\n[校准工具 - 窗口1（左键下载，支持宠物图片）]")
    print("流程：")
    print("  非宠物图片：点击输入框 → 输入提示词 → 发送 → 检测图片 → 左键下载 → 保存")
    print("  宠物图片(idle_0)：点击输入框 → 输入提示词 → 发送 → 检测图片 → 左键下载 → 保存")
    print("  宠物图片(其他帧)：点击+号 → 点击上传图片 → 输入参考图名称 → 点击输入框 → 输入提示词 → 发送 → 检测图片 → 左键下载 → 保存")
    print("\n请依次将鼠标移动到以下位置并按 Enter：")
    print("  1. 输入框位置（点击后输入提示词）")
    print("  2. 发送按钮位置")
    print("  3. 图片检测区域左上角")
    print("  4. 图片检测区域右下角")
    print("  5. 下载按钮位置")
    print("  6. 加号按钮位置（用于上传参考图）")
    print("  7. 上传图片按钮位置")
    print("\n按 Enter 开始...")
    input()

    positions = {}
    for name in ["输入框位置", "发送按钮", "检测区域左上角", "检测区域右下角", "下载按钮", "加号按钮", "上传图片按钮"]:
        print(f"\n请将鼠标移动到 [{name}] 位置，然后按 Enter...")
        input()
        pos = pyautogui.position()
        positions[name] = (pos.x, pos.y)
        print(f"[OK] {name}: x={pos.x}, y={pos.y}")

    # 计算检测区域
    x1, y1 = positions["检测区域左上角"]
    x2, y2 = positions["检测区域右下角"]
    positions["检测区域"] = [x1, y1, x2 - x1, y2 - y1]  # (x, y, width, height)

    print("\n[校准完成] 坐标如下：")
    for name, pos in positions.items():
        print(f"  {name}: {pos}")

    save_coords(positions)
    return positions

def save_coords2(positions):
    """保存校准坐标到窗口2"""
    with open(COORDS_FILE2, "w", encoding="utf-8") as f:
        json.dump(positions, f, ensure_ascii=False, indent=2)
    log(f"💾 窗口2坐标已保存到 {COORDS_FILE2}")

def calibrate_window2():
    """校准工具 - 窗口2（右键下载模式）"""
    print("\n[校准工具 - 窗口2]")
    print("流程：点击输入框 → 输入提示词 → 发送 → 检测图片 → 右键 → 下载 → 保存")
    print("\n请依次将鼠标移动到以下位置并按 Enter：")
    print("  1. 输入框位置（点击后输入提示词）")
    print("  2. 发送按钮位置")
    print("  3. 图片检测区域左上角")
    print("  4. 图片检测区域右下角")
    print("  5. 右键图片位置")
    print("  6. 右键菜单中的下载选项位置")
    print("\n按 Enter 开始...")
    input()

    positions = {}
    for name in ["输入框位置", "发送按钮", "检测区域左上角", "检测区域右下角", "右键位置", "下载选项"]:
        print(f"\n请将鼠标移动到 [{name}] 位置，然后按 Enter...")
        input()
        pos = pyautogui.position()
        positions[name] = (pos.x, pos.y)
        print(f"[OK] {name}: x={pos.x}, y={pos.y}")

    # 计算检测区域
    x1, y1 = positions["检测区域左上角"]
    x2, y2 = positions["检测区域右下角"]
    positions["检测区域"] = [x1, y1, x2 - x1, y2 - y1]  # (x, y, width, height)

    print("\n[校准完成] 窗口2坐标如下：")
    for name, pos in positions.items():
        print(f"  {name}: {pos}")

    save_coords2(positions)
    return positions

def calibrate_window2_with_pet():
    """校准工具 - 窗口2（支持宠物图片上传参考图）"""
    print("\n[校准工具 - 窗口2（支持宠物图片）]")
    print("流程：")
    print("  非宠物图片：点击输入框 → 输入提示词 → 发送 → 检测图片 → 右键 → 下载 → 保存")
    print("  宠物图片(idle_0)：点击输入框 → 输入提示词 → 发送 → 检测图片 → 右键 → 下载 → 保存")
    print("  宠物图片(其他帧)：点击+号 → 点击上传图片 → 输入参考图名称 → 点击输入框 → 输入提示词 → 发送 → 检测图片 → 右键 → 下载 → 保存")
    print("\n请依次将鼠标移动到以下位置并按 Enter：")
    print("  1. 输入框位置（点击后输入提示词）")
    print("  2. 发送按钮位置")
    print("  3. 图片检测区域左上角")
    print("  4. 图片检测区域右下角")
    print("  5. 右键图片位置")
    print("  6. 右键菜单中的下载选项位置")
    print("  7. 加号按钮位置（用于上传参考图）")
    print("  8. 上传图片按钮位置")
    print("\n按 Enter 开始...")
    input()

    positions = {}
    for name in ["输入框位置", "发送按钮", "检测区域左上角", "检测区域右下角", "右键位置", "下载选项", "加号按钮", "上传图片按钮"]:
        print(f"\n请将鼠标移动到 [{name}] 位置，然后按 Enter...")
        input()
        pos = pyautogui.position()
        positions[name] = (pos.x, pos.y)
        print(f"[OK] {name}: x={pos.x}, y={pos.y}")

    # 计算检测区域
    x1, y1 = positions["检测区域左上角"]
    x2, y2 = positions["检测区域右下角"]
    positions["检测区域"] = [x1, y1, x2 - x1, y2 - y1]  # (x, y, width, height)

    print("\n[校准完成] 窗口2坐标如下：")
    for name, pos in positions.items():
        print(f"  {name}: {pos}")

    save_coords2(positions)
    return positions

def calibrate_window2_left_click():
    """校准工具 - 窗口2（左键下载模式）"""
    print("\n[校准工具 - 窗口2（左键下载）]")
    print("流程：点击输入框 → 输入提示词 → 发送 → 检测图片 → 左键下载 → 保存")
    print("\n请依次将鼠标移动到以下位置并按 Enter：")
    print("  1. 输入框位置（点击后输入提示词）")
    print("  2. 发送按钮位置")
    print("  3. 图片检测区域左上角")
    print("  4. 图片检测区域右下角")
    print("  5. 下载按钮位置")
    print("\n按 Enter 开始...")
    input()

    positions = {}
    for name in ["输入框位置", "发送按钮", "检测区域左上角", "检测区域右下角", "下载按钮"]:
        print(f"\n请将鼠标移动到 [{name}] 位置，然后按 Enter...")
        input()
        pos = pyautogui.position()
        positions[name] = (pos.x, pos.y)
        print(f"[OK] {name}: x={pos.x}, y={pos.y}")

    # 计算检测区域
    x1, y1 = positions["检测区域左上角"]
    x2, y2 = positions["检测区域右下角"]
    positions["检测区域"] = [x1, y1, x2 - x1, y2 - y1]  # (x, y, width, height)

    print("\n[校准完成] 窗口2坐标如下：")
    for name, pos in positions.items():
        print(f"  {name}: {pos}")

    save_coords2(positions)
    return positions

def calibrate_window2_left_click_with_pet():
    """校准工具 - 窗口2（左键下载模式，支持宠物图片）"""
    print("\n[校准工具 - 窗口2（左键下载，支持宠物图片）]")
    print("流程：")
    print("  非宠物图片：点击输入框 → 输入提示词 → 发送 → 检测图片 → 左键下载 → 保存")
    print("  宠物图片(idle_0)：点击输入框 → 输入提示词 → 发送 → 检测图片 → 左键下载 → 保存")
    print("  宠物图片(其他帧)：点击+号 → 点击上传图片 → 输入参考图名称 → 点击输入框 → 输入提示词 → 发送 → 检测图片 → 左键下载 → 保存")
    print("\n请依次将鼠标移动到以下位置并按 Enter：")
    print("  1. 输入框位置（点击后输入提示词）")
    print("  2. 发送按钮位置")
    print("  3. 图片检测区域左上角")
    print("  4. 图片检测区域右下角")
    print("  5. 下载按钮位置")
    print("  6. 加号按钮位置（用于上传参考图）")
    print("  7. 上传图片按钮位置")
    print("\n按 Enter 开始...")
    input()

    positions = {}
    for name in ["输入框位置", "发送按钮", "检测区域左上角", "检测区域右下角", "下载按钮", "加号按钮", "上传图片按钮"]:
        print(f"\n请将鼠标移动到 [{name}] 位置，然后按 Enter...")
        input()
        pos = pyautogui.position()
        positions[name] = (pos.x, pos.y)
        print(f"[OK] {name}: x={pos.x}, y={pos.y}")

    # 计算检测区域
    x1, y1 = positions["检测区域左上角"]
    x2, y2 = positions["检测区域右下角"]
    positions["检测区域"] = [x1, y1, x2 - x1, y2 - y1]  # (x, y, width, height)

    print("\n[校准完成] 窗口2坐标如下：")
    for name, pos in positions.items():
        print(f"  {name}: {pos}")

    save_coords2(positions)
    return positions

# ==================== 加载Prompt ====================

def load_prompts(file_path="E:/CozyHome/prompts_cn.txt"):
    """从文件加载中文Prompt"""
    prompts = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "|" in line:
                name, prompt = line.split("|", 1)
                prompts.append((name.strip(), prompt.strip()))
    return prompts

# ==================== 主程序 ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  [腾讯元宝] 自动化生图脚本")
    print("="*60)
    print("\n功能：")
    print("  1. 自动输入中文 Prompt 到元宝")
    print("  2. 自动上传并生成图片")
    print("  3. 等待图片生成")
    print("  4. 右键下载保存")
    print("\n操作流程：")
    print("  输入Prompt -> 点击上传 -> 等待生成 -> 右键图片 -> 下载保存")
    print("\n注意事项：")
    print("  - 需要先打开腾讯元宝")
    print("  - 首次使用需要校准按钮位置")
    print("  - 鼠标移到左上角可紧急中断")
    print("="*60)

    print("\n请选择：")
    print("  1. 校准按钮位置（窗口1，右键下载模式）")
    print("  2. 校准按钮位置（窗口2，直接下载模式）")
    print("  3. 测试单个 Prompt")
    print("  4. 批量生成所有素材")
    print("  5. 获取鼠标位置（调试用）")

    choice = input("\n输入选择 (1/2/3/4/5): ").strip()

    # 加载校准坐标
    coords = load_coords()
    if not coords:
        print("\n⚠️ 未找到校准坐标，请先运行选项1进行校准")

    if choice == '1':
        calibrate()
    elif choice == '2':
        calibrate_window2()
    elif choice == '3':
        if not coords:
            print("❌ 请先校准按钮位置（选项1）")
        else:
            print("\n[测试单个 Prompt]")
            print("  直接粘贴 名称|prompt 格式的一行，例如：")
            print("  tomato_stage0|像素风格，32x32像素...")
            print("  或者分开输入名称和prompt\n")
            user_input = input("输入名称|prompt（或只输入prompt）: ").strip()

            if "|" in user_input:
                name, prompt = user_input.split("|", 1)
                name = name.strip()
                prompt = prompt.strip()
            else:
                prompt = user_input
                name = input("输入文件名（如 tomato_stage0）: ").strip()

            if not prompt:
                print("❌ Prompt 不能为空")
            else:
                generate_one(prompt, name or "test", coords)
    elif choice == '4':
        if not coords:
            print("❌ 请先校准按钮位置（选项1）")
        else:
            all_prompts = load_prompts("E:/CozyHome/prompts_crops.txt")
            print(f"\n[加载] {len(all_prompts)} 个 Prompt")
            batch_generate(all_prompts, coords)
    elif choice == '5':
        get_mouse_position()
    else:
        print("无效选择")
