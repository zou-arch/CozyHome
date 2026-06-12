"""
世界类 - 管理整个游戏平面（俯视角）
按区块划分，每个区块有类型：地板、种植区
无限延伸的世界
"""
import pygame
import os
import math
import time
import random
from collections import OrderedDict
from ..entities.furniture import Furniture
from ..entities.crop import Crop
from .collision import CollisionSystem
from .weather import Weather

class World:
    """世界类"""

    # 区块类型
    TILE_FLOOR = 0  # 地板（室内）
    TILE_FARM = 1   # 种植区（室外）

    # 地板外观模板（3套）
    FLOOR_STYLES = [
        {"name": "木地板", "color": (180, 150, 120), "pattern": "wood", "file": "F_floor_wood.png"},
        {"name": "瓷砖", "color": (200, 200, 210), "pattern": "tile", "file": "F_floor_tile.png"},
        {"name": "地毯", "color": (150, 100, 100), "pattern": "carpet", "file": "F_floor_carpet.png"},
    ]

    # 种植区外观模板（4套）
    FARM_STYLES = [
        {"name": "土生", "color": (139, 90, 43), "pattern": "soil"},
        {"name": "水生", "color": (100, 150, 255), "pattern": "water"},
        {"name": "盆栽", "color": (200, 150, 100), "pattern": "pot"},
        {"name": "沙生", "color": (240, 220, 160), "pattern": "sand"},
    ]

    # 种植区容量限制（每种类型每个区块的最大作物数）
    FARM_CAPACITY = {
        0: 12,  # 土生
        1: 6,   # 水生
        2: 4,   # 盆栽
        3: 6,   # 沙生
    }

    # 种植区行列布局
    FARM_LAYOUT = {
        0: (4, 3),  # 土生: 4列3行 = 12格
        1: (3, 2),  # 水生: 3列2行 = 6格
        2: (2, 2),  # 盆栽: 2列2行 = 4格
        3: (3, 2),  # 沙生: 3列2行 = 6格
    }

    # 区块颜色
    TILE_COLORS = {
        TILE_FLOOR: (180, 150, 120),  # 浅棕色地板（默认）
        TILE_FARM: (120, 180, 100),   # 浅绿色种植区
    }

    # 2:1 等距像素风格参数
    # 菱形边角度: A边 26°, B边 334°(-26°)
    # 间距(法线方向) = 120
    TILE_SPACING = 120
    TILE_WIDTH = 174    # 菱形水平半对角线（实际 ≈ 173.7）
    TILE_HEIGHT = 85    # 菱形垂直对角线（实际 ≈ 169.4，取一半）

    def __init__(self, game_manager):
        self.game_manager = game_manager

        # 已定义的区块地图
        # 初始只有1个地板(0,0) + 1个种植区(1,0)，其他全部未解锁(-1)
        self.tile_map = [
            [ 0,  1, -1, -1, -1, -1, -1, -1, -1, -1],
            [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
            [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
            [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
        ]

        # 地板样式索引（每个地板区块可以有不同的样式）
        self.floor_styles = {}  # key: (x, y), value: style_index

        # 种植区样式索引（每个种植区区块可以有不同的类型）
        self.farm_styles = {}  # key: (x, y), value: style_index (0=土生, 1=水生, 2=盆栽, 3=沙生)

        # 加载地板图像
        self.floor_images = {}
        self.load_floor_images()

        # 加载种植区图像
        self.farm_images = {}
        self.load_farm_images()

        # overlay 缓存（优化性能）
        self._overlay_cache = None
        self._overlay_size = (0, 0)

        # 临时 Surface 缓存（避免每帧创建 SRCALPHA Surface）
        self._temp_surface = None
        self._mask_surface = None
        self._temp_surface_size = (0, 0)

        # 精灵图缩放缓存（避免每帧 smoothscale，使用 OrderedDict 实现 LRU 淘汰）
        self._img_scale_cache = OrderedDict()

        # 预渲染菱形裁剪后的区块图片缓存
        # key: (tile_type, style_idx, zoom_int) -> pre-rendered surface
        self._tile_prerender_cache = {}
        self._tile_prerender_vertices = {}  # 缓存菱形顶点

        # 加载作物精灵图
        Crop.load_all_sprites()

        # 预加载家具图片
        Furniture.load_all_images()

        # 物体列表
        self.furniture_list: list[Furniture] = []
        self.crop_list: list[Crop] = []

        # 碰撞系统
        self.collision = CollisionSystem()

        # 天气系统
        self.weather = Weather()

        # 宠物管理器
        from ..managers.pet_manager import PetManager
        self.pet_manager = PetManager(self)

        # 字体缓存（避免每帧创建 SysFont）
        self._font_cache = pygame.font.SysFont(None, 24)

        # 拖拽可视化状态（用于渲染槽位点和 footprint）
        self._drag_visualization = {
            "active": False,           # 是否正在拖拽
            "furniture": None,         # 被拖拽的家具
            "show_slots": True,        # 是否显示槽位点
            "show_footprint": True,    # 是否显示 footprint
            "cached_slots": None,      # 缓存的槽位点（世界坐标）
            "cached_occupied": None,   # 缓存的占用状态
            "last_furniture_pos": None,# 上次家具位置（用于判断是否需要更新）
        }

        # 当前选中的物体
        self.selected_object = None

    def _prerender_tile(self, img, zoom_int):
        """预渲染带有菱形裁剪的区块图片（等距视角 2:1 菱形）"""
        cache_key = (id(img), zoom_int)
        if cache_key in self._tile_prerender_cache:
            return self._tile_prerender_cache[cache_key]

        # 缩放图片
        w = int(img.get_width() * zoom_int / 100)
        h = int(img.get_height() * zoom_int / 100)
        if w <= 0 or h <= 0:
            return None
        scaled_img = pygame.transform.smoothscale(img, (w, h))

        # 等距视角菱形顶点（2:1 比例，基于图片尺寸）
        # 顶点：上、右、下、左
        diamond_vertices = [
            (w // 2, 0),      # 上
            (w, h // 2),      # 右
            (w // 2, h),      # 下
            (0, h // 2),      # 左
        ]

        # 创建带透明度的 Surface
        result = pygame.Surface((w, h), pygame.SRCALPHA)
        result.blit(scaled_img, (0, 0))

        # 创建菱形遮罩
        mask_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(mask_surface, (255, 255, 255, 255), diamond_vertices)

        # 应用遮罩
        result.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # 缓存
        self._tile_prerender_cache[cache_key] = result
        return result

    def _get_diamond_bbox(self, img):
        """提取菱形非透明像素的最小包围盒，边缘羽化抗锯齿"""
        import numpy as np
        from scipy.ndimage import gaussian_filter
        w, h = img.get_size()
        alpha = np.array(pygame.surfarray.pixels_alpha(img), dtype=np.float64)
        non_transparent = alpha > 0

        if not non_transparent.any():
            return img

        cols = non_transparent.any(axis=1)
        rows = non_transparent.any(axis=0)
        left = int(cols.argmax())
        right = int(w - cols[::-1].argmax())
        top = int(rows.argmax())
        bottom = int(h - rows[::-1].argmax())

        cropped = img.subsurface((left, top, right - left, bottom - top)).copy()

        # 边缘羽化：对 alpha 通道做高斯模糊
        crop_alpha = np.array(pygame.surfarray.pixels_alpha(cropped), dtype=np.float64)
        blurred = gaussian_filter(crop_alpha, sigma=1.0)
        # 只保留边缘区域的模糊结果，内部保持 255
        mask_edge = (crop_alpha > 0) & (crop_alpha < 255)
        crop_alpha[~mask_edge] = blurred[~mask_edge]
        crop_alpha = np.clip(crop_alpha, 0, 255).astype(np.uint8)

        # 写回 alpha
        pygame.surfarray.pixels_alpha(cropped)[:] = crop_alpha
        return cropped

    def _get_tile_pixel_size(self):
        """获取区块在 zoom=1.0 时的像素尺寸"""
        corners = self.get_tile_vertices(0, 0)
        xs = [p[0] for p in corners]
        ys = [p[1] for p in corners]
        world_w = max(xs) - min(xs)
        world_h = max(ys) - min(ys)
        return int(world_w), int(world_h)

    def load_floor_images(self):
        """加载地板图像（缩放到区块实际像素大小）"""
        sprites_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sprites", "furniture")
        tile_w, tile_h = self._get_tile_pixel_size()
        scale = 1.3  # 缩放因子，调整这个值

        for i, style in enumerate(self.FLOOR_STYLES):
            file_path = os.path.join(sprites_dir, style["file"])
            if os.path.exists(file_path):
                try:
                    img = pygame.image.load(file_path).convert_alpha()
                    img = pygame.transform.smoothscale(img, (int(tile_w * scale), int(tile_h * scale)))
                    self.floor_images[i] = self._get_diamond_bbox(img)
                    print(f"加载地板图像: {style['name']} -> {int(tile_w*scale)}x{int(tile_h*scale)}")
                except Exception as e:
                    print(f"加载地板图像失败: {style['name']}, {e}")
            else:
                print(f"地板图像不存在: {file_path}")

    def load_farm_images(self):
        """加载种植区图像（缩放到区块实际像素大小）"""
        sprites_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sprites", "floor")
        tile_w, tile_h = self._get_tile_pixel_size()
        scale = 1.05  # 缩放因子，调整这个值

        farm_files = {
            0: "F_farm_soil.png",   # 土生
            1: "F_farm_water.png",  # 水生
            2: "F_farm_pot.png",    # 盆栽
            3: "F_farm_sand.png",   # 沙生
        }

        for i, file_name in farm_files.items():
            file_path = os.path.join(sprites_dir, file_name)
            if os.path.exists(file_path):
                try:
                    img = pygame.image.load(file_path).convert_alpha()
                    img = pygame.transform.smoothscale(img, (int(tile_w * scale), int(tile_h * scale)))
                    self.farm_images[i] = self._get_diamond_bbox(img)
                    print(f"加载种植区图像: {self.FARM_STYLES[i]['name']} -> {int(tile_w*scale)}x{int(tile_h*scale)}")
                except Exception as e:
                    print(f"加载种植区图像失败: {self.FARM_STYLES[i]['name']}, {e}")
            else:
                print(f"种植区图像不存在: {file_path}")

    # 预计算坐标变换矩阵（常量，只计算一次）
    _M_FORWARD = None  # 正变换矩阵 M
    _M_INVERSE = None  # 逆变换矩阵 M_inv

    @classmethod
    def _init_transform_matrices(cls):
        """初始化坐标变换矩阵（只执行一次）"""
        if cls._M_FORWARD is not None:
            return

        alpha = math.radians(116)
        beta = math.radians(244)
        cos_a, sin_a = math.cos(alpha), math.sin(alpha)
        cos_b, sin_b = math.cos(beta), math.sin(beta)
        det = cos_a * sin_b - sin_a * cos_b
        K = cls.TILE_SPACING / abs(det)

        # 正变换矩阵
        cls._M_FORWARD = [
            [-sin_a * K / det, sin_b * K / det],
            [cos_a * K / det, -cos_b * K / det]
        ]

        # 逆变换矩阵
        M = cls._M_FORWARD
        det_M = M[0][0] * M[1][1] - M[0][1] * M[1][0]
        cls._M_INVERSE = [
            [M[1][1] / det_M, -M[0][1] / det_M],
            [-M[1][0] / det_M, M[0][0] / det_M]
        ]

    def world_to_grid(self, x: float, y: float) -> tuple:
        """世界坐标转区块坐标（与 coordinate_viewer 一致，返回浮点数）"""
        # 确保矩阵已初始化
        self._init_transform_matrices()

        # 使用预计算的逆变换矩阵
        M_inv = self._M_INVERSE
        grid_x = M_inv[0][0] * x + M_inv[0][1] * y
        grid_y = M_inv[1][0] * x + M_inv[1][1] * y
        return (grid_x, grid_y)

    def grid_to_world(self, grid_x: int, grid_y: int) -> tuple:
        """区块坐标转世界坐标（菱形边 116°/244°）"""
        # 确保矩阵已初始化
        self._init_transform_matrices()

        # 使用预计算的正变换矩阵
        M = self._M_FORWARD
        world_x = M[0][0] * grid_x + M[0][1] * grid_y
        world_y = M[1][0] * grid_x + M[1][1] * grid_y
        return (world_x, world_y)

    def get_tile_type(self, grid_x: int, grid_y: int) -> int:
        """获取区块类型（超出范围返回-1未解锁，支持无限世界）"""
        if 0 <= grid_y < len(self.tile_map) and 0 <= grid_x < len(self.tile_map[grid_y]):
            return self.tile_map[grid_y][grid_x]
        return -1  # 未定义的区域视为未解锁

    @staticmethod
    def get_unlock_cost(unlock_count: int) -> int:
        """
        计算解锁第N个区块的价格

        价格梯度：
        - 前5个：15金币
        - 6-10个：30金币
        - 11-20个：50金币
        - 21+：100金币
        """
        if unlock_count <= 5:
            return 15
        elif unlock_count <= 10:
            return 30
        elif unlock_count <= 20:
            return 50
        else:
            return 100

    def get_unlocked_count(self) -> int:
        """获取已解锁区块数量（不含初始的2个区块）"""
        count = 0
        for row in self.tile_map:
            for tile in row:
                if tile >= 0:
                    count += 1
        return count - 2  # 减去初始的2个区块（地板+种植区）

    def unlock_tile(self, grid_x: int, grid_y: int) -> bool:
        """
        解锁指定区块（支持无限扩展）

        解锁规则：
        - 第0行：解锁为种植区
        - 其他行：解锁为地板
        """
        # 动态扩展 tile_map 以容纳新区块
        self._ensure_tile_map_size(grid_x, grid_y)

        if self.tile_map[grid_y][grid_x] == -1:
            # 根据行号决定解锁类型
            if grid_y == 0:
                self.tile_map[grid_y][grid_x] = self.TILE_FARM
            else:
                self.tile_map[grid_y][grid_x] = self.TILE_FLOOR
            print(f"解锁区块({grid_x},{grid_y}) -> 类型: {self.tile_map[grid_y][grid_x]}")
            return True
        return False

    def _ensure_tile_map_size(self, grid_x: int, grid_y: int):
        """确保 tile_map 足够大以容纳指定区块"""
        # 扩展行数
        while len(self.tile_map) <= grid_y:
            # 新增行，宽度与第一行相同或至少 grid_x+1
            row_width = max(len(self.tile_map[0]) if self.tile_map else 0, grid_x + 1)
            new_row = [-1] * row_width
            self.tile_map.append(new_row)

        # 扩展列数
        for row in self.tile_map:
            while len(row) <= grid_x:
                row.append(-1)

    def get_floor_style(self, grid_x: int, grid_y: int) -> dict:
        """获取地板样式"""
        key = (grid_x, grid_y)
        style_index = self.floor_styles.get(key, 0)
        return self.FLOOR_STYLES[style_index]

    def get_farm_style(self, grid_x: int, grid_y: int) -> dict:
        """获取种植区样式"""
        key = (grid_x, grid_y)
        style_index = self.farm_styles.get(key, 0)
        return self.FARM_STYLES[style_index]

    def get_farm_type(self, grid_x: int, grid_y: int) -> int:
        """获取种植区类型 (0=soil, 1=water, 2=pot, 3=sand)"""
        return self.farm_styles.get((grid_x, grid_y), 0)

    def get_adjacent_farm_tiles(self, grid_x: int, grid_y: int) -> list:
        """获取指定位置四方向相邻的种植区块，返回 [(gx, gy, farm_type), ...]"""
        result = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = grid_x + dx, grid_y + dy
            if self.get_tile_type(nx, ny) == self.TILE_FARM:
                farm_type = self.get_farm_type(nx, ny)
                result.append((nx, ny, farm_type))
        return result

    def has_furniture_at_grid(self, grid_x: int, grid_y: int) -> bool:
        """检查指定区块内是否有家具"""
        # 遍历所有家具，检查是否有家具的中心点在这个区块内
        for furniture in self.furniture_list:
            # 使用 world_to_grid 将家具坐标转为区块坐标
            fg_x, fg_y = self.world_to_grid(furniture.x, furniture.y)
            # 取整后比较
            if math.floor(fg_x) == grid_x and math.floor(fg_y) == grid_y:
                return True
        return False

    def click_tile(self, grid_x: int, grid_y: int, is_edit_mode: bool, world_pos: tuple = None):
        """点击区块"""
        tile_type = self.get_tile_type(grid_x, grid_y)
        farm_type = self.farm_styles.get((grid_x, grid_y), 0) if tile_type == self.TILE_FARM else -1

        if is_edit_mode:
            # 编辑模式：打开样式选择菜单
            if tile_type == self.TILE_FLOOR:
                return {"type": "floor_menu", "grid_x": grid_x, "grid_y": grid_y}
            elif tile_type == self.TILE_FARM:
                # 检查区块内是否有家具，有则不允许切换样式
                if self.has_furniture_at_grid(grid_x, grid_y):
                    print(f"区块({grid_x},{grid_y})内有家具，无法切换样式")
                    return None
                return {"type": "farm_menu", "grid_x": grid_x, "grid_y": grid_y}
        else:
            # 普通模式
            if tile_type == self.TILE_FARM and world_pos:
                # 找到最近的空闲槽位
                slot_idx = self.find_empty_slot(grid_x, grid_y, world_pos)
                if slot_idx >= 0:
                    return {"type": "plant_slot", "grid_x": grid_x, "grid_y": grid_y, "slot_idx": slot_idx}
                else:
                    print("区块已满")
            elif tile_type == self.TILE_FLOOR:
                print("点击地板")
        return None

    def can_plant_at(self, grid_x: int, grid_y: int, crop_type: int) -> bool:
        """检查是否可以在指定位置种植指定类型的作物"""
        tile_type = self.get_tile_type(grid_x, grid_y)
        if tile_type != self.TILE_FARM:
            return False

        # 获取种植区类型
        farm_style = self.get_farm_style(grid_x, grid_y)
        farm_type = self.farm_styles.get((grid_x, grid_y), 0)

        # 检查作物类型是否匹配
        if farm_type != crop_type:
            return False

        # 检查容量限制
        count = self.count_crops_in_block(grid_x, grid_y)
        capacity = self.FARM_CAPACITY.get(farm_type, 6)
        if count >= capacity:
            return False

        return True

    def count_crops_in_block(self, grid_x: int, grid_y: int) -> int:
        """统计指定区块内的作物数量"""
        count = 0
        for crop in self.crop_list:
            crop_gx, crop_gy = self.world_to_grid(crop.x, crop.y)
            if math.floor(crop_gx) == grid_x and math.floor(crop_gy) == grid_y:
                count += 1
        return count

    def get_farm_slots(self, grid_x: int, grid_y: int) -> list:
        """获取指定种植区的所有预定义种植位置（交错网格，用户视觉均匀分布）"""
        farm_type = self.farm_styles.get((grid_x, grid_y), 0)
        # 使用 grid_to_world(grid_x + 0.5, grid_y + 0.5) 获取区块中心
        cx, cy = self.grid_to_world(grid_x + 0.5, grid_y + 0.5)
        capacity = self.FARM_CAPACITY.get(farm_type, 6)

        hw = self.TILE_WIDTH   # 水平对角线长度
        hh = self.TILE_HEIGHT  # 垂直对角线长度

        # 交错网格排列（旋转45°回正方形看就是砖墙式排列）
        # 等距网格：用 grid_to_world 的逆变换
        # 在区块内定义一个小网格，然后用等距变换转为世界坐标
        # 这样在用户眼中就是均匀的菱形网格

        if capacity == 12:
            cols, rows = 4, 3
        elif capacity == 6:
            cols, rows = 3, 2
        elif capacity == 4:
            cols, rows = 2, 2
        else:
            cols, rows = 3, 2

        slots = []
        for r in range(rows):
            for c in range(cols):
                # 小网格坐标（以区块中心为原点）
                nx = (c + 0.5) / cols * 2 - 1  # [-1, 1]
                ny = (r + 0.5) / rows * 2 - 1  # [-1, 1]

                # 等距变换到世界坐标
                offset_x = (nx - ny) * hw * 0.55
                offset_y = (nx + ny) * hh * 0.55

                slot_x = cx + offset_x
                slot_y = cy + offset_y

                # 菱形边界检查
                check_nx = (slot_x - cx) / hw
                check_ny = (slot_y - cy) / hh
                if abs(check_nx) + abs(check_ny) > 1.0:
                    continue

                slots.append((slot_x, slot_y))

        return slots

    def get_occupied_slots(self, grid_x: int, grid_y: int) -> set:
        """获取指定区块内已被占用的槽位索引"""
        slots = self.get_farm_slots(grid_x, grid_y)
        occupied = set()
        for crop in self.crop_list:
            crop_gx, crop_gy = self.world_to_grid(crop.x, crop.y)
            if math.floor(crop_gx) == grid_x and math.floor(crop_gy) == grid_y:
                # 找到最近的槽位
                min_dist = float('inf')
                min_idx = -1
                for i, (sx, sy) in enumerate(slots):
                    dist = (crop.x - sx) ** 2 + (crop.y - sy) ** 2
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = i
                if min_idx >= 0:
                    occupied.add(min_idx)
        return occupied

    def find_empty_slot(self, grid_x: int, grid_y: int, world_pos: tuple) -> int:
        """找到最近的空闲槽位索引"""
        slots = self.get_farm_slots(grid_x, grid_y)
        occupied = self.get_occupied_slots(grid_x, grid_y)

        min_dist = float('inf')
        best_idx = -1
        for i, (sx, sy) in enumerate(slots):
            if i not in occupied:
                dist = (world_pos[0] - sx) ** 2 + (world_pos[1] - sy) ** 2
                if dist < min_dist:
                    min_dist = dist
                    best_idx = i
        return best_idx

    def is_slot_empty(self, grid_x: int, grid_y: int, slot_idx: int) -> bool:
        """检查指定槽位是否为空"""
        occupied = self.get_occupied_slots(grid_x, grid_y)
        return slot_idx not in occupied

    def harvest_crop(self, crop) -> dict:
        """收获作物"""
        if crop not in self.crop_list:
            return {}
        result = crop.harvest()
        if result:
            self.crop_list.remove(crop)
        return result

    def plant_crop(self, crop_id: str, grid_x: int, grid_y: int, slot_idx: int = -1) -> bool:
        """在指定槽位种植作物"""
        from ..entities.crop import Crop

        # 获取作物数据
        crop_data = Crop.CROP_DATA.get(crop_id)
        if not crop_data:
            print(f"未知作物: {crop_id}")
            return False

        # 检查是否可以种植
        if not self.can_plant_at(grid_x, grid_y, crop_data["type"]):
            farm_type = self.farm_styles.get((grid_x, grid_y), 0)
            farm_name = self.FARM_STYLES[farm_type]["name"]
            crop_type_name = self.FARM_STYLES[crop_data["type"]]["name"]
            count = self.count_crops_in_block(grid_x, grid_y)
            capacity = self.FARM_CAPACITY.get(farm_type, 6)
            if count >= capacity:
                print(f"区块已满: {farm_name}区最多{capacity}株")
            else:
                print(f"无法种植: {crop_data['name']}需要{crop_type_name}区")
            return False

        # 获取种植位置
        slots = self.get_farm_slots(grid_x, grid_y)

        if slot_idx >= 0 and slot_idx < len(slots):
            # 使用指定槽位
            if not self.is_slot_empty(grid_x, grid_y, slot_idx):
                print(f"槽位 {slot_idx} 已被占用")
                return False
            crop_x, crop_y = slots[slot_idx]
        else:
            # 自动找空闲槽位
            slot_idx = self.find_empty_slot(grid_x, grid_y, (0, 0))
            if slot_idx < 0:
                print(f"区块已满")
                return False
            crop_x, crop_y = slots[slot_idx]

        # 创建作物
        crop = Crop(crop_id, crop_x, crop_y)

        # 菱形边界检查（使用区块中心作为参考点）
        cx, cy = self.grid_to_world(grid_x + 0.5, grid_y + 0.5)
        hw = self.TILE_WIDTH   # 水平半对角线长度
        hh = self.TILE_HEIGHT  # 垂直半对角线长度
        check_nx = (crop_x - cx) / hw
        check_ny = (crop_y - cy) / hh
        in_diamond = abs(check_nx) + abs(check_ny) <= 1.0

        self.crop_list.append(crop)

        return True

    def get_tile_vertices(self, grid_x: int, grid_y: int) -> list:
        """获取区块的四个顶点（直接使用网格点）"""
        corners = [
            self.grid_to_world(grid_x, grid_y),
            self.grid_to_world(grid_x + 1, grid_y),
            self.grid_to_world(grid_x + 1, grid_y + 1),
            self.grid_to_world(grid_x, grid_y + 1),
        ]
        return corners

    def add_furniture(self, furniture_id: str, x: float, y: float):
        """放置家具，自由放置"""
        furniture = Furniture(furniture_id, x, y)

        # 加载 footprint
        fp = self.collision.get_footprint(furniture_id)
        if fp:
            furniture.set_footprint(fp)

        # 统一放置检测
        all_objects = self.furniture_list + self.crop_list
        if not self.can_place_furniture(furniture, x, y, all_objects):
            return False

        self.furniture_list.append(furniture)
        print(f"放置成功: {furniture.name}")
        return True

    def can_place_furniture(self, furniture, new_x: float, new_y: float, all_objects: list) -> bool:
        """
        【统一放置检测入口】放置和移动都用这个函数，确保逻辑一致

        参数：
        - furniture: 要放置/移动的家具对象
        - new_x, new_y: 新位置的世界坐标（家具中心点）
        - all_objects: 所有物体列表（用于碰撞检测）

        返回：
        - True: 可以放置
        - False: 不能放置

        检测流程：
        0. 未解锁区块检测 - 家具不能放在未解锁区块
        1. 水种植区检测 - 家具不能放在水种植区
        2. 槽位重叠检测 - 家具footprint不能与种植区槽位有任何重叠
        3. 碰撞检测 - 与其他物体的footprint不能重叠

        【后续添加新规则的位置】
        如果需要添加新的放置限制（如边界检测、特殊区域限制等），
        请在下面按顺序添加，并更新注释
        """
        # 获取家具 footprint（用于所有检测）
        furniture_fp = self.collision.get_world_footprint(furniture)
        print(f"[放置检测] footprint数据: {furniture_fp}")

        # 0. 未解锁区块检测：家具不能放在未解锁区块（基于 footprint）
        if furniture_fp:
            # 获取 footprint 覆盖的所有区块
            covered_blocks = set()
            for px, py in furniture_fp:
                block_x, block_y = self.world_to_grid(px, py)
                covered_blocks.add((math.floor(block_x), math.floor(block_y)))
            print(f"[放置检测] footprint覆盖区块: {covered_blocks}")

            # 检查是否有未解锁区块
            for block_x, block_y in covered_blocks:
                tile_type = self.get_tile_type(block_x, block_y)
                print(f"[放置检测] 区块({block_x},{block_y}) 类型: {tile_type}")
                if tile_type == -1:
                    print(f"[放置检测] footprint覆盖未解锁区块({block_x},{block_y})，拒绝放置")
                    return False
        else:
            # 没有 footprint 数据，使用中心点检测
            grid_x_raw, grid_y_raw = self.world_to_grid(new_x, new_y)
            grid_x, grid_y = math.floor(grid_x_raw), math.floor(grid_y_raw)
            tile_type = self.get_tile_type(grid_x, grid_y)
            print(f"[放置检测] 无footprint，中心点区块({grid_x},{grid_y}) 类型: {tile_type}")
            if tile_type == -1:
                print(f"[放置检测] 中心点在未解锁区块({grid_x},{grid_y})，拒绝放置")
                return False

        # 0.1 no_collision 特例（如地毯）：只检测种植区，不检测碰撞
        no_collision = getattr(furniture, 'no_collision', False)
        if not no_collision:
            no_collision = Furniture.FURNITURE_DATA.get(furniture.furniture_id, {}).get('no_collision', False)
        if no_collision:
            # no_collision 物体只能放在地板上，不能放在种植区
            if furniture_fp:
                for block_x, block_y in covered_blocks:
                    tile_type = self.get_tile_type(block_x, block_y)
                    if tile_type == self.TILE_FARM:
                        return False
            else:
                grid_x_raw, grid_y_raw = self.world_to_grid(new_x, new_y)
                grid_x, grid_y = math.floor(grid_x_raw), math.floor(grid_y_raw)
                tile_type = self.get_tile_type(grid_x, grid_y)
                if tile_type == self.TILE_FARM:
                    return False
            return True

        # 1. 水种植区检测（家具不能放在水种植区）
        # 原因：水种植区是专门用于水生作物的，家具会影响种植
        # 基于家具 footprint 覆盖的所有区块进行检测（复用上面的 covered_blocks）
        if furniture_fp:
            # 检查是否有水种植区
            for block_x, block_y in covered_blocks:
                tile_type = self.get_tile_type(block_x, block_y)
                if tile_type == self.TILE_FARM:
                    farm_type = self.farm_styles.get((block_x, block_y), 0)
                    if farm_type == 1:  # 1 = 水生
                        print(f"放置失败: 家具footprint覆盖水种植区({block_x},{block_y})")
                        return False
        else:
            # 没有 footprint 数据，使用中心点检测
            grid_x_raw, grid_y_raw = self.world_to_grid(new_x, new_y)
            grid_x, grid_y = math.floor(grid_x_raw), math.floor(grid_y_raw)
            tile_type = self.get_tile_type(grid_x, grid_y)
            if tile_type == -1:
                print(f"[放置检测] 区块({grid_x},{grid_y}) 是未解锁区域，拒绝放置")
                return False
            if tile_type == self.TILE_FARM:
                farm_type = self.farm_styles.get((grid_x, grid_y), 0)
                if farm_type == 1:  # 1 = 水生
                    print(f"放置失败: 家具中心点在水种植区")
                    return False

        # 2. 槽位重叠检测（家具footprint不能与种植区槽位重叠）
        # 原因：槽位是预定义的种植位置，重叠会导致作物无法种植
        if self.check_furniture_overlap_farm_slots(furniture):
            print(f"放置失败: 家具与种植区槽位重叠")
            return False

        # 3. 碰撞检测（与其他物体的footprint不能重叠）
        # 使用 collision.py 中的检测逻辑，支持地面/墙面/表面等类型
        if self.collision.check_overlap(furniture, new_x, new_y, all_objects):
            print(f"放置失败: 与已有物体重叠")
            return False

        return True

    def check_furniture_overlap_farm_slots(self, furniture) -> bool:
        """
        检查家具是否与任何种植区槽位重叠

        调用者：can_place_furniture() → 本函数
        被调用场景：
        - 放置家具时（place_furniture_from_backpack）
        - 拖拽移动家具时（input_handler.py handle_mouse_motion）
        - 结束拖拽时（furniture.py end_drag）

        参数：
        - furniture: 要检查的家具对象

        返回：
        - True: 有重叠（不能放置）
        - False: 无重叠（可以放置）

        检测逻辑：
        1. 获取家具的世界坐标 footprint（多边形）
        2. 遍历所有种植区区块
        3. 获取每个种植区的槽位（预定义的种植点）
        4. 检查每个槽位点是否在家具 footprint 内
        5. 如果任意槽位在 footprint 内，则判定为重叠

        【后续修改提示】
        - 槽位数据来自 get_farm_slots() 函数
        - footprint 数据来自 collision.get_world_footprint() 函数
        - 如果需要修改槽位布局，修改 get_farm_slots() 即可
        """
        # 获取家具的世界坐标 footprint
        furniture_fp = self.collision.get_world_footprint(furniture)
        if not furniture_fp:
            return False

        # 检查所有种植区
        for grid_y in range(len(self.tile_map)):
            for grid_x in range(len(self.tile_map[grid_y])):
                if self.tile_map[grid_y][grid_x] == self.TILE_FARM:
                    # 获取该区块的槽位
                    slots = self.get_farm_slots(grid_x, grid_y)
                    for slot_x, slot_y in slots:
                        # 检查槽位点是否在家具 footprint 内
                        if self.collision._point_in_polygon((slot_x, slot_y), furniture_fp):
                            return True
        return False

    def place_furniture_from_backpack(self, furniture_id: str, x: float, y: float):
        """从背包放置家具到世界，返回放置的家具对象或 None"""
        # 检查背包中是否有该家具
        if furniture_id not in self.game_manager.unlocked_furniture:
            print(f"放置失败: 背包中没有 {furniture_id}")
            return None

        # 记录放置前的数量
        count_before = len(self.furniture_list)
        # 尝试放置
        if self.add_furniture(furniture_id, x, y):
            # 放置成功，从背包移除
            self.game_manager.unlocked_furniture.remove(furniture_id)
            # 返回新放置的家具
            return self.furniture_list[-1] if len(self.furniture_list) > count_before else None
        return None

    def remove_furniture(self, furniture):
        """将家具放回仓库，处理依附物品"""
        obj_type = getattr(furniture, 'obj_type', 'ground')

        # 如果是surface/surface_wall/wall_surface，检查依附物品
        if obj_type in ('surface', 'surface_wall', 'wall_surface'):
            all_objects = self.furniture_list + self.crop_list
            attached = furniture.get_attached_items(all_objects, self.collision)

            if attached:
                print(f"放回 {furniture.name}，依附物品: {[i.name for i in attached]}")
                # 依附物品也放回仓库
                for item in attached:
                    if item in self.furniture_list:
                        self.furniture_list.remove(item)
                        # 添加回仓库库存
                        self.game_manager.unlocked_furniture.append(item.furniture_id)

        if furniture in self.furniture_list:
            self.furniture_list.remove(furniture)
            # 添加回仓库库存
            self.game_manager.unlocked_furniture.append(furniture.furniture_id)
            print(f"已放回仓库: {furniture.name}")

    def get_object_at_pos(self, world_pos: tuple, camera=None) -> object:
        for crop in self.crop_list:
            hit = crop.handle_click(world_pos, camera)
            if hit:
                return crop
        for furniture in self.furniture_list:
            hit = furniture.is_clicked_at(world_pos, camera)
            if hit:
                return furniture
        return None

    def select_object(self, obj):
        self.selected_object = obj
        if obj:
            obj.selected = True

    def deselect_all(self):
        if self.selected_object:
            self.selected_object.selected = False
        self.selected_object = None

    def update(self, screen_w=480, screen_h=270):
        # 天气更新
        self.weather.update(self)
        self.weather.update_rain_drops(screen_w, screen_h)
        # 作物更新
        for crop in self.crop_list:
            crop.update(self)

        # 宠物更新
        if hasattr(self, 'pet_manager'):
            self.pet_manager.update(1/60, self.camera)  # 假设60fps

    def get_crop_save_data(self) -> list:
        """获取作物存档数据（包含区块坐标，用于加载时验证位置）"""
        crops_data = []
        for crop in self.crop_list:
            gx_raw, gy_raw = self.world_to_grid(crop.x, crop.y)
            crops_data.append({
                "crop_id": crop.crop_id,
                "x": crop.x,
                "y": crop.y,
                "grid_x": math.floor(gx_raw),
                "grid_y": math.floor(gy_raw),
                "start_time": crop.start_time,
                "water_level": crop.water_level,
                "is_fertilized": crop.is_fertilized,
                "last_water_update": crop.last_water_update,
                "current_stage": crop.current_stage,
            })
        return crops_data

    def load_crop_save_data(self, crops_data: list):
        """加载作物存档数据（自动迁移网格坐标不匹配的作物）"""
        self.crop_list.clear()
        for data in crops_data:
            crop = Crop(data["crop_id"], data["x"], data["y"])
            crop.start_time = data.get("start_time", time.time())
            crop.water_level = data.get("water_level", 80.0)
            crop.is_fertilized = data.get("is_fertilized", False)
            crop.last_water_update = data.get("last_water_update", time.time())

            # 从存档恢复当前生长阶段
            # 如果存档中有 current_stage 字段则使用它，否则根据时间重新计算
            saved_stage = data.get("current_stage", None)
            if saved_stage is not None:
                crop.current_stage = saved_stage
                # 如果已成熟，设置 growth_progress 为 1.0
                if crop.current_stage >= 3:
                    crop.growth_progress = 1.0

            # 验证作物是否在正确的区块内
            saved_gx = data.get("grid_x")
            saved_gy = data.get("grid_y")
            if saved_gx is not None and saved_gy is not None:
                cur_gx, cur_gy = self.world_to_grid(crop.x, crop.y)
                if math.floor(cur_gx) != saved_gx or math.floor(cur_gy) != saved_gy:
                    # 世界坐标在新区块系统中偏移了，重新定位到目标区块的最近槽位
                    target_type = self.get_tile_type(saved_gx, saved_gy)
                    if target_type == self.TILE_FARM:
                        slots = self.get_farm_slots(saved_gx, saved_gy)
                        if slots:
                            # 找最近的槽位
                            min_dist = float('inf')
                            best = slots[0]
                            for sx, sy in slots:
                                d = (crop.x - sx) ** 2 + (crop.y - sy) ** 2
                                if d < min_dist:
                                    min_dist = d
                                    best = (sx, sy)
                            crop.x, crop.y = best
                            print(f"作物迁移: {crop.name} ({data['x']:.0f},{data['y']:.0f}) -> ({crop.x:.0f},{crop.y:.0f}) 区块({saved_gx},{saved_gy})")

            # 更新水分消耗和生长状态
            # 注意：如果 water_level == 0，update() 会直接返回，保留 current_stage
            crop.update(self)
            self.crop_list.append(crop)

    def get_furniture_save_data(self) -> list:
        """获取家具存档数据"""
        furniture_data = []
        for furniture in self.furniture_list:
            save_item = {
                "furniture_id": furniture.furniture_id,
                "x": furniture.x,
                "y": furniture.y,
                "is_on": furniture.is_on,
                "is_flipped": furniture.is_flipped,
            }
            # 蓄水器需要保存储水量
            if furniture.furniture_id == "waterstorage" and hasattr(furniture, 'water_stored'):
                save_item["water_stored"] = furniture.water_stored
            furniture_data.append(save_item)
        return furniture_data

    def load_furniture_save_data(self, furniture_data: list):
        """加载家具存档数据"""
        self.furniture_list.clear()
        for data in furniture_data:
            furniture = Furniture(data["furniture_id"], data["x"], data["y"])
            furniture.is_on = data.get("is_on", False)
            furniture.is_flipped = data.get("is_flipped", False)
            # 加载蓄水器储水量
            if data["furniture_id"] == "waterstorage":
                furniture.water_stored = data.get("water_stored", 0)
            # 加载 footprint
            fp = self.collision.get_footprint(data["furniture_id"])
            if fp:
                furniture.set_footprint(fp)
            self.furniture_list.append(furniture)
        print(f"加载家具: {len(self.furniture_list)} 个")

    def render(self, screen: pygame.Surface, camera, is_edit_mode=False):
        """渲染：只绘制 AB 线网格（与 coordinate_viewer 一致）"""
        self.is_edit_mode = is_edit_mode
        screen.fill((255, 255, 255))  # 白色背景

        zoom = camera.zoom
        screen_w = screen.get_width()
        screen_h = screen.get_height()

        # 计算屏幕在世界坐标中的范围
        world_left = camera.x - screen_w / (2 * zoom)
        world_right = camera.x + screen_w / (2 * zoom)
        world_top = camera.y - screen_h / (2 * zoom)
        world_bottom = camera.y + screen_h / (2 * zoom)

        # 计算需要渲染的区块范围
        gx1, gy1 = self.world_to_grid(world_left, world_top)
        gx2, gy2 = self.world_to_grid(world_right, world_top)
        gx3, gy3 = self.world_to_grid(world_left, world_bottom)
        gx4, gy4 = self.world_to_grid(world_right, world_bottom)

        min_gx = math.floor(min(gx1, gx2, gx3, gx4)) - 2
        max_gx = math.floor(max(gx1, gx2, gx3, gx4)) + 2
        min_gy = math.floor(min(gy1, gy2, gy3, gy4)) - 2
        max_gy = math.floor(max(gy1, gy2, gy3, gy4)) + 2

        # 使用缓存的字体
        font = self._font_cache

        # 预创建 overlay（复用，优化性能）
        if self._overlay_cache is None or self._overlay_size != (screen_w, screen_h):
            self._overlay_cache = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            self._overlay_size = (screen_w, screen_h)
        self._overlay_cache.fill((0, 0, 0, 0))

        # 复用临时 Surface（用于菱形裁剪）
        if self._temp_surface is None or self._temp_surface_size != (screen_w, screen_h):
            self._temp_surface = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            self._mask_surface = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            self._temp_surface_size = (screen_w, screen_h)
        self._temp_surface.fill((0, 0, 0, 0))
        self._mask_surface.fill((0, 0, 0, 0))

        # 绘制所有区块（优化：减少每帧操作）
        for gy in range(min_gy, max_gy + 1):
            for gx in range(min_gx, max_gx + 1):
                tile_type = self.get_tile_type(gx, gy)
                if tile_type < 0:
                    # 未解锁：黑色覆盖
                    vertices = self.get_tile_vertices(gx, gy)
                    screen_vertices = [camera.world_to_screen((vx, vy)) for vx, vy in vertices]
                    screen_vertices_int = [(int(sx), int(sy)) for sx, sy in screen_vertices]
                    pygame.draw.polygon(self._overlay_cache, (30, 30, 30, 200), screen_vertices_int)
                    continue

                # 已解锁：绘制菱形精灵图
                if tile_type == self.TILE_FLOOR:
                    style_idx = self.floor_styles.get((gx, gy), 0)
                    img = self.floor_images.get(style_idx)
                else:
                    style_idx = self.farm_styles.get((gx, gy), 0)
                    img = self.farm_images.get(style_idx)

                if not img:
                    continue

                # 获取缩放后的图片（带缓存）
                zoom_int = int(zoom * 100)
                cache_key = (id(img), zoom_int)
                if cache_key not in self._img_scale_cache:
                    if len(self._img_scale_cache) > 50:
                        self._img_scale_cache.popitem(last=False)
                    w = int(img.get_width() * zoom)
                    h = int(img.get_height() * zoom)
                    self._img_scale_cache[cache_key] = pygame.transform.smoothscale(img, (w, h))
                self._img_scale_cache.move_to_end(cache_key)
                scaled_img = self._img_scale_cache[cache_key]

                # 计算屏幕位置和菱形顶点
                vertices = self.get_tile_vertices(gx, gy)
                screen_vertices = [camera.world_to_screen((vx, vy)) for vx, vy in vertices]
                screen_vertices_int = [(int(sx), int(sy)) for sx, sy in screen_vertices]

                # 清空临时 Surface
                self._temp_surface.fill((0, 0, 0, 0))
                self._mask_surface.fill((0, 0, 0, 0))

                # 绘制精灵图
                cx, cy = self.grid_to_world(gx + 0.5, gy + 0.5)
                sp_cx, sp_cy = camera.world_to_screen((cx, cy))
                img_rect = scaled_img.get_rect(center=(int(sp_cx), int(sp_cy)))
                self._temp_surface.blit(scaled_img, img_rect)
                # 用菱形遮罩裁剪
                pygame.draw.polygon(self._mask_surface, (255, 255, 255, 255), screen_vertices_int)
                self._temp_surface.blit(self._mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                # 渲染到屏幕
                screen.blit(self._temp_surface, (0, 0))

        # 统一 blit overlay（未解锁区域）
        screen.blit(self._overlay_cache, (0, 0))

        # 绘制未解锁区块的白色边框和问号
        for gy in range(min_gy, max_gy + 1):
            for gx in range(min_gx, max_gx + 1):
                if self.get_tile_type(gx, gy) < 0:
                    vertices = self.get_tile_vertices(gx, gy)
                    screen_vertices = [camera.world_to_screen((vx, vy)) for vx, vy in vertices]
                    screen_vertices_int = [(int(sx), int(sy)) for sx, sy in screen_vertices]
                    pygame.draw.polygon(screen, (255, 255, 255), screen_vertices_int, 2)
                    # 白色问号（中心位置）
                    cx, cy = self.grid_to_world(gx + 0.5, gy + 0.5)
                    sp_cx, sp_cy = camera.world_to_screen((cx, cy))
                    q_text = font.render("?", True, (255, 255, 255))
                    screen.blit(q_text, (int(sp_cx - 5), int(sp_cy - 8)))

        # 渲染物体（保持原有逻辑）
        # 地毯（最底层，纯装饰）
        rug_objects = []
        # 所有其他物体（统一按Y排序）
        all_objects = []

        for crop in self.crop_list:
            all_objects.append((crop.get_footprint_bottom_y(), crop))

        for furniture in self.furniture_list:
            obj_type = getattr(furniture, 'obj_type', 'ground')

            # 地毯：最底层，纯装饰
            if furniture.furniture_id == 'rug':
                rug_objects.append((furniture.get_footprint_bottom_y(), furniture))

            # 墙挂（如painting）：使用依附体的Y值
            elif obj_type == 'wall_mount':
                base_y = furniture.get_footprint_bottom_y()
                for other in self.furniture_list:
                    other_type = getattr(other, 'obj_type', 'ground')
                    if other_type in ("wall_surface", "surface_wall"):
                        if self.collision.point_in_wall_surface(other, (furniture.x, furniture.y)):
                            base_y = other.get_footprint_bottom_y()
                            break
                all_objects.append((base_y, furniture))

            # 墙面物体（如wardrobe）
            elif obj_type == 'wall_surface':
                all_objects.append((furniture.get_footprint_bottom_y(), furniture))

            # 地面物体
            else:
                base_y = furniture.get_footprint_bottom_y()
                obj_center = (furniture.x + furniture.width / 2, furniture.y + furniture.height / 2)
                surface_obj = self.collision.get_surface_under_point(obj_center, self.furniture_list, furniture)
                if surface_obj:
                    base_y = surface_obj.get_footprint_bottom_y()
                all_objects.append((base_y, furniture))

        # 添加宠物到排序列表
        if hasattr(self, 'pet_manager'):
            for pet in self.pet_manager.scene_pets:
                all_objects.append((pet.get_footprint_bottom_y(), pet))

        # 排序
        rug_objects.sort(key=lambda obj: obj[0])
        all_objects.sort(key=lambda obj: obj[0])

        # 预计算透明物体集合
        transparent_objects = set()
        if hasattr(self, 'pet_manager') and self.pet_manager.scene_pets:
            for _, obj in all_objects:
                if not hasattr(obj, 'pet_id'):
                    if self.pet_manager.is_object_behind_pet(obj, camera):
                        transparent_objects.add(id(obj))

        # 渲染地毯
        for _, obj in rug_objects:
            obj.render(screen, camera)

        # 渲染所有物体（优化：减少类型检查）
        furniture_list = self.furniture_list
        render_with_alpha = Furniture.render_with_alpha
        render_normal = Furniture.render
        collision = self.collision
        has_alpha = transparent_objects.__contains__

        for _, obj in all_objects:
            obj_id = id(obj)
            if obj in furniture_list:
                if has_alpha(obj_id):
                    render_with_alpha(obj, screen, camera, collision, 128)
                else:
                    render_normal(obj, screen, camera, collision)
            else:
                obj.render(screen, camera)

        # 拖拽可视化
        if self._drag_visualization["active"]:
            self._render_drag_visualization(screen, camera)

        # 渲染雨滴
        self.weather.render_rain(screen)


    def _cache_farm_slots(self):
        """
        缓存所有种植区的槽位点（世界坐标和占用状态）

        优化：槽位位置固定，只需计算一次
        占用状态也在拖拽开始时缓存（拖拽过程中不会变化）
        """
        slots_data = []  # [(world_x, world_y, is_occupied), ...]
        no_place_data = {
            "water_farm": [],      # 水种植区 [(grid_x, grid_y), ...]
            "locked": [],          # 未解锁区域 [(grid_x, grid_y), ...]
            "farm_slots": [],      # 所有种植槽位 [(world_x, world_y), ...]
        }

        for grid_y in range(len(self.tile_map)):
            for grid_x in range(len(self.tile_map[grid_y])):
                tile_type = self.tile_map[grid_y][grid_x]
                if tile_type == self.TILE_FARM:
                    # 检查是否是水种植区
                    farm_type = self.farm_styles.get((grid_x, grid_y), 0)
                    if farm_type == 1:  # 1 = 水生
                        no_place_data["water_farm"].append((grid_x, grid_y))

                    # 获取该区块的槽位
                    slots = self.get_farm_slots(grid_x, grid_y)
                    # 渲染每个槽位点
                    for i, (slot_x, slot_y) in enumerate(slots):
                        # 检查槽位是否被占用
                        is_occupied = not self.is_slot_empty(grid_x, grid_y, i)
                        slots_data.append((slot_x, slot_y, is_occupied))
                        # 所有种植槽位都标红（家具不能放在槽位上）
                        no_place_data["farm_slots"].append((slot_x, slot_y))

                elif tile_type == -1:
                    # 未解锁区域
                    no_place_data["locked"].append((grid_x, grid_y))

        self._drag_visualization["cached_slots"] = slots_data
        self._drag_visualization["cached_no_place"] = no_place_data

    def start_drag_visualization(self, furniture):
        """
        开始拖拽可视化（显示槽位点和 footprint）

        调用者：input_handler.py 拖拽开始时
        优化：缓存槽位点位置和占用状态，避免每帧重新计算
        """
        self._drag_visualization["active"] = True
        self._drag_visualization["furniture"] = furniture
        # 缓存槽位点（世界坐标和占用状态）
        self._cache_farm_slots()
        # 记录初始位置
        self._drag_visualization["last_furniture_pos"] = (furniture.x, furniture.y)

    def stop_drag_visualization(self):
        """
        停止拖拽可视化

        调用者：input_handler.py 拖拽结束时
        """
        self._drag_visualization["active"] = False
        self._drag_visualization["furniture"] = None
        self._drag_visualization["cached_slots"] = None
        self._drag_visualization["cached_no_place"] = None
        self._drag_visualization["cached_occupied"] = None
        self._drag_visualization["last_furniture_pos"] = None

    def _render_drag_visualization(self, screen, camera):
        """
        渲染拖拽可视化：根据家具类型显示不同内容

        功能：
        1. 普通家具（ground/surface）：非放置区域标红 + footprint + placeable_area
        2. 墙挂物品（wall_mount）：所有 wall_surface 区域 + 自身的 wall_surface + footprint
        3. 可挂墙面家具（surface_wall）：非放置区域标红 + placeable_area + 自身 wall_surface + footprint
        """
        furniture = self._drag_visualization["furniture"]
        if not furniture:
            return

        zoom = camera.zoom
        obj_type = getattr(furniture, 'obj_type', 'ground')

        if obj_type == "wall_mount":
            # 墙挂物品：显示所有 wall_surface 区域和自身的 wall_surface
            # 渲染顺序：wall_surface(底层) → footprint(顶层)
            self._render_wall_surfaces(screen, camera, furniture)
            self._render_furniture_footprint(screen, camera, furniture)
        elif obj_type in ("surface_wall", "wall_surface"):
            # 可挂墙面家具（如书架、衣柜、通用墙）：显示可放置区域 + 自身 wall_surface + footprint
            # 渲染顺序：非放置区域(底层) → placeable_area(中间) → wall_surface(中间) → footprint(顶层)
            self._render_no_place_zones(screen, camera, zoom)
            self._render_placeable_areas(screen, camera, furniture)
            self._render_self_wall_surface(screen, camera, furniture)
            self._render_furniture_footprint(screen, camera, furniture)
        else:
            # 普通家具：显示非放置区域标红、footprint 和 placeable_area
            # 渲染顺序：非放置区域(底层) → placeable_area(中间) → footprint(顶层)
            self._render_no_place_zones(screen, camera, zoom)
            self._render_placeable_areas(screen, camera, furniture)
            self._render_furniture_footprint(screen, camera, furniture)

    def _render_no_place_zones(self, screen, camera, zoom):
        """
        渲染非放置区域标红（使用缓存数据）

        功能：
        1. 水种植区：红色覆盖整个区块
        2. 未解锁区域：红色覆盖整个区块
        3. 所有种植槽位：红色标记槽位轮廓

        优化：使用缓存的区块数据，避免每帧重新计算
        """
        # 获取缓存数据
        cached_no_place = self._drag_visualization.get("cached_no_place")
        if not cached_no_place:
            return

        # 创建半透明表面
        zone_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)

        # 渲染缓存的非放置区域
        for zone_type, data in cached_no_place.items():
            if zone_type == "water_farm":
                # 水种植区：红色覆盖整个区块
                for grid_x, grid_y in data:
                    vertices = self.get_tile_vertices(grid_x, grid_y)
                    screen_points = [camera.world_to_screen((px, py)) for px, py in vertices]
                    pygame.draw.polygon(zone_surface, (255, 50, 50, 80), screen_points)
                    pygame.draw.polygon(zone_surface, (255, 50, 50, 200), screen_points, 2)

            elif zone_type == "locked":
                # 未解锁区域：红色覆盖整个区块
                for grid_x, grid_y in data:
                    vertices = self.get_tile_vertices(grid_x, grid_y)
                    screen_points = [camera.world_to_screen((px, py)) for px, py in vertices]
                    pygame.draw.polygon(zone_surface, (255, 50, 50, 100), screen_points)
                    pygame.draw.polygon(zone_surface, (255, 50, 50, 200), screen_points, 2)

            elif zone_type == "farm_slots":
                # 所有种植槽位：红色标记槽位轮廓
                for slot_x, slot_y in data:
                    screen_x, screen_y = camera.world_to_screen((slot_x, slot_y))
                    # 绘制槽位点（红色圆形，半径更大更醒目）
                    radius = max(4, int(8 * zoom))
                    pygame.draw.circle(zone_surface, (255, 50, 50, 120), (int(screen_x), int(screen_y)), radius)
                    pygame.draw.circle(zone_surface, (255, 50, 50, 220), (int(screen_x), int(screen_y)), radius, 2)

        # 渲染到主屏幕
        screen.blit(zone_surface, (0, 0))

    def _render_wall_surfaces(self, screen, camera, mount_furniture):
        """
        渲染 wall_surface 区域（用于墙挂物品拖拽可视化）

        功能：
        1. 渲染所有 wall_surface 物体的 wall_surface 区域（蓝色半透明）
        2. 渲染墙挂物品自身的 wall_surface 区域（绿色半透明）
        3. 检测当前位置是否合法（80% 重叠要求）
        """
        # 创建半透明表面
        ws_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)

        # 1. 渲染所有可挂载物体的 wall_surface 区域（蓝色半透明）
        # surface_wall 类型（如 wardrobe、bookshelf）有 wall_surfaces 数据
        for furniture in self.furniture_list:
            obj_type = getattr(furniture, 'obj_type', 'ground')
            if obj_type in ("wall_surface", "surface_wall"):
                wall_area = self.collision.get_world_wall_surface(furniture)
                if wall_area and len(wall_area) >= 3:
                    # 转换为屏幕坐标
                    screen_points = [camera.world_to_screen((px, py)) for px, py in wall_area]
                    # 绘制蓝色半透明多边形（可挂载区域）
                    pygame.draw.polygon(ws_surface, (100, 150, 255, 60), screen_points)
                    pygame.draw.polygon(ws_surface, (100, 150, 255, 150), screen_points, 2)

        # 2. 渲染墙挂物品自身的 wall_surface 区域
        mount_ws = self.collision.get_wall_surface(mount_furniture.furniture_id)
        if mount_ws and len(mount_ws) >= 3:
            # 计算墙挂的世界坐标 wf
            scale = Furniture.get_total_scale(mount_furniture.furniture_id)
            is_flipped = getattr(mount_furniture, 'is_flipped', False)
            img = Furniture._images.get(mount_furniture.furniture_id)
            if img:
                img_w, img_h = img.get_size()
                rendered_w = img_w * scale
                rendered_h = img_h * scale
                offset_x = mount_furniture.x - rendered_w / 2
                offset_y = mount_furniture.y - rendered_h / 2
            else:
                offset_x = mount_furniture.x
                offset_y = mount_furniture.y
            # 如果翻转，需要对 x 坐标进行水平镜像
            if is_flipped:
                mount_ws_world = [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in mount_ws]
            else:
                mount_ws_world = [(offset_x + px * scale, offset_y + py * scale) for px, py in mount_ws]

            # 转换为屏幕坐标
            screen_points = [camera.world_to_screen((px, py)) for px, py in mount_ws_world]

            # 检测当前位置是否合法（80% 重叠要求）
            can_place = False
            for furniture in self.furniture_list:
                other_type = getattr(furniture, 'obj_type', 'ground')
                if other_type in ("wall_surface", "surface_wall"):
                    wall_area = self.collision.get_world_wall_surface(furniture)
                    if wall_area and len(wall_area) >= 3:
                        mount_ws_area = self.collision._polygon_area(mount_ws_world)
                        if mount_ws_area > 0:
                            intersection = self.collision._polygon_intersection_area(mount_ws_world, wall_area)
                            if intersection / mount_ws_area >= 0.8:
                                can_place = True
                                break

            # 选择颜色：绿色=可放置，红色=不可放置
            color = (0, 200, 0, 80) if can_place else (200, 0, 0, 80)
            border_color = (0, 200, 0, 200) if can_place else (200, 0, 0, 200)

            # 绘制填充多边形
            pygame.draw.polygon(ws_surface, color, screen_points)
            # 绘制边框
            pygame.draw.polygon(ws_surface, border_color, screen_points, 2)

        # 渲染到主屏幕
        screen.blit(ws_surface, (0, 0))

    def _render_self_wall_surface(self, screen, camera, furniture):
        """
        渲染家具自身的 wall_surface 区域（用于 surface_wall 类型家具拖拽可视化）

        功能：
        1. 只渲染当前拖拽家具的 wall_surface 区域
        2. 显示为蓝色半透明，告诉用户这里可以挂装饰画
        """
        # 获取 wall_surface 数据
        ws_data = self.collision.get_wall_surface(furniture.furniture_id)
        if not ws_data or len(ws_data) < 3:
            return

        # 计算世界坐标
        scale = Furniture.get_total_scale(furniture.furniture_id)
        is_flipped = getattr(furniture, 'is_flipped', False)
        img = Furniture._images.get(furniture.furniture_id)

        if img:
            img_w, img_h = img.get_size()
            rendered_w = img_w * scale
            rendered_h = img_h * scale
            offset_x = furniture.x - rendered_w / 2
            offset_y = furniture.y - rendered_h / 2
        else:
            offset_x = furniture.x
            offset_y = furniture.y
            img_w, img_h = 0, 0

        # 如果翻转，需要对 x 坐标进行水平镜像
        if is_flipped:
            ws_world = [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in ws_data]
        else:
            ws_world = [(offset_x + px * scale, offset_y + py * scale) for px, py in ws_data]

        # 转换为屏幕坐标
        screen_points = [camera.world_to_screen((px, py)) for px, py in ws_world]

        # 创建半透明表面
        ws_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)

        # 绘制蓝色半透明多边形（可挂载区域）
        pygame.draw.polygon(ws_surface, (100, 150, 255, 60), screen_points)
        pygame.draw.polygon(ws_surface, (100, 150, 255, 150), screen_points, 2)

        # 渲染到主屏幕
        screen.blit(ws_surface, (0, 0))

    def _render_furniture_footprint(self, screen, camera, furniture):
        """
        渲染家具的 footprint（半透明多边形）

        优化：使用较小的Surface，只覆盖footprint区域
        """
        # 获取世界坐标 footprint
        footprint = self.collision.get_world_footprint(furniture)
        if not footprint:
            return

        # 转换为屏幕坐标
        screen_points = [camera.world_to_screen((px, py)) for px, py in footprint]

        # 计算bounding box
        min_x = min(p[0] for p in screen_points)
        min_y = min(p[1] for p in screen_points)
        max_x = max(p[0] for p in screen_points)
        max_y = max(p[1] for p in screen_points)

        # 添加边距
        padding = 10
        bbox_x = int(min_x - padding)
        bbox_y = int(min_y - padding)
        bbox_w = int(max_x - min_x + padding * 2)
        bbox_h = int(max_y - min_y + padding * 2)

        # 创建较小的半透明表面
        fp_surface = pygame.Surface((bbox_w, bbox_h), pygame.SRCALPHA)

        # 调整坐标到surface内
        local_points = [(p[0] - bbox_x, p[1] - bbox_y) for p in screen_points]

        # 检测当前位置是否可以放置（复用拖拽时的缓存结果）
        if hasattr(self, '_drag_can_place') and self._drag_furniture is furniture:
            can_place = self._drag_can_place
        else:
            all_objects = self.furniture_list + self.crop_list
            if furniture in all_objects:
                all_objects.remove(furniture)
            can_place = self.can_place_furniture(furniture, furniture.x, furniture.y, all_objects)

        # 选择颜色：绿色=可放置，红色=不可放置
        color = (0, 200, 0, 80) if can_place else (200, 0, 0, 80)
        border_color = (0, 200, 0, 200) if can_place else (200, 0, 0, 200)

        # 绘制填充多边形
        pygame.draw.polygon(fp_surface, color, local_points)
        # 绘制边框
        pygame.draw.polygon(fp_surface, border_color, local_points, 2)

        # 渲染到主屏幕
        screen.blit(fp_surface, (bbox_x, bbox_y))

    def _render_placeable_areas(self, screen, camera, furniture):
        """
        渲染家具的可放置区域（placeable_area）

        功能：显示 surface/surface_wall 类型家具的可放置平面区域
        """
        obj_type = getattr(furniture, 'obj_type', 'ground')
        if obj_type not in ('surface', 'surface_wall'):
            return

        # 获取可放置区域数据
        areas = self.collision.get_placeable_areas(furniture.furniture_id)
        if not areas:
            return

        # 创建半透明表面
        pa_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)

        # 渲染每个可放置区域
        for area in areas:
            points = area.get("points", [])
            if not points or len(points) < 3:
                continue

            # 计算世界坐标
            scale = Furniture.get_total_scale(furniture.furniture_id)
            img = Furniture._images.get(furniture.furniture_id)
            if img:
                img_w, img_h = img.get_size()
                rendered_w = img_w * scale
                rendered_h = img_h * scale
                offset_x = furniture.x - rendered_w / 2
                offset_y = furniture.y - rendered_h / 2
            else:
                offset_x = furniture.x
                offset_y = furniture.y

            is_flipped = getattr(furniture, 'is_flipped', False)
            if is_flipped:
                world_points = [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in points]
            else:
                world_points = [(offset_x + px * scale, offset_y + py * scale) for px, py in points]

            # 转换为屏幕坐标
            screen_points = [camera.world_to_screen((px, py)) for px, py in world_points]

            # 绘制紫色半透明多边形（可放置区域）
            pygame.draw.polygon(pa_surface, (180, 100, 255, 60), screen_points)
            pygame.draw.polygon(pa_surface, (180, 100, 255, 180), screen_points, 2)

        # 渲染到主屏幕
        screen.blit(pa_surface, (0, 0))
