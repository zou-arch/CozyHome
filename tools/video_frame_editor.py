"""
视频帧编辑器
从 scot 文件夹读取截图，自动去除背景和水印，保存到 A 文件夹
功能：
- 启动时自动处理未处理的图片
- 左键：预览去除背景（洪水填充）
- 右键：恢复像素
- F键：手动去背景
- W键：手动去水印
- C键：保存（有预览时先确认再保存）
- 方向键/滚轮：切换图片
- 右侧配置面板：配置宠物动作的等级解锁
"""
import pygame
import os
import sys
import json
import re
import tkinter as tk
from tkinter import filedialog
from collections import deque, Counter

# 路径配置
SCOT_DIR = os.path.join(os.path.dirname(__file__), "..", "temp", "scot")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "temp", "A")
TEMP_DIR = os.path.join(os.path.dirname(__file__), "..", "temp")
PET_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pet_config.json")
PETS_SPRITES_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "pets")

# 窗口配置
WIN_W, WIN_H = 1400, 800
IMG_DISPLAY = 600
PANEL_H = 60
INFO_H = 25
LIST_W = 200
CONFIG_W = 250  # 右侧配置面板宽度

# 初始化
pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("视频帧编辑器")
clock = pygame.time.Clock()

try:
    font = pygame.font.SysFont("microsoftyahei", 13)
    font_title = pygame.font.SysFont("microsoftyahei", 15, bold=True)
    font_info = pygame.font.SysFont("microsoftyahei", 12)
except:
    font = pygame.font.Font(None, 16)
    font_title = font
    font_info = font


def _process_single_image(args):
    """处理单张图片（用于多线程）"""
    fname, scot_dir, output_dir = args
    import pygame
    from collections import deque, Counter

    path = os.path.join(scot_dir, fname)
    img = pygame.image.load(path).convert_alpha()
    w, h = img.get_size()
    pixels = pygame.surfarray.array3d(img)
    alpha = pygame.surfarray.array_alpha(img)

    # 检测背景色
    samples = []
    for x, y in [(2, 2), (w-3, 2), (2, h-3), (w-3, h-3),
                  (w//2, 2), (w//2, h-3), (2, h//2), (w-3, h//2)]:
        if x < w and y < h:
            samples.append((int(pixels[x, y, 0]), int(pixels[x, y, 1]), int(pixels[x, y, 2])))
    bg = Counter(samples).most_common(1)[0][0]

    # 从边缘洪水填充
    outside = set()
    visited = set()
    queue = deque()
    tolerance = 110

    def matches_bg(x, y):
        r, g, b = int(pixels[x, y, 0]), int(pixels[x, y, 1]), int(pixels[x, y, 2])
        a = alpha[x, y]
        if a == 0:
            return True
        dist = ((r - bg[0])**2 + (g - bg[1])**2 + (b - bg[2])**2) ** 0.5
        return dist < tolerance

    for x in range(w):
        for y in [0, h - 1]:
            if (x, y) not in visited:
                visited.add((x, y))
                if matches_bg(x, y):
                    outside.add((x, y))
                    queue.append((x, y))
    for y in range(h):
        for x in [0, w - 1]:
            if (x, y) not in visited:
                visited.add((x, y))
                if matches_bg(x, y):
                    outside.add((x, y))
                    queue.append((x, y))

    while queue:
        cx, cy = queue.popleft()
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                visited.add((nx, ny))
                if matches_bg(nx, ny):
                    outside.add((nx, ny))
                    queue.append((nx, ny))

    # 应用去除
    result = img.copy()
    for (x, y) in outside:
        result.set_at((x, y), (0, 0, 0, 0))

    # 去水印（右下角区域）
    watermark_x_start = int(w * 0.8)
    watermark_y_start = int(h * 0.85)
    for y in range(watermark_y_start, h):
        for x in range(watermark_x_start, w):
            if 0 <= x < w and 0 <= y < h:
                result.set_at((x, y), (0, 0, 0, 0))

    # 保存
    pygame.image.save(result, os.path.join(output_dir, fname))
    return fname, len(outside)


def batch_process_images():
    """批量处理 scot 文件夹中的图片，去除背景和水印，保存到 A 文件夹"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(SCOT_DIR):
        print(f"源文件夹不存在: {SCOT_DIR}")
        return

    all_files = sorted([f for f in os.listdir(SCOT_DIR)
                       if f.endswith(".png") and not f.startswith(".")])

    files = []
    skipped = []
    for fname in all_files:
        output_path = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(output_path):
            skipped.append(fname)
        else:
            files.append(fname)

    if skipped:
        print(f"跳过 {len(skipped)} 张已处理: {', '.join(skipped[:5])}{'...' if len(skipped) > 5 else ''}")

    if not files:
        print("所有图片已处理完成！")
        return

    print(f"处理 {len(files)} 张图片...")

    for i, fname in enumerate(files, 1):
        fname_result, removed = _process_single_image((fname, SCOT_DIR, OUTPUT_DIR))
        print(f"  [{i}/{len(files)}] {fname_result}: 去除 {removed} 像素 + 水印")

    print("批量处理完成!\n")


class VideoFrameEditor:
    def __init__(self):
        # 加载文件列表（优先从 A 文件夹读取已处理的）
        self.files = []
        self.source_dir = {}  # {filename: 来源目录}

        # 优先从 A 文件夹加载
        if os.path.exists(OUTPUT_DIR):
            for f in sorted(os.listdir(OUTPUT_DIR)):
                if f.endswith(".png") and not f.startswith("."):
                    self.files.append(f)
                    self.source_dir[f] = OUTPUT_DIR

        # 补充 scot 中未处理的
        if os.path.exists(SCOT_DIR):
            for f in sorted(os.listdir(SCOT_DIR)):
                if f.endswith(".png") and not f.startswith(".") and f not in self.files:
                    self.files.append(f)
                    self.source_dir[f] = SCOT_DIR

        self.idx = 0
        self.original = None
        self.processed = None
        self.manual_remove = set()
        self.manual_keep = set()
        self.checker = self._make_checker(IMG_DISPLAY, IMG_DISPLAY)
        self.display_surf = None
        self.need_redraw = True
        self.scroll_offset = 0

        # 预览状态
        self.preview_pixels = set()
        self.preview_active = False

        # 缩放状态
        self.zoom = 1.0
        self.zoom_offset_x = 0
        self.zoom_offset_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0

        # 框选删除状态
        self.rect_selecting = False
        self.rect_start = None
        self.rect_end = None

        # 水印区域配置（右下角）
        self.watermark_x_ratio = 0.8
        self.watermark_y_ratio = 0.85

        # 保存文件夹
        self.save_dir = OUTPUT_DIR

        # 宠物配置相关
        self.pet_config = self._load_pet_config()
        self.current_pet_id = None  # 当前宠物ID
        self.pet_states = []  # 当前宠物的所有动作
        self.level_unlocks = {}  # {动作名: 解锁等级}
        self.focused_field = None  # 当前聚焦的输入框
        self.field_rects = {}  # {动作名: Rect} 用于点击检测
        self.cursor_visible = True
        self.cursor_timer = 0

        # 从文件名中提取宠物ID
        self._extract_pet_id_from_files()

        if self.files:
            self._load(0)

    def _load_pet_config(self):
        """加载 pet_config.json"""
        if os.path.exists(PET_CONFIG_PATH):
            try:
                with open(PET_CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载 pet_config.json 失败: {e}")
        return {}

    def _save_pet_config(self):
        """保存 pet_config.json"""
        try:
            os.makedirs(os.path.dirname(PET_CONFIG_PATH), exist_ok=True)
            with open(PET_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.pet_config, f, ensure_ascii=False, indent=2)
            print(f"已保存 pet_config.json")
        except Exception as e:
            print(f"保存 pet_config.json 失败: {e}")

    def _extract_pet_id_from_files(self):
        """从文件名中提取宠物ID"""
        # 文件名格式: {pet_id}_{state}_{frame_idx}.png
        # 或者在子目录: pets/{pet_id}/{state}/xxx.png
        pet_pattern = re.compile(r'^(.+?)_(idle|walk|run|hungry|sleep|roll|tongueidle|special|happy)_\d+\.png$')

        pet_ids = set()
        for fname in self.files:
            match = pet_pattern.match(fname)
            if match:
                pet_id = match.group(1)
                pet_ids.add(pet_id)

        # 如果找到宠物ID，设置第一个为当前宠物
        if pet_ids:
            self.current_pet_id = list(pet_ids)[0]
            self._update_pet_states()
            print(f"识别到宠物: {self.current_pet_id}")

    def _update_pet_states(self):
        """更新当前宠物的动作列表和等级解锁配置"""
        if not self.current_pet_id:
            return

        # 从文件名中提取所有动作
        pet_pattern = re.compile(r'^' + re.escape(self.current_pet_id) + r'_(.+?)_\d+\.png$')
        states = set()
        for fname in self.files:
            match = pet_pattern.match(fname)
            if match:
                state = match.group(1)
                states.add(state)

        self.pet_states = sorted(list(states))

        # 从配置中读取等级解锁
        if self.current_pet_id in self.pet_config:
            config = self.pet_config[self.current_pet_id]
            self.level_unlocks = config.get("level_unlocks", {})
        else:
            # 默认配置：所有动作在0级解锁
            self.level_unlocks = {state: 0 for state in self.pet_states}

        print(f"动作列表: {self.pet_states}")
        print(f"等级解锁: {self.level_unlocks}")

    def _draw_config_panel(self):
        """绘制右侧配置面板"""
        panel_x = WIN_W - CONFIG_W
        panel_y = INFO_H
        panel_h = WIN_H - INFO_H - PANEL_H

        # 背景
        pygame.draw.rect(screen, (50, 50, 65), (panel_x, panel_y, CONFIG_W, panel_h))
        pygame.draw.line(screen, (70, 70, 90), (panel_x, panel_y), (panel_x, panel_y + panel_h))

        # 标题
        title = font_title.render("等级解锁配置", True, (255, 220, 100))
        screen.blit(title, (panel_x + 10, panel_y + 8))

        # 当前宠物ID
        if self.current_pet_id:
            pet_label = font_info.render(f"宠物: {self.current_pet_id}", True, (200, 200, 200))
            screen.blit(pet_label, (panel_x + 10, panel_y + 30))

        # 动作列表和等级输入
        y = panel_y + 55
        self.field_rects = {}
        mx, my = pygame.mouse.get_pos()

        for state in self.pet_states:
            if y + 25 > panel_y + panel_h:
                break

            # 动作名称
            state_label = font_info.render(f"{state}:", True, (180, 180, 180))
            screen.blit(state_label, (panel_x + 10, y + 5))

            # 等级输入框
            level = self.level_unlocks.get(state, 0)
            input_rect = pygame.Rect(panel_x + 100, y, 60, 20)
            self.field_rects[state] = input_rect

            # 绘制输入框
            focused = (self.focused_field == state)
            border_color = (150, 180, 255) if focused else (100, 100, 130)
            pygame.draw.rect(screen, (35, 35, 50), input_rect, border_radius=2)
            pygame.draw.rect(screen, border_color, input_rect, 1, border_radius=2)

            # 显示等级
            level_text = font_info.render(str(level), True, (220, 220, 220))
            screen.blit(level_text, (input_rect.x + 5, input_rect.y + 3))

            # 光标
            if focused and self.cursor_visible:
                text_w = font_info.size(str(level))[0]
                cx = input_rect.x + 5 + text_w
                if cx < input_rect.right - 3:
                    pygame.draw.line(screen, (255, 255, 255),
                                     (cx, input_rect.y + 3), (cx, input_rect.bottom - 3))

            y += 25

        # 保存按钮
        btn_y = panel_y + panel_h - 60
        save_btn = pygame.Rect(panel_x + 10, btn_y, CONFIG_W - 20, 28)
        hover = save_btn.collidepoint(mx, my)
        btn_color = (100, 140, 100) if hover else (60, 120, 60)
        pygame.draw.rect(screen, btn_color, save_btn, border_radius=4)
        save_text = font.render("保存配置", True, (220, 255, 220))
        screen.blit(save_text, (panel_x + 20, btn_y + 6))

        # 提示
        hint = "点击输入框设置等级"
        screen.blit(font_info.render(hint, True, (120, 120, 120)), (panel_x + 10, btn_y + 35))

    def _handle_config_click(self, mx, my, button):
        """处理配置面板的点击事件"""
        if button != 1:
            return False

        panel_x = WIN_W - CONFIG_W

        # 检查是否在配置面板区域内
        if mx < panel_x:
            return False

        # 检查保存按钮
        btn_y = INFO_H + (WIN_H - INFO_H - PANEL_H) - 60
        save_btn = pygame.Rect(panel_x + 10, btn_y, CONFIG_W - 20, 28)
        if save_btn.collidepoint(mx, my):
            self._save_level_unlocks_to_config()
            return True

        # 检查输入框点击
        for state, rect in self.field_rects.items():
            if rect.collidepoint(mx, my):
                self.focused_field = state
                self.cursor_timer = 0
                self.cursor_visible = True
                return True

        # 点击空白取消聚焦
        self.focused_field = None
        return False

    def _handle_config_input(self, ev):
        """处理配置面板的键盘输入"""
        if self.focused_field is None:
            return False

        if ev.key == pygame.K_RETURN:
            self.focused_field = None
            return True
        elif ev.key == pygame.K_ESCAPE:
            self.focused_field = None
            return True
        elif ev.key == pygame.K_BACKSPACE:
            current = self.level_unlocks.get(self.focused_field, 0)
            # 删除最后一位数字
            current_str = str(current)
            if len(current_str) > 1:
                current_str = current_str[:-1]
                self.level_unlocks[self.focused_field] = int(current_str) if current_str else 0
            else:
                self.level_unlocks[self.focused_field] = 0
            return True
        elif ev.key == pygame.K_UP:
            current = self.level_unlocks.get(self.focused_field, 0)
            self.level_unlocks[self.focused_field] = current + 1
            return True
        elif ev.key == pygame.K_DOWN:
            current = self.level_unlocks.get(self.focused_field, 0)
            self.level_unlocks[self.focused_field] = max(0, current - 1)
            return True
        else:
            # 数字输入
            if hasattr(ev, 'unicode') and ev.unicode.isdigit():
                current = self.level_unlocks.get(self.focused_field, 0)
                current_str = str(current)
                if current_str == "0":
                    current_str = ev.unicode
                else:
                    current_str += ev.unicode
                self.level_unlocks[self.focused_field] = int(current_str)
                return True
        return False

    def _save_level_unlocks_to_config(self):
        """保存等级解锁配置到 pet_config.json"""
        if not self.current_pet_id:
            print("没有选择宠物")
            return

        # 确保宠物配置存在
        if self.current_pet_id not in self.pet_config:
            self.pet_config[self.current_pet_id] = {}

        # 更新配置
        self.pet_config[self.current_pet_id]["level_unlocks"] = self.level_unlocks
        self.pet_config[self.current_pet_id]["states"] = self.pet_states

        # 保存
        self._save_pet_config()
        print(f"已保存 {self.current_pet_id} 的等级解锁配置")

    def _choose_save_dir(self):
        """弹出文件夹选择对话框"""
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder = filedialog.askdirectory(title="选择保存文件夹", initialdir=TEMP_DIR)
        root.destroy()
        if folder:
            self.save_dir = folder
            print(f"保存到: {folder}")

    def _make_checker(self, w, h):
        surf = pygame.Surface((w, h))
        for y in range(0, h, 16):
            for x in range(0, w, 16):
                c = (200, 200, 200) if ((x // 16) + (y // 16)) % 2 == 0 else (240, 240, 240)
                pygame.draw.rect(surf, c, (x, y, 16, 16))
        return surf

    def _load(self, idx):
        if idx < 0 or idx >= len(self.files):
            return
        self.idx = idx
        fname = self.files[idx]
        # 优先从来源目录加载
        src = self.source_dir.get(fname, SCOT_DIR)
        path = os.path.join(src, fname)
        self.original = pygame.image.load(path).convert_alpha()
        self.processed = self.original.copy()
        self.manual_remove.clear()
        self.manual_keep.clear()
        self.need_redraw = True

    def _get_display(self):
        if self.processed is None:
            return None
        d = self.processed.copy()
        for (x, y) in self.manual_remove:
            if 0 <= x < d.get_width() and 0 <= y < d.get_height():
                d.set_at((x, y), (0, 0, 0, 0))
        for (x, y) in self.manual_keep:
            if self.original and 0 <= x < self.original.get_width() and 0 <= y < self.original.get_height():
                d.set_at((x, y), self.original.get_at((x, y)))
        # 缩放
        w, h = d.get_size()
        zw = int(w * self.zoom)
        zh = int(h * self.zoom)
        return pygame.transform.scale(d, (zw, zh))

    def preview_flood(self, sx, sy):
        """预览洪水填充区域"""
        w, h = self.processed.get_size()
        pixels = pygame.surfarray.array3d(self.processed)
        alpha = pygame.surfarray.array_alpha(self.processed)

        ref_color = (int(pixels[sx, sy, 0]), int(pixels[sx, sy, 1]), int(pixels[sx, sy, 2]))

        if alpha[sx, sy] == 0:
            return 0

        q = deque([(sx, sy)])
        filled = {(sx, sy)}
        tolerance = 110

        while q:
            cx, cy = q.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in filled:
                    r, g, b = int(pixels[nx, ny, 0]), int(pixels[nx, ny, 1]), int(pixels[nx, ny, 2])
                    a = alpha[nx, ny]
                    dist = ((r - ref_color[0])**2 + (g - ref_color[1])**2 + (b - ref_color[2])**2) ** 0.5
                    if a > 0 and dist < tolerance:
                        filled.add((nx, ny))
                        q.append((nx, ny))

        self.preview_pixels = filled
        self.preview_active = True
        self.need_redraw = True
        return len(filled)

    def confirm_preview(self):
        """确认删除预览区域"""
        self.manual_remove.update(self.preview_pixels)
        self.manual_keep -= self.preview_pixels
        self.preview_pixels.clear()
        self.preview_active = False
        self.need_redraw = True

    def cancel_preview(self):
        """取消预览"""
        self.preview_pixels.clear()
        self.preview_active = False
        self.need_redraw = True

    def flood_restore(self, sx, sy):
        """从点击位置洪水填充恢复"""
        w, h = self.processed.get_size()
        q = deque([(sx, sy)])
        filled = {(sx, sy)}

        while q:
            cx, cy = q.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in filled:
                    if (nx, ny) in self.manual_remove:
                        filled.add((nx, ny))
                        q.append((nx, ny))

        self.manual_remove -= filled
        self.manual_keep.update(filled)
        self.need_redraw = True
        return len(filled)

    def auto_remove_background(self):
        """自动去除背景（从边缘洪水填充）"""
        w, h = self.processed.get_size()
        pixels = pygame.surfarray.array3d(self.processed)
        alpha = pygame.surfarray.array_alpha(self.processed)

        # 检测背景色（四角采样）
        samples = []
        for x, y in [(2, 2), (w-3, 2), (2, h-3), (w-3, h-3),
                      (w//2, 2), (w//2, h-3), (2, h//2), (w-3, h//2)]:
            if x < w and y < h:
                samples.append((int(pixels[x, y, 0]), int(pixels[x, y, 1]), int(pixels[x, y, 2])))
        bg = Counter(samples).most_common(1)[0][0]
        print(f"检测背景色: RGB{bg}")

        # 从四边边缘开始洪水填充
        outside = set()
        visited = set()
        queue = deque()
        tolerance = 110

        def matches_bg(x, y):
            r, g, b = int(pixels[x, y, 0]), int(pixels[x, y, 1]), int(pixels[x, y, 2])
            a = alpha[x, y]
            if a == 0:
                return True
            dist = ((r - bg[0])**2 + (g - bg[1])**2 + (b - bg[2])**2) ** 0.5
            return dist < tolerance

        # 四条边
        for x in range(w):
            for y in [0, h - 1]:
                if (x, y) not in visited:
                    visited.add((x, y))
                    if matches_bg(x, y):
                        outside.add((x, y))
                        queue.append((x, y))

        for y in range(h):
            for x in [0, w - 1]:
                if (x, y) not in visited:
                    visited.add((x, y))
                    if matches_bg(x, y):
                        outside.add((x, y))
                        queue.append((x, y))

        # 洪水填充
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    if matches_bg(nx, ny):
                        outside.add((nx, ny))
                        queue.append((nx, ny))

        self.manual_remove.update(outside)
        self.need_redraw = True
        print(f"边缘洪水去除: {len(outside)} 像素")
        return len(outside)

    def remove_watermark(self):
        """去除水印（右下角区域）"""
        w, h = self.processed.get_size()
        watermark_x_start = int(w * self.watermark_x_ratio)
        watermark_y_start = int(h * self.watermark_y_ratio)

        count = 0
        for y in range(watermark_y_start, h):
            for x in range(watermark_x_start, w):
                if 0 <= x < w and 0 <= y < h:
                    self.manual_remove.add((x, y))
                    self.manual_keep.discard((x, y))
                    count += 1

        self.need_redraw = True
        print(f"去除水印区域: x={watermark_x_start}-{w}, y={watermark_y_start}-{h}, {count} 像素")
        return count

    def _clear_rect(self, start, end):
        """清除矩形区域内的所有像素"""
        x1, y1 = min(start[0], end[0]), min(start[1], end[1])
        x2, y2 = max(start[0], end[0]), max(start[1], end[1])
        count = 0
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if 0 <= x < self.processed.get_width() and 0 <= y < self.processed.get_height():
                    self.manual_remove.add((x, y))
                    self.manual_keep.discard((x, y))
                    count += 1
        print(f"框选删除: ({x1},{y1})-({x2},{y2}), {count} 像素")

    def save(self):
        """保存处理后的图片到当前选择的文件夹"""
        if self.processed is None:
            return

        final = self.processed.copy()
        w, h = final.get_size()

        # 应用手动保留
        for (x, y) in self.manual_keep:
            if 0 <= x < w and 0 <= y < h and self.original:
                final.set_at((x, y), self.original.get_at((x, y)))

        # 应用手动去除
        for (x, y) in self.manual_remove:
            if 0 <= x < w and 0 <= y < h:
                final.set_at((x, y), (0, 0, 0, 0))

        os.makedirs(self.save_dir, exist_ok=True)
        fname = self.files[self.idx]
        save_path = os.path.join(self.save_dir, fname)
        pygame.image.save(final, save_path)

        # 更新来源目录
        self.source_dir[fname] = self.save_dir

        # 确保文件在列表中
        if fname not in self.files:
            self.files.append(fname)

        print(f"已保存: {save_path}")

    def handle_img_click(self, mx, my, button):
        """处理图片区域点击"""
        if not self.display_surf or not hasattr(self, 'display_x'):
            return
        px = int((mx - self.display_x) / self.zoom)
        py = int((my - self.display_y) / self.zoom)

        if 0 <= px < self.processed.get_width() and 0 <= py < self.processed.get_height():
            if button == 1:
                self.cancel_preview()
                n = self.preview_flood(px, py)
                print(f"预览去除: {n} 像素 → Enter确认, Esc取消")
            elif button == 3:
                n = self.flood_restore(px, py)
                print(f"恢复: {n} 像素")

    def draw(self):
        screen.fill((40, 40, 50))

        # 文件列表
        pygame.draw.rect(screen, (50, 50, 65), (0, 0, LIST_W, WIN_H))

        # 标题
        title = font_title.render(f"文件列表 [共{len(self.files)}张]", True, (255, 220, 100))
        screen.blit(title, (10, 8))

        # 文件列表
        y = 30
        visible = (WIN_H - 40) // 20
        for i in range(self.scroll_offset, min(self.scroll_offset + visible, len(self.files))):
            fname = self.files[i]
            sel = (i == self.idx)

            rect = pygame.Rect(5, y, LIST_W - 10, 18)
            pygame.draw.rect(screen, (80, 100, 140) if sel else (50, 50, 65), rect, border_radius=3)

            txt = font.render(fname, True, (255, 255, 255) if sel else (180, 180, 180))
            screen.blit(txt, (10, y + 2))
            y += 20

        # 信息栏
        pygame.draw.rect(screen, (55, 55, 70), (LIST_W, 0, WIN_W - LIST_W - CONFIG_W, INFO_H))
        if self.files:
            fname = self.files[self.idx]
            save_name = os.path.basename(self.save_dir)
            info = f"当前: {fname} | 去除:{len(self.manual_remove)}px | 恢复:{len(self.manual_keep)}px | 保存到:{save_name}"
            screen.blit(font_info.render(info, True, (200, 200, 200)), (LIST_W + 10, 6))

        # 图片区域
        img_area_w = WIN_W - LIST_W - CONFIG_W
        img_area_h = WIN_H - PANEL_H - INFO_H
        cx = LIST_W + img_area_w // 2 + self.zoom_offset_x
        cy = INFO_H + img_area_h // 2 + self.zoom_offset_y

        if self.need_redraw or self.display_surf is None:
            self.display_surf = self._get_display()
            self.need_redraw = False

        if self.display_surf:
            dw, dh = self.display_surf.get_size()
            dx = cx - dw // 2
            dy = cy - dh // 2

            clip = pygame.Rect(LIST_W, INFO_H, img_area_w, img_area_h)
            screen.set_clip(clip)
            screen.blit(self.display_surf, (dx, dy))
            screen.set_clip(None)

            self.display_x = dx
            self.display_y = dy

        # 绘制预览高亮
        if self.preview_active and self.preview_pixels:
            preview_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
            for (px, py) in self.preview_pixels:
                sx = int(px * self.zoom)
                sy = int(py * self.zoom)
                sw = max(1, int(self.zoom))
                sh = max(1, int(self.zoom))
                pygame.draw.rect(preview_surf, (255, 50, 50, 120), (sx, sy, sw, sh))
            screen.set_clip(clip)
            screen.blit(preview_surf, (dx, dy))
            screen.set_clip(None)

        # 绘制框选矩形
        if self.rect_selecting and self.rect_start and self.rect_end and self.display_surf:
            dw, dh = self.display_surf.get_size()
            rx1 = int(min(self.rect_start[0], self.rect_end[0]) * self.zoom)
            ry1 = int(min(self.rect_start[1], self.rect_end[1]) * self.zoom)
            rx2 = int(max(self.rect_start[0], self.rect_end[0]) * self.zoom)
            ry2 = int(max(self.rect_start[1], self.rect_end[1]) * self.zoom)
            rect_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
            pygame.draw.rect(rect_surf, (100, 150, 255, 60), (rx1, ry1, rx2 - rx1, ry2 - ry1))
            pygame.draw.rect(rect_surf, (100, 150, 255, 200), (rx1, ry1, rx2 - rx1, ry2 - ry1), 2)
            screen.set_clip(clip)
            screen.blit(rect_surf, (dx, dy))
            screen.set_clip(None)

        # 面板
        pygame.draw.rect(screen, (30, 30, 40), (0, WIN_H - PANEL_H, WIN_W, PANEL_H))

        # 按钮
        btns = [
            ("上一张(<)", 15), ("下一张(>)", 110),
            ("去背景(F)", 210), ("去水印(W)", 310),
            ("保存(C)", 410), ("退出(Q)", 510)
        ]
        for text, x in btns:
            rect = pygame.Rect(x, WIN_H - PANEL_H + 5, 85, 24)
            pygame.draw.rect(screen, (80, 80, 100), rect, border_radius=4)
            screen.blit(font.render(text, True, (220, 220, 220)), (x + 6, WIN_H - PANEL_H + 9))

        # 保存文件夹按钮
        save_name = os.path.basename(self.save_dir)
        dir_btn_text = f"选择文件夹: {save_name}"
        rect = pygame.Rect(15, WIN_H - PANEL_H + 32, 180, 24)
        pygame.draw.rect(screen, (80, 100, 80), rect, border_radius=4)
        screen.blit(font.render(dir_btn_text, True, (220, 255, 220)), (20, WIN_H - PANEL_H + 36))

        # 提示
        hint = "左键:去背景 | 右键:恢复 | Enter:确认 | C:保存"
        screen.blit(font_info.render(hint, True, (150, 150, 150)), (210, WIN_H - PANEL_H + 37))

        # 绘制配置面板
        self._draw_config_panel()

    def run(self):
        running = True

        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False

                elif ev.type == pygame.KEYDOWN:
                    # 优先处理配置面板的输入
                    if self.focused_field is not None:
                        if self._handle_config_input(ev):
                            continue

                    if ev.key == pygame.K_q:
                        running = False
                    elif ev.key == pygame.K_c:
                        if self.preview_active:
                            self.confirm_preview()
                            print("已确认删除")
                        self.save()
                    elif ev.key == pygame.K_ESCAPE:
                        if self.preview_active:
                            self.cancel_preview()
                            print("已取消预览")
                        elif self.focused_field is not None:
                            self.focused_field = None
                        else:
                            running = False
                    elif ev.key == pygame.K_z:
                        if self.files:
                            self._load((self.idx - 1) % len(self.files))
                    elif ev.key == pygame.K_x:
                        if self.files:
                            self._load((self.idx + 1) % len(self.files))
                    elif ev.key == pygame.K_UP and self.scroll_offset > 0:
                        self.scroll_offset -= 1
                    elif ev.key == pygame.K_DOWN:
                        self.scroll_offset = min(self.scroll_offset + 1,
                            max(0, len(self.files) - (WIN_H - 40) // 20))

                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = ev.pos
                    # 检测配置面板点击
                    if self._handle_config_click(mx, my, ev.button):
                        continue
                    # 检测文件夹按钮点击
                    if 15 <= mx <= 195 and WIN_H - PANEL_H + 32 <= my <= WIN_H - PANEL_H + 56:
                        self._choose_save_dir()
                    elif mx < LIST_W and my < WIN_H - 25:
                        y = 30
                        visible_count = (WIN_H - 40) // 20
                        for i in range(self.scroll_offset, min(self.scroll_offset + visible_count, len(self.files))):
                            if y <= my < y + 18:
                                self._load(i)
                                break
                            y += 20
                    elif self.display_x is not None and mx >= LIST_W and mx < WIN_W - CONFIG_W and my >= INFO_H and my < WIN_H - PANEL_H:
                        if ev.button == 1:
                            px = int((mx - self.display_x) / self.zoom)
                            py = int((my - self.display_y) / self.zoom)
                            if self.processed and 0 <= px < self.processed.get_width() and 0 <= py < self.processed.get_height():
                                self.rect_selecting = True
                                self.rect_start = (px, py)
                                self.rect_end = (px, py)
                        elif ev.button == 3:
                            self.handle_img_click(mx, my, ev.button)
                        elif ev.button == 2:
                            self.is_panning = True
                            self.pan_start_x, self.pan_start_y = ev.pos

                elif ev.type == pygame.MOUSEMOTION:
                    if self.rect_selecting:
                        mx, my = ev.pos
                        if self.display_x is not None:
                            px = int((mx - self.display_x) / self.zoom)
                            py = int((my - self.display_y) / self.zoom)
                            if self.processed:
                                px = max(0, min(px, self.processed.get_width() - 1))
                                py = max(0, min(py, self.processed.get_height() - 1))
                            self.rect_end = (px, py)
                            self.need_redraw = True
                    elif self.is_panning:
                        dx = ev.pos[0] - self.pan_start_x
                        dy = ev.pos[1] - self.pan_start_y
                        self.zoom_offset_x += dx
                        self.zoom_offset_y += dy
                        self.pan_start_x, self.pan_start_y = ev.pos
                        self.need_redraw = True

                elif ev.type == pygame.MOUSEBUTTONUP:
                    if ev.button == 2:
                        self.is_panning = False
                    elif ev.button == 1 and self.rect_selecting:
                        mx, my = ev.pos
                        if self.display_x is not None:
                            px = int((mx - self.display_x) / self.zoom)
                            py = int((my - self.display_y) / self.zoom)
                            if self.processed:
                                px = max(0, min(px, self.processed.get_width() - 1))
                                py = max(0, min(py, self.processed.get_height() - 1))
                            self.rect_end = (px, py)

                        if self.rect_start and self.rect_end:
                            dx = abs(self.rect_end[0] - self.rect_start[0])
                            dy = abs(self.rect_end[1] - self.rect_start[1])
                            if dx > 3 or dy > 3:
                                self._clear_rect(self.rect_start, self.rect_end)
                            else:
                                self.handle_img_click(mx, my, 1)

                        self.rect_selecting = False
                        self.rect_start = None
                        self.rect_end = None
                        self.need_redraw = True

                elif ev.type == pygame.MOUSEWHEEL:
                    mx, my = pygame.mouse.get_pos()
                    if mx < LIST_W:
                        if ev.y > 0 and self.scroll_offset > 0:
                            self.scroll_offset -= 1
                        elif ev.y < 0:
                            self.scroll_offset = min(self.scroll_offset + 1,
                                max(0, len(self.files) - (WIN_H - 40) // 20))
                    else:
                        if ev.y > 0:
                            self.zoom = min(self.zoom * 1.3, 10.0)
                        elif ev.y < 0:
                            self.zoom = max(self.zoom / 1.3, 0.5)
                        self.need_redraw = True
                        print(f"缩放: {self.zoom:.1f}x")

            self.draw()
            pygame.display.flip()
            clock.tick(30)

        pygame.quit()


if __name__ == "__main__":
    print("=" * 50)
    print("视频帧编辑器")
    print("=" * 50)
    print(f"源文件夹: {SCOT_DIR}")
    print(f"输出文件夹: {OUTPUT_DIR}")
    print("=" * 50)

    if not os.path.exists(SCOT_DIR):
        print(f"错误: 源文件夹不存在 {SCOT_DIR}")
        print("请先运行 screenshot_tool.py 截图")
    else:
        # 先批量处理未处理的图片
        batch_process_images()

        # 打开编辑器
        editor = VideoFrameEditor()
        if not editor.files:
            print("没有图片")
        else:
            print(f"找到 {len(editor.files)} 张图片")
            editor.run()
