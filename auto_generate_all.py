#!/usr/bin/env python3
"""
全自动生图流程
1. 使用 yuanbao_auto 生成图片到 temp 目录
2. 使用 furniture_editor 处理图片（去背景）
3. 保存到对应目录
"""
import sys
import os
import time

# 添加工具目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))

def step1_generate_images(prompts_file="prompts_crops.txt"):
    """步骤1：使用元宝生成图片"""
    print("\n" + "="*60)
    print("  步骤1：使用腾讯元宝生成图片")
    print("="*60)

    try:
        from yuanbao_auto import load_coords, load_prompts, batch_generate, find_yuanbao, find_all_yuanbao_windows, COORDS_FILE2

        # 检查校准坐标
        coords1 = load_coords()
        coords2 = {}
        if COORDS_FILE2.exists():
            with open(COORDS_FILE2, "r", encoding="utf-8") as f:
                import json
                coords2 = json.load(f)

        if not coords1:
            print("\n❌ 未找到校准坐标，请先运行 yuanbao_auto.py 进行校准")
            print("   命令: python yuanbao_auto.py")
            return False

        # 自适应检查下载方式
        download_mode = None
        if "下载按钮" in coords1:
            download_mode = "left_click"
            print("[检测] 窗口1：左键下载模式")
        elif "右键位置" in coords1 and "下载选项" in coords1:
            download_mode = "right_click"
            print("[检测] 窗口1：右键下载模式")
        else:
            print("\n❌ 未找到下载相关按钮，请先校准")
            return False

        # 检查窗口2的下载方式
        if coords2:
            if "下载按钮" in coords2:
                print("[检测] 窗口2：左键下载模式")
            elif "右键位置" in coords2 and "下载选项" in coords2:
                print("[检测] 窗口2：右键下载模式")
            else:
                print("[警告] 窗口2未找到下载相关按钮，将使用单窗口模式")
                coords2 = {}

        # 检查是否支持宠物图片
        if "pets" in prompts_file.lower():
            # 检查是否有上传参考图的按钮
            if "加号按钮" in coords1 and "上传图片按钮" in coords1:
                print("[检测] 窗口1：支持宠物图片上传参考图")
            else:
                print("[警告] 窗口1未找到上传参考图按钮，宠物图片可能无法生成")
                print("[提示] 请使用支持宠物图片的校准选项（选项13-16）")

        # 检查元宝窗口数量
        windows = find_all_yuanbao_windows()
        print(f"\n[检测] 找到 {len(windows)} 个元宝窗口")

        # 加载提示词
        prompts_file_path = os.path.join(os.path.dirname(__file__), prompts_file)
        prompts = load_prompts(prompts_file_path)
        print(f"[加载] {len(prompts)} 个提示词")

        # 检查是否是宠物提示词
        if "pets" in prompts_file.lower():
            print("[提示] 宠物图片需要上传参考图（idle_0 除外）")

        # 单窗口模式（稳定可靠）
        print("\n[模式] 单窗口生成")
        if not find_yuanbao():
            print("\n❌ 请先打开腾讯元宝窗口")
            return False
        batch_generate(prompts, coords1, prompts_file)

        return True

    except ImportError as e:
        print(f"\n❌ 导入错误: {e}")
        print("   请确保已安装 pyautogui, pyperclip 等依赖")
        return False

def step2b_resize_images(target_width=240, target_height=120):
    """步骤2b：统一调整图片尺寸"""
    print("\n" + "="*60)
    print(f"  步骤2b：统一调整图片尺寸为 {target_width}x{target_height}")
    print("="*60)

    try:
        from PIL import Image

        temp_dir = os.path.join(os.path.dirname(__file__), "temp")
        processed_dir = os.path.join(temp_dir, "processed")

        # 检查是否是宠物图片（64x64）
        if target_width == 64 and target_height == 64:
            print("[提示] 宠物图片尺寸调整为 64x64")

        if not os.path.exists(processed_dir):
            print("[跳过] processed目录不存在")
            return True

        # 获取所有图片文件
        files = [f for f in os.listdir(processed_dir) if f.endswith(".png")]
        if not files:
            print("[跳过] 没有图片文件")
            return True

        resized = 0
        for fname in files:
            file_path = os.path.join(processed_dir, fname)
            try:
                img = Image.open(file_path)
                w, h = img.get_size()

                if w != target_width or h != target_height:
                    # 使用LANCZOS重采样保持像素清晰
                    img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    img_resized.save(file_path)
                    print(f"  ✓ {fname}: {w}x{h} -> {target_width}x{target_height}")
                    resized += 1
                else:
                    print(f"  - {fname}: 已是 {target_width}x{target_height}")
            except Exception as e:
                print(f"  ✗ {fname}: 处理失败 - {e}")

        print(f"\n[完成] 调整了 {resized} 张图片")
        return True

    except ImportError as e:
        print(f"\n❌ 导入错误: {e}")
        print("   请确保已安装 Pillow: pip install Pillow")
        return False

def step2_process_images():
    """步骤2：处理图片（去背景）"""
    print("\n" + "="*60)
    print("  步骤2：处理图片（去背景）")
    print("="*60)

    try:
        # 初始化 pygame
        import pygame
        pygame.init()
        # 创建隐藏的显示表面（batch_flood_remove 需要）
        pygame.display.set_mode((1, 1))

        # 导入并调用处理函数
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))
        from furniture_editor import batch_flood_remove

        # 创建临时目录
        temp_dir = os.path.join(os.path.dirname(__file__), "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # 处理图片
        batch_flood_remove()

        pygame.quit()
        return True

    except Exception as e:
        print(f"\n❌ 处理错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def step3_organize_files():
    """步骤3：整理文件到对应目录"""
    print("\n" + "="*60)
    print("  步骤3：整理文件到对应目录")
    print("="*60)

    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    processed_dir = os.path.join(temp_dir, "processed")

    # 目标目录
    crops_dir = os.path.join(os.path.dirname(__file__), "assets", "sprites", "crops")
    furniture_dir = os.path.join(os.path.dirname(__file__), "assets", "sprites", "furniture")
    pets_dir = os.path.join(os.path.dirname(__file__), "assets", "sprites", "pets")
    os.makedirs(crops_dir, exist_ok=True)
    os.makedirs(furniture_dir, exist_ok=True)
    os.makedirs(pets_dir, exist_ok=True)

    # 作物文件映射
    crop_files = {
        "tomato_stage0.png": "tomato_stage0.png",
        "tomato_stage1.png": "tomato_stage1.png",
        "tomato_stage2.png": "tomato_stage2.png",
        "tomato_stage3.png": "tomato_stage3.png",
        "carrot_stage0.png": "carrot_stage0.png",
        "carrot_stage1.png": "carrot_stage1.png",
        "carrot_stage2.png": "carrot_stage2.png",
        "carrot_stage3.png": "carrot_stage3.png",
        "pumpkin_stage0.png": "pumpkin_stage0.png",
        "pumpkin_stage1.png": "pumpkin_stage1.png",
        "pumpkin_stage2.png": "pumpkin_stage2.png",
        "pumpkin_stage3.png": "pumpkin_stage3.png",
        "sunflower_stage0.png": "sunflower_stage0.png",
        "sunflower_stage1.png": "sunflower_stage1.png",
        "sunflower_stage2.png": "sunflower_stage2.png",
        "sunflower_stage3.png": "sunflower_stage3.png",
        "rose_stage0.png": "rose_stage0.png",
        "rose_stage1.png": "rose_stage1.png",
        "rose_stage2.png": "rose_stage2.png",
        "rose_stage3.png": "rose_stage3.png",
        "strawberry_stage0.png": "strawberry_stage0.png",
        "strawberry_stage1.png": "strawberry_stage1.png",
        "strawberry_stage2.png": "strawberry_stage2.png",
        "strawberry_stage3.png": "strawberry_stage3.png",
        "lotus_stage0.png": "lotus_stage0.png",
        "lotus_stage1.png": "lotus_stage1.png",
        "lotus_stage2.png": "lotus_stage2.png",
        "lotus_stage3.png": "lotus_stage3.png",
        "waterlily_stage0.png": "waterlily_stage0.png",
        "waterlily_stage1.png": "waterlily_stage1.png",
        "waterlily_stage2.png": "waterlily_stage2.png",
        "waterlily_stage3.png": "waterlily_stage3.png",
        "succulent_stage0.png": "succulent_stage0.png",
        "succulent_stage1.png": "succulent_stage1.png",
        "succulent_stage2.png": "succulent_stage2.png",
        "succulent_stage3.png": "succulent_stage3.png",
        "cactus_stage0.png": "cactus_stage0.png",
        "cactus_stage1.png": "cactus_stage1.png",
        "cactus_stage2.png": "cactus_stage2.png",
        "cactus_stage3.png": "cactus_stage3.png",
        "aloe_stage0.png": "aloe_stage0.png",
        "aloe_stage1.png": "aloe_stage1.png",
        "aloe_stage2.png": "aloe_stage2.png",
        "aloe_stage3.png": "aloe_stage3.png",
        "sandthorn_stage0.png": "sandthorn_stage0.png",
        "sandthorn_stage1.png": "sandthorn_stage1.png",
        "sandthorn_stage2.png": "sandthorn_stage2.png",
        "sandthorn_stage3.png": "sandthorn_stage3.png",
    }

    # 复制文件
    copied = 0
    for src_name, dst_name in crop_files.items():
        src_path = os.path.join(processed_dir, src_name)
        dst_path = os.path.join(crops_dir, dst_name)

        if os.path.exists(src_path):
            import shutil
            shutil.copy2(src_path, dst_path)
            print(f"  ✓ {dst_name}")
            copied += 1
        else:
            print(f"  ✗ {src_name} 不存在")

    print(f"\n[完成] 复制了 {copied} 个文件到 {crops_dir}")

    # 家具文件映射
    furniture_files = {
        "desk.png": "desk.png",
        "sofa.png": "sofa.png",
        "bookshelf.png": "bookshelf.png",
        "floor_lamp.png": "floor_lamp.png",
        "storage_basket.png": "storage_basket.png",
        "flower_stand.png": "flower_stand.png",
        "chair.png": "chair.png",
        "table_lamp.png": "table_lamp.png",
        "wardrobe.png": "wardrobe.png",
        "bed.png": "bed.png",
        "painting.png": "painting.png",
        "tv.png": "tv.png",
        "piano.png": "piano.png",
        "coffee_table.png": "coffee_table.png",
        "rug.png": "rug.png",
    }

    # 复制家具文件
    copied_furniture = 0
    for src_name, dst_name in furniture_files.items():
        src_path = os.path.join(processed_dir, src_name)
        dst_path = os.path.join(furniture_dir, dst_name)

        if os.path.exists(src_path):
            import shutil
            shutil.copy2(src_path, dst_path)
            print(f"  ✓ {dst_name}")
            copied_furniture += 1
        else:
            print(f"  ✗ {src_name} 不存在")

    print(f"\n[完成] 复制了 {copied_furniture} 个家具文件到 {furniture_dir}")

    # 宠物文件映射（动态生成，基于命名规范）
    # 宠物文件命名：pet_name_state_frame.png
    # 例如：golden_retriever_idle_0.png, golden_retriever_walk_0.png
    copied_pets = 0
    for filename in os.listdir(processed_dir):
        if not filename.endswith(".png"):
            continue

        # 检查是否符合宠物命名规范
        # 格式：pet_name_state_frame.png
        parts = filename.replace(".png", "").split("_")
        if len(parts) >= 3:
            # 检查最后一部分是否是数字（帧号）
            frame_num = parts[-1]
            if frame_num.isdigit():
                # 检查倒数第二部分是否是状态
                state = parts[-2]
                valid_states = [
                    # 通用状态
                    "idle", "walk", "run", "hungry", "happy", "sleep", "eat", "follow", "special",
                    # 金毛犬
                    "eardownidle", "tongueidle", "tailwag", "sitbeg", "sleepside", "playball",
                    # 猫
                    "tailtwitch", "blink", "stalk", "knead", "headbunt", "meow", "sleepcurled", "playpaw",
                    # 兔子
                    "eartwitch", "nosewiggle", "hop", "chewcarrot", "dig", "sleepball",
                    # 仓鼠
                    "groom", "cheekfull", "holdseed",
                    # 小鸡
                    "headtilt", "peck", "flap", "scratch", "sleeponeleg",
                    # 企鹅
                    "bellyslide", "wingflap", "fish", "neckstretch", "sleeptuck", "swim",
                ]
                if state in valid_states:
                    # 这是一个宠物精灵图
                    src_path = os.path.join(processed_dir, filename)
                    dst_path = os.path.join(pets_dir, filename)

                    if os.path.exists(src_path):
                        import shutil
                        shutil.copy2(src_path, dst_path)
                        print(f"  ✓ {filename}")
                        copied_pets += 1

    print(f"\n[完成] 复制了 {copied_pets} 个宠物文件到 {pets_dir}")

    return copied > 0 or copied_furniture > 0 or copied_pets > 0

def main():
    """主流程"""
    print("\n" + "="*60)
    print("  全自动生图流程")
    print("="*60)
    print("\n流程说明：")
    print("  1. 使用腾讯元宝生成作物关键帧图片")
    print("  2. 自动处理图片（去背景、裁剪）")
    print("  3. 整理文件到对应目录")
    print("\n注意事项：")
    print("  - 需要先打开腾讯元宝")
    print("  - 首次使用需要校准按钮位置")
    print("  - 鼠标移到左上角可紧急中断")
    print("="*60)

    print("\n请选择：")
    print("  1. 运行完整流程（生成 + 处理 + 整理）")
    print("  2. 仅生成图片（步骤1）")
    print("  3. 仅处理图片（步骤2，自动去背景）")
    print("  4. 仅整理文件（步骤3）")
    print("  5. 校准元宝按钮位置（窗口1，右键下载）")
    print("  6. 校准元宝按钮位置（窗口2，右键下载）")
    print("  7. 生成UI图标（prompts_ui_icons.txt）")
    print("  8. 手动编辑图片（furniture_editor）")
    print("  9. 生成家具图片（prompts_furniture.txt）")
    print("  10. 生成宠物图片（prompts_pets.txt）")
    print("  11. 校准元宝按钮位置（窗口1，左键下载）")
    print("  12. 校准元宝按钮位置（窗口2，左键下载）")
    print("  13. 校准元宝按钮位置（窗口1，右键下载，支持宠物图片）")
    print("  14. 校准元宝按钮位置（窗口2，右键下载，支持宠物图片）")
    print("  15. 校准元宝按钮位置（窗口1，左键下载，支持宠物图片）")
    print("  16. 校准元宝按钮位置（窗口2，左键下载，支持宠物图片）")

    choice = input("\n输入选择 (1/2/3/4/5/6/7/8/9/10/11/12/13/14/15/16): ").strip()

    if choice == '1':
        # 完整流程
        step1_generate_images()
        step2_process_images()
        step3_organize_files()
    elif choice == '2':
        step1_generate_images()
    elif choice == '7':
        # 生成UI图标
        step1_generate_images("prompts_ui_icons.txt")
    elif choice == '9':
        # 生成家具图片（完整流程）
        step1_generate_images("prompts_furniture.txt")
        step2_process_images()
        step3_organize_files()
    elif choice == '10':
        # 生成宠物图片（完整流程）
        step1_generate_images("prompts_pets.txt")
        step2_process_images()
        step3_organize_files()
    elif choice == '11':
        # 校准窗口1（左键下载）
        try:
            from yuanbao_auto import calibrate
            calibrate()
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
    elif choice == '12':
        # 校准窗口2（左键下载）
        try:
            from yuanbao_auto import calibrate_window2
            calibrate_window2()
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
    elif choice == '13':
        # 校准窗口1（右键下载，支持宠物图片）
        try:
            from yuanbao_auto import calibrate_with_pet
            calibrate_with_pet()
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
    elif choice == '14':
        # 校准窗口2（右键下载，支持宠物图片）
        try:
            from yuanbao_auto import calibrate_window2_with_pet
            calibrate_window2_with_pet()
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
    elif choice == '15':
        # 校准窗口1（左键下载，支持宠物图片）
        try:
            from yuanbao_auto import calibrate_left_click_with_pet
            calibrate_left_click_with_pet()
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
    elif choice == '16':
        # 校准窗口2（左键下载，支持宠物图片）
        try:
            from yuanbao_auto import calibrate_window2_left_click_with_pet
            calibrate_window2_left_click_with_pet()
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
    elif choice == '3':
        step2_process_images()
    elif choice == '4':
        step3_organize_files()
    elif choice == '5':
        # 校准窗口1
        try:
            from yuanbao_auto import calibrate
            calibrate()
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            
    elif choice == '6':
        # 校准窗口2
        try:
            from yuanbao_auto import calibrate_window2
            calibrate_window2()
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
    elif choice == '8':
        # 手动编辑图片
        print("\n[启动手动编辑器]")
        print("功能说明：")
        print("  - 左键点击：去除像素（连通区域洪水填充）")
        print("  - 右键点击：恢复像素")
        print("  - F键：自动去除背景")
        print("  - S键：保存")
        print("  - Enter：确认删除预览")
        print("  - Esc：取消预览")
        print("  - 方向键/滚轮：切换图片")
        print()
        try:
            import subprocess
            subprocess.run([sys.executable, "tools/furniture_editor.py"], cwd=os.path.dirname(__file__))
        except Exception as e:
            print(f"❌ 启动编辑器失败: {e}")
    else:
        print("无效选择")

if __name__ == "__main__":
    main()
