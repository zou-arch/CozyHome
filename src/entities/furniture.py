"""
家具类 - 管理家具的属性和交互
"""
import pygame
import os
import json
from collections import OrderedDict

class Furniture:
    """家具类"""

    # 预加载的图片 {furniture_id: pygame.Surface}
    _images = {}
    _images_on = {}  # 开灯状态的图片 {furniture_id: pygame.Surface}
    _images_full = {}  # 蓄满水状态的图片 {furniture_id: pygame.Surface}
    _images_loaded = False

    # 缩放精灵图缓存（避免每帧 transform.scale，使用 OrderedDict 实现 LRU 淘汰）
    _scale_cache = OrderedDict()  # {(furniture_id, zoom_int, is_flipped, is_light_on): scaled_surface}

    # 编辑模式高亮缓存（避免每帧像素级操作）
    _edit_highlight_cache = {}  # {(furniture_id, zoom_int, is_flipped): highlight_surface}

    # 缩放比例（像素 → 游戏显示尺寸）
    SCALE = 0.1  # 10%缩放（增大至2倍）

    # 从配置文件加载的 scale（覆盖默认 SCALE）
    SCALE_CONFIG = {}  # {furniture_id: scale_value}

    # 特定家具的额外缩放倍率（在基础缩放基础上再调整）
    # 修改这里即可全局生效（渲染 + 碰撞检测）
    EXTRA_SCALE = {
        "storage_basket": 0.8,    # 篮子
        "piano": 1.5,             # 钢琴
        "bed": 1.8,               # 床
        "table_lamp": 0.8,        # 台灯
        "sofa": 1.3,              # 沙发
        "wardrobe": 1.8,          # 衣柜
        "bookshelf": 1.8,         # 书架
    }

    @classmethod
    def get_extra_scale(cls, furniture_id: str) -> float:
        """获取家具的额外缩放倍率（统一入口，渲染和碰撞检测都用这个）"""
        return cls.EXTRA_SCALE.get(furniture_id, 1.0)

    @classmethod
    def get_total_scale(cls, furniture_id: str) -> float:
        """获取家具的总缩放倍率（配置scale × 额外缩放）"""
        scale = cls.SCALE_CONFIG.get(furniture_id, cls.SCALE)
        return scale * cls.get_extra_scale(furniture_id)

    @classmethod
    def load_scale_config(cls):
        """从 data/furniture_configs.json 加载缩放配置（覆盖硬编码值）"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "furniture_configs.json")
        if not os.path.exists(config_path):
            return
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                configs = json.load(f)
            loaded_extra = 0
            loaded_scale = 0
            for item_id, cfg in configs.items():
                # 只处理 FURNITURE_DATA 中存在的家具
                if item_id not in cls.FURNITURE_DATA:
                    continue
                # 如果有 file_type 字段，跳过非家具
                file_type = cfg.get("file_type")
                if file_type is not None and file_type != "furniture":
                    continue
                # 加载 extra_scale
                extra = cfg.get("extra_scale")
                if extra is not None and extra != "":
                    cls.EXTRA_SCALE[item_id] = float(extra)
                    loaded_extra += 1
                # 加载 scale（覆盖默认的 SCALE）
                scale = cfg.get("scale")
                if scale is not None and scale != "":
                    cls.SCALE_CONFIG[item_id] = float(scale)
                    loaded_scale += 1
            if loaded_extra or loaded_scale:
                print(f"从 furniture_configs.json 加载: {loaded_extra} 个 extra_scale, {loaded_scale} 个 scale")
                # 调试：打印加载的配置
                for item_id in list(cls.SCALE_CONFIG.keys())[:5]:
                    print(f"  {item_id}: scale={cls.SCALE_CONFIG[item_id]}, extra={cls.EXTRA_SCALE.get(item_id, 1.0)}")
        except Exception as e:
            print(f"加载家具缩放配置失败: {e}")

    @classmethod
    def get_scaled_image(cls, furniture_id: str, zoom: float, is_flipped: bool = False, is_light_on: bool = False, is_water_full: bool = False):
        """获取缩放后的图片（带缓存）"""
        zoom_int = int(zoom * 100)
        cache_key = (furniture_id, zoom_int, is_flipped, is_light_on, is_water_full)

        if cache_key not in cls._scale_cache:
            # LRU 淘汰：超过限制时移除最旧的条目
            if len(cls._scale_cache) > 100:
                cls._scale_cache.popitem(last=False)

            # 选择图片（蓄满水时优先使用 _max 图片，开灯时优先使用 turn_on 图片）
            if is_water_full and furniture_id in cls._images_full:
                img = cls._images_full[furniture_id]
            elif is_light_on and furniture_id in cls._images_on:
                img = cls._images_on[furniture_id]
            else:
                img = cls._images.get(furniture_id)

            if img:
                # 镜像翻转
                render_img = img if not is_flipped else pygame.transform.flip(img, True, False)
                # 缩放
                img_w, img_h = img.get_size()
                total_scale = cls.get_total_scale(furniture_id)
                scaled_w = int(img_w * zoom * total_scale)
                scaled_h = int(img_h * zoom * total_scale)
                cls._scale_cache[cache_key] = pygame.transform.scale(render_img, (scaled_w, scaled_h))

        # 移到末尾（标记为最近使用）
        cls._scale_cache.move_to_end(cache_key)
        return cls._scale_cache.get(cache_key)

    @classmethod
    def get_edit_highlight(cls, furniture_id: str, zoom: float, is_flipped: bool):
        """获取编辑模式高亮覆盖层（带缓存）"""
        zoom_int = int(zoom * 100)
        cache_key = (furniture_id, zoom_int, is_flipped)

        if cache_key not in cls._edit_highlight_cache:
            # 缓存大小限制
            if len(cls._edit_highlight_cache) > 50:
                cls._edit_highlight_cache.clear()

            img = cls._images.get(furniture_id)
            if img:
                img_w, img_h = img.get_size()
                total_scale = cls.get_total_scale(furniture_id)
                scaled_w = max(1, int(img_w * zoom * total_scale))
                scaled_h = max(1, int(img_h * zoom * total_scale))
                scaled_sprite = pygame.transform.scale(img, (scaled_w, scaled_h))

                # 镜像翻转
                if is_flipped:
                    scaled_sprite = pygame.transform.flip(scaled_sprite, True, False)

                # 创建半透明黄色覆盖层
                highlight = pygame.Surface((scaled_w, scaled_h), pygame.SRCALPHA)
                highlight.fill((255, 200, 0, 70))
                # 用精灵图 alpha 做遮罩
                highlight.blit(scaled_sprite, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                # 恢复黄色 alpha
                highlight_array = pygame.surfarray.pixels_alpha(highlight)
                mask_array = pygame.surfarray.pixels_alpha(scaled_sprite)
                highlight_array[:] = mask_array
                del highlight_array, mask_array

                cls._edit_highlight_cache[cache_key] = highlight

        return cls._edit_highlight_cache.get(cache_key)

    @classmethod
    def load_all_images(cls):
        """预加载所有家具图片（保持原始尺寸，渲染时缩放）"""
        if cls._images_loaded:
            return
        sprites_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sprites", "furniture")
        if not os.path.exists(sprites_dir):
            print(f"家具图片目录不存在: {sprites_dir}")
            return

        # 扫描 sprites 目录中的所有 .png 文件
        all_files = os.listdir(sprites_dir)
        for fname in all_files:
            if not fname.endswith(".png"):
                continue
            # 跳过 _turn_on 和 F_floor_ 前缀的文件
            if "_turn_on" in fname or fname.startswith("F_"):
                continue

            ftype = fname.replace(".png", "")
            img_path = os.path.join(sprites_dir, fname)

            # 如果 FURNITURE_DATA 中没有这个家具，动态添加
            if ftype not in cls.FURNITURE_DATA:
                cls._add_furniture_from_config(ftype)

            # 加载图片
            try:
                img = pygame.image.load(img_path).convert_alpha()
                cls._images[ftype] = img
                # 更新碰撞尺寸为原始图片尺寸（渲染时再缩放）
                orig_w, orig_h = img.get_size()
                cls.FURNITURE_DATA[ftype]["width"] = orig_w
                cls.FURNITURE_DATA[ftype]["height"] = orig_h
            except Exception as e:
                print(f"加载家具图片失败: {img_path}, {e}")

            # 加载开灯状态图片（_turn_on 后缀）
            on_path = os.path.join(sprites_dir, f"{ftype}_turn_on.png")
            if os.path.exists(on_path):
                try:
                    cls._images_on[ftype] = pygame.image.load(on_path).convert_alpha()
                except Exception as e:
                    print(f"加载开灯图片失败: {on_path}, {e}")

            # 加载蓄满水状态图片（_max 后缀，用于蓄水器）
            full_path = os.path.join(sprites_dir, f"{ftype}_max.png")
            if os.path.exists(full_path):
                try:
                    cls._images_full[ftype] = pygame.image.load(full_path).convert_alpha()
                except Exception as e:
                    print(f"加载蓄满水图片失败: {full_path}, {e}")

        cls._images_loaded = True
        cls.load_scale_config()
        print(f"预加载家具图片: {len(cls._images)} 个, 开灯图片: {len(cls._images_on)} 个, 蓄满水图片: {len(cls._images_full)} 个")

    @classmethod
    def _add_furniture_from_config(cls, ftype: str):
        """从 furniture_configs.json 添加新家具配置"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "furniture_configs.json")
        if not os.path.exists(config_path):
            # 使用默认配置
            cls.FURNITURE_DATA[ftype] = {
                "name": ftype,
                "width": 40,
                "height": 40,
                "color": (128, 128, 128),
                "type": "ground"
            }
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                configs = json.load(f)

            if ftype in configs:
                cfg = configs[ftype]
                # 只处理家具类型
                file_type = cfg.get("file_type", "furniture")
                if file_type != "furniture":
                    return

                # 从配置中读取数据
                category = cfg.get("category", "ground")
                name_cn = cfg.get("name_cn", ftype)
                is_light = cfg.get("is_light", False)
                no_collision = cfg.get("no_collision", False)
                is_wall = cfg.get("is_wall", False)

                # 转换 category 到 type
                type_map = {
                    "ground": "ground",
                    "surface": "surface",
                    "surface_wall": "surface_wall",
                    "wall_surface": "wall_surface",
                    "wall_mount": "wall_mount"
                }
                obj_type = type_map.get(category, "ground")

                cls.FURNITURE_DATA[ftype] = {
                    "name": name_cn,
                    "width": 40,  # 会在加载图片时更新
                    "height": 40,
                    "color": (128, 128, 128),
                    "type": obj_type,
                    "is_light": is_light,
                    "no_collision": no_collision,
                    "is_wall": is_wall
                }
            else:
                # 配置文件中没有，使用默认配置
                cls.FURNITURE_DATA[ftype] = {
                    "name": ftype,
                    "width": 40,
                    "height": 40,
                    "color": (128, 128, 128),
                    "type": "ground"
                }
        except Exception as e:
            print(f"读取家具配置失败: {e}")
            # 使用默认配置
            cls.FURNITURE_DATA[ftype] = {
                "name": ftype,
                "width": 40,
                "height": 40,
                "color": (128, 128, 128),
                "type": "ground"
            }

    # 家具数据（尺寸为原始精灵图尺寸，load_all_images 会同步更新）
    FURNITURE_DATA = {
        # 纯地面家具（无placeable，无wall）
        "tv": {"name": "电视", "width": 35, "height": 39, "color": (50, 50, 50), "type": "ground", "shop_price": 300},
        "piano": {"name": "钢琴", "width": 36, "height": 40, "color": (20, 20, 20), "type": "ground", "shop_price": 400},
        "floor_lamp": {"name": "落地灯", "width": 15, "height": 44, "color": (100, 100, 100), "type": "ground", "is_light": True, "shop_price": 150},
        "storage_basket": {"name": "收纳篮", "width": 28, "height": 40, "color": (180, 150, 100), "type": "ground", "shop_price": 100},
        "rug": {"name": "地毯", "width": 38, "height": 37, "color": (220, 210, 190), "type": "ground", "no_collision": True, "shop_price": 80},
        "table_lamp": {"name": "台灯", "width": 14, "height": 37, "color": (100, 100, 100), "type": "ground", "is_light": True, "shop_price": 120},
        "waterstorage": {"name": "蓄水器", "width": 30, "height": 35, "color": (70, 130, 200), "type": "ground", "max_water": 400, "shop_price": 220},

        # 可放置平面（有placeable，无wall）
        "bed": {"name": "双人床", "width": 35, "height": 26, "color": (255, 250, 240), "type": "surface", "shop_price": 380},
        "chair": {"name": "椅子", "width": 26, "height": 43, "color": (160, 82, 45), "type": "surface", "shop_price": 200},
        "coffee_table": {"name": "茶几", "width": 27, "height": 24, "color": (120, 100, 80), "type": "surface", "shop_price": 200},
        "desk": {"name": "书桌", "width": 36, "height": 33, "color": (160, 120, 80), "type": "surface", "shop_price": 250},
        "flower_stand": {"name": "花架", "width": 26, "height": 36, "color": (80, 80, 80), "type": "surface", "shop_price": 180},
        "sofa": {"name": "沙发", "width": 37, "height": 29, "color": (178, 34, 34), "type": "surface", "shop_price": 350},

        # 可放置 + 可挂（有placeable + 有wall）
        "bookshelf": {"name": "书架", "width": 28, "height": 46, "color": (101, 67, 33), "type": "surface_wall", "shop_price": 280},
        "wardrobe": {"name": "衣柜", "width": 23, "height": 42, "color": (139, 69, 19), "type": "surface_wall", "shop_price": 320},

        # 墙面
        "wall": {"name": "通用墙", "width": 29, "height": 37, "color": (200, 200, 200), "type": "wall_surface"},

        # 挂饰类（只有wall，无placeable）
        "painting": {"name": "装饰画", "width": 27, "height": 29, "color": (70, 130, 180), "type": "wall_mount", "shop_price": 150},
    }

    # 从配置文件加载的描述 {furniture_id: description}
    _descriptions = {}

    @classmethod
    def get_description(cls, furniture_id: str) -> str:
        """获取家具描述"""
        # 先从配置文件加载的描述中查找
        if not cls._descriptions:
            cls._load_descriptions()
        return cls._descriptions.get(furniture_id, "装饰家具")

    @classmethod
    def _load_descriptions(cls):
        """加载家具描述配置"""
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "furniture_configs.json")
        if not os.path.exists(config_path):
            return
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                configs = json.load(f)
            for item_id, cfg in configs.items():
                desc = cfg.get("description")
                if desc:
                    cls._descriptions[item_id] = desc
        except Exception as e:
            pass

    def __init__(self, furniture_id: str, x: float, y: float):
        self.furniture_id = furniture_id
        self.x = x
        self.y = y

        # 获取家具数据
        data = self.FURNITURE_DATA.get(furniture_id, {})
        self.name = data.get("name", "未知家具")
        self.width = data.get("width", 40)
        self.height = data.get("height", 40)
        self.color = data.get("color", (128, 128, 128))
        self.obj_type = data.get("type", "ground")  # 物体类型
        self.is_light = data.get("is_light", False)  # 是否是光源
        self.no_collision = data.get("no_collision", False)  # 是否无碰撞（如地毯）

        # 蓄水器专属属性
        self.max_water = data.get("max_water", 0)  # 最大储水量（0表示不是蓄水器）
        self.water_stored = 0  # 当前储水量

        # 状态
        self.selected = False
        self.is_on = False  # 台灯等可开关的家具
        self.is_edit_mode = False  # 编辑模式下可拖拽
        self.is_flipped = False  # 左右镜像翻转

        # 拖拽状态
        self.is_dragging = False
        self.drag_offset = (0, 0)
        self.drag_start_pos = (x, y)

        # 矩形区域（x,y 是中心，rect 需要左上角）
        self.rect = pygame.Rect(x - self.width // 2, y - self.height // 2, self.width, self.height)

        # footprint（底部碰撞区域，相对于物体左上角的多边形顶点）
        self.footprint_points = []

    def handle_click(self, world_pos: tuple, game_manager=None):
        """处理点击交互"""
        x, y = world_pos
        if self.rect.collidepoint(x, y):
            # 根据家具类型执行不同交互
            if self.is_light:
                self.toggle_light()
            elif self.furniture_id == "piano":
                self.play_music()
            elif self.furniture_id == "tv":
                self.play_animation()
            elif self.furniture_id == "bed":
                self.rest()
            elif self.furniture_id == "waterstorage":
                self.collect_water(game_manager)
            return True
        return False

    def toggle_light(self):
        """开关灯"""
        self.is_on = not self.is_on
        print(f"{self.name} {'开灯' if self.is_on else '关灯'}")

    def play_music(self):
        """播放音乐"""
        print(f"{self.name} 播放音乐")

    def play_animation(self):
        """播放动画"""
        print(f"{self.name} 播放动画")

    def rest(self):
        """休息/存档"""
        print(f"{self.name} 休息/存档")

    def collect_water(self, game_manager=None):
        """收集蓄水器中的水"""
        if self.furniture_id != "waterstorage":
            return False

        if self.water_stored <= 0:
            print(f"{self.name} 还没有收集到雨水")
            return False

        if game_manager is None:
            print(f"{self.name} 无法收集：游戏管理器未绑定")
            return False

        # 收集水
        water_amount = self.water_stored
        self.water_stored = 0
        game_manager.water += water_amount
        print(f"{self.name} 收集了 {water_amount} 点水资源，当前水资源: {game_manager.water}")

        # 清除缩放缓存，确保下次渲染使用正确的图片
        Furniture._scale_cache.clear()
        return True

    def update_drag(self, mouse_pos: tuple):
        """
        更新拖拽位置（仅更新坐标，不做合法性检测）

        调用方式：由 input_handler.py 在拖拽时调用
        合法性检测：在 input_handler.py 中调用 can_place_furniture() 后才调用此函数
        """
        if self.is_dragging:
            self.x = mouse_pos[0] + self.drag_offset[0]
            self.y = mouse_pos[1] + self.drag_offset[1]
            self.rect.x = self.x - self.width // 2
            self.rect.y = self.y - self.height // 2

    def end_drag(self, collision_system=None, all_objects=None, world=None):
        """
        结束拖拽，检测最终位置是否合法

        调用方式：mouseup 时由 input_handler.py 调用
        检测逻辑：优先使用 world.can_place_furniture()（统一入口）
        不合法时：家具跳回原始位置 drag_start_pos
        """
        self.is_dragging = False

        if collision_system and all_objects:
            obj_type = getattr(self, 'obj_type', 'ground')
            center = (self.x + self.width / 2, self.y + self.height / 2)
            failed = False

            # 使用统一的 can_place_furniture 检测（如果 world 可用）
            if world and hasattr(world, 'can_place_furniture'):
                if not world.can_place_furniture(self, self.x, self.y, all_objects):
                    failed = True
            else:
                # 后备方案：使用旧的检测逻辑
                if obj_type == "wall_mount":
                    if not collision_system.check_wall_mount_placement(self, self.x, self.y, all_objects):
                        failed = True
                        print(f"放置失败: {self.name} 未在墙面区域内")

                elif obj_type in ('surface', 'surface_wall'):
                    surface_obj = collision_system.get_surface_under_point(center, all_objects, self)
                    if surface_obj:
                        if not collision_system.check_item_on_surface(self, surface_obj):
                            failed = True
                            print(f"放置失败: {self.name} 不在放置区域内")
                        elif collision_system.check_surface_items_collision(self, surface_obj, None, all_objects):
                            failed = True
                            print(f"放置失败: {self.name} 与表面上其他物体重叠")
                    else:
                        if collision_system.check_ground_placement(self, self.x, self.y, all_objects):
                            failed = True
                            print(f"放置失败: {self.name} 与其他地面物体重叠")

                else:
                    if collision_system.check_ground_placement(self, self.x, self.y, all_objects):
                        failed = True
                        print(f"放置失败: {self.name} 与其他物体重叠")

            # 检测失败时，家具跳回原始位置
            if failed:
                self.x = self.drag_start_pos[0]
                self.y = self.drag_start_pos[1]
            else:
                # 放置成功：依附的子物体跟着一起移动
                if hasattr(self, '_drag_attached_items') and self._drag_attached_items:
                    dx = self.x - self.drag_start_pos[0]
                    dy = self.y - self.drag_start_pos[1]
                    for child in self._drag_attached_items:
                        child.x += dx
                        child.y += dy
                        child.rect.x = child.x - child.width // 2
                        child.rect.y = child.y - child.height // 2
                print(f"放置成功: {self.name}")

            self.rect.x = self.x - self.width // 2
            self.rect.y = self.y - self.height // 2

    def start_drag(self, mouse_pos: tuple, collision_system=None, all_objects=None):
        """
        开始拖拽，记录原始位置和点击偏移

        记录内容：
        - drag_start_pos: 原始位置（用于失败时跳回）
        - drag_offset: 点击位置与家具中心的偏移（用于拖拽时保持相对位置）
        - _drag_attached_items: 依附于本家具的子物体（移动时跟着一起动）
        """
        if self.is_edit_mode:
            self.is_dragging = True
            self.drag_start_pos = (self.x, self.y)  # 记录原始位置
            self.drag_offset = (self.x - mouse_pos[0], self.y - mouse_pos[1])

            # 记录拖拽前依附于本家具的子物体（移动时跟着一起动）
            self._drag_attached_items = []
            if collision_system and all_objects:
                self._drag_attached_items = self.get_attached_items(all_objects, collision_system)

    def get_attached_items(self, all_objects, collision_system=None):
        """获取依附于本家具的物品（挂在墙上或放在表面上的）"""
        attached = []
        obj_type = getattr(self, 'obj_type', 'ground')

        if obj_type not in ('surface', 'surface_wall', 'wall_surface'):
            return attached

        if not collision_system:
            return attached

        for other in all_objects:
            if other is self:
                continue
            other_type = getattr(other, 'obj_type', 'ground')

            # 检查wall_mount类是否挂在本家具上
            if other_type == 'wall_mount':
                other_center = (other.x + other.width / 2, other.y + other.height / 2)
                if collision_system.point_in_wall_surface(self, other_center):
                    attached.append(other)

            # 检查小物件是否放在本家具上
            elif other_type in ('ground', 'surface', 'surface_wall'):
                other_center = (other.x + other.width / 2, other.y + other.height / 2)
                if collision_system.point_in_placeable_area(self, other_center):
                    attached.append(other)

        return attached

    def set_edit_mode(self, enabled: bool):
        """设置编辑模式"""
        self.is_edit_mode = enabled

    def set_footprint(self, points: list):
        """设置 footprint 多边形顶点（相对于物体左上角）"""
        self.footprint_points = points

    def flip(self):
        """左右镜像翻转"""
        self.is_flipped = not self.is_flipped
        print(f"{self.name} {'翻转' if self.is_flipped else '还原'}")

    def get_footprint_world(self) -> list:
        """获取世界坐标下的 footprint 顶点（自动应用缩放比例）"""
        # 使用总缩放倍率（基础缩放 × 额外缩放），渲染和碰撞统一
        scale = Furniture.get_total_scale(self.furniture_id)
        extra_scale = Furniture.get_extra_scale(self.furniture_id)
        # self.x, self.y 是精灵图中心，需要减去偏移（需要乘 total_scale 与渲染保持一致）
        img = self._images.get(self.furniture_id)
        if img:
            img_w, img_h = img.get_size()
            total_scale = Furniture.get_total_scale(self.furniture_id)
            rendered_w = img_w * total_scale
            rendered_h = img_h * total_scale
            offset_x = self.x - rendered_w / 2
            offset_y = self.y - rendered_h / 2
        else:
            offset_x = self.x
            offset_y = self.y

        if self.footprint_points:
            # 如果翻转，需要对原始像素坐标进行水平翻转
            if self.is_flipped:
                return [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in self.footprint_points]
            else:
                return [(offset_x + px * scale, offset_y + py * scale) for px, py in self.footprint_points]
        # 默认矩形
        return [
            (offset_x, offset_y),
            (offset_x + self.width, offset_y),
            (offset_x + self.width, offset_y + self.height),
            (offset_x, offset_y + self.height)
        ]

    def get_footprint_bottom_y(self) -> float:
        """获取 footprint 底部 Y 坐标（用于渲染排序）"""
        world_fp = self.get_footprint_world()
        if world_fp:
            return max(py for _, py in world_fp)
        return self.y + self.height

    def is_clicked_at(self, world_pos: tuple, camera) -> bool:
        """像素级点击检测：检查点击位置是否在精灵图非透明像素上"""
        # 蓄水器蓄满水时用 _max 图片做点击检测
        is_water_full = (self.furniture_id == "waterstorage" and
                        hasattr(self, 'water_stored') and
                        hasattr(self, 'max_water') and
                        self.water_stored >= self.max_water and
                        self.furniture_id in self._images_full)
        if is_water_full:
            img = self._images_full[self.furniture_id]
        # 开灯时用 turn_on 图片做点击检测
        elif self.is_light and self.is_on and self.furniture_id in self._images_on:
            img = self._images_on[self.furniture_id]
        else:
            img = self._images.get(self.furniture_id)
        if not img:
            # 无图片时退回矩形检测
            return self.rect.collidepoint(world_pos[0], world_pos[1])

        zoom = camera.zoom
        img_w, img_h = img.get_size()
        # 应用缩放倍率（基础缩放 × 额外缩放），与渲染保持一致
        total_scale = Furniture.get_total_scale(self.furniture_id)
        scaled_w = max(1, int(img_w * zoom * total_scale))
        scaled_h = max(1, int(img_h * zoom * total_scale))

        # 精灵图屏幕位置（与渲染一致，所有类型都居中对齐）
        screen_x, screen_y = camera.world_to_screen((self.x, self.y))
        draw_x = screen_x - scaled_w // 2
        draw_y = screen_y - scaled_h // 2

        # 屏幕点击 → 精灵图像素坐标
        click_sx, click_sy = camera.world_to_screen(world_pos)
        sprite_px = int((click_sx - draw_x) * img_w / scaled_w)
        sprite_py = int((click_sy - draw_y) * img_h / scaled_h)

        # 如果翻转，需要对 x 坐标进行水平镜像
        if self.is_flipped:
            sprite_px = img_w - 1 - sprite_px

        if 0 <= sprite_px < img_w and 0 <= sprite_py < img_h:
            return img.get_at((sprite_px, sprite_py)).a > 0
        return False

    def update(self):
        """更新"""
        pass

    def render(self, surface: pygame.Surface, camera, collision_system=None):
        """渲染家具"""
        # 计算屏幕位置（使用 world_to_screen）
        zoom = camera.zoom
        screen_x, screen_y = camera.world_to_screen((self.x, self.y))

        # 屏幕裁剪：跳过不在屏幕内的家具
        margin = 100  # 边距，确保部分在屏幕内也能渲染
        if (screen_x < -margin or screen_x > surface.get_width() + margin or
            screen_y < -margin or screen_y > surface.get_height() + margin):
            return  # 不在屏幕内，跳过渲染

        # 根据物体类型选择渲染方式
        if self.obj_type == "wall_surface":
            self._render_wall_surface(surface, screen_x, screen_y, 255, zoom)
        elif self.obj_type == "wall_mount":
            self._render_wall_mount(surface, screen_x, screen_y, 255, zoom)
        else:
            self._render_ground(surface, screen_x, screen_y, 255, zoom)

        # 选中时显示高光
        if self.selected:
            self._render_edit_mode(surface, screen_x, screen_y, camera, collision_system)

    def render_with_alpha(self, surface: pygame.Surface, camera, collision_system=None, alpha=128):
        """渲染家具（带透明度，用于宠物遮挡效果）"""
        # 计算屏幕位置
        zoom = camera.zoom
        screen_x, screen_y = camera.world_to_screen((self.x, self.y))

        # 获取缩放后的图片
        scaled_img = self.get_scaled_image(self.furniture_id, zoom, self.is_flipped)
        if not scaled_img:
            return

        # 创建带透明度的临时 Surface
        temp_surface = pygame.Surface(scaled_img.get_size(), pygame.SRCALPHA)
        temp_surface.blit(scaled_img, (0, 0))

        # 应用透明度
        temp_surface.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)

        # 渲染到目标 Surface
        scaled_w, scaled_h = temp_surface.get_size()
        draw_x = screen_x - scaled_w // 2
        draw_y = screen_y - scaled_h // 2
        surface.blit(temp_surface, (draw_x, draw_y))

    def _render_wall_surface(self, surface, screen_x, screen_y, alpha, zoom=1.0):
        """渲染墙面（使用预加载图片，按图片实际尺寸渲染）"""
        # 使用缓存的缩放图片
        scaled_img = self.get_scaled_image(self.furniture_id, zoom, self.is_flipped)
        if scaled_img:
            # 图片中心对齐到世界坐标（与其他类型物体保持一致）
            scaled_w, scaled_h = scaled_img.get_size()
            draw_x = screen_x - scaled_w // 2
            draw_y = screen_y - scaled_h // 2
            surface.blit(scaled_img, (draw_x, draw_y))
        else:
            # 没有图片，使用半透明填充
            w = int(self.width * zoom)
            h = int(self.height * zoom)
            wall_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            fill_color = (*self.color, 80)
            pygame.draw.rect(wall_surf, fill_color, (0, 0, w, h))
            surface.blit(wall_surf, (screen_x, screen_y))

        # 虚线边框（仅在编辑模式且没有图片时显示）
        if not scaled_img and self.is_edit_mode:
            border_color = (200, 200, 200)
            dash_length = 8
            w, h = self.width, self.height
            for start, end in [
                ((screen_x, screen_y), (screen_x + w, screen_y)),
                ((screen_x + w, screen_y), (screen_x + w, screen_y + h)),
                ((screen_x + w, screen_y + h), (screen_x, screen_y + h)),
                ((screen_x, screen_y + h), (screen_x, screen_y))
            ]:
                self._draw_dashed_line(surface, border_color, start, end, dash_length)

    def _render_wall_mount(self, surface, screen_x, screen_y, alpha, zoom=1.0):
        """渲染墙挂（使用预加载图片，按图片实际尺寸渲染）"""
        # 使用缓存的缩放图片
        scaled_img = self.get_scaled_image(self.furniture_id, zoom, self.is_flipped)
        if scaled_img:
            # 图片中心对齐到世界坐标
            scaled_w, scaled_h = scaled_img.get_size()
            draw_x = screen_x - scaled_w // 2
            draw_y = screen_y - scaled_h // 2
            surface.blit(scaled_img, (draw_x, draw_y))
        else:
            # 没有图片，使用纯色
            w = int(self.width * zoom)
            h = int(self.height * zoom)
            mount_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            shadow_color = (0, 0, 0, 60)
            pygame.draw.rect(mount_surf, shadow_color, (3, 3, w, h))
            color_with_alpha = (*self.color, alpha)
            pygame.draw.rect(mount_surf, color_with_alpha, (0, 0, w, h))
            surface.blit(mount_surf, (screen_x, screen_y))

    def _render_ground(self, surface, screen_x, screen_y, alpha, zoom=1.0):
        """渲染地面物体（使用预加载图片，按图片实际尺寸渲染）"""
        # 开灯时优先使用 turn_on 图片
        is_light_on = self.is_light and self.is_on and self.furniture_id in self._images_on
        # 蓄水器蓄满水时优先使用 _max 图片
        is_water_full = (self.furniture_id == "waterstorage" and
                        hasattr(self, 'water_stored') and
                        hasattr(self, 'max_water') and
                        self.water_stored >= self.max_water and
                        self.furniture_id in self._images_full)
        # 使用缓存的缩放图片（需要区分开灯/蓄满水状态）
        scaled_img = self.get_scaled_image(self.furniture_id, zoom, self.is_flipped, is_light_on, is_water_full)
        if scaled_img:
            # 图片中心对齐到世界坐标
            scaled_w, scaled_h = scaled_img.get_size()
            draw_x = screen_x - scaled_w // 2
            draw_y = screen_y - scaled_h // 2
            surface.blit(scaled_img, (draw_x, draw_y))
        else:
            # 没有图片，使用纯色矩形
            w = int(self.width * zoom)
            h = int(self.height * zoom)
            obj_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            color_with_alpha = (*self.color, alpha)
            pygame.draw.rect(obj_surf, color_with_alpha, (0, 0, w, h))
            surface.blit(obj_surf, (screen_x, screen_y))

    def _render_edit_mode(self, surface, screen_x, screen_y, camera, collision_system):
        """渲染编辑模式下的辅助显示（像素级高光 + footprint）"""
        zoom = camera.zoom

        # 使用缓存的高亮覆盖层
        highlight = self.get_edit_highlight(self.furniture_id, zoom, self.is_flipped)
        if highlight:
            scaled_w, scaled_h = highlight.get_size()
            # 定位（与渲染一致，所有类型都居中对齐）
            hl_x = screen_x - scaled_w // 2
            hl_y = screen_y - scaled_h // 2
            surface.blit(highlight, (hl_x, hl_y), special_flags=pygame.BLEND_RGBA_ADD)
        # 无图片时不画边框

    def _draw_dashed_line(self, surface, color, start, end, dash_length):
        """绘制虚线"""
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        length = (dx**2 + dy**2) ** 0.5
        if length == 0:
            return

        dx, dy = dx / length, dy / length
        drawn = 0
        while drawn < length:
            seg_end = min(drawn + dash_length, length)
            sx = x1 + dx * drawn
            sy = y1 + dy * drawn
            ex = x1 + dx * seg_end
            ey = y1 + dy * seg_end
            pygame.draw.line(surface, color, (int(sx), int(sy)), (int(ex), int(ey)), 2)
            drawn += dash_length * 2  # 跳过一段空白
