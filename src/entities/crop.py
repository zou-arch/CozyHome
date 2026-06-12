"""
作物类 - 管理作物的种植、生长和收获
"""
import pygame
import time
import os
from collections import OrderedDict

class Crop:
    """作物类"""

    # 精灵图缓存（类级别，所有实例共享）
    _sprite_cache = {}
    _sprites_loaded = False

    # 精灵图有效区域缓存（非透明像素的bounding box）
    _sprite_bbox_cache = {}  # {(crop_id, stage): (x, y, w, h)}

    # 缩放精灵图缓存（避免每帧 smoothscale，使用 OrderedDict 实现 LRU 淘汰）
    _sprite_scale_cache = OrderedDict()  # {(crop_id, stage, zoom_int, scale_int): scaled_surface}

    # 枯萎覆盖层缓存（避免每帧像素级操作）
    _wither_cache = {}  # {(crop_id, stage, zoom_int): gray_surface}

    # 高亮覆盖层缓存（避免每帧像素级操作）
    _highlight_cache = {}  # {(crop_id, stage, zoom_int): highlight_surface}

    @classmethod
    def load_all_sprites(cls):
        """加载所有作物精灵图（只执行一次）"""
        if cls._sprites_loaded:
            return

        sprites_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sprites", "crops")
        stage_names = ["stage0", "stage1", "stage2", "stage3"]

        # 确保pygame display已初始化
        if not pygame.display.get_active():
            pygame.display.set_mode((1, 1))

        # 扫描 sprites 目录，发现新的植物
        if os.path.exists(sprites_dir):
            all_files = os.listdir(sprites_dir)
            # 收集所有 stage0 文件，提取植物 ID
            stage0_files = [f for f in all_files if f.endswith("_stage0.png")]
            for stage0_file in stage0_files:
                crop_id = stage0_file.replace("_stage0.png", "")
                # 检查是否同时存在 stage1/2/3
                all_stages_exist = True
                for stage_name in stage_names[1:]:  # 跳过 stage0
                    stage_file = f"{crop_id}_{stage_name}.png"
                    if stage_file not in all_files:
                        all_stages_exist = False
                        break

                # 如果4个状态都完整且不在 CROP_DATA 中，自动添加
                if all_stages_exist and crop_id not in cls.CROP_DATA:
                    cls._add_crop_from_config(crop_id)

        # 加载所有植物的精灵图
        for crop_id in cls.CROP_DATA:
            cls._sprite_cache[crop_id] = []
            for stage_idx, stage_name in enumerate(stage_names):
                file_path = os.path.join(sprites_dir, f"{crop_id}_{stage_name}.png")
                if os.path.exists(file_path):
                    try:
                        img = pygame.image.load(file_path).convert_alpha()
                        cls._sprite_cache[crop_id].append(img)
                    except Exception as e:
                        print(f"加载精灵图失败: {file_path}, {e}")
                        cls._sprite_cache[crop_id].append(None)
                else:
                    cls._sprite_cache[crop_id].append(None)

        cls._sprites_loaded = True
        loaded = sum(1 for v in cls._sprite_cache.values() if any(s is not None for s in v))
        print(f"作物精灵图加载完成: {loaded}/{len(cls._sprite_cache)} 种作物有精灵图")

    @classmethod
    def _add_crop_from_config(cls, crop_id: str):
        """从 furniture_configs.json 添加新植物配置"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "furniture_configs.json")
        if not os.path.exists(config_path):
            # 使用默认配置
            cls.CROP_DATA[crop_id] = {
                "name": crop_id,
                "type": 0,  # 土生
                "growth_time": 1.5,
                "sell_price": 10,
                "seed_price": 5,
                "color": (100, 200, 100),
                "water_rate": 8
            }
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                configs = json.load(f)

            if crop_id in configs:
                cfg = configs[crop_id]
                # 只处理植物类型
                file_type = cfg.get("file_type", "crop")
                if file_type != "crop":
                    return

                # 从配置中读取数据
                name_cn = cfg.get("name_cn", crop_id)
                crop_type_str = cfg.get("crop_type", "soil")
                growth_time = float(cfg.get("growth_time", 1.5))
                sell_price = int(cfg.get("sell_price", 10))
                seed_price = int(cfg.get("seed_price", 5))
                water_rate = int(cfg.get("water_rate", 8))

                # 转换 crop_type 字符串到数字
                type_map = {
                    "soil": 0,   # 土生
                    "water": 1,  # 水生
                    "pot": 2,    # 盆栽
                    "sand": 3    # 沙生
                }
                crop_type = type_map.get(crop_type_str, 0)

                # 默认颜色（可以从配置中读取）
                color = (100, 200, 100)

                cls.CROP_DATA[crop_id] = {
                    "name": name_cn,
                    "type": crop_type,
                    "growth_time": growth_time,
                    "sell_price": sell_price,
                    "seed_price": seed_price,
                    "color": color,
                    "water_rate": water_rate
                }
                print(f"从配置添加植物: {crop_id} ({name_cn})")
            else:
                # 配置文件中没有，使用默认配置
                cls.CROP_DATA[crop_id] = {
                    "name": crop_id,
                    "type": 0,
                    "growth_time": 1.5,
                    "sell_price": 10,
                    "seed_price": 5,
                    "color": (100, 200, 100),
                    "water_rate": 8
                }
                print(f"使用默认配置添加植物: {crop_id}")
        except Exception as e:
            print(f"读取植物配置失败: {e}")
            # 使用默认配置
            cls.CROP_DATA[crop_id] = {
                "name": crop_id,
                "type": 0,
                "growth_time": 1.5,
                "sell_price": 10,
                "seed_price": 5,
                "color": (100, 200, 100),
                "water_rate": 8
            }

    @classmethod
    def _compute_sprite_bbox(cls, sprite: pygame.Surface) -> tuple:
        """计算精灵图的有效区域（非透明像素的bounding box）
        返回: (x, y, width, height) 或 None（如果全透明）
        """
        if sprite is None:
            return None

        # 获取alpha通道
        try:
            alpha = pygame.surfarray.array_alpha(sprite)
        except Exception:
            return None

        # 找到非透明像素的行和列
        # surfarray.array_alpha 返回 shape (width, height)
        alpha = pygame.surfarray.array_alpha(sprite)

        # axis=0 沿 height 方向求最大 → 每个 x 是否有非透明像素
        x_mask = alpha.max(axis=0) > 0
        if not x_mask.any():
            return None  # 全透明

        # axis=1 沿 width 方向求最大 → 每个 y 是否有非透明像素
        y_mask = alpha.max(axis=1) > 0

        # 计算 bounding box (x_min, y_min, width, height)
        x_min = int(x_mask.argmax())
        x_max = int(len(x_mask) - 1 - x_mask[::-1].argmax())
        y_min = int(y_mask.argmax())
        y_max = int(len(y_mask) - 1 - y_mask[::-1].argmax())

        # 安全裁剪：确保不超出图片范围
        spr_w, spr_h = sprite.get_size()
        x_min = max(0, min(x_min, spr_w - 1))
        x_max = max(x_min, min(x_max, spr_w - 1))
        y_min = max(0, min(y_min, spr_h - 1))
        y_max = max(y_min, min(y_max, spr_h - 1))

        return (x_min, y_min, x_max - x_min + 1, y_max - y_min + 1)

    @classmethod
    def get_sprite_bbox(cls, crop_id: str, stage: int) -> tuple:
        """获取精灵图的有效区域（带缓存）"""
        cache_key = (crop_id, stage)
        if cache_key not in cls._sprite_bbox_cache:
            sprites = cls._sprite_cache.get(crop_id, [])
            if stage < len(sprites) and sprites[stage] is not None:
                bbox = cls._compute_sprite_bbox(sprites[stage])
                cls._sprite_bbox_cache[cache_key] = bbox
            else:
                cls._sprite_bbox_cache[cache_key] = None
        return cls._sprite_bbox_cache[cache_key]

    # 作物数据
    # type: 0=土生, 1=水生, 2=盆栽, 3=沙生
    # growth_time: 每阶段所需小时数
    # water_rate: 每小时水分消耗量（水生=0永久湿润）
    CROP_DATA = {
        # 土生作物 (water_rate=8)
        "tomato": {"name": "番茄", "type": 0, "growth_time": 1.5, "sell_price": 14, "seed_price": 5, "color": (255, 99, 71), "water_rate": 8},
        "carrot": {"name": "胡萝卜", "type": 0, "growth_time": 1.5, "sell_price": 10, "seed_price": 3, "color": (255, 140, 0), "water_rate": 8},
        "pumpkin": {"name": "南瓜", "type": 0, "growth_time": 2.0, "sell_price": 25, "seed_price": 8, "color": (255, 165, 0), "water_rate": 8},
        "sunflower": {"name": "向日葵", "type": 0, "growth_time": 1.5, "sell_price": 18, "seed_price": 6, "color": (255, 215, 0), "water_rate": 8},
        "rose": {"name": "玫瑰", "type": 0, "growth_time": 2.5, "sell_price": 32, "seed_price": 10, "color": (255, 0, 128), "water_rate": 8},
        "strawberry": {"name": "草莓", "type": 0, "growth_time": 1.5, "sell_price": 17, "seed_price": 6, "color": (220, 20, 60), "water_rate": 8},
        # 水生作物 (water_rate=0，永久湿润)
        "lotus": {"name": "荷花", "type": 1, "growth_time": 2.0, "sell_price": 38, "seed_price": 12, "color": (255, 182, 193), "water_rate": 0},
        "waterlily": {"name": "睡莲", "type": 1, "growth_time": 2.0, "sell_price": 22, "seed_price": 8, "color": (144, 238, 144), "water_rate": 0},
        # 盆栽作物 (water_rate=10)
        "succulent": {"name": "多肉", "type": 2, "growth_time": 3.0, "sell_price": 48, "seed_price": 15, "color": (107, 142, 35), "water_rate": 10},
        "cactus": {"name": "仙人掌", "type": 2, "growth_time": 3.0, "sell_price": 55, "seed_price": 18, "color": (34, 139, 34), "water_rate": 10},
        # 沙生作物 (water_rate=6)
        "aloe": {"name": "芦荟", "type": 3, "growth_time": 2.0, "sell_price": 28, "seed_price": 10, "color": (50, 205, 50), "water_rate": 6},
        "sandthorn": {"name": "沙棘", "type": 3, "growth_time": 2.5, "sell_price": 40, "seed_price": 14, "color": (255, 140, 0), "water_rate": 6},
    }

    # 生长阶段
    STAGE_COLORS = [
        (139, 90, 43),    # 种子：棕色
        (100, 200, 100),  # 幼苗：浅绿
        (50, 150, 50),    # 成长：深绿
        (255, 100, 100),  # 成熟：红色
    ]

    # 统一缩放因子定义
    BASE_SCALE = 0.85  # 基础缩放因子
    SPECIAL_SCALE = {
        "bonsai": 0.75,           # 盆栽类型
        "aquatic_grown": 1.0,     # 水生成长期（stage > 0）
        "seed_large": 0.75,       # 大种子（胡萝卜、番茄）
        "seed_small": 0.25,       # 小种子（其他）
    }
    # 大种子列表
    LARGE_SEED_CROPS = ["carrot", "tomato"]

    # 从配置文件加载的 scale（覆盖默认值）
    SCALE_CONFIG = {}  # {crop_id: scale_value}

    @classmethod
    def load_scale_config(cls):
        """从 data/furniture_configs.json 加载缩放配置（覆盖硬编码值）"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "furniture_configs.json")
        if not os.path.exists(config_path):
            return
        try:
            import json
            with open(config_path, "r", encoding="utf-8") as f:
                configs = json.load(f)
            loaded = 0
            for item_id, cfg in configs.items():
                # 只处理已有图片的作物
                if item_id not in cls._sprite_cache:
                    continue
                file_type = cfg.get("file_type")
                if file_type is not None and file_type != "crop":
                    continue
                # 加载 scale
                scale = cfg.get("scale")
                if scale is not None and scale != "":
                    cls.SCALE_CONFIG[item_id] = float(scale)
                    loaded += 1
            if loaded:
                print(f"从 furniture_configs.json 加载 {loaded} 个作物缩放配置")
        except Exception as e:
            print(f"加载作物缩放配置失败: {e}")

    @classmethod
    def get_scale(cls, crop_id: str, crop_type: int, stage: int) -> float:
        """获取作物的缩放因子（统一入口）"""
        # 优先使用配置文件中的 scale
        if crop_id in cls.SCALE_CONFIG:
            return cls.SCALE_CONFIG[crop_id]
        # 盆栽类型
        if crop_type == 2:
            return cls.SPECIAL_SCALE["bonsai"]
        # 水生且已过种子阶段
        if crop_type == 1 and stage > 0:
            return cls.SPECIAL_SCALE["aquatic_grown"]
        # 种子阶段（stage 0）
        if stage == 0:
            if crop_id in cls.LARGE_SEED_CROPS:
                return cls.SPECIAL_SCALE["seed_large"]
            else:
                return cls.SPECIAL_SCALE["seed_small"]
        # 其他情况使用基础缩放
        return cls.BASE_SCALE

    @classmethod
    def get_scaled_sprite(cls, crop_id: str, stage: int, zoom: float, scale: float):
        """获取缩放后的精灵图（带缓存）"""
        zoom_int = int(zoom * 100)
        scale_int = int(scale * 100)
        cache_key = (crop_id, stage, zoom_int, scale_int)

        if cache_key not in cls._sprite_scale_cache:
            # LRU 淘汰：超过限制时移除最旧的条目
            if len(cls._sprite_scale_cache) > 200:
                cls._sprite_scale_cache.popitem(last=False)

            sprites = cls._sprite_cache.get(crop_id, [])
            if stage < len(sprites) and sprites[stage] is not None:
                sprite = sprites[stage]
                target_w = int(40 * zoom * scale)
                sprite_ratio = sprite.get_height() / sprite.get_width()
                sprite_w = max(1, target_w)
                sprite_h = max(1, int(sprite_w * sprite_ratio))
                cls._sprite_scale_cache[cache_key] = pygame.transform.smoothscale(sprite, (sprite_w, sprite_h))

        # 移到末尾（标记为最近使用）
        cls._sprite_scale_cache.move_to_end(cache_key)
        return cls._sprite_scale_cache.get(cache_key)

    @classmethod
    def get_wither_overlay(cls, crop_id: str, stage: int, zoom: float, scale: float):
        """获取枯萎覆盖层（带缓存）"""
        zoom_int = int(zoom * 100)
        cache_key = (crop_id, stage, zoom_int)

        if cache_key not in cls._wither_cache:
            # 缓存大小限制
            if len(cls._wither_cache) > 50:
                cls._wither_cache.clear()

            scaled_sprite = cls.get_scaled_sprite(crop_id, stage, zoom, scale)
            if scaled_sprite:
                gw, gh = scaled_sprite.get_size()
                # 创建黑色半透明覆盖层（像素级，使用精灵图alpha作为遮罩）
                gray_surface = pygame.Surface((gw, gh), pygame.SRCALPHA)
                # 复制精灵图的alpha通道，RGB设为黑色，alpha设为50%
                sprite_alpha = pygame.surfarray.array_alpha(scaled_sprite)
                gray_array = pygame.surfarray.pixels_alpha(gray_surface)
                gray_array[:] = (sprite_alpha * 0.5).astype(int)
                del gray_array
                gray_rgb = pygame.surfarray.pixels3d(gray_surface)
                gray_rgb[:] = 0  # 黑色
                del gray_rgb
                cls._wither_cache[cache_key] = gray_surface

        return cls._wither_cache.get(cache_key)

    @classmethod
    def get_highlight_overlay(cls, crop_id: str, stage: int, zoom: float, scale: float):
        """获取高亮覆盖层（带缓存）"""
        zoom_int = int(zoom * 100)
        cache_key = (crop_id, stage, zoom_int)

        if cache_key not in cls._highlight_cache:
            # 缓存大小限制
            if len(cls._highlight_cache) > 50:
                cls._highlight_cache.clear()

            scaled_sprite = cls.get_scaled_sprite(crop_id, stage, zoom, scale)
            if scaled_sprite:
                sprite_w, sprite_h = scaled_sprite.get_size()
                # 创建半透明黄色覆盖层（仅覆盖非透明像素）
                highlight = pygame.Surface((sprite_w, sprite_h), pygame.SRCALPHA)
                highlight.fill((255, 255, 0, 80))  # 半透明黄色
                # 使用精灵图的alpha通道作为遮罩
                highlight.blit(scaled_sprite, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                # 重新应用黄色（因为BLEND_RGBA_MULT会变暗）
                highlight_array = pygame.surfarray.pixels_alpha(highlight)
                mask_array = pygame.surfarray.pixels_alpha(scaled_sprite)
                highlight_array[:] = mask_array  # 使用原图alpha
                del highlight_array, mask_array
                cls._highlight_cache[cache_key] = highlight

        return cls._highlight_cache.get(cache_key)

    def __init__(self, crop_id: str, x: float, y: float):
        self.crop_id = crop_id
        self.x = x
        self.y = y

        # 获取作物数据
        data = self.CROP_DATA.get(crop_id, {})
        self.name = data.get("name", "未知作物")
        self.type = data.get("type", 0)  # 0=土生, 1=水生, 2=盆栽, 3=沙生
        self.growth_time = data.get("growth_time", 1.5)
        self.sell_price = data.get("sell_price", 10)
        self.color = data.get("color", (100, 200, 100))
        self.water_rate = data.get("water_rate", 8)  # 每小时水分消耗

        # 生长状态
        self.current_stage = 0  # 0-3
        self.growth_progress = 0.0  # 0.0-1.0
        self.start_time = time.time()

        # 水分系统
        self.water_level = 0.0 if self.type == 1 else 80.0  # 水生永久湿润，其他初始80
        self.last_water_update = time.time()  # 上次水分更新时间

        # 状态
        self.selected = False
        self.is_fertilized = False

        # 尺寸（与渲染保持一致：基础宽度40像素，居中底部对齐）
        self.width = 40
        self.height = 40

        # 矩形区域（用于点击检测，不缩放，保持世界坐标）
        # rect 左上角 = 作物中心 - 宽度/2，底部 = 作物中心 + 10（与渲染一致）
        self.rect = pygame.Rect(x - self.width // 2, y - self.height // 2, self.width, self.height)

        # footprint（底部碰撞区域）
        self.footprint_points = [
            (-self.width // 2, -self.height // 4),
            (self.width // 2, -self.height // 4),
            (self.width // 2, self.height // 4),
            (-self.width // 2, self.height // 4)
        ]

    def handle_click(self, world_pos: tuple, camera=None) -> bool:
        """处理点击交互（像素级检测，只命中实际渲染区域）"""
        if camera is None:
            return self.rect.collidepoint(world_pos[0], world_pos[1])

        # 获取当前阶段的精灵图
        sprites = self._sprite_cache.get(self.crop_id, [])
        if self.current_stage >= len(sprites) or sprites[self.current_stage] is None:
            return self.rect.collidepoint(world_pos[0], world_pos[1])

        sprite = sprites[self.current_stage]

        # 获取统一缩放因子
        zoom = camera.zoom
        scale = self.get_scale(self.crop_id, self.type, self.current_stage)

        # 精灵图在屏幕上的位置
        target_w = max(1, int(40 * zoom * scale))
        sprite_ratio = sprite.get_height() / sprite.get_width()
        target_h = max(1, int(target_w * sprite_ratio))

        # 使用 camera.world_to_screen 计算屏幕坐标
        screen_x, screen_y = camera.world_to_screen((self.x, self.y))

        # 精灵图左上角（居中，底部对齐）
        sprite_left = screen_x - target_w // 2
        sprite_top = screen_y + 10 * zoom - target_h

        # 屏幕点击坐标 → 缩放后的精灵图像素坐标
        click_screen_x, click_screen_y = camera.world_to_screen(world_pos)
        sprite_px = int((click_screen_x - sprite_left) * sprite.get_width() / target_w)
        sprite_py = int((click_screen_y - sprite_top) * sprite.get_height() / target_h)

        # 检查是否在精灵图范围内
        if 0 <= sprite_px < sprite.get_width() and 0 <= sprite_py < sprite.get_height():
            alpha = sprite.get_at((sprite_px, sprite_py)).a
            if alpha > 0:
                return True

        return False

    def get_footprint_world(self) -> list:
        """获取世界坐标下的 footprint"""
        if self.footprint_points:
            return [(self.x + px, self.y + py) for px, py in self.footprint_points]
        return [
            (self.x - self.width // 2, self.y - self.height // 4),
            (self.x + self.width // 2, self.y - self.height // 4),
            (self.x + self.width // 2, self.y + self.height // 4),
            (self.x - self.width // 2, self.y + self.height // 4)
        ]

    def get_footprint_bottom_y(self) -> float:
        """获取 footprint 底部 Y"""
        world_fp = self.get_footprint_world()
        if world_fp:
            return max(py for _, py in world_fp)
        return self.y + self.height // 4

    def is_near_water(self, world) -> bool:
        """检查是否旁边有水生区块"""
        import math
        grid_x, grid_y = world.world_to_grid(self.x, self.y)
        grid_x, grid_y = math.floor(grid_x), math.floor(grid_y)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = grid_x + dx, grid_y + dy
            farm_type = world.farm_styles.get((nx, ny), -1)
            if farm_type == 1:  # 水生
                return True
        return False

    def water(self, amount: int = 40):
        """浇水"""
        if self.current_stage < 3 and self.type != 1:
            self.water_level = min(100, self.water_level + amount)
            print(f"{self.name} 浇水 +{amount}，当前水分 {self.water_level:.0f}")

    def fertilize(self):
        """施肥"""
        if self.current_stage < 3:
            self.is_fertilized = True
            print(f"{self.name} 施肥完成")

    def harvest(self) -> dict:
        """收获作物"""
        if self.current_stage == 3:
            print(f"{self.name} 收获成功！获得 {self.sell_price} 代币")
            return {"crop_id": self.crop_id, "crop_name": self.name, "amount": 1, "sell_price": self.sell_price}
        else:
            print(f"{self.name} 还未成熟")
            return {}

    def update(self, world=None):
        """更新生长状态（growth_time = 每阶段所需小时数，基于系统时间）"""
        now = time.time()

        # 水分消耗（基于系统时间）
        if self.type != 1 and self.current_stage < 3:  # 水生不消耗
            hours_elapsed = (now - self.last_water_update) / 3600
            water_rate = self.water_rate
            # 水源加成：旁边是水生区，消耗减半
            if world and self.is_near_water(world):
                water_rate *= 0.5
            self.water_level = max(0, self.water_level - water_rate * hours_elapsed)
        self.last_water_update = now

        if self.current_stage >= 3:
            return

        # 计算生长进度
        elapsed_seconds = now - self.start_time
        growth_rate = 1.0

        # 水分对生长率的影响
        if self.water_level >= 80:
            growth_rate += 0.3  # 湿润 +30%
        elif self.water_level >= 40:
            growth_rate += 0.15  # 正常 +15%
        elif self.water_level > 0:
            growth_rate -= 0.2  # 干渴 -20%
        else:
            # 枯萎：停止生长，保持当前阶段
            return

        # 施肥加速
        if self.is_fertilized:
            growth_rate += 0.5  # 施肥 +50%

        stage_seconds = self.growth_time * 3600
        total_elapsed = elapsed_seconds * growth_rate
        stage_progress = total_elapsed / stage_seconds
        new_stage = min(3, int(stage_progress))

        self.current_stage = new_stage
        self.growth_progress = min(1.0, stage_progress % 1.0) if new_stage < 3 else 1.0

    def render(self, surface: pygame.Surface, camera):
        """渲染作物"""
        # 计算屏幕位置（使用 world_to_screen）
        zoom = camera.zoom
        screen_x, screen_y = camera.world_to_screen((self.x, self.y))

        # 屏幕裁剪：跳过不在屏幕内的作物
        margin = 50
        if (screen_x < -margin or screen_x > surface.get_width() + margin or
            screen_y < -margin or screen_y > surface.get_height() + margin):
            return  # 不在屏幕内，跳过渲染

        # 尝试使用精灵图渲染（带缓存）
        scale = self.get_scale(self.crop_id, self.type, self.current_stage)
        scaled_sprite = self.get_scaled_sprite(self.crop_id, self.current_stage, zoom, scale)

        if scaled_sprite:
            sprite_rect = scaled_sprite.get_rect(centerx=screen_x, bottom=screen_y + 10 * zoom)
            surface.blit(scaled_sprite, sprite_rect)
        else:
            # 回退到程序化绘制
            stage_color = self.STAGE_COLORS[self.current_stage]
            cx = int(screen_x)
            cy = int(screen_y)
            if self.current_stage == 0:
                pygame.draw.circle(surface, stage_color, (cx, cy + 8), int(3 * zoom))
            elif self.current_stage == 1:
                pygame.draw.rect(surface, stage_color, (cx - 2, cy - 5, 4, 10))
                pygame.draw.circle(surface, (50, 150, 50), (cx, cy - 8), int(5 * zoom))
            elif self.current_stage == 2:
                pygame.draw.rect(surface, (101, 67, 33), (cx - 1, cy - 10, 3, 15))
                pygame.draw.circle(surface, stage_color, (cx, cy - 12), int(8 * zoom))
            else:
                pygame.draw.rect(surface, (101, 67, 33), (cx - 1, cy - 10, 3, 15))
                pygame.draw.circle(surface, self.color, (cx, cy - 12), int(10 * zoom))

        # 绘制缺水图标（水分≤20%时，在footprint上方显示）
        if self.type != 1 and self.current_stage < 3 and self.water_level <= 20:
            icon_y = screen_y - 20 * zoom
            icon_x = screen_x
            # 水滴图标
            if self.water_level == 0:
                # 枯萎：灰色水滴
                color = (150, 150, 150)
            else:
                # 缺水：蓝色水滴
                color = (100, 150, 255)
            # 绘制水滴形状
            drop_size = int(6 * zoom)
            points = [
                (icon_x, icon_y - drop_size),
                (icon_x - drop_size * 0.6, icon_y + drop_size * 0.3),
                (icon_x + drop_size * 0.6, icon_y + drop_size * 0.3),
            ]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, (50, 50, 50), points, 1)

        # 枯萎时：给精灵图叠加黑色（像素级，仅覆盖非透明像素）
        if self.water_level == 0 and self.current_stage < 3 and self.type != 1:
            # 使用缓存的枯萎覆盖层
            gs = self.get_scale(self.crop_id, self.type, self.current_stage)
            gray_surface = self.get_wither_overlay(self.crop_id, self.current_stage, zoom, gs)

            if gray_surface:
                gray_rect = gray_surface.get_rect(centerx=screen_x, bottom=screen_y + 10 * zoom)
                surface.blit(gray_surface, gray_rect)
