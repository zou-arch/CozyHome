"""
宠物动作配置测试工具
用 idle_0 作为参考图，调整偏移量和帧率
功能：
- 调整动作参数（偏移量、帧率、缩放、循环模式）
- 配置等级解锁（每个动作在哪个等级解锁）
- 保存到 pet_config.json
"""
import pygame
import os
import sys
import json
import re
import tkinter as tk
from tkinter import filedialog

pygame.init()

# 窗口配置
WIN_W, WIN_H = 1100, 700
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("宠物动作配置测试")
clock = pygame.time.Clock()

# 字体
try:
    font = pygame.font.SysFont("microsoftyahei", 16)
    font_big = pygame.font.SysFont("microsoftyahei", 20, bold=True)
    font_small = pygame.font.SysFont("microsoftyahei", 14)
except:
    font = pygame.font.Font(None, 20)
    font_big = font
    font_small = font

# 宠物配置（与 pet.py 保持同步）
PET_CONFIG = {
    "golden_retriever": {
        "states": ["idle", "walk", "hungry", "sleep", "roll", "special"],
        "level_unlocks": {
            0: ["idle", "walk", "run", "hungry", "sleep"],
            2: ["tongueidle"],
            3: ["roll"],
            5: ["special"],
        },
        "state_config": {
            "idle": {"fps": 6, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "walk": {"fps": 8, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "hungry": {"fps": 6, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "sleep": {"fps": 4, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "roll": {"fps": 12, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "special": {"fps": 10, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
        },
    },
    "blue_cat": {
        "states": ["idle", "walk", "hungry", "sleep", "happy"],
        "level_unlocks": {
            0: ["idle", "walk"],
            2: ["hungry"],
            3: ["sleep"],
            5: ["happy"],
        },
        "state_config": {
            "idle": {"fps": 6, "loop": True, "offset_x": 0, "offset_y": 0},
            "walk": {"fps": 8, "loop": True, "offset_x": 0, "offset_y": 0},
            "hungry": {"fps": 6, "loop": False, "offset_x": 0, "offset_y": 0},
            "sleep": {"fps": 4, "loop": True, "offset_x": 0, "offset_y": 0},
            "happy": {"fps": 10, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
        },
    },
    "rabbit": {
        "states": ["idle", "walk", "hungry", "sleep"],
        "level_unlocks": {
            0: ["idle", "walk"],
            2: ["hungry"],
            3: ["sleep"],
        },
        "state_config": {
            "idle": {"fps": 6, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "walk": {"fps": 10, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "hungry": {"fps": 6, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "sleep": {"fps": 4, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
        },
    },
    "hamster": {
        "states": ["idle", "walk", "hungry", "sleep"],
        "level_unlocks": {
            0: ["idle", "walk"],
            2: ["hungry"],
            3: ["sleep"],
        },
        "state_config": {
            "idle": {"fps": 6, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "walk": {"fps": 10, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "hungry": {"fps": 6, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "sleep": {"fps": 4, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
        },
    },
    "chick": {
        "states": ["idle", "walk", "hungry", "sleep"],
        "level_unlocks": {
            0: ["idle", "walk"],
            2: ["hungry"],
            3: ["sleep"],
        },
        "state_config": {
            "idle": {"fps": 6, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "walk": {"fps": 10, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "hungry": {"fps": 6, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            "sleep": {"fps": 4, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
        },
    },
    "penguin": {
        "states": ["idle", "walk", "hungry", "sleep", "roll"],
        "level_unlocks": {
            0: ["idle", "walk"],
            2: ["hungry"],
            3: ["sleep"],
            5: ["roll"],
        },
        "state_config": {
            "idle": {"fps": 6, "loop": True, "offset_x": 0, "offset_y": 0},
            "walk": {"fps": 8, "loop": True, "offset_x": 0, "offset_y": 0},
            "hungry": {"fps": 6, "loop": False, "offset_x": 0, "offset_y": 0},
            "sleep": {"fps": 4, "loop": True, "offset_x": 0, "offset_y": 0},
            "roll": {"fps": 12, "loop": False, "offset_x": 0, "offset_y": 0},
        },
    },
}


def load_frames_from_dir(dir_path):
    """从文件夹加载帧图片，按数字排序"""
    import re
    image_exts = ('.png', '.jpg', '.jpeg', '.bmp')
    files = [f for f in os.listdir(dir_path) if f.lower().endswith(image_exts)]

    def extract_number(filename):
        nums = re.findall(r'\d+', filename)
        return int(nums[0]) if nums else 0

    files.sort(key=extract_number)

    frames = []
    for f in files:
        filepath = os.path.join(dir_path, f)
        try:
            img = pygame.image.load(filepath).convert_alpha()
            frames.append((f, img))
        except Exception as e:
            print(f"加载失败: {filepath} - {e}")

    return frames


def choose_folder():
    """弹出文件夹选择对话框"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder = filedialog.askdirectory(title="选择宠物精灵图文件夹")
    root.destroy()
    return folder


def load_config_from_json():
    """从 pet_config.json 加载配置，合并到 PET_CONFIG"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "data", "pet_config.json")
    if not os.path.exists(config_path):
        print("未找到 pet_config.json，使用默认配置")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        for pet_id, config in loaded.items():
            if pet_id in PET_CONFIG:
                if "state_config" in config:
                    PET_CONFIG[pet_id]["state_config"] = {
                        **PET_CONFIG[pet_id].get("state_config", {}),
                        **config["state_config"]
                    }
            else:
                PET_CONFIG[pet_id] = config
        print(f"已加载 pet_config.json")
    except Exception as e:
        print(f"加载 pet_config.json 失败: {e}")


def main():
    # 选择宠物文件夹
    folder = choose_folder()
    if not folder:
        print("未选择文件夹")
        pygame.quit()
        return

    pet_id = os.path.basename(folder)
    print(f"加载宠物: {pet_id}")

    # 加载所有动作的帧
    all_frames = {}
    for state in os.listdir(folder):
        state_dir = os.path.join(folder, state)
        if os.path.isdir(state_dir):
            frames = load_frames_from_dir(state_dir)
            if frames:
                all_frames[state] = frames
                print(f"  {state}: {len(frames)}帧")

    if not all_frames:
        print("没有找到任何帧")
        pygame.quit()
        return

    # 获取 idle_0 作为参考图
    ref_img = None
    if "idle" in all_frames and all_frames["idle"]:
        ref_img = all_frames["idle"][0][1]

    # 状态变量
    states = list(all_frames.keys())
    current_state_idx = 0
    current_state = states[0]
    current_frame_idx = 0
    frame_timer = 0
    paused = False
    show_ref = True  # 显示参考图
    ref_alpha = 128  # 参考图透明度

    # 等级解锁编辑状态
    editing_level = False  # 是否正在编辑等级解锁
    level_input = ""  # 等级输入缓冲

    # 加载配置（优先从 pet_config.json）
    load_config_from_json()

    # 获取当前配置
    if pet_id in PET_CONFIG:
        pet_config = PET_CONFIG[pet_id]
    else:
        pet_config = {"states": list(all_frames.keys()), "level_unlocks": {}, "state_config": {}}

    # 确保 level_unlocks 存在
    if "level_unlocks" not in pet_config:
        pet_config["level_unlocks"] = {}

    running = True
    while running:
        dt = clock.get_time() / 1000.0

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN:
                # 等级解锁编辑模式
                if editing_level:
                    if ev.key == pygame.K_ESCAPE:
                        editing_level = False
                        level_input = ""
                    elif ev.key == pygame.K_RETURN:
                        # 保存输入的等级
                        try:
                            level = int(level_input) if level_input else 0
                            # 移除该动作在其他等级中的记录
                            for lvl in list(pet_config["level_unlocks"].keys()):
                                if current_state in pet_config["level_unlocks"][lvl]:
                                    pet_config["level_unlocks"][lvl].remove(current_state)
                            # 添加到新等级
                            if level not in pet_config["level_unlocks"]:
                                pet_config["level_unlocks"][level] = []
                            pet_config["level_unlocks"][level].append(current_state)
                            print(f"设置 {current_state} 解锁等级: {level}")
                        except ValueError:
                            print("无效的等级输入")
                        editing_level = False
                        level_input = ""
                    elif ev.key == pygame.K_BACKSPACE:
                        level_input = level_input[:-1]
                    elif ev.unicode.isdigit():
                        level_input += ev.unicode
                    continue

                # 正常模式
                if ev.key == pygame.K_ESCAPE or ev.key == pygame.K_q:
                    running = False

                # 切换动作
                elif ev.key == pygame.K_LEFT:
                    current_state_idx = (current_state_idx - 1) % len(states)
                    current_state = states[current_state_idx]
                    current_frame_idx = 0
                    frame_timer = 0
                elif ev.key == pygame.K_RIGHT:
                    current_state_idx = (current_state_idx + 1) % len(states)
                    current_state = states[current_state_idx]
                    current_frame_idx = 0
                    frame_timer = 0

                # 暂停/播放
                elif ev.key == pygame.K_SPACE:
                    paused = not paused

                # 显示/隐藏参考图
                elif ev.key == pygame.K_r:
                    show_ref = not show_ref

                # 调整参考图透明度
                elif ev.key == pygame.K_UP:
                    ref_alpha = min(255, ref_alpha + 32)
                elif ev.key == pygame.K_DOWN:
                    ref_alpha = max(32, ref_alpha - 32)

                # 调整偏移量
                elif ev.key == pygame.K_w:  # W - 上移
                    pet_config["state_config"].setdefault(current_state, {})
                    pet_config["state_config"][current_state]["offset_y"] = \
                        pet_config["state_config"][current_state].get("offset_y", 0) - 1
                elif ev.key == pygame.K_s:  # S - 下移
                    pet_config["state_config"].setdefault(current_state, {})
                    pet_config["state_config"][current_state]["offset_y"] = \
                        pet_config["state_config"][current_state].get("offset_y", 0) + 1
                elif ev.key == pygame.K_a:  # A - 左移
                    pet_config["state_config"].setdefault(current_state, {})
                    pet_config["state_config"][current_state]["offset_x"] = \
                        pet_config["state_config"][current_state].get("offset_x", 0) - 1
                elif ev.key == pygame.K_d:  # D - 右移
                    pet_config["state_config"].setdefault(current_state, {})
                    pet_config["state_config"][current_state]["offset_x"] = \
                        pet_config["state_config"][current_state].get("offset_x", 0) + 1

                # 调整帧率
                elif ev.key == pygame.K_EQUALS or ev.key == pygame.K_PLUS:  # + 加速
                    pet_config["state_config"].setdefault(current_state, {})
                    pet_config["state_config"][current_state]["fps"] = \
                        min(60, pet_config["state_config"][current_state].get("fps", 8) + 1)
                elif ev.key == pygame.K_MINUS:  # - 减速
                    pet_config["state_config"].setdefault(current_state, {})
                    pet_config["state_config"][current_state]["fps"] = \
                        max(1, pet_config["state_config"][current_state].get("fps", 8) - 1)

                # 切换循环模式
                elif ev.key == pygame.K_l:
                    pet_config["state_config"].setdefault(current_state, {})
                    current_loop = pet_config["state_config"][current_state].get("loop", True)
                    pet_config["state_config"][current_state]["loop"] = not current_loop

                # 调整缩放
                elif ev.key == pygame.K_z:  # Z - 缩小
                    pet_config["state_config"].setdefault(current_state, {})
                    pet_config["state_config"][current_state]["scale"] = \
                        round(max(0.1, pet_config["state_config"][current_state].get("scale", 1.0) - 0.05), 2)
                elif ev.key == pygame.K_x:  # X - 放大
                    pet_config["state_config"].setdefault(current_state, {})
                    pet_config["state_config"][current_state]["scale"] = \
                        round(min(3.0, pet_config["state_config"][current_state].get("scale", 1.0) + 0.05), 2)

                # 编辑等级解锁
                elif ev.key == pygame.K_e:
                    editing_level = True
                    # 显示当前等级
                    current_level = 0
                    for lvl, state_list in pet_config.get("level_unlocks", {}).items():
                        if current_state in state_list:
                            current_level = int(lvl)
                            break
                    level_input = str(current_level)
                    print(f"编辑 {current_state} 解锁等级 (当前: {current_level})")

                # 保存配置
                elif ev.key == pygame.K_F5:
                    save_config(pet_id, pet_config)

        # 播放逻辑
        if not paused and current_state in all_frames:
            frames = all_frames[current_state]
            state_config = pet_config.get("state_config", {}).get(current_state, {})
            fps = state_config.get("fps", 8)
            loop = state_config.get("loop", True)

            frame_timer += dt
            if frame_timer >= 1.0 / fps:
                frame_timer = 0
                current_frame_idx += 1
                if current_frame_idx >= len(frames):
                    if loop:
                        current_frame_idx = 0
                    else:
                        current_frame_idx = len(frames) - 1
                        paused = True

        # 绘制
        screen.fill((40, 40, 50))

        # 获取当前帧
        if current_state in all_frames:
            frames = all_frames[current_state]
            if frames:
                fname, img = frames[current_frame_idx]
                state_config = pet_config.get("state_config", {}).get(current_state, {})
                offset_x = state_config.get("offset_x", 0)
                offset_y = state_config.get("offset_y", 0)
                scale = state_config.get("scale", 1.0)

                # 居中位置
                center_x = WIN_W // 2
                center_y = WIN_H // 2

                # 绘制参考图（idle_0）
                if show_ref and ref_img:
                    ref_w, ref_h = ref_img.get_size()
                    ref_surface = pygame.Surface((ref_w, ref_h), pygame.SRCALPHA)
                    ref_surface.blit(ref_img, (0, 0))
                    ref_surface.set_alpha(ref_alpha)
                    screen.blit(ref_surface, (center_x - ref_w // 2, center_y - ref_h // 2))

                # 绘制当前帧（带偏移和缩放）
                w, h = img.get_size()
                scaled_w = max(1, int(w * scale))
                scaled_h = max(1, int(h * scale))
                if scale != 1.0:
                    scaled_img = pygame.transform.scale(img, (scaled_w, scaled_h))
                else:
                    scaled_img = img
                screen.blit(scaled_img, (center_x - scaled_w // 2 + offset_x, center_y - scaled_h // 2 + offset_y))

        # 绘制信息面板
        draw_info_panel(pet_id, current_state, current_frame_idx,
                       all_frames.get(current_state, []), pet_config, show_ref, ref_alpha, paused,
                       editing_level, level_input)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def draw_info_panel(pet_id, state, frame_idx, frames, config, show_ref, ref_alpha, paused,
                    editing_level=False, level_input=""):
    """绘制信息面板"""
    panel_x = 10
    panel_y = 10
    panel_w = 320
    panel_h = 380

    # 背景
    bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    bg.fill((20, 20, 30, 200))
    screen.blit(bg, (panel_x, panel_y))

    state_config = config.get("state_config", {}).get(state, {})
    fps = state_config.get("fps", 8)
    loop = state_config.get("loop", True)
    offset_x = state_config.get("offset_x", 0)
    offset_y = state_config.get("offset_y", 0)
    scale = state_config.get("scale", 1.0)

    # 获取当前动作的解锁等级
    current_level = 0
    level_unlocks = config.get("level_unlocks", {})
    for lvl, state_list in level_unlocks.items():
        if state in state_list:
            current_level = int(lvl)
            break

    lines = [
        f"宠物: {pet_id}",
        f"动作: {state} ({frame_idx + 1}/{len(frames)})",
        f"帧率: {fps} FPS {'[L+]' if fps < 60 else ''} {'[L-]' if fps > 1 else ''}",
        f"循环: {'是' if loop else '否'} (L切换)",
        f"偏移: X={offset_x}, Y={offset_y}",
        f"缩放: {scale:.2f} (Z缩小 X放大)",
        f"解锁等级: {current_level} (E编辑)",
        f"参考图: {'显示' if show_ref else '隐藏'} (R切换)",
        f"参考透明度: {ref_alpha} (↑↓调整)",
        f"{'暂停' if paused else '播放'} (空格切换)",
    ]

    # 等级解锁编辑模式提示
    if editing_level:
        lines.append("")
        lines.append(f">>> 编辑解锁等级 <<<")
        lines.append(f"输入等级: {level_input}_")
        lines.append("Enter确认 / Esc取消")

    lines.extend([
        "",
        "--- 操作说明 ---",
        "← → : 切换动作",
        "WASD : 调整偏移量",
        "Z X : 调整缩放",
        "+ - : 调整帧率",
        "L : 切换循环模式",
        "E : 编辑解锁等级",
        "R : 显示/隐藏参考图",
        "↑ ↓ : 调整参考图透明度",
        "F5 : 保存配置",
        "ESC : 退出",
    ])

    # 绘制等级解锁列表
    lines.append("")
    lines.append("--- 等级解锁配置 ---")
    for lvl in sorted(level_unlocks.keys()):
        state_list = level_unlocks[lvl]
        if state_list:
            lines.append(f"Lv.{lvl}: {', '.join(state_list)}")

    y = panel_y + 10
    for line in lines:
        # 高亮当前编辑的等级
        if editing_level and "解锁等级" in line:
            txt = font.render(line, True, (255, 220, 100))
        elif line.startswith("Lv.") and state in line:
            txt = font.render(line, True, (100, 255, 100))
        else:
            txt = font.render(line, True, (255, 255, 255))
        screen.blit(txt, (panel_x + 10, y))
        y += 20


def save_config(pet_id, config):
    """保存配置到 pet_config.json"""
    save_path = os.path.join(os.path.dirname(__file__), "..", "data", "pet_config.json")

    # 确保目录存在
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # 读取现有配置
    existing = {}
    if os.path.exists(save_path):
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except:
            pass

    # 更新配置
    existing[pet_id] = config

    # 保存
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"配置已保存: {save_path}")
    print(f"内容: {json.dumps(config, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
