"""
家具编辑器（完整版）
支持抠图、footprint/wall/placeable编辑、配置、游戏预览、自动注册

布局:
  +---------+----------------+-----------+
  | Left    |   Center       | Right     |
  | 150px   |   (flex)       | 280px     |
  | File    |  Edit/Game     | Config    |
  | List    |  Preview       | Panel     |
  |         |                |           |
  +---------+----------------+-----------+
  | Bottom Toolbar (60px)               |
  +--------------------------------------+
  | Top Info Bar (28px)                  |
  +--------------------------------------+

快捷键:
  Z/X:切换图片  Q:退出  C:确认+保存
  F/W/A:编辑模式(footprint/wall/placeable)  V:裁剪
  T:标签切换  0/1/2:筛选
  Ctrl+G:游戏预览  Ctrl+E:编辑模式
  左键:洪水填充(预览)  右键:恢复
  中键拖动:平移  滚轮:缩放/滚动
  框选:拖拽左键(>3像素)
"""
import pygame
import os
import sys
import json
import math
from collections import deque, Counter

# ============================================================
# 路径常量
# ============================================================
TEMP_DIR = os.path.join(os.path.dirname(__file__), "..", "temp")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "temp", "processed")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "furniture")
FARM_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "floor")
CROPS_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "crops")
UI_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "ui")
PET_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "pets")
FURNITURE_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "entities", "furniture.py")

# ============================================================
# 窗口布局常量
# ============================================================
WIN_W, WIN_H = 1400, 840
LEFT_W = 150                          # 左侧文件列表宽度
RIGHT_W = 280                         # 右侧配置面板宽度
TOOLBAR_H = 60                        # 底部工具栏高度
INFO_H = 28                           # 顶部信息栏高度
CENTER_X = LEFT_W                     # 中央区域起始X
CENTER_W = WIN_W - LEFT_W - RIGHT_W   # 中央区域宽度
CENTER_H = WIN_H - INFO_H - TOOLBAR_H # 中央区域高度

# 配置面板参数
CFG_X = WIN_W - RIGHT_W
CFG_W = RIGHT_W
CFG_ROW_H = 22                        # 配置行高
CFG_PAD = 6                           # 内边距
CFG_LABEL_W = 60                      # 标签宽度

# ============================================================
# 颜色
# ============================================================
COLOR_BG = (40, 40, 50)
COLOR_PANEL = (50, 50, 65)
COLOR_TOOLBAR = (30, 30, 40)
COLOR_INFO = (55, 55, 70)
COLOR_TEXT = (220, 220, 220)
COLOR_TEXT_DIM = (150, 150, 150)
COLOR_TEXT_BRIGHT = (255, 255, 255)
COLOR_ACCENT = (255, 220, 100)
COLOR_BTN = (80, 80, 100)
COLOR_BTN_HOVER = (100, 100, 120)
COLOR_BTN_GREEN = (60, 140, 60)
COLOR_BTN_BLUE = (60, 100, 180)
COLOR_INPUT_BG = (35, 35, 50)
COLOR_INPUT_BORDER = (100, 100, 130)
COLOR_INPUT_FOCUS = (150, 180, 255)

# ============================================================
# 游戏坐标系参数（与 world.py / coordinate_viewer 一致）
# ============================================================
GAME_TILE_SPACING = 120
GAME_TILE_WIDTH = 174   # 菱形水平半对角线
GAME_TILE_HEIGHT = 85   # 菱形垂直半对角线

# 斜坐标系角度（116°/244°，对应 26°/334° 边方向）
GAME_ALPHA = math.radians(116)
GAME_BETA = math.radians(244)
GAME_COS_A, GAME_SIN_A = math.cos(GAME_ALPHA), math.sin(GAME_ALPHA)
GAME_COS_B, GAME_SIN_B = math.cos(GAME_BETA), math.sin(GAME_BETA)
GAME_DET = GAME_COS_A * GAME_SIN_B - GAME_SIN_A * GAME_COS_B
GAME_K = GAME_TILE_SPACING / abs(GAME_DET)

# 正变换矩阵（斜网格坐标 -> 世界坐标）
GAME_M_FORWARD = [
    [-GAME_SIN_A * GAME_K / GAME_DET, GAME_SIN_B * GAME_K / GAME_DET],
    [GAME_COS_A * GAME_K / GAME_DET, -GAME_COS_B * GAME_K / GAME_DET]
]

# 逆变换矩阵（世界坐标 -> 斜网格坐标）
GAME_DET_M = GAME_M_FORWARD[0][0] * GAME_M_FORWARD[1][1] - GAME_M_FORWARD[0][1] * GAME_M_FORWARD[1][0]
GAME_M_INVERSE = [
    [GAME_M_FORWARD[1][1] / GAME_DET_M, -GAME_M_FORWARD[0][1] / GAME_DET_M],
    [-GAME_M_FORWARD[1][0] / GAME_DET_M, GAME_M_FORWARD[0][0] / GAME_DET_M]
]

# 游戏默认缩放因子（与 camera.py 一致）
GAME_DEFAULT_ZOOM = 0.8

# ============================================================
# 全局对象（懒加载）
# ============================================================
screen = None
clock = None
font = None
font_bold = None
font_small = None
font_title = None

def init_fonts():
    """初始化字体（线程安全）"""
    global font, font_bold, font_small, font_title
    if font is not None:
        return
    try:
        font = pygame.font.SysFont("microsoftyahei", 13)
        font_bold = pygame.font.SysFont("microsoftyahei", 13, bold=True)
        font_small = pygame.font.SysFont("microsoftyahei", 12)
        font_title = pygame.font.SysFont("microsoftyahei", 15, bold=True)
    except:
        font = pygame.font.Font(None, 16)
        font_bold = font
        font_small = pygame.font.Font(None, 14)
        font_title = font

def init_editor_display():
    """初始化编辑器显示"""
    global screen, clock
    if screen is None:
        pygame.init()
        screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("家具抠图编辑器 v2")
        clock = pygame.time.Clock()
    init_fonts()


# ============================================================
# 批量去背
# ============================================================
# ============================================================
# 工具函数
# ============================================================
def detect_file_type_by_name(fname):
    """
    根据文件名检测文件类型（模块级版本，编辑器内外都能用）
    """
    import re
    crop_suffixes = ["_stage0.png", "_stage1.png", "_stage2.png", "_stage3.png"]
    farm_files = ["Soil.png", "水生.png", "盆栽.png", "沙生.png",
                  "F_farm_soil.png", "F_farm_water.png", "F_farm_pot.png", "F_farm_sand.png"]
    ui_icon_suffixes = ["_icon.png", "_btn.png", "_slot.png"]

    # 宠物: *_state_N.png 格式
    pet_pattern = re.compile(r'^(.+)_(idle|walk|run|hungry|sleep|roll|tongueidle|special|happy)_\d+\.png$')
    if pet_pattern.match(fname):
        return "pet"

    # 作物
    if any(fname.endswith(suffix) for suffix in crop_suffixes):
        return "crop"

    # 种植区/地板
    if fname in farm_files or "farm" in fname or fname.startswith("F_floor"):
        return "floor"

    # UI图标
    if any(fname.endswith(suffix) for suffix in ui_icon_suffixes) or fname.startswith("ui_"):
        return "ui"

    # 地板 (F_ 开头)
    if fname.startswith("F"):
        return "floor"

    # 家具 (需要检查文件是否存在)
    furniture_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "furniture")
    if os.path.exists(os.path.join(furniture_dir, fname)):
        return "furniture"

    return "unknown"


# ============================================================
# 批量去背
# ============================================================
def batch_flood_remove():
    """批量从边缘洪水填充去青色背景，保存到中间目录（跳过已处理的）"""
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    all_files = sorted([f for f in os.listdir(TEMP_DIR)
                       if f.endswith(".png") and not f.startswith(".")])

    files = []
    skipped = []
    for fname in all_files:
        processed_path = os.path.join(PROCESSED_DIR, fname)
        source_path = os.path.join(TEMP_DIR, fname)
        if os.path.exists(processed_path):
            if os.path.getmtime(source_path) > os.path.getmtime(processed_path):
                files.append(fname)
            else:
                skipped.append(fname)
        else:
            files.append(fname)

    if skipped:
        print(f"跳过 {len(skipped)} 张已处理: {', '.join(skipped[:5])}{'...' if len(skipped) > 5 else ''}")
    if not files:
        print("所有图片已处理完成！")
        return

    print(f"批量处理 {len(files)} 张图片...")
    for fname in files:
        path = os.path.join(TEMP_DIR, fname)
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        pixels = pygame.surfarray.array3d(img)
        alpha = pygame.surfarray.array_alpha(img)

        samples = []
        for x, y in [(2, 2), (w-3, 2), (2, h-3), (w-3, h-3),
                      (w//2, 2), (w//2, h-3), (2, h//2), (w-3, h//2)]:
            samples.append((int(pixels[x, y, 0]), int(pixels[x, y, 1]), int(pixels[x, y, 2])))
        bg = Counter(samples).most_common(1)[0][0]

        outside = set()
        visited = set()
        queue = deque()
        tolerance = 60

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

        result = img.copy()
        for (x, y) in outside:
            result.set_at((x, y), (0, 0, 0, 0))

        watermark_x_start = int(w * 0.8)
        watermark_y_start = int(h * 0.85)
        for y in range(watermark_y_start, h):
            for x in range(watermark_x_start, w):
                if 0 <= x < w and 0 <= y < h:
                    result.set_at((x, y), (0, 0, 0, 0))
        print(f"  去除水印区域: x={watermark_x_start}-{w}, y={watermark_y_start}-{h}")

        r_alpha = pygame.surfarray.array_alpha(result)
        min_x, min_y = w, h
        max_x, max_y = 0, 0
        for y in range(h):
            for x in range(w):
                if r_alpha[x, y] > 10:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if min_x < max_x:
            pad = 4
            min_x = max(0, min_x - pad)
            min_y = max(0, min_y - pad)
            max_x = min(w - 1, max_x + pad)
            max_y = min(h - 1, max_y + pad)
            cw, ch = max_x - min_x + 1, max_y - min_y + 1
            cropped = pygame.Surface((cw, ch), pygame.SRCALPHA)
            for y in range(ch):
                for x in range(cw):
                    cropped.set_at((x, y), result.get_at((min_x + x, min_y + y)))
            result = cropped

        save_path = os.path.join(PROCESSED_DIR, fname)
        pygame.image.save(result, save_path)
        print(f"  {fname}: 去除 {len(outside)} 像素")

        # 根据文件类型自动保存到对应目录
        ftype = detect_file_type_by_name(fname)
        type_to_dir = {
            "furniture": OUTPUT_DIR,
            "crop": CROPS_OUTPUT_DIR,
            "pet": PET_OUTPUT_DIR,
            "floor": FARM_OUTPUT_DIR,
            "ui": UI_OUTPUT_DIR,
        }
        target_dir = type_to_dir.get(ftype, PROCESSED_DIR)
        os.makedirs(target_dir, exist_ok=True)
        pygame.image.save(result, os.path.join(target_dir, fname))
        print(f"  保存 [{ftype}]: {fname} → {os.path.basename(target_dir)}/")
    print("批量处理完成!\n")


# ============================================================
# 坐标变换函数（与 coordinate_viewer 一致）
# ============================================================
def game_grid_to_world(gx, gy):
    """斜网格坐标 -> 世界坐标"""
    wx = GAME_M_FORWARD[0][0] * gx + GAME_M_FORWARD[0][1] * gy
    wy = GAME_M_FORWARD[1][0] * gx + GAME_M_FORWARD[1][1] * gy
    return wx, wy

def game_world_to_grid(wx, wy):
    """世界坐标 -> 斜网格坐标"""
    gx = GAME_M_INVERSE[0][0] * wx + GAME_M_INVERSE[0][1] * wy
    gy = GAME_M_INVERSE[1][0] * wx + GAME_M_INVERSE[1][1] * wy
    return gx, gy

def game_world_to_screen(wx, wy, cam_x, cam_y, zoom, scr_w, scr_h):
    """世界坐标 -> 屏幕坐标"""
    sx = (wx - cam_x) * zoom + scr_w // 2
    sy = (wy - cam_y) * zoom + scr_h // 2
    return sx, sy

def game_screen_to_world(sx, sy, cam_x, cam_y, zoom, scr_w, scr_h):
    """屏幕坐标 -> 世界坐标"""
    wx = (sx - scr_w // 2) / zoom + cam_x
    wy = (sy - scr_h // 2) / zoom + cam_y
    return wx, wy

def game_get_tile_vertices(gx, gy):
    """获取区块的四个顶点（菱形）"""
    x0, y0 = game_grid_to_world(gx, gy)
    x1, y1 = game_grid_to_world(gx + 1, gy)
    x2, y2 = game_grid_to_world(gx + 1, gy + 1)
    x3, y3 = game_grid_to_world(gx, gy + 1)
    return [(x0, y0), (x1, y1), (x2, y2), (x3, y3)]

# ============================================================
# 家具编辑器主类
# ============================================================
class FurnitureEditor:
    def __init__(self):
        init_editor_display()
        self._init_file_list()
        self._init_edit_state()
        self._init_view_state()
        self._init_config()
        self._init_polygon_modes()

        # 加载数据
        self._load_all_data()
        self._update_filter()

        if self.files:
            self._load(0)
            self._load_config_for_current()

    # ---- 初始化分组 ----

    def _init_file_list(self):
        """初始化文件列表"""
        processed_files = set()
        self.files = []
        if os.path.exists(PROCESSED_DIR):
            processed_files = set(f for f in os.listdir(PROCESSED_DIR)
                                if f.endswith(".png") and not f.startswith("."))
            self.files = sorted(list(processed_files))
        if os.path.exists(TEMP_DIR):
            for f in sorted(os.listdir(TEMP_DIR)):
                if f.endswith(".png") and not f.startswith(".") and f not in processed_files:
                    self.files.append(f)
        self.source_dir = PROCESSED_DIR
        self.current_file_idx = 0

        # 植物文件映射：{植物名: [stage0文件, stage1文件, stage2文件, stage3文件]}
        self._crop_file_map = {}
        # 为植物创建统一的显示名称
        self._build_crop_file_map()

    def _init_edit_state(self):
        """初始化编辑状态"""
        self.idx = 0
        self.original = None
        self.processed = None
        self.manual_remove = set()
        self.manual_keep = set()
        self.checker = self._make_checker(400, 400)
        self.display_surf = None
        self.need_redraw = True

        # 预览状态
        self.preview_pixels = set()
        self.preview_active = False

        # 显示缓存（避免每帧 copy + 逐像素操作）
        self._display_cache = None
        self._display_cache_key = None  # (id(processed), frozenset(manual_remove), frozenset(manual_keep))

        # 框选
        self.rect_selecting = False
        self.rect_start = None
        self.rect_end = None

    def _build_crop_file_map(self):
        """构建植物文件映射，识别 stage0-3 文件"""
        import re

        # 检查所有文件目录
        all_dirs = [PROCESSED_DIR, TEMP_DIR, CROPS_OUTPUT_DIR]
        all_files = set()
        for d in all_dirs:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.endswith(".png") and not f.startswith("."):
                        all_files.add(f)

        # 识别植物文件
        crop_pattern = re.compile(r'^(.+)_stage(\d)\.png$')
        crop_files = {}  # {植物名: {stage: 文件名}}

        for fname in all_files:
            match = crop_pattern.match(fname)
            if match:
                crop_name = match.group(1)
                stage = int(match.group(2))
                if crop_name not in crop_files:
                    crop_files[crop_name] = {}
                crop_files[crop_name][stage] = fname

        # 构建映射，只保留有4个完整阶段的植物
        self._crop_file_map = {}
        for crop_name, stages in crop_files.items():
            if all(stage in stages for stage in range(4)):
                self._crop_file_map[crop_name] = [stages[i] for i in range(4)]

        # 从文件列表中移除植物的 stage 文件，替换为植物名称
        new_files = []
        for f in self.files:
            match = crop_pattern.match(f)
            if match:
                crop_name = match.group(1)
                stage = int(match.group(2))
                # 只添加 stage0 作为植物的代表
                if stage == 0 and crop_name in self._crop_file_map:
                    new_files.append(crop_name)  # 使用植物名称作为显示名
                # 其他 stage 跳过
            else:
                new_files.append(f)

        self.files = sorted(new_files)
        print(f"识别到 {len(self._crop_file_map)} 种完整植物")

        # 标签
        self.tags = {}
        self.filter_mode = 0
        self.filtered_files = []

    def _init_view_state(self):
        """初始化视图状态"""
        self.zoom = 1.0
        self.zoom_offset_x = 0
        self.zoom_offset_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.display_x = None
        self.display_y = None

        # 预览模式: 'edit' | 'game'
        self.preview_mode = 'edit'

        # 游戏预览相机（模拟游戏 camera.py）
        self.game_cam_x = 0.0
        self.game_cam_y = 0.0
        self.game_zoom = GAME_DEFAULT_ZOOM
        self.game_cam_dragging = False
        self.game_cam_drag_start = (0, 0)
        self.game_cam_drag_start_pos = (0.0, 0.0)

        # 游戏预览网格缓存
        self._game_grid_surface = None
        self._game_grid_camera = (0.0, 0.0)
        self._game_grid_zoom = 1.0
        self._game_grid_size = (0, 0)

        # 滚动
        self.scroll_offset = 0

    def _init_config(self):
        """初始化配置系统"""
        self.configs = {}                                   # {key: {fields...}}
        self.config = {}                                    # 当前家具配置
        self.focused_field = None                           # 当前聚焦的配置字段名
        self.field_rects = {}                                # {field: Rect} 用于点击检测
        self.cursor_visible = True
        self.cursor_timer = 0

        # 通用字段（所有类型共享）
        self._common_fields = [
            {"key": "name_cn",     "label": "名称(CN)",  "type": "text",   "default": ""},
            {"key": "name_en",     "label": "名称(EN)",  "type": "text",   "default": ""},
            {"key": "file_type",   "label": "文件类型",  "type": "choice", "default": "furniture",
             "choices": ["furniture", "pet", "crop", "floor", "ui"]},
            {"key": "tags",        "label": "标签",      "type": "text",   "default": ""},
            {"key": "description", "label": "描述",      "type": "text",   "default": ""},
        ]

        # 家具特有字段
        self._furniture_fields = [
            {"key": "category",    "label": "家具类型",  "type": "choice", "default": "ground",
             "choices": ["ground", "surface", "surface_wall", "wall_surface", "wall_mount"]},
            {"key": "scale",       "label": "缩放因子",  "type": "number", "default": 0.1},
            {"key": "extra_scale", "label": "额外缩放",  "type": "number", "default": 1.0},
            {"key": "height",      "label": "高度(Z)",   "type": "number", "default": 0},
            {"key": "is_wall",     "label": "是墙壁",    "type": "bool",   "default": False},
            {"key": "no_collision","label": "无碰撞",    "type": "bool",   "default": False},
            {"key": "is_light",    "label": "是光源",    "type": "bool",   "default": False},
        ]

        # 植物特有字段
        self._crop_fields = [
            {"key": "crop_type",   "label": "种植类型",  "type": "choice", "default": "soil",
             "choices": ["soil", "water", "pot", "sand"]},
            {"key": "growth_time", "label": "生长时间(h)","type": "number", "default": 1.5},
            {"key": "sell_price",  "label": "售价",      "type": "number", "default": 10},
            {"key": "seed_price",  "label": "种子价格",  "type": "number", "default": 5},
            {"key": "water_rate",  "label": "水分消耗/h","type": "number", "default": 8},
        ]

        # 宠物特有字段（只处理缩放因子，等级解锁在 video_frame_editor.py 中配置）
        self._pet_fields = [
            {"key": "extra_scale", "label": "额外缩放",  "type": "number", "default": 0.4},
        ]

        # 当前字段列表（根据 file_type 动态更新）
        self.config_fields = []

        # 文件类型对应的默认缩放因子
        self._type_default_scale = {
            "furniture": 0.1,
            "pet": 0.15,
            "crop": 1.0,
            "floor": 1.0,
            "ui": 1.0,
        }

        # 种植类型映射（中文 -> 英文）
        self._crop_type_map = {
            "soil": 0,    # 土生
            "water": 1,   # 水生
            "pot": 2,     # 盆栽
            "sand": 3,    # 沙生
        }

    def _init_polygon_modes(self):
        """初始化多边形编辑模式"""
        self.footprint_mode = False
        self.footprint_points = []
        self.footprint_data = {}

        self.wall_mode = False
        self.wall_points = []
        self.wall_data = {}

        self.placeable_mode = False
        self.placeable_points = []
        self.placeable_data = {}

    # ---- 数据路径 / JSON ----

    def _data_path(self, name):
        return os.path.join(os.path.dirname(__file__), "..", "data", f"{name}.json")

    def _load_json(self, name):
        path = self._data_path(name)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载 {name} 失败: {e}")
        return {}

    def _save_json(self, name, data):
        path = self._data_path(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"保存 {name}: {len(data)} 个物体")

    def _config_path(self):
        return self._data_path("furniture_configs")

    def _load_all_data(self):
        """加载所有数据和配置"""
        self.footprint_data = self._load_json("footprints")
        self.wall_data = self._load_json("wall_surfaces")
        self.placeable_data = self._load_json("placeable_areas")
        self.tags = self._load_json("tags")
        self.configs = self._load_json("furniture_configs")
        print(f"加载: footprint={len(self.footprint_data)}, wall={len(self.wall_data)}, "
              f"placeable={len(self.placeable_data)}, tags={len(self.tags)}, configs={len(self.configs)}")

    def _save_all_data(self):
        """保存所有数据（含配置）"""
        self._save_json("footprints", self.footprint_data)
        self._save_json("wall_surfaces", self.wall_data)
        self._save_json("placeable_areas", self.placeable_data)
        self._save_json("tags", self.tags)
        # 配置单独保存（文件名不同）
        self._save_configs()
        print("全部数据已保存")

    def _save_configs(self):
        """保存配置数据"""
        path = self._config_path()
        # 先保存当前家具的配置
        if hasattr(self, 'config') and self.config:
            key = self._config_key_of_current()
            if key:
                self.configs[key] = dict(self.config)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.configs, f, ensure_ascii=False, indent=2)

    # ---- 筛选 / 标签 ----

    def _update_filter(self):
        if self.filter_mode == 0:
            self.filtered_files = self.files.copy()
        elif self.filter_mode == 1:
            self.filtered_files = [f for f in self.files if self.tags.get(f) == 1]
        elif self.filter_mode == 2:
            self.filtered_files = [f for f in self.files if self.tags.get(f) != 1]
        self.scroll_offset = 0

    def toggle_tag(self):
        if not self.filtered_files:
            return
        fname = self.filtered_files[self.idx]
        current = self.tags.get(fname, 2)
        self.tags[fname] = 2 if current == 1 else 1
        print(f"{fname} → {'已完成' if self.tags[fname] == 1 else '待处理'}")

        old_fname = fname
        self._update_filter()
        if old_fname in self.filtered_files:
            self.idx = self.filtered_files.index(old_fname)
        elif self.filtered_files:
            self.idx = min(self.idx, len(self.filtered_files) - 1)
            self._load(self.idx)

    def set_filter(self, mode):
        self.filter_mode = mode
        mode_names = ["全部", "已完成", "待处理"]
        print(f"筛选: {mode_names[mode]}")
        self._update_filter()
        self.idx = 0
        if self.filtered_files:
            self._load(0)

    # ---- 棋盘格 ----

    def _make_checker(self, w, h):
        surf = pygame.Surface((w, h))
        for y in range(0, h, 16):
            for x in range(0, w, 16):
                c = (200, 200, 200) if ((x // 16) + (y // 16)) % 2 == 0 else (240, 240, 240)
                pygame.draw.rect(surf, c, (x, y, 16, 16))
        return surf

    # ---- 加载图片 ----

    def _load(self, idx):
        if idx < 0 or idx >= len(self.filtered_files):
            return
        self.idx = idx
        fname = self.filtered_files[idx]
        if fname in self.files:
            self.current_file_idx = self.files.index(fname)

        # 检查是否是植物（使用植物名称）
        actual_fname = fname
        if fname in self._crop_file_map:
            # 植物：加载 stage0 文件
            actual_fname = self._crop_file_map[fname][0]

        # 尝试从不同目录加载
        path = os.path.join(CROPS_OUTPUT_DIR, actual_fname)
        if not os.path.exists(path):
            path = os.path.join(PROCESSED_DIR, actual_fname)
        if not os.path.exists(path):
            path = os.path.join(TEMP_DIR, actual_fname)

        if os.path.exists(path):
            self.original = pygame.image.load(path).convert_alpha()
            self.processed = self.original.copy()
            self.manual_remove.clear()
            self.manual_keep.clear()
            self.need_redraw = True
            self._cancel_all_modes()
            self._load_config_for_current()
        else:
            print(f"找不到文件: {actual_fname}")

    def _get_display(self):
        """获取编辑后的显示表面（带缓存）"""
        if self.processed is None:
            return None

        # 生成缓存 key
        cache_key = (
            id(self.processed),
            frozenset(self.manual_remove),
            frozenset(self.manual_keep),
        )

        # 命中缓存直接返回
        if self._display_cache is not None and self._display_cache_key == cache_key:
            return self._display_cache

        d = self.processed.copy()
        for (x, y) in self.manual_remove:
            if 0 <= x < d.get_width() and 0 <= y < d.get_height():
                d.set_at((x, y), (0, 0, 0, 0))
        for (x, y) in self.manual_keep:
            if self.original and 0 <= x < self.original.get_width() and 0 <= y < self.original.get_height():
                d.set_at((x, y), self.original.get_at((x, y)))

        # 写入缓存（不缩放，缩放由调用方按各自 zoom 处理）
        self._display_cache = d
        self._display_cache_key = cache_key
        return d

    # ---- 配置管理 ----

    def _load_config_for_current(self):
        """加载当前家具的配置"""
        self.config = {}
        if not self.filtered_files:
            return
        fname = self.filtered_files[self.idx]

        # 获取配置键（植物使用植物名称，其他使用文件名去掉 .png）
        key = self._config_key_of_current()

        if key in self.configs:
            self.config = dict(self.configs[key])
        # 自动填充英文名
        if not self.config.get("name_en"):
            self.config["name_en"] = key
        # 自动检测文件类型（仅首次，不覆盖已有配置）
        if not self.config.get("_type_detected"):
            # 植物类型检测
            if fname in self._crop_file_map:
                detected = "crop"
            else:
                detected = detect_file_type_by_name(fname)
            if detected in self._type_default_scale:
                self.config["file_type"] = detected
                # 自动设置该类型的默认缩放因子
                cur_scale = self.config.get("scale", 0.1)
                cur_scale = float(cur_scale) if cur_scale else 0.1
                if cur_scale == 0.1 and detected != "furniture":
                    self.config["scale"] = self._type_default_scale[detected]
            self.config["_type_detected"] = True

        # 根据 file_type 动态更新字段列表
        self._update_config_fields()

        # 确保所有字段都有值
        for field in self.config_fields:
            if field["key"] not in self.config:
                self.config[field["key"]] = field["default"]

    def _config_key_of_current(self):
        """获取当前项目的配置键"""
        if not self.filtered_files:
            return None
        fname = self.filtered_files[self.idx]
        # 植物使用植物名称（不含 _stage0 后缀）
        if fname in self._crop_file_map:
            return fname
        # 其他类型使用文件名去掉 .png
        return fname.replace('.png', '')

    def _update_config_fields(self):
        """根据 file_type 动态更新字段列表"""
        file_type = self.config.get("file_type", "furniture")

        # 通用字段
        self.config_fields = list(self._common_fields)

        # 根据类型添加特有字段
        if file_type == "furniture":
            self.config_fields.extend(self._furniture_fields)
        elif file_type == "crop":
            self.config_fields.extend(self._crop_fields)
        elif file_type == "pet":
            self.config_fields.extend(self._pet_fields)
        # floor 和 ui 不需要额外字段

    def _save_current_config(self):
        """保存当前家具的配置到内存中"""
        key = self._config_key_of_current()
        if key and self.config:
            self.configs[key] = dict(self.config)

    # ---- 洪水填充预览 ----

    def preview_flood(self, sx, sy):
        w, h = self.processed.get_size()
        pixels = pygame.surfarray.array3d(self.processed)
        alpha = pygame.surfarray.array_alpha(self.processed)
        ref_color = (int(pixels[sx, sy, 0]), int(pixels[sx, sy, 1]), int(pixels[sx, sy, 2]))

        if alpha[sx, sy] == 0:
            return 0
        q = deque([(sx, sy)])
        filled = {(sx, sy)}
        tolerance = 60
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
        self.manual_remove.update(self.preview_pixels)
        self.manual_keep -= self.preview_pixels
        self.preview_pixels.clear()
        self.preview_active = False
        self.need_redraw = True

    def cancel_preview(self):
        self.preview_pixels.clear()
        self.preview_active = False
        self.need_redraw = True

    # ---- 矩形删除 ----

    def _clear_rect(self, start, end):
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

    # ---- 多边形编辑模式 ----

    def _cancel_all_modes(self):
        self.footprint_mode = False
        self.wall_mode = False
        self.placeable_mode = False
        self.footprint_points = []
        self.wall_points = []
        self.placeable_points = []

    def _close_polygon(self):
        """关闭多边形并保存到内存，成功返回 True"""
        fname = self.filtered_files[self.idx] if self.filtered_files else None
        if not fname:
            return False
        key = fname.replace('.png', '')

        if self.footprint_mode and len(self.footprint_points) >= 3:
            self.footprint_data[key] = self.footprint_points.copy()
            print(f"Footprint 已保存: {key}, {len(self.footprint_points)} 个点")
            self.footprint_points = []
            self.footprint_mode = False
            return True
        elif self.wall_mode and len(self.wall_points) >= 3:
            self.wall_data[key] = self.wall_points.copy()
            print(f"WallSurface 已保存: {key}, {len(self.wall_points)} 个点")
            self.wall_points = []
            self.wall_mode = False
            return True
        elif self.placeable_mode and len(self.placeable_points) >= 3:
            area_name = f"area_{len(self.placeable_data.get(key, []))}"
            if key not in self.placeable_data:
                self.placeable_data[key] = []
            self.placeable_data[key].append({
                "name": area_name,
                "points": self.placeable_points.copy()
            })
            print(f"PlaceableArea 已保存: {key}.{area_name}, {len(self.placeable_points)} 个点")
            self.placeable_points = []
            self.placeable_mode = False
            return True
        else:
            print("点数不足，需要至少3个点")
            return False

    def flood_restore(self, sx, sy):
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

    def auto_remove_cyan(self):
        w, h = self.processed.get_size()
        pixels = pygame.surfarray.array3d(self.processed)
        alpha = pygame.surfarray.array_alpha(self.processed)

        samples = []
        for x, y in [(2, 2), (w-3, 2), (2, h-3), (w-3, h-3),
                      (w//2, 2), (w//2, h-3), (2, h//2), (w-3, h//2)]:
            samples.append((int(pixels[x, y, 0]), int(pixels[x, y, 1]), int(pixels[x, y, 2])))
        bg = Counter(samples).most_common(1)[0][0]
        print(f"检测背景色: RGB{bg}")

        outside = set()
        visited = set()
        queue = deque()
        tolerance = 60

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

        self.manual_remove.update(outside)
        self.need_redraw = True
        print(f"边缘洪水去除: {len(outside)} 像素")
        return len(outside)

    def crop_to_content(self):
        w, h = self.processed.get_size()
        alpha = pygame.surfarray.array_alpha(self.processed)

        min_x, min_y = w, h
        max_x, max_y = 0, 0
        for y in range(h):
            for x in range(w):
                is_removed = (x, y) in self.manual_remove
                is_keep = (x, y) in self.manual_keep
                if not is_removed:
                    if is_keep or (alpha[x, y] > 0):
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
        if min_x >= max_x:
            return

        pad = 2
        min_x = max(0, min_x - pad)
        min_y = max(0, min_y - pad)
        max_x = min(w - 1, max_x + pad)
        max_y = min(h - 1, max_y + pad)
        offset_x = -min_x
        offset_y = -min_y
        new_w = max_x - min_x + 1
        new_h = max_y - min_y + 1

        new_remove = set()
        for (x, y) in self.manual_remove:
            nx, ny = x + offset_x, y + offset_y
            if 0 <= nx < new_w and 0 <= ny < new_h:
                new_remove.add((nx, ny))
        new_keep = set()
        for (x, y) in self.manual_keep:
            nx, ny = x + offset_x, y + offset_y
            if 0 <= nx < new_w and 0 <= ny < new_h:
                new_keep.add((nx, ny))

        new_surf = pygame.Surface((new_w, new_h), pygame.SRCALPHA)
        for y in range(new_h):
            for x in range(new_w):
                ox, oy = x + min_x, y + min_y
                new_surf.set_at((x, y), self.processed.get_at((ox, oy)))

        self.processed = new_surf
        self.original = new_surf.copy()
        self.manual_remove = new_remove
        self.manual_keep = new_keep
        self.need_redraw = True
        print(f"裁剪到 {new_w}x{new_h}")

    # ---- 保存图片 ----

    def save(self):
        if self.processed is None:
            return
        final = self.processed.copy()
        w, h = final.get_size()

        for (x, y) in self.manual_keep:
            if 0 <= x < w and 0 <= y < h and self.original:
                final.set_at((x, y), self.original.get_at((x, y)))
        for (x, y) in self.manual_remove:
            if 0 <= x < w and 0 <= y < h:
                final.set_at((x, y), (0, 0, 0, 0))

        fname = self.filtered_files[self.idx]

        # 检查是否是植物
        if fname in self._crop_file_map:
            # 植物：保存 stage0 文件
            save_fname = self._crop_file_map[fname][0]
            save_dir = CROPS_OUTPUT_DIR
        else:
            # 其他类型：根据文件类型自动保存到对应目录
            ftype = self.detect_file_type(fname)
            type_to_dir = {
                "furniture": OUTPUT_DIR,
                "crop": CROPS_OUTPUT_DIR,
                "pet": PET_OUTPUT_DIR,
                "floor": FARM_OUTPUT_DIR,
                "ui": UI_OUTPUT_DIR,
            }
            save_dir = type_to_dir.get(ftype, PROCESSED_DIR)
            save_fname = fname
        save_dir_name = os.path.basename(save_dir)

        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, save_fname)
        pygame.image.save(final, save_path)

        if save_dir != PROCESSED_DIR:
            os.makedirs(PROCESSED_DIR, exist_ok=True)
            pygame.image.save(final, os.path.join(PROCESSED_DIR, save_fname))

        print(f"已保存 [{save_dir_name}]: {save_fname}")

    # ---- 点击图片 ----

    def handle_img_click(self, mx, my, button):
        if not self.display_surf or self.display_x is None:
            return
        px = int((mx - self.display_x) / self.zoom)
        py = int((my - self.display_y) / self.zoom)

        if self.processed and 0 <= px < self.processed.get_width() and 0 <= py < self.processed.get_height():
            if button == 1:
                self.cancel_preview()
                n = self.preview_flood(px, py)
                print(f"预览去除: {n} 像素 → Enter确认, Esc取消")
            elif button == 3:
                n = self.flood_restore(px, py)
                print(f"恢复: {n} 像素")

    # ============================================================
    # 新功能：从图片取色
    # ============================================================
    def pick_dominant_color(self):
        """提取当前图片的主色调"""
        if self.processed is None:
            return (128, 128, 128)
        w, h = self.processed.get_size()
        pixels = pygame.surfarray.array3d(self.processed)
        alpha = pygame.surfarray.array_alpha(self.processed)

        color_counts = Counter()
        for y in range(h):
            for x in range(w):
                if alpha[x, y] > 10:
                    # 量化颜色到 32x32x32 格子
                    rq = int(pixels[x, y, 0]) // 32 * 32
                    gq = int(pixels[x, y, 1]) // 32 * 32
                    bq = int(pixels[x, y, 2]) // 32 * 32
                    color_counts[(rq, gq, bq)] += 1

        if not color_counts:
            return (128, 128, 128)

        # 取最多的颜色
        dominant = color_counts.most_common(1)[0][0]
        # 转回非量化
        r = min(255, dominant[0] + 16)
        g = min(255, dominant[1] + 16)
        b = min(255, dominant[2] + 16)
        print(f"提取主色调: RGB({r},{g},{b})")
        return (r, g, b)

    # ============================================================
    # 新功能：生成代码（FURNITURE_DATA entry）
    # ============================================================
    def generate_furniture_data_entry(self):
        """生成 FURNITURE_DATA 的 python 代码"""
        key = self._config_key_of_current()
        if not key:
            return "# 无当前家具"

        name_cn = self.config.get("name_cn", key)
        w = self.processed.get_width() if self.processed else 40
        h = self.processed.get_height() if self.processed else 40
        obj_type = self.config.get("category", "ground")
        color = self.config.get("picked_color", (128, 128, 128))
        if isinstance(color, list):
            color = tuple(color)

        # 构建参数字典
        params = []
        params.append(f'"name": "{name_cn}"')
        params.append(f'"width": {w}')
        params.append(f'"height": {h}')
        params.append(f'"color": {color}')
        params.append(f'"type": "{obj_type}"')

        if self.config.get("no_collision"):
            params.append(f'"no_collision": True')
        if self.config.get("is_light"):
            params.append(f'"is_light": True')
        if self.config.get("is_wall"):
            params.append(f'"is_wall": True')

        code = f'        "{key}": {{{", ".join(params)}}},'
        return code

    # ============================================================
    # 文件类型检测
    # ============================================================
    def detect_file_type(self, fname=None):
        """
        检测当前文件的类型（类方法，复用模块级函数）
        """
        if fname is None:
            if not self.filtered_files:
                return "unknown"
            fname = self.filtered_files[self.idx]
        return detect_file_type_by_name(fname)


    def auto_register_to_game(self):
        """自动将当前家具注册到 furniture.py 的 FURNITURE_DATA 中"""
        key = self._config_key_of_current()
        if not key:
            print("无当前家具，无法注册")
            return False

        # 严格检查：只有家具类型才能注册到 furniture.py
        file_type = self.detect_file_type()
        if file_type == "crop":
            print(f"[拒绝] [{key}] 是作物类型，不能注册到 FURNITURE_DATA")
            print(f"  作物需要注册到 src/entities/crop.py 的 CROP_DATA")
            return False
        elif file_type == "pet":
            print(f"[拒绝] [{key}] 是宠物类型，不能注册到 FURNITURE_DATA")
            print(f"  宠物需要注册到 src/entities/pet.py 的 PET_CONFIG")
            return False
        elif file_type == "floor":
            print(f"[拒绝] [{key}] 是地板/种植区类型，无需注册")
            return False
        elif file_type == "ui":
            print(f"[拒绝] [{key}] 是UI图标类型，无需注册")
            return False
        elif file_type == "unknown":
            # 未知类型：要求用户先在配置面板设置 category
            cat = self.config.get("category", "")
            if cat not in ("ground", "surface", "surface_wall", "wall_surface", "wall_mount"):
                print(f"[拒绝] [{key}] 类型未知，请先在配置面板设置「类型」字段为家具类型")
                print(f"  当前类型: {cat or '(未设置)'}")
                return False

        # 检查必要的配置字段
        required_fields = ["name_cn", "category"]
        missing = [f for f in required_fields if not self.config.get(f)]
        if missing:
            print(f"[拒绝] 缺少必要配置: {', '.join(missing)}")
            print(f"  请在配置面板填写后再注册")
            return False

        # 检查图片是否已保存到 furniture 目录
        furniture_path = os.path.join(OUTPUT_DIR, f"{key}.png")
        if not os.path.exists(furniture_path):
            print(f"[警告] 图片未保存到 {furniture_path}")
            print(f"  请先按 S 保存图片")
            return False

        entry = self.generate_furniture_data_entry()
        if not entry:
            return False

        # 读取 furniture.py
        fpath = FURNITURE_DATA_PATH
        if not os.path.exists(fpath):
            print(f"找不到: {fpath}")
            return False

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"读取失败: {e}")
            return False

        # 检查是否已存在
        if f'"{key}"' in content:
            print(f"家具 [{key}] 已在 FURNITURE_DATA 中，请手动更新")
            return False

        # 在 FURNITURE_DATA 的最后一个条目之前插入
        # 策略：在最后一个条目后插入
        lines = content.split('\n')
        insert_idx = None
        in_furniture_data = False
        brace_depth = 0
        found_last_entry = False

        for i, line in enumerate(lines):
            if 'FURNITURE_DATA' in line and '=' in line:
                in_furniture_data = True
            if in_furniture_data:
                brace_depth += line.count('{') - line.count('}')
                if brace_depth == 0 and i > 0 and in_furniture_data:
                    # FURNITURE_DATA 的闭括号在这一行
                    insert_idx = i
                    found_last_entry = True
                    break

        if found_last_entry and insert_idx is not None:
            # 在闭括号前插入
            # 找实际的缩进量
            leading_spaces = 8
            for j in range(insert_idx - 1, 0, -1):
                stripped = lines[j].strip()
                if stripped.startswith('"') or stripped.startswith("'"):
                    leading_spaces = len(lines[j]) - len(lines[j].lstrip())
                    break

            new_entry_line = f'{" " * leading_spaces}{entry}'
            lines.insert(insert_idx, new_entry_line)

            new_content = '\n'.join(lines)
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"已注册 [{key}] 到 furniture.py！")
                return True
            except Exception as e:
                print(f"写入失败: {e}")
                return False
        else:
            print("未找到 FURNITURE_DATA 结束位置")
            return False

    # ============================================================
    # 配置面板绘制
    # ============================================================
    def _draw_config_panel(self):
        """绘制右侧配置面板"""
        x, y = CFG_X, INFO_H
        w = CFG_W
        h = WIN_H - INFO_H - TOOLBAR_H

        # 背景
        pygame.draw.rect(screen, COLOR_PANEL, (x, y, w, h))
        pygame.draw.line(screen, (70, 70, 90), (x, y), (x, y + h), 1)

        # 标题
        title = font_bold.render("家具配置", True, COLOR_ACCENT)
        screen.blit(title, (x + 8, y + 4))

        # 当前家具名
        fname = self.filtered_files[self.idx] if self.filtered_files else "(无)"
        name_label = font_small.render(f"文件: {fname}", True, COLOR_TEXT_DIM)
        screen.blit(name_label, (x + 8, y + 24))

        # 游戏 preview 按钮
        btn_edit = pygame.Rect(x + 8, y + 42, 80, 22)
        btn_game = pygame.Rect(x + 92, y + 42, 80, 22)
        btn_save_cfg = pygame.Rect(x + 176, y + 42, 96, 22)

        # 边缘按钮效果
        edit_active = self.preview_mode == 'edit'
        game_active = self.preview_mode == 'game'
        pygame.draw.rect(screen, (70, 100, 140) if edit_active else COLOR_BTN, btn_edit, border_radius=3)
        pygame.draw.rect(screen, (70, 100, 140) if game_active else COLOR_BTN, btn_game, border_radius=3)
        pygame.draw.rect(screen, COLOR_BTN_BLUE, btn_save_cfg, border_radius=3)

        screen.blit(font.render("编辑", True, COLOR_TEXT), (x + 16, y + 47))
        screen.blit(font.render("游戏", True, COLOR_TEXT), (x + 100, y + 47))
        screen.blit(font.render("保存配置", True, COLOR_TEXT), (x + 184, y + 47))

        # 存储按钮rect用于点击检测
        self._cfg_btns = {
            'mode_edit': btn_edit,
            'mode_game': btn_game,
            'save_cfg': btn_save_cfg,
        }

        # 字段绘制区
        fy = y + 70
        self.field_rects = {}
        mx, my = pygame.mouse.get_pos()

        for field in self.config_fields:
            if fy + CFG_ROW_H > y + h:
                break

            key = field["key"]
            label = field["label"]
            ftype = field["type"]

            # 标签
            lbl_surf = font_small.render(label, True, COLOR_TEXT_DIM)
            screen.blit(lbl_surf, (x + 8, fy + 4))

            # 根据类型绘制控件
            if ftype in ("text", "number"):
                val = str(self.config.get(key, ""))
                input_rect = pygame.Rect(x + CFG_LABEL_W + 2, fy, w - CFG_LABEL_W - 10, CFG_ROW_H - 2)
                self.field_rects[key] = input_rect

                focused = (self.focused_field == key)
                border_color = COLOR_INPUT_FOCUS if focused else COLOR_INPUT_BORDER
                pygame.draw.rect(screen, COLOR_INPUT_BG, input_rect, border_radius=2)
                pygame.draw.rect(screen, border_color, input_rect, 1, border_radius=2)

                # 绘制文本（修剪到宽度）
                text_surf = font_small.render(val, True, COLOR_TEXT)
                screen.blit(text_surf, (input_rect.x + 3, input_rect.y + 3))

                # 光标
                if focused and self.cursor_visible:
                    text_w = font_small.size(val)[0]
                    cx = input_rect.x + 3 + text_w
                    if cx < input_rect.right - 3:
                        pygame.draw.line(screen, COLOR_TEXT_BRIGHT,
                                         (cx, input_rect.y + 3), (cx, input_rect.bottom - 3))

            elif ftype == "bool":
                val = self.config.get(key, False)
                bx = x + CFG_LABEL_W + 4
                by = fy + 2
                check_rect = pygame.Rect(bx, by, 16, 16)
                self.field_rects[key] = check_rect
                pygame.draw.rect(screen, COLOR_INPUT_BG, check_rect, border_radius=2)
                pygame.draw.rect(screen, COLOR_INPUT_BORDER, check_rect, 1, border_radius=2)
                if val:
                    # 画勾
                    pts = [(bx + 3, by + 8), (bx + 7, by + 12), (bx + 13, by + 4)]
                    pygame.draw.lines(screen, COLOR_ACCENT, False, pts, 2)

            elif ftype == "choice":
                val = self.config.get(key, field["choices"][0])
                choice_names = {
                    "ground": "地面家具",
                    "surface": "可放置面",
                    "surface_wall": "面+墙面",
                    "wall_surface": "墙面",
                    "wall_mount": "墙挂",
                    "furniture": "家具",
                    "pet": "宠物",
                    "crop": "作物",
                    "floor": "地板",
                    "ui": "UI",
                }
                current_label = choice_names.get(val, val)

                # 下拉框简化版：点击循环
                choice_rect = pygame.Rect(x + CFG_LABEL_W + 2, fy, w - CFG_LABEL_W - 10, CFG_ROW_H - 2)
                self.field_rects[key] = choice_rect
                pygame.draw.rect(screen, COLOR_INPUT_BG, choice_rect, border_radius=2)
                pygame.draw.rect(screen, COLOR_INPUT_BORDER, choice_rect, 1, border_radius=2)
                text_surf = font_small.render(current_label, True, COLOR_TEXT)
                screen.blit(text_surf, (choice_rect.x + 3, choice_rect.y + 3))
                # 小箭头
                arrow = font_small.render("▼", True, COLOR_TEXT_DIM)
                screen.blit(arrow, (choice_rect.right - 14, choice_rect.y + 3))

            fy += CFG_ROW_H + 3

        # 底部操作按钮
        btn_y = y + h - 100
        btn_w = w - 16

        btns = [
            ("提取主色调", self.pick_dominant_color_and_refresh, COLOR_BTN),
            ("生成代码(复制)", self._generate_and_copy, COLOR_BTN_GREEN),
            ("自动注册到游戏", self.auto_register_to_game, COLOR_BTN_BLUE),
        ]

        self._cfg_action_btns = []
        for btext, baction, bcolor in btns:
            brect = pygame.Rect(x + 8, btn_y, btn_w, 26)
            hover = brect.collidepoint(mx, my)
            draw_color = (min(255, bcolor[0] + 20), min(255, bcolor[1] + 20), min(255, bcolor[2] + 20)) if hover else bcolor
            pygame.draw.rect(screen, draw_color, brect, border_radius=4)

            # 如果有颜色预览（提取主色调按钮）
            if btext == "提取主色调":
                color_val = self.config.get("picked_color")
                if color_val and len(color_val) == 3:
                    c_rect = pygame.Rect(brect.right - 24, brect.y + 3, 18, 18)
                    pygame.draw.rect(screen, color_val, c_rect)
                    pygame.draw.rect(screen, (100, 100, 100), c_rect, 1)

            screen.blit(font.render(btext, True, COLOR_TEXT), (x + 14, btn_y + 5))
            self._cfg_action_btns.append((brect, baction))

        # 已生成代码预览
        code_y = btn_y - 80
        code_preview = self.generate_furniture_data_entry()
        if code_preview:
            pygame.draw.rect(screen, (20, 20, 30), (x + 4, code_y, w - 8, 74), border_radius=2)
            # 分两行显示
            max_chars = 35
            if len(code_preview) > max_chars:
                part1 = code_preview[:max_chars]
                part2 = "  " + code_preview[max_chars:]
            else:
                part1 = code_preview
                part2 = ""
            preview_surf1 = font_small.render(part1, True, (180, 220, 180))
            preview_surf2 = font_small.render(part2, True, (180, 220, 180)) if part2 else None
            screen.blit(preview_surf1, (x + 8, code_y + 4))
            if preview_surf2:
                screen.blit(preview_surf2, (x + 8, code_y + 18))

        # 数据状态
        data_y = code_y - 18
        key_name = self._config_key_of_current() or ""
        has_fp = "FP" if key_name in self.footprint_data else "--"
        has_w = "W" if key_name in self.wall_data else "--"
        has_pl = "PL" if key_name in self.placeable_data else "--"
        status = font_small.render(f"数据: [{has_fp}] [{has_w}] [{has_pl}]", True, COLOR_TEXT_DIM)
        screen.blit(status, (x + 8, data_y))

    def pick_dominant_color_and_refresh(self):
        """提取颜色并存入配置"""
        color = self.pick_dominant_color()
        self.config["picked_color"] = list(color)
        self.config["color"] = list(color)
        self._save_current_config()
        print(f"颜色已保存: {color}")
        self.need_redraw = True

    def _generate_and_copy(self):
        """生成代码并复制到剪贴板"""
        code = self.generate_furniture_data_entry()
        print(f"生成的代码:\n{code}")
        # 尝试写入剪贴板
        try:
            import pyperclip
            pyperclip.copy(code)
            print("✓ 已复制到剪贴板！")
        except ImportError:
            print("提示: 安装 pyperclip 可自动复制到剪贴板 (pip install pyperclip)")
        self.need_redraw = True

    # ============================================================
    # 游戏预览模式（26/334 菱形网格，与 coordinate_viewer 一致）
    # ============================================================
    # 预定义常量（避免每帧重建）
    _PREVIEW_TILE_MAP = [
        [0, 0, 0, 0, 1, 1, 1, -1, -1, -1],
        [0, 0, 0, 0, 1, 1, 1, -1, -1, -1],
        [0, 0, 0, 0, 1, 1, 1, -1, -1, -1],
        [0, 0, 0, 0, 1, 1, 1, -1, -1, -1],
    ]
    _PREVIEW_TILE_COLORS = {
        0: (180, 150, 120),
        1: (120, 180, 100),
    }

    def _draw_game_preview(self):
        """绘制游戏预览模式（真实游戏坐标系：26/334 菱形网格，带缓存）"""
        img_area_x = CENTER_X
        img_area_y = INFO_H
        img_area_w = CENTER_W
        img_area_h = CENTER_H

        cam_x = self.game_cam_x
        cam_y = self.game_cam_y
        zoom = self.game_zoom

        # 检查网格是否需要重绘
        needs_grid_redraw = (
            self._game_grid_surface is None or
            self._game_grid_size != (img_area_w, img_area_h) or
            abs(self._game_grid_camera[0] - cam_x) > 0.1 or
            abs(self._game_grid_camera[1] - cam_y) > 0.1 or
            abs(self._game_grid_zoom - zoom) > 0.01
        )

        if needs_grid_redraw:
            self._redraw_game_grid(cam_x, cam_y, zoom, img_area_w, img_area_h)

        # 裁剪区域
        clip = pygame.Rect(img_area_x, img_area_y, img_area_w, img_area_h)
        screen.set_clip(clip)

        # 绘制缓存的网格
        screen.blit(self._game_grid_surface, (img_area_x, img_area_y))

        # 绘制原点标记
        ox, oy = game_world_to_screen(0, 0, cam_x, cam_y, zoom, img_area_w, img_area_h)
        ox += img_area_x
        oy += img_area_y
        pygame.draw.circle(screen, (255, 0, 0), (int(ox), int(oy)), 5)
        origin_label = font_small.render("O(0,0)", True, (255, 0, 0))
        screen.blit(origin_label, (int(ox) + 8, int(oy) - 8))

        # 在原点格子中心放置当前家具
        if self.processed is not None:
            furniture_wx, furniture_wy = game_grid_to_world(0.5, 0.5)
            fsx, fsy = game_world_to_screen(furniture_wx, furniture_wy, cam_x, cam_y, zoom, img_area_w, img_area_h)
            fsx += img_area_x
            fsy += img_area_y

            # 按游戏实际缩放公式计算显示尺寸
            # furniture: img * zoom * scale * extra_scale
            # pet:       img * zoom * scale * extra_scale
            # crop:      宽=40*zoom*scale, 高按比例
            # ui:        缩放到 24x24 区域
            display = self._get_display()
            if display:
                dw, dh = display.get_size()
                file_type = self.config.get("file_type", "furniture")
                scale_val = self.config.get("scale", 0.1)
                scale = float(scale_val) if scale_val else 0.1
                extra_scale_val = self.config.get("extra_scale", 1.0)
                extra_scale = float(extra_scale_val) if extra_scale_val else 1.0

                if file_type == "crop":
                    # 作物：宽度固定 40*scale，高度按比例
                    pw = max(1, int(40 * zoom * scale))
                    ph = max(1, int(pw * dh / max(dw, 1)))
                elif file_type == "ui":
                    # UI：缩放到 24px 区域，保持比例
                    ui_size = 24
                    ratio = min(ui_size / max(dw, 1), ui_size / max(dh, 1))
                    pw = max(1, int(dw * ratio))
                    ph = max(1, int(dh * ratio))
                else:
                    # 家具/宠物/地板：img * zoom * scale * extra_scale
                    total_scale = scale * extra_scale
                    pw = max(1, int(dw * zoom * total_scale))
                    ph = max(1, int(dh * zoom * total_scale))

                preview = pygame.transform.scale(display, (pw, ph))
                px = int(fsx - pw // 2)
                py = int(fsy - ph // 2)
                screen.blit(preview, (px, py))

                # 绘制 footprint 覆盖
                key = self._config_key_of_current()
                if key and key in self.footprint_data:
                    fp_points = self.footprint_data[key]
                    if len(fp_points) >= 3:
                        fp_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
                        fp_screen = [(int(p[0] * zoom * scale * extra_scale),
                                      int(p[1] * zoom * scale * extra_scale)) for p in fp_points]
                        pygame.draw.polygon(fp_surf, (0, 255, 0, 60), fp_screen)
                        pygame.draw.polygon(fp_surf, (0, 200, 0, 180), fp_screen, 2)
                        screen.blit(fp_surf, (px, py))

                # 家具信息
                info_lines = []
                if key:
                    info_lines.append(f"ID: {key}")
                    info_lines.append(f"名称: {self.config.get('name_cn', '未设置')}")
                    info_lines.append(f"文件类型: {file_type}")
                    if file_type == "furniture":
                        info_lines.append(f"家具类型: {self.config.get('category', 'ground')}")
                    info_lines.append(f"尺寸: {self.processed.get_width()}x{self.processed.get_height()}")
                    info_lines.append(f"缩放: {scale} x {extra_scale} = {scale * extra_scale:.3f}")
                    info_lines.append(f"显示: {pw}x{ph}px  Zoom: {zoom:.2f}")
                    if key in self.footprint_data:
                        info_lines.append(f"FP: {len(self.footprint_data[key])} 点")
                    if key in self.wall_data:
                        info_lines.append(f"W: {len(self.wall_data[key])} 点")
                    if key in self.placeable_data:
                        areas = self.placeable_data.get(key, [])
                        info_lines.append(f"PL: {len(areas)} 区域")

                for i, line in enumerate(info_lines):
                    surf = font_small.render(line, True, COLOR_TEXT_DIM)
                    screen.blit(surf, (img_area_x + 10, img_area_y + 10 + i * 16))

        screen.set_clip(None)

        # 模式提示
        hint = font_small.render("[游戏预览] 中键拖动 | 滚轮缩放 | Ctrl+E 返回编辑", True, COLOR_ACCENT)
        screen.blit(hint, (img_area_x + 10, img_area_y + img_area_h - 20))

    def _redraw_game_grid(self, cam_x, cam_y, zoom, area_w, area_h):
        """重绘游戏网格到缓存 Surface"""
        # 创建或重用 Surface
        if self._game_grid_surface is None or self._game_grid_size != (area_w, area_h):
            self._game_grid_surface = pygame.Surface((area_w, area_h))
            self._game_grid_size = (area_w, area_h)

        self._game_grid_surface.fill((255, 255, 255))

        # 计算可见范围（世界坐标）
        world_left = cam_x - area_w / (2 * zoom)
        world_right = cam_x + area_w / (2 * zoom)
        world_top = cam_y - area_h / (2 * zoom)
        world_bottom = cam_y + area_h / (2 * zoom)

        # 转换为网格坐标范围
        gx1, gy1 = game_world_to_grid(world_left, world_top)
        gx2, gy2 = game_world_to_grid(world_right, world_top)
        gx3, gy3 = game_world_to_grid(world_left, world_bottom)
        gx4, gy4 = game_world_to_grid(world_right, world_bottom)

        min_gx = int(math.floor(min(gx1, gx2, gx3, gx4))) - 1
        max_gx = int(math.floor(max(gx1, gx2, gx3, gx4))) + 1
        min_gy = int(math.floor(min(gy1, gy2, gy3, gy4))) - 1
        max_gy = int(math.floor(max(gy1, gy2, gy3, gy4))) + 1

        tile_map = self._PREVIEW_TILE_MAP
        tile_colors = self._PREVIEW_TILE_COLORS
        surf = self._game_grid_surface

        for gy in range(min_gy, max_gy + 1):
            for gx in range(min_gx, max_gx + 1):
                vertices = game_get_tile_vertices(gx, gy)
                screen_vertices = [
                    game_world_to_screen(vx, vy, cam_x, cam_y, zoom, area_w, area_h)
                    for vx, vy in vertices
                ]
                screen_vertices_int = [(int(sx), int(sy)) for sx, sy in screen_vertices]

                # 判断区块类型
                tile_type = -1
                if 0 <= gy < len(tile_map) and 0 <= gx < len(tile_map[gy]):
                    tile_type = tile_map[gy][gx]

                if tile_type >= 0:
                    color = tile_colors.get(tile_type, (180, 180, 180))
                    if gx == 0 and gy == 0:
                        color = (60, 60, 70)
                    pygame.draw.polygon(surf, color, screen_vertices_int)
                    pygame.draw.polygon(surf, (100, 100, 100), screen_vertices_int, 1)
                else:
                    pygame.draw.polygon(surf, (30, 30, 30), screen_vertices_int)

        # 更新缓存状态
        self._game_grid_camera = (cam_x, cam_y)
        self._game_grid_zoom = zoom

    # ============================================================
    # 配置面板点击处理
    # ============================================================
    def _handle_config_click(self, mx, my, button):
        """处理配置面板的点击事件"""
        if button != 1:
            return False

        x, y = mx, my

        # 检查模式切换按钮
        if hasattr(self, '_cfg_btns'):
            for name, rect in self._cfg_btns.items():
                if rect.collidepoint(x, y):
                    if name == 'mode_edit':
                        self.preview_mode = 'edit'
                        self.need_redraw = True
                        print("切换到: 编辑模式")
                    elif name == 'mode_game':
                        self.preview_mode = 'game'
                        self.need_redraw = True
                        print("切换到: 游戏预览模式")
                    elif name == 'save_cfg':
                        self._save_current_config()
                        print("配置已保存")
                        self.need_redraw = True
                    return True

        # 检查操作按钮
        if hasattr(self, '_cfg_action_btns'):
            for brect, action in self._cfg_action_btns:
                if brect.collidepoint(x, y):
                    action()
                    self.need_redraw = True
                    return True

        # 检查字段
        for key, rect in self.field_rects.items():
            if rect.collidepoint(x, y):
                # 找到对应的字段
                field = next((f for f in self.config_fields if f["key"] == key), None)
                if field:
                    ftype = field["type"]
                    if ftype in ("text", "number"):
                        self.focused_field = key
                        self.cursor_timer = 0
                        self.cursor_visible = True
                    elif ftype == "bool":
                        self.config[key] = not self.config.get(key, False)
                        self._save_current_config()
                        print(f"{field['label']}: {self.config[key]}")
                    elif ftype == "choice":
                        choices = field["choices"]
                        current = self.config.get(key, choices[0])
                        try:
                            idx = choices.index(current)
                            idx = (idx + 1) % len(choices)
                        except ValueError:
                            idx = 0
                        self.config[key] = choices[idx]
                        # 切换文件类型时自动更新默认缩放因子和字段列表
                        if key == "file_type":
                            new_type = choices[idx]
                            default_scale = self._type_default_scale.get(new_type, 0.1)
                            self.config["scale"] = default_scale
                            # 更新字段列表
                            self._update_config_fields()
                            # 确保新字段有默认值
                            for field in self.config_fields:
                                if field["key"] not in self.config:
                                    self.config[field["key"]] = field["default"]
                            print(f"文件类型: {new_type}, 默认缩放: {default_scale}")
                        self._save_current_config()
                        print(f"{field['label']}: {choices[idx]}")
                    self.need_redraw = True
                return True

        # 点击空白取消聚焦
        self.focused_field = None
        self.need_redraw = True
        return False

    # ============================================================
    # 文本输入处理
    # ============================================================
    def _handle_text_input(self, ev):
        """处理键盘输入（配置字段文本）"""
        if self.focused_field is None:
            return False

        field = next((f for f in self.config_fields if f["key"] == self.focused_field), None)
        if not field or field["type"] not in ("text", "number"):
            self.focused_field = None
            return False

        key = self.focused_field
        val = str(self.config.get(key, ""))

        if ev.key == pygame.K_RETURN:
            self.focused_field = None
            self._save_current_config()
            self.need_redraw = True
            return True
        elif ev.key == pygame.K_TAB:
            # 切换到下一个字段
            keys = [f["key"] for f in self.config_fields if f["type"] in ("text", "number")]
            try:
                idx = keys.index(key)
                self.focused_field = keys[(idx + 1) % len(keys)]
            except ValueError:
                pass
            self.need_redraw = True
            return True
        elif ev.key == pygame.K_ESCAPE:
            self.focused_field = None
            self.need_redraw = True
            return True
        elif ev.key == pygame.K_BACKSPACE:
            self.config[key] = val[:-1]
            self.need_redraw = True
            return True
        else:
            # 字符输入
            if hasattr(ev, 'unicode') and ev.unicode:
                if field["type"] == "number":
                    # 数字字段接受数字、负号和小数点
                    if ev.unicode.isdigit() or (ev.unicode == '-' and len(val) == 0) or (ev.unicode == '.' and '.' not in val):
                        self.config[key] = val + ev.unicode
                        self.need_redraw = True
                else:
                    self.config[key] = val + ev.unicode
                    self.need_redraw = True
            return True

        return False  # 非文本字符按键

    # ============================================================
    # 主绘制函数
    # ============================================================
    def draw(self):
        """主绘制入口"""
        screen.fill(COLOR_BG)

        # 计算中央区域坐标
        img_area_x = CENTER_X
        img_area_y = INFO_H
        img_area_w = CENTER_W
        img_area_h = CENTER_H

        # ---- 左侧：文件列表 ----
        pygame.draw.rect(screen, COLOR_PANEL, (0, 0, LEFT_W, WIN_H))

        filter_names = ["全部", "已完成", "待处理"]
        title = font_title.render(f"文件 [{filter_names[self.filter_mode]}]", True, COLOR_ACCENT)
        screen.blit(title, (8, 8))

        total = len(self.files)
        done = sum(1 for f in self.files if self.tags.get(f) == 1)
        pending = total - done
        stats = font_small.render(f"{total} | {done}✓ {pending}○", True, COLOR_TEXT_DIM)
        screen.blit(stats, (8, 25))

        y = 42
        visible = (WIN_H - 55) // 20
        for i in range(self.scroll_offset, min(self.scroll_offset + visible, len(self.filtered_files))):
            fname = self.filtered_files[i]
            sel = (i == self.idx)
            tag = self.tags.get(fname, 2)
            tag_color = (100, 200, 100) if tag == 1 else (200, 150, 100)
            tag_text = "✓" if tag == 1 else "○"

            rect = pygame.Rect(5, y, LEFT_W - 10, 18)
            pygame.draw.rect(screen, (80, 100, 140) if sel else COLOR_PANEL, rect, border_radius=3)

            tag_s = font.render(tag_text, True, tag_color)
            screen.blit(tag_s, (10, y + 2))
            txt = font.render(fname, True, COLOR_TEXT_BRIGHT if sel else COLOR_TEXT_DIM)
            screen.blit(txt, (25, y + 2))
            y += 20

        # ---- 顶部信息栏 ----
        pygame.draw.rect(screen, COLOR_INFO, (LEFT_W, 0, WIN_W - LEFT_W, INFO_H))
        key = None
        if self.filtered_files:
            fname = self.filtered_files[self.idx]
            key = fname.replace('.png', '')
            has_fp = " [FP]" if key in self.footprint_data else ""
            has_wall = " [W]" if key in self.wall_data else ""
            has_pl = " [PL]" if key in self.placeable_data else ""
            tag = self.tags.get(fname, 2)
            tag_str = "✓完成" if tag == 1 else "○待处理"
            info = f"当前: {fname}{has_fp}{has_wall}{has_pl} | {tag_str} | 去除:{len(self.manual_remove)}px | 恢复:{len(self.manual_keep)}px"
            screen.blit(font_small.render(info, True, (200, 200, 200)), (LEFT_W + 10, 6))

        # ---- 中央区域 ----
        if self.preview_mode == 'game':
            # 游戏预览模式
            self._draw_game_preview()
        else:
            # 编辑模式（原有图片显示）
            clip = pygame.Rect(img_area_x, img_area_y, img_area_w, img_area_h)
            screen.set_clip(clip)

            cx = img_area_x + img_area_w // 2 + self.zoom_offset_x
            cy = img_area_y + img_area_h // 2 + self.zoom_offset_y

            if self.need_redraw or self.display_surf is None:
                base = self._get_display()
                if base:
                    w, h = base.get_size()
                    zw = max(1, int(w * self.zoom))
                    zh = max(1, int(h * self.zoom))
                    self.display_surf = pygame.transform.scale(base, (zw, zh))
                else:
                    self.display_surf = None
                self.need_redraw = False

            if self.display_surf:
                dw, dh = self.display_surf.get_size()
                dx = cx - dw // 2
                dy = cy - dh // 2
                screen.blit(self.display_surf, (dx, dy))
                self.display_x = dx
                self.display_y = dy
            else:
                self.display_x = None
                self.display_y = None
                dw, dh = 0, 0
                dx, dy = 0, 0

            # 预览高亮
            if self.preview_active and self.preview_pixels and self.display_surf:
                preview_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
                for (px, py) in self.preview_pixels:
                    sx = int(px * self.zoom)
                    sy = int(py * self.zoom)
                    sw = max(1, int(self.zoom))
                    sh = max(1, int(self.zoom))
                    pygame.draw.rect(preview_surf, (255, 50, 50, 120), (sx, sy, sw, sh))
                screen.blit(preview_surf, (dx, dy))

            # 框选矩形
            if self.rect_selecting and self.rect_start and self.rect_end and self.display_surf:
                rx1 = int(min(self.rect_start[0], self.rect_end[0]) * self.zoom)
                ry1 = int(min(self.rect_start[1], self.rect_end[1]) * self.zoom)
                rx2 = int(max(self.rect_start[0], self.rect_end[0]) * self.zoom)
                ry2 = int(max(self.rect_start[1], self.rect_end[1]) * self.zoom)
                rect_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
                pygame.draw.rect(rect_surf, (100, 150, 255, 60), (rx1, ry1, rx2 - rx1, ry2 - ry1))
                pygame.draw.rect(rect_surf, (100, 150, 255, 200), (rx1, ry1, rx2 - rx1, ry2 - ry1), 2)
                screen.blit(rect_surf, (dx, dy))

            # footprint 覆盖层
            if key and key in self.footprint_data and self.display_surf:
                fp_points = self.footprint_data[key]
                if len(fp_points) >= 3:
                    fp_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
                    screen_fp = [(int(px * self.zoom), int(py * self.zoom)) for px, py in fp_points]
                    pygame.draw.polygon(fp_surf, (0, 255, 0, 60), screen_fp)
                    pygame.draw.polygon(fp_surf, (0, 200, 0, 180), screen_fp, 2)
                    for px, py in screen_fp:
                        pygame.draw.circle(fp_surf, (0, 255, 0, 200), (px, py), 4)
                    screen.blit(fp_surf, (dx, dy))

            # wall_surface 覆盖层
            if key and key in self.wall_data and self.display_surf:
                wall_points = self.wall_data[key]
                if len(wall_points) >= 3:
                    wall_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
                    screen_wall = [(int(px * self.zoom), int(py * self.zoom)) for px, py in wall_points]
                    pygame.draw.polygon(wall_surf, (0, 100, 255, 60), screen_wall)
                    pygame.draw.polygon(wall_surf, (0, 100, 255, 180), screen_wall, 2)
                    for px, py in screen_wall:
                        pygame.draw.circle(wall_surf, (0, 100, 255, 200), (px, py), 4)
                    screen.blit(wall_surf, (dx, dy))

            # placeable_areas 覆盖层
            if key and key in self.placeable_data and self.display_surf:
                for area in self.placeable_data[key]:
                    area_points = area.get("points", [])
                    if len(area_points) >= 3:
                        pl_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
                        screen_pl = [(int(px * self.zoom), int(py * self.zoom)) for px, py in area_points]
                        pygame.draw.polygon(pl_surf, (255, 150, 0, 60), screen_pl)
                        pygame.draw.polygon(pl_surf, (255, 150, 0, 180), screen_pl, 2)
                        for px, py in screen_pl:
                            pygame.draw.circle(pl_surf, (255, 150, 0, 200), (px, py), 4)
                        screen.blit(pl_surf, (dx, dy))

            # 编辑模式：当前绘制点
            if (self.footprint_mode or self.wall_mode or self.placeable_mode) and self.display_surf:
                current_points = self.footprint_points if self.footprint_mode else (self.wall_points if self.wall_mode else self.placeable_points)
                if current_points:
                    dw, dh = self.display_surf.get_size()
                    edit_surf = pygame.Surface((dw, dh), pygame.SRCALPHA)
                    screen_pts = [(int(px * self.zoom), int(py * self.zoom)) for px, py in current_points]
                    if len(screen_pts) >= 2:
                        pygame.draw.lines(edit_surf, (255, 255, 0, 200), False, screen_pts, 2)
                    for px, py in screen_pts:
                        pygame.draw.circle(edit_surf, (255, 255, 0, 255), (px, py), 5)
                    mmx, mmy = pygame.mouse.get_pos()
                    if self.display_x is not None:
                        mpx = int((mmx - self.display_x) / self.zoom)
                        mpy = int((mmy - self.display_y) / self.zoom)
                        mscreen = (int(mpx * self.zoom), int(mpy * self.zoom))
                        pygame.draw.line(edit_surf, (255, 255, 0, 100), screen_pts[-1], mscreen, 1)
                        pygame.draw.line(edit_surf, (255, 255, 0, 100), mscreen, screen_pts[0], 1)
                    screen.blit(edit_surf, (dx, dy))

                mode_name = "Footprint" if self.footprint_mode else ("WallSurface" if self.wall_mode else "Placeable")
                hint = f"[{mode_name}模式] 左键:添加点 | 右键:删除最后点 | C:闭合保存 | Esc:取消"
                screen.blit(font_small.render(hint, True, (255, 200, 100)),
                           (CENTER_X + 10, WIN_H - TOOLBAR_H - 20))

            screen.set_clip(None)

        # ---- 右侧：配置面板 ----
        self._draw_config_panel()

        # ---- 底部：工具栏 ----
        pygame.draw.rect(screen, COLOR_TOOLBAR, (0, WIN_H - TOOLBAR_H, WIN_W, TOOLBAR_H))

        # 第一行：图片编辑
        btns_row1 = [
            ("上一张(<)", 15), ("下一张(>)", 110),
            ("去青色(F)", 210), ("裁剪(V)", 310),
            ("保存(C)", 400)
        ]
        for text, x in btns_row1:
            rect = pygame.Rect(x, WIN_H - TOOLBAR_H + 4, 85, 24)
            pygame.draw.rect(screen, COLOR_BTN, rect, border_radius=4)
            screen.blit(font.render(text, True, COLOR_TEXT), (x + 6, WIN_H - TOOLBAR_H + 9))

        # 第二行：编辑模式
        btns_row2 = [
            ("Footprint(F)", 15), ("墙面(W)", 120), ("放置区(A)", 210),
            ("退出(Q)", 310)
        ]
        for text, x in btns_row2:
            rect = pygame.Rect(x, WIN_H - TOOLBAR_H + 32, 90, 24)
            pygame.draw.rect(screen, COLOR_BTN, rect, border_radius=4)
            screen.blit(font.render(text, True, COLOR_TEXT), (x + 6, WIN_H - TOOLBAR_H + 37))

        # 模式提示
        mode = "Footprint" if self.footprint_mode else ("WallSurface" if self.wall_mode else ("Placeable" if self.placeable_mode else "编辑"))
        preview_str = "游戏预览" if self.preview_mode == 'game' else "编辑"
        hint = f"模式:{mode} | 预览:{preview_str} | Z/X:切换 | T:标签 | 0/1/2:筛选 | Ctrl+E/G:切换预览 | C:确认保存"
        screen.blit(font_small.render(hint, True, COLOR_TEXT_DIM), (420, WIN_H - TOOLBAR_H + 42))

    # ============================================================
    # 主循环
    # ============================================================
    def run(self):
        init_editor_display()
        running = True

        while running:
            # 光标闪烁计时
            self.cursor_timer += 1
            if self.cursor_timer >= 30:  # 约0.5秒（30fps）
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False

                elif ev.type == pygame.KEYDOWN:
                    # 优先处理文本输入
                    if self.focused_field is not None:
                        if self._handle_text_input(ev):
                            continue

                    # ---- 快捷键 ----
                    if ev.key == pygame.K_q:
                        # 询问是否保存
                        running = False

                    elif ev.key == pygame.K_f and not (ev.mod & pygame.KMOD_CTRL):
                        if self.footprint_mode:
                            self.footprint_mode = False
                            self.footprint_points = []
                            print("Footprint 编辑模式: 关闭")
                        else:
                            self._cancel_all_modes()
                            self.footprint_mode = True
                            print("Footprint 编辑模式: 开启 - 左键添加点，C闭合")

                    elif ev.key == pygame.K_w and not (ev.mod & pygame.KMOD_CTRL):
                        if self.wall_mode:
                            self.wall_mode = False
                            self.wall_points = []
                            print("WallSurface: 关闭")
                        else:
                            self._cancel_all_modes()
                            self.wall_mode = True
                            print("WallSurface: 开启")

                    elif ev.key == pygame.K_a and not (ev.mod & pygame.KMOD_CTRL):
                        if self.placeable_mode:
                            self.placeable_mode = False
                            self.placeable_points = []
                            print("Placeable: 关闭")
                        else:
                            self._cancel_all_modes()
                            self.placeable_mode = True
                            print("Placeable: 开启")

                    elif ev.key == pygame.K_c and not (ev.mod & pygame.KMOD_CTRL):
                        if self.preview_active:
                            self.confirm_preview()
                            self.save()
                            self._save_current_config()
                            self._save_all_data()
                            print("已确认删除 + 保存")
                        elif self.footprint_mode or self.wall_mode or self.placeable_mode:
                            if self._close_polygon():
                                self.save()
                                self._save_current_config()
                                self._save_all_data()
                        else:
                            # 无编辑模式时，C = 仅保存
                            self.save()
                            self._save_current_config()
                            self._save_all_data()

                    elif ev.key == pygame.K_v:
                        self.crop_to_content()

                    elif ev.key == pygame.K_t:
                        self.toggle_tag()

                    elif ev.key == pygame.K_1:
                        self.set_filter(1)
                    elif ev.key == pygame.K_2:
                        self.set_filter(2)
                    elif ev.key == pygame.K_0:
                        self.set_filter(0)

                    elif ev.key == pygame.K_ESCAPE:
                        if self.footprint_mode or self.wall_mode or self.placeable_mode:
                            self._cancel_all_modes()
                            print("编辑模式: 取消")
                        elif self.preview_active:
                            self.cancel_preview()
                            print("已取消预览")
                        elif self.focused_field is not None:
                            self.focused_field = None
                        else:
                            running = False

                    elif ev.key == pygame.K_z:
                        if self.filtered_files:
                            self._load((self.idx - 1) % len(self.filtered_files))
                    elif ev.key == pygame.K_x:
                        if self.filtered_files:
                            self._load((self.idx + 1) % len(self.filtered_files))

                    elif ev.key == pygame.K_UP and self.scroll_offset > 0:
                        self.scroll_offset -= 1
                    elif ev.key == pygame.K_DOWN:
                        max_scroll = max(0, len(self.filtered_files) - (WIN_H - 55) // 20)
                        self.scroll_offset = min(self.scroll_offset + 1, max_scroll)

                    # Ctrl 组合键
                    elif ev.key == pygame.K_g and (ev.mod & pygame.KMOD_CTRL):
                        self.preview_mode = 'game' if self.preview_mode == 'edit' else 'edit'
                        print(f"预览模式: {'游戏预览' if self.preview_mode == 'game' else '编辑'}")
                        self.need_redraw = True

                    # F5: 注册到游戏
                    elif ev.key == pygame.K_F5:
                        self._save_current_config()
                        self.auto_register_to_game()

                    # F6: 生成代码
                    elif ev.key == pygame.K_F6:
                        self._generate_and_copy()

                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = ev.pos

                    # 游戏预览模式：中键拖动
                    if self.preview_mode == 'game' and mx >= CENTER_X and mx < CENTER_X + CENTER_W:
                        if ev.button == 2:  # 中键拖动
                            self.game_cam_dragging = True
                            self.game_cam_drag_start = (mx, my)
                            self.game_cam_drag_start_pos = (self.game_cam_x, self.game_cam_y)

                    # 文件列表点击
                    if mx < LEFT_W and my < WIN_H - TOOLBAR_H:
                        y = 42
                        visible_count = (WIN_H - 55) // 20
                        for i in range(self.scroll_offset, min(self.scroll_offset + visible_count, len(self.filtered_files))):
                            if y <= my < y + 18:
                                self._load(i)
                                break
                            y += 20

                    # 配置面板点击
                    elif mx >= CFG_X and my >= INFO_H and my < WIN_H - TOOLBAR_H:
                        self._handle_config_click(mx, my, ev.button)

                    # 按钮点击（底部工具栏区域）
                    elif my >= WIN_H - TOOLBAR_H and my < WIN_H:
                        if 15 <= mx <= 100 and WIN_H - TOOLBAR_H + 4 <= my <= WIN_H - TOOLBAR_H + 28:
                            if self.filtered_files:
                                self._load((self.idx - 1) % len(self.filtered_files))
                        elif 110 <= mx <= 195 and WIN_H - TOOLBAR_H + 4 <= my <= WIN_H - TOOLBAR_H + 28:
                            if self.filtered_files:
                                self._load((self.idx + 1) % len(self.filtered_files))
                        elif 210 <= mx <= 295 and WIN_H - TOOLBAR_H + 4 <= my <= WIN_H - TOOLBAR_H + 28:
                            self.auto_remove_cyan()
                        elif 310 <= mx <= 395 and WIN_H - TOOLBAR_H + 4 <= my <= WIN_H - TOOLBAR_H + 28:
                            self.crop_to_content()
                        elif 400 <= mx <= 485 and WIN_H - TOOLBAR_H + 4 <= my <= WIN_H - TOOLBAR_H + 28:
                            self.save()
                            self._save_current_config()
                            self._save_all_data()
                            print("已保存")

                        # 模式按钮
                        elif 15 <= mx <= 105 and WIN_H - TOOLBAR_H + 32 <= my <= WIN_H - TOOLBAR_H + 56:
                            self._cancel_all_modes()
                            self.footprint_mode = True
                            print("Footprint: 开启")
                        elif 120 <= mx <= 210 and WIN_H - TOOLBAR_H + 32 <= my <= WIN_H - TOOLBAR_H + 56:
                            self._cancel_all_modes()
                            self.wall_mode = True
                            print("WallSurface: 开启")
                        elif 210 <= mx <= 300 and WIN_H - TOOLBAR_H + 32 <= my <= WIN_H - TOOLBAR_H + 56:
                            self._cancel_all_modes()
                            self.placeable_mode = True
                            print("Placeable: 开启")
                        elif 310 <= mx <= 400 and WIN_H - TOOLBAR_H + 32 <= my <= WIN_H - TOOLBAR_H + 56:
                            running = False

                    # 中央区域点击（仅编辑模式）
                    elif self.preview_mode == 'edit' and self.display_x is not None and my >= INFO_H and my < WIN_H - TOOLBAR_H:
                        # 多边形编辑模式
                        if self.footprint_mode or self.wall_mode or self.placeable_mode:
                            px = int((mx - self.display_x) / self.zoom)
                            py = int((my - self.display_y) / self.zoom)
                            if self.processed and 0 <= px < self.processed.get_width() and 0 <= py < self.processed.get_height():
                                if ev.button == 1:
                                    pt = (px, py)
                                    if self.footprint_mode:
                                        self.footprint_points.append(pt)
                                        print(f"FP+ ({px},{py}) #{len(self.footprint_points)}")
                                    elif self.wall_mode:
                                        self.wall_points.append(pt)
                                        print(f"Wall+ ({px},{py}) #{len(self.wall_points)}")
                                    elif self.placeable_mode:
                                        self.placeable_points.append(pt)
                                        print(f"PL+ ({px},{py}) #{len(self.placeable_points)}")
                                elif ev.button == 3:
                                    if self.footprint_mode and self.footprint_points:
                                        print(f"FP- {self.footprint_points.pop()}")
                                    elif self.wall_mode and self.wall_points:
                                        print(f"Wall- {self.wall_points.pop()}")
                                    elif self.placeable_mode and self.placeable_points:
                                        print(f"PL- {self.placeable_points.pop()}")
                        else:
                            # 普通编辑
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
                    # 游戏预览相机拖动
                    if self.game_cam_dragging:
                        dx = (self.game_cam_drag_start[0] - ev.pos[0]) / self.game_zoom
                        dy = (self.game_cam_drag_start[1] - ev.pos[1]) / self.game_zoom
                        self.game_cam_x = self.game_cam_drag_start_pos[0] + dx
                        self.game_cam_y = self.game_cam_drag_start_pos[1] + dy
                        self.need_redraw = True

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
                        self.game_cam_dragging = False
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
                    if mx < LEFT_W:
                        if ev.y > 0 and self.scroll_offset > 0:
                            self.scroll_offset -= 1
                        elif ev.y < 0:
                            max_scroll = max(0, len(self.filtered_files) - (WIN_H - 55) // 20)
                            self.scroll_offset = min(self.scroll_offset + 1, max_scroll)
                    elif self.preview_mode == 'game' and mx >= CENTER_X and mx < CENTER_X + CENTER_W:
                        # 游戏预览：滚轮缩放
                        if ev.y > 0:
                            self.game_zoom = min(self.game_zoom + 0.1, 2.0)
                        elif ev.y < 0:
                            self.game_zoom = max(self.game_zoom - 0.1, 0.3)
                        self.need_redraw = True
                    elif self.preview_mode == 'edit':
                        if ev.y > 0:
                            self.zoom = min(self.zoom * 1.3, 10.0)
                        elif ev.y < 0:
                            self.zoom = max(self.zoom / 1.3, 0.5)
                        self.need_redraw = True
                        print(f"缩放: {self.zoom:.1f}x")

            # 绘制
            self.draw()
            pygame.display.flip()
            clock.tick(30)

        # 退出前保存
        self._save_current_config()
        self._save_all_data()
        pygame.quit()

    # ---- 兼容老版本的 old_run 方法 ----------
    # 直接使用 run() 代替


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    existing = [f for f in os.listdir(PROCESSED_DIR) if f.endswith(".png")] if os.path.exists(PROCESSED_DIR) else []
    if not existing:
        batch_flood_remove()
    else:
        print(f"已处理过 {len(existing)} 张图，跳过批量处理")
    editor = FurnitureEditor()
    editor.run()
