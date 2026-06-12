"""
宠物类 - 管理宠物的属性、行为和交互
"""
import pygame
import math
import random
import time
import os
import json
from collections import OrderedDict


class Pet:
    """宠物类"""

    # 预加载的图片 {pet_id: {state: [frame0, frame1, ...]}}
    _images = {}
    _images_loaded = False

    # 预加载的 footprint 数据 {pet_id: [[x,y], ...]}
    _footprints = {}
    _footprints_loaded = False

    # 缩放精灵图缓存（避免每帧 transform.scale）
    _scale_cache = OrderedDict()  # {(pet_id, state, frame_idx, zoom_int): scaled_surface}

    # 精灵图有效区域缓存（非透明像素的bounding box）
    _bbox_cache = {}  # {(pet_id, state, frame_idx): (x, y, w, h)}

    # 宠物数据（从 pet_config.json 加载，类似 Crop.CROP_DATA）
    PET_DATA = {}  # {pet_id: {"name": "金毛犬", "shop_price": 200, "intro": "..."}}

    # 基础缩放（统一）
    SCALE = 0.15  # 15%缩放

    # 从配置文件加载的 scale（覆盖默认 SCALE）
    SCALE_CONFIG = {}  # {pet_id: scale_value}

    # 额外缩放（因宠物而异）
    EXTRA_SCALE = {
        "golden_retriever": 0.6,   # 金毛犬
        "blue_cat": 0.4,           # 蓝猫
        "rabbit": 0.35,             # 兔子
        "hamster": 0.3,            # 仓鼠
        "chick": 0.4,              # 小鸡
        "penguin": 0.4,            # 小企鹅
    }

    # 默认移动速度
    DEFAULT_SPEED = 1.0

    # 动画帧率
    ANIMATION_FPS = 8  # 每秒8帧

    # 默认配置（pet_config.json 不存在时使用）
    _DEFAULT_PET_CONFIG = {
        "golden_retriever": {
            "states": ["idle", "walk", "run", "hungry", "sleep", "roll", "tongueidle", "special"],
            "level_unlocks": {
                0: ["idle", "walk", "run", "hungry", "sleep"],
                2: ["tongueidle"],
                3: ["roll"],
                5: ["special"],
            },
            "state_config": {
                "idle": {"fps": 18, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "walk": {"fps": 8, "loop": True, "offset_x": -15, "offset_y": 3, "scale": 1.0},
                "run": {"fps": 12, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "hungry": {"fps": 6, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "sleep": {"fps": 4, "loop": True, "loop_start": 0, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "roll": {"fps": 12, "loop": True, "offset_x": -12, "offset_y": 12, "scale": 1.0},
                "tongueidle": {"fps": 6, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "special": {"fps": 10, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            },
        },
        "blue_cat": {
            "states": ["idle", "walk", "hungry", "sleep", "happy"],
            "level_unlocks": {
                0: ["idle", "walk", "hungry"],
                1: ["sleep"],
                3: ["happy"],
            },
            "state_config": {
                "idle": {"fps": 6, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "walk": {"fps": 8, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "hungry": {"fps": 6, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "sleep": {"fps": 4, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "happy": {"fps": 10, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            },
        },
        "rabbit": {
            "states": ["idle", "walk", "hungry", "sleep"],
            "level_unlocks": {
                0: ["idle", "walk", "hungry"],
                1: ["sleep"],
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
                0: ["idle", "walk", "hungry"],
                1: ["sleep"],
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
                0: ["idle", "walk", "hungry"],
                1: ["sleep"],
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
                0: ["idle", "walk", "hungry"],
                1: ["sleep"],
                3: ["roll"],
            },
            "state_config": {
                "idle": {"fps": 6, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "walk": {"fps": 8, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "hungry": {"fps": 6, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "sleep": {"fps": 4, "loop": True, "offset_x": 0, "offset_y": 0, "scale": 1.0},
                "roll": {"fps": 12, "loop": False, "offset_x": 0, "offset_y": 0, "scale": 1.0},
            },
        },
    }

    # 运行时配置（从 pet_config.json 加载）
    PET_CONFIG = {}

    @classmethod
    def load_config(cls):
        """加载配置（从 pet_config.json，必须包含 level_unlocks）"""
        import json
        import os

        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pet_config.json")

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # 只加载配置完整的宠物（必须包含 level_unlocks）
                    for pet_id, config in loaded.items():
                        # 检查必要字段
                        if "states" not in config:
                            print(f"跳过宠物 {pet_id}: 缺少 states 字段")
                            continue
                        if "level_unlocks" not in config:
                            print(f"跳过宠物 {pet_id}: 缺少 level_unlocks 字段")
                            continue

                        # 合并到默认配置（如果有）
                        if pet_id in cls._DEFAULT_PET_CONFIG:
                            # 深度合并 state_config
                            merged_config = cls._DEFAULT_PET_CONFIG[pet_id].copy()
                            if "state_config" in config:
                                merged_config["state_config"] = {
                                    **cls._DEFAULT_PET_CONFIG[pet_id].get("state_config", {}),
                                    **config["state_config"]
                                }
                            # 使用提供的 level_unlocks
                            merged_config["level_unlocks"] = config["level_unlocks"]
                            # 使用提供的 states
                            merged_config["states"] = config["states"]
                            cls.PET_CONFIG[pet_id] = merged_config
                        else:
                            # 新宠物，直接使用配置
                            cls.PET_CONFIG[pet_id] = config

                        # 加载商店数据到 PET_DATA
                        cls.PET_DATA[pet_id] = {
                            "name": config.get("name", pet_id),
                            "shop_price": config.get("shop_price", 0),
                            "intro": config.get("intro", ""),
                        }

                    print(f"已加载 pet_config.json: {len(cls.PET_CONFIG)} 个宠物")
            except Exception as e:
                print(f"加载 pet_config.json 失败: {e}")
                cls.PET_CONFIG = cls._DEFAULT_PET_CONFIG.copy()
        else:
            cls.PET_CONFIG = cls._DEFAULT_PET_CONFIG.copy()
            print("使用默认宠物配置")

    # 兼容旧代码的辅助方法
    @classmethod
    def get_states(cls, pet_id):
        return cls.PET_CONFIG.get(pet_id, {}).get("states", cls.STATES)

    @classmethod
    def get_level_unlocks(cls, pet_id):
        return cls.PET_CONFIG.get(pet_id, {}).get("level_unlocks", {})

    @classmethod
    def get_state_config(cls, pet_id, state):
        default = {"fps": 8, "loop": True, "offset_x": 0, "offset_y": 0}
        return cls.PET_CONFIG.get(pet_id, {}).get("state_config", {}).get(state, default)

    @classmethod
    def get_name(cls, pet_id: str) -> str:
        """获取宠物显示名称"""
        return cls.PET_DATA.get(pet_id, {}).get("name", pet_id)

    @classmethod
    def get_shop_price(cls, pet_id: str) -> int:
        """获取宠物商店价格"""
        return cls.PET_DATA.get(pet_id, {}).get("shop_price", 0)

    @classmethod
    def get_intro(cls, pet_id: str) -> str:
        """获取宠物简介"""
        return cls.PET_DATA.get(pet_id, {}).get("intro", "")

    # 全局状态列表（用于兼容）
    STATES = ["idle", "walk", "hungry", "happy", "sleep", "roll", "special"]

    @classmethod
    def get_extra_scale(cls, pet_id: str) -> float:
        """获取宠物的额外缩放倍率"""
        return cls.EXTRA_SCALE.get(pet_id, 1.0)

    @classmethod
    def get_total_scale(cls, pet_id: str) -> float:
        """获取宠物的总缩放倍率（配置scale × 额外缩放）"""
        scale = cls.SCALE_CONFIG.get(pet_id, cls.SCALE)
        return scale * cls.get_extra_scale(pet_id)

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
                file_type = cfg.get("file_type")
                if file_type is not None and file_type != "pet":
                    continue

                # 从 item_id 提取 pet_id（处理 "golden_retriever_idle_0" 格式）
                pet_id = item_id
                if "_idle_0" in item_id:
                    pet_id = item_id.replace("_idle_0", "")
                elif "_idle" in item_id:
                    pet_id = item_id.replace("_idle", "")

                # 只处理已有图片的宠物
                if pet_id not in cls._images:
                    continue

                # 加载 extra_scale
                extra = cfg.get("extra_scale")
                if extra is not None and extra != "":
                    cls.EXTRA_SCALE[pet_id] = float(extra)
                    loaded_extra += 1
                # 加载 scale（覆盖默认的 SCALE）
                scale = cfg.get("scale")
                if scale is not None:
                    cls.SCALE_CONFIG[pet_id] = float(scale)
                    loaded_scale += 1
            if loaded_extra or loaded_scale:
                print(f"从 furniture_configs.json 加载: {loaded_extra} 个 extra_scale, {loaded_scale} 个 scale")
                # 调试：打印加载的配置
                for item_id in list(cls.SCALE_CONFIG.keys())[:5]:
                    print(f"  {item_id}: scale={cls.SCALE_CONFIG[item_id]}, extra={cls.EXTRA_SCALE.get(item_id, 1.0)}")
        except Exception as e:
            print(f"加载宠物缩放配置失败: {e}")

    @classmethod
    def load_all_images(cls):
        """加载所有宠物精灵图"""
        if cls._images_loaded:
            return

        import os
        sprites_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sprites", "pets")

        # 扫描 sprites 目录，发现新的宠物
        if os.path.exists(sprites_dir):
            all_items = os.listdir(sprites_dir)
            for item in all_items:
                item_path = os.path.join(sprites_dir, item)
                # 检查是否是目录（新格式宠物）
                if os.path.isdir(item_path):
                    pet_id = item
                    # 检查是否在 PET_CONFIG 中
                    if pet_id not in cls.PET_CONFIG:
                        # 尝试从 pet_config.json 加载配置
                        cls._load_pet_config_from_json(pet_id)
                # 检查是否是 _idle_0.png 文件（旧格式宠物）
                elif item.endswith("_idle_0.png"):
                    pet_id = item.replace("_idle_0.png", "")
                    # 检查是否在 PET_CONFIG 中
                    if pet_id not in cls.PET_CONFIG:
                        # 尝试从 pet_config.json 加载配置
                        cls._load_pet_config_from_json(pet_id)

        # 加载所有宠物的精灵图
        for pet_id, config in cls.PET_CONFIG.items():
            cls._images[pet_id] = {}
            states = config["states"]

            # 方式1：从子文件夹加载（新格式）
            pet_dir = os.path.join(sprites_dir, pet_id)
            if os.path.isdir(pet_dir):
                for state in states:
                    state_dir = os.path.join(pet_dir, state)
                    if os.path.isdir(state_dir):
                        frames = cls._load_frames_from_dir(state_dir)
                        if frames:
                            cls._images[pet_id][state] = frames
                            print(f"从文件夹加载: {pet_id}/{state} - {len(frames)}帧")

            # 方式2：从扁平文件加载（旧格式，兼容）
            for state in states:
                if state in cls._images.get(pet_id, {}):
                    continue  # 已从文件夹加载，跳过

                frames = []
                frame_idx = 0

                while True:
                    filename = f"{pet_id}_{state}_{frame_idx}.png"
                    filepath = os.path.join(sprites_dir, filename)

                    if os.path.exists(filepath):
                        try:
                            img = pygame.image.load(filepath).convert_alpha()
                            frames.append(img)
                            frame_idx += 1
                        except Exception as e:
                            print(f"加载宠物图片失败: {filepath} - {e}")
                            break
                    else:
                        break

                if frames:
                    cls._images[pet_id][state] = frames

        cls._images_loaded = True
        cls.load_scale_config()

    @classmethod
    def _load_pet_config_from_json(cls, pet_id: str):
        """从 pet_config.json 加载单个宠物配置"""
        import json
        import os

        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pet_config.json")
        if not os.path.exists(config_path):
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                configs = json.load(f)

            if pet_id in configs:
                config = configs[pet_id]
                # 检查必要字段
                if "states" not in config:
                    print(f"跳过宠物 {pet_id}: 缺少 states 字段")
                    return
                if "level_unlocks" not in config:
                    print(f"跳过宠物 {pet_id}: 缺少 level_unlocks 字段")
                    return

                # 添加到 PET_CONFIG
                cls.PET_CONFIG[pet_id] = config
                print(f"从 pet_config.json 加载宠物配置: {pet_id}")
        except Exception as e:
            print(f"读取宠物配置失败: {e}")

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

        # 找到有非透明像素的行和列
        row_mask = alpha.max(axis=1) > 0
        col_mask = alpha.max(axis=0) > 0

        if not row_mask.any():
            return None  # 全透明

        # 计算bounding box
        y_min = row_mask.argmax()
        y_max = len(row_mask) - 1 - row_mask[::-1].argmax()
        x_min = col_mask.argmax()
        x_max = len(col_mask) - 1 - col_mask[::-1].argmax()

        return (x_min, y_min, x_max - x_min + 1, y_max - y_min + 1)

    @classmethod
    def get_sprite_bbox(cls, pet_id: str, state: str, frame_idx: int) -> tuple:
        """获取精灵图的有效区域（带缓存）"""
        cache_key = (pet_id, state, frame_idx)
        if cache_key not in cls._bbox_cache:
            images = cls._images.get(pet_id, {})
            frames = images.get(state, [])
            if frame_idx < len(frames) and frames[frame_idx] is not None:
                bbox = cls._compute_sprite_bbox(frames[frame_idx])
                cls._bbox_cache[cache_key] = bbox
            else:
                cls._bbox_cache[cache_key] = None
        return cls._bbox_cache[cache_key]

    @classmethod
    def _load_frames_from_dir(cls, dir_path):
        """从文件夹加载帧图片，按文件名中的数字自动排序"""
        import re

        # 获取所有图片文件
        image_exts = ('.png', '.jpg', '.jpeg', '.bmp')
        files = [f for f in os.listdir(dir_path) if f.lower().endswith(image_exts)]

        # 提取文件名中的数字并排序
        def extract_number(filename):
            nums = re.findall(r'\d+', filename)
            return int(nums[0]) if nums else 0

        files.sort(key=extract_number)

        # 加载图片
        frames = []
        for f in files:
            filepath = os.path.join(dir_path, f)
            try:
                img = pygame.image.load(filepath).convert_alpha()
                frames.append(img)
            except Exception as e:
                print(f"加载帧图片失败: {filepath} - {e}")

        return frames

    @classmethod
    def load_all_footprints(cls):
        """加载所有宠物的 footprint 数据"""
        if cls._footprints_loaded:
            return

        import json
        try:
            with open("data/footprints.json", "r", encoding="utf-8") as f:
                all_footprints = json.load(f)

            # 从 PET_CONFIG 动态获取所有宠物ID（不再硬编码）
            pet_ids = list(cls.PET_CONFIG.keys()) if cls.PET_CONFIG else []

            # 如果 PET_CONFIG 为空，扫描 footprints.json 找所有宠物
            if not pet_ids:
                pet_ids = set()
                for key in all_footprints.keys():
                    # 宠物格式: {pet_id}_idle_0, {pet_id}_walk_0 等
                    parts = key.rsplit("_", 2)
                    if len(parts) >= 3:
                        pet_id = parts[0]
                        pet_ids.add(pet_id)
                pet_ids = list(pet_ids)

            for pet_id in pet_ids:
                # 查找对应的 footprint key（格式：pet_id_idle_0）
                fp_key = f"{pet_id}_idle_0"
                if fp_key in all_footprints:
                    cls._footprints[pet_id] = all_footprints[fp_key]

            print(f"加载宠物 footprint: {list(cls._footprints.keys())}")

        except Exception as e:
            print(f"加载宠物 footprint 失败: {e}")

        cls._footprints_loaded = True

    @classmethod
    def get_footprint(cls, pet_id: str):
        """获取宠物的 footprint 数据"""
        return cls._footprints.get(pet_id, [])

    @classmethod
    def get_scaled_frame(cls, pet_id: str, state: str, frame_idx: int, zoom: float):
        """获取缩放后的帧图片（带缓存）"""
        zoom_int = int(zoom * 100)
        cache_key = (pet_id, state, frame_idx, zoom_int)

        if cache_key not in cls._scale_cache:
            # LRU 淘汰
            if len(cls._scale_cache) > 150:
                cls._scale_cache.popitem(last=False)

            # 获取原始帧
            frames = cls._images.get(pet_id, {}).get(state, [])
            if not frames or frame_idx >= len(frames):
                return None

            img = frames[frame_idx]
            img_w, img_h = img.get_size()

            # 计算缩放（一次性缩放，避免多次缩放导致画质损失）
            total_scale = cls.get_total_scale(pet_id)
            state_scale = cls.get_state_config(pet_id, state).get("scale", 1.0)
            scaled_w = max(1, int(img_w * zoom * total_scale * state_scale))
            scaled_h = max(1, int(img_h * zoom * total_scale * state_scale))

            # 缩放
            scaled_img = pygame.transform.scale(img, (scaled_w, scaled_h))
            cls._scale_cache[cache_key] = scaled_img

        # 移到末尾（标记为最近使用）
        cls._scale_cache.move_to_end(cache_key)
        return cls._scale_cache.get(cache_key)

    def __init__(self, pet_id: str, pet_data: dict):
        """初始化宠物"""
        self.pet_id = pet_id  # 实例唯一ID，如 golden_retriever_1
        self.pet_data = pet_data

        # 宠物类型（用于获取图片和配置）
        self.pet_type = pet_data.get("pet_type", self._get_pet_type_from_id(pet_id))

        # 位置（世界坐标）
        self.x = pet_data.get("x", 0)
        self.y = pet_data.get("y", 0)

        # 好感度和饱腹度（需在 _get_available_states 之前设置）
        self.happiness = pet_data.get("happiness", 0)
        self.satiety = pet_data.get("satiety", 50)  # 饱腹度，默认50
        self.level = pet_data.get("level", 0)  # 等级，默认Lv0

        # 状态
        self.state = "idle"
        self.available_states = self._get_available_states()

        # 动画
        self.current_frame = 0
        self.animation_timer = 0.0

        # 行为
        self.target_pos = None  # 目标位置 (x, y)
        self.path = []  # A* 路径 [(x, y), ...]
        self.path_index = 0  # 当前路径点索引
        self.idle_timer = 0.0  # 闲置计时器
        self.speed = self.DEFAULT_SPEED
        self.paused = False  # 暂停状态（喂食菜单等交互时使用）

        # 碰撞检测用的 footprint（从 footprints.json 加载）
        self.footprint = self._load_footprint()

        # 互动时间追踪
        self.last_interaction_time = pet_data.get("last_interaction_time", time.time())
        self.last_petting_time = pet_data.get("last_petting_time", 0)  # 上次抚摸时间
        self.petting_cooldown = 4 * 3600  # 抚摸冷却4小时（秒）

        # 衰减计时器
        self.decay_timer = 0.0
        self.decay_check_interval = 3600  # 每小时检查一次

        # 粒子效果
        self.particles = []

        # 方向（默认向左）
        self.facing_left = True

        # 外部引用（由 PetManager 设置）
        self.valid_area = None  # 有效巡逻区域
        self.world = None  # 世界对象

        # puddle_play 水坑嬉戏状态
        self.puddle_play_cooldown = 30 * 60  # 30分钟冷却（秒）
        self.last_puddle_play_time = pet_data.get("last_puddle_play_time", 0)
        self.puddle_play_active = False  # 是否正在执行 puddle_play
        self.puddle_play_target = None  # 目标水种植区 (grid_x, grid_y)

        # 启动时计算离线衰减
        self._calculate_offline_decay()

    def _get_pet_type_from_id(self, pet_id):
        """从实例ID获取宠物类型"""
        # 先检查是否是已知的宠物类型（完整匹配）
        if pet_id in Pet._images or pet_id in Pet.PET_CONFIG:
            return pet_id
        # 尝试去掉末尾的 _数字 后缀
        last_underscore = pet_id.rfind('_')
        if last_underscore > 0:
            suffix = pet_id[last_underscore + 1:]
            if suffix.isdigit():
                return pet_id[:last_underscore]
        return pet_id

    def _load_footprint(self):
        """从预加载的 footprint 数据中获取"""
        return Pet.get_footprint(self.pet_type)

    def _calculate_offline_decay(self):
        """计算离线期间的衰减"""
        current_time = time.time()
        offline_seconds = current_time - self.last_interaction_time
        offline_hours = offline_seconds / 3600

        # 饱腹度衰减：每小时-10
        satiety_decay = offline_hours * 10
        self.satiety = max(0, self.satiety - satiety_decay)

        # 好感度衰减：未互动>24h，每小时-1（Lv5不衰减）
        if offline_hours > 24 and self.level < 5:
            happiness_decay = (offline_hours - 24) * 1
            self.happiness = max(0, self.happiness - happiness_decay)

        # 保存更新后的数据
        self.pet_data["satiety"] = self.satiety
        self.pet_data["happiness"] = self.happiness
        self.pet_data["last_interaction_time"] = current_time
        self.last_interaction_time = current_time

    def _get_available_states(self):
        """获取当前可用的状态（基于拥有的精灵图 + 等级解锁）"""
        available = []
        pet_images = self._images.get(self.pet_type, {})

        # 获取该宠物的配置
        level_unlocks = Pet.get_level_unlocks(self.pet_type)
        pet_states = Pet.get_states(self.pet_type)

        # 收集所有已解锁的状态
        unlocked_states = []
        for lvl in range(self.level + 1):
            if lvl in level_unlocks:
                unlocked_states.extend(level_unlocks[lvl])

        # 检查是否有对应精灵图
        for state in pet_states:
            if state in unlocked_states and state in pet_images and pet_images[state]:
                available.append(state)

        return available

    def get_footprint_world(self, zoom=1.0):
        """获取世界坐标下的 footprint 顶点

        Args:
            zoom: 相机缩放倍率，默认 1.0（用于碰撞检测时传入实际 zoom）
        """
        if not self.footprint:
            return []

        total_scale = self.get_total_scale(self.pet_type)
        state_scale = Pet.get_state_config(self.pet_type, "idle").get("scale", 1.0)
        # 获取原始图片尺寸
        frames = self._images.get(self.pet_type, {}).get("idle", [])
        if not frames:
            return []

        img_w, img_h = frames[0].get_size()
        # 计算缩放后的尺寸（需要乘 zoom，与渲染保持一致）
        scaled_w = img_w * total_scale * zoom * state_scale
        scaled_h = img_h * total_scale * zoom * state_scale

        # 渲染时的偏移（与 render 方法一致）
        # screen.blit(scaled_frame, (int(screen_x), int(screen_y)))
        # screen_x, screen_y = camera.world_to_screen((self.x, self.y))
        # 所以精灵图左上角在 (self.x, self.y)

        world_fp = []
        for px, py in self.footprint:
            # footprint 坐标是原始图片坐标，需要缩放（包括 zoom）
            # 然后加上宠物的世界坐标位置
            world_x = self.x + px * total_scale * zoom * state_scale
            world_y = self.y + py * total_scale * zoom * state_scale
            world_fp.append((world_x, world_y))

        return world_fp

    def get_footprint_bottom_y(self, zoom=1.0):
        """获取 footprint 底部 Y 坐标（用于渲染排序）

        Args:
            zoom: 相机缩放倍率，默认 1.0
        """
        world_fp = self.get_footprint_world(zoom)
        if world_fp:
            return max(py for _, py in world_fp)
        return self.y

    @staticmethod
    def point_in_polygon(point, polygon):
        """检测点是否在多边形内（射线法）"""
        x, y = point
        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    def check_overlap_with(self, other_fp_world, zoom=1.0):
        """检测本宠物的 footprint 是否与另一个 footprint（世界坐标）重叠

        Args:
            other_fp_world: 另一个 footprint 的世界坐标顶点列表
            zoom: 相机缩放倍率
        """
        my_fp = self.get_footprint_world(zoom)
        if not my_fp or not other_fp_world:
            return False

        # 检测本宠物的顶点是否在对方多边形内
        for point in my_fp:
            if self.point_in_polygon(point, other_fp_world):
                return True

        # 检测对方的顶点是否在本宠物多边形内
        for point in other_fp_world:
            if self.point_in_polygon(point, my_fp):
                return True

        return False

    def get_screen_rect(self, camera):
        """获取宠物在屏幕空间的包围盒（与渲染尺寸一致）"""
        frames = self._images.get(self.pet_type, {}).get(self.state, [])
        if not frames:
            return None

        frame_idx = self.current_frame % len(frames)
        sprite = frames[frame_idx]
        zoom = camera.zoom
        total_scale = self.get_total_scale(self.pet_type)

        # 计算缩放后的尺寸（与渲染一致）
        state_scale = Pet.get_state_config(self.pet_type, self.state).get("scale", 1.0)
        scaled_w = max(1, int(sprite.get_width() * zoom * total_scale * state_scale))
        scaled_h = max(1, int(sprite.get_height() * zoom * total_scale * state_scale))

        # 屏幕位置（与渲染一致）
        screen_x, screen_y = camera.world_to_screen((self.x, self.y))

        return pygame.Rect(int(screen_x), int(screen_y), scaled_w, scaled_h)

    def update(self, dt, zoom=1.0):
        """更新宠物状态

        Args:
            dt: 时间增量
            zoom: 相机缩放倍率，用于碰撞检测
        """
        # 更新动画
        self.update_animation(dt)

        # 更新行为
        self.update_behavior(dt, zoom)

        # 更新粒子
        self.update_particles(dt)

        # 更新饱腹度和好感度衰减
        self.update_decay(dt)

    def update_animation(self, dt):
        """更新动画帧"""
        # 获取当前状态的配置
        state_config = Pet.get_state_config(self.pet_type, self.state)
        fps = state_config.get("fps", 8)
        loop = state_config.get("loop", True)
        loop_start = state_config.get("loop_start", 0)

        # 计算帧间隔
        frame_interval = 1.0 / fps if fps > 0 else 0.125

        self.animation_timer += dt
        if self.animation_timer >= frame_interval:
            self.animation_timer = 0.0
            frames = self._images.get(self.pet_type, {}).get(self.state, [])
            if frames:
                next_frame = self.current_frame + 1
                if next_frame >= len(frames):
                    if loop:
                        # 循环：回到 loop_start 帧
                        self.current_frame = loop_start
                    else:
                        # 不循环：停在最后一帧，切换回 idle
                        self.current_frame = 0
                        self.animation_timer = 0.0
                        # puddle_play 结束时触发浇水效果
                        if self.state == "puddle_play":
                            self._finish_puddle_play()
                        self.state = "idle"
                else:
                    self.current_frame = next_frame

    def update_behavior(self, dt, zoom=1.0):
        """更新行为逻辑

        Args:
            dt: 时间增量
            zoom: 相机缩放倍率，用于碰撞检测
        """
        # 暂停状态时不更新行为
        if self.paused:
            return

        # sleep 触发：游戏时间 22:00-4:00
        if "sleep" in self.available_states:
            from ..core.lighting import LightingManager
            game_hour, _ = LightingManager.get_game_time()
            is_night = game_hour >= 22 or game_hour < 4
            if is_night and self.state != "sleep":
                self.state = "sleep"
                self.current_frame = 0
                self.animation_timer = 0.0
                return
            elif not is_night and self.state == "sleep":
                self.state = "idle"
                self.current_frame = 0
                self.animation_timer = 0.0

        # sleep 状态下不执行其他行为
        if self.state == "sleep":
            return

        # puddle_play 状态下不执行其他行为（动画由 update_animation 处理）
        if self.state == "puddle_play":
            return

        # 如果有目标位置，向目标移动
        if self.target_pos:
            self.move_towards_target(dt, zoom)
        else:
            # 闲置计时
            if self.idle_timer > 0:
                self.idle_timer -= dt
                if self.idle_timer <= 0:
                    # 选择新的目标
                    self.choose_new_target(zoom)
            else:
                # 随机决定是否开始巡逻
                if random.random() < 0.01:  # 1%概率开始巡逻
                    self.choose_new_target(zoom)
                else:
                    # 闲置时随机行为：roll 或 tongueidle
                    self._pick_idle_variant()
                    self.idle_timer = random.uniform(10, 20)

    def _pick_idle_variant(self):
        """闲置时随机选择 idle 变体（hungry、tongueidle、roll 或 puddle_play）"""

        # puddle_play 触发检测（CD满足立即触发）
        if "puddle_play" in self.available_states:
            current_time = time.time()
            if current_time - self.last_puddle_play_time >= self.puddle_play_cooldown:
                if self._do_puddle_play():
                    return

        # roll 随机触发（5%概率）
        if "roll" in self.available_states and random.random() < 0.05:
            self.state = "roll"
            self.current_frame = 0
            self.animation_timer = 0.0
            return

        # hungry 随机触发（饱腹度<30时40%概率）
        if "hungry" in self.available_states and self.satiety < 30 and random.random() < 0.4:
            self.state = "hungry"
            self.current_frame = 0
            self.animation_timer = 0.0
            return

        # tongueidle 随机变体（30%概率）
        if "tongueidle" in self.available_states and random.random() < 0.3:
            self.state = "tongueidle"
        else:
            self.state = "idle"
        self.current_frame = 0
        self.animation_timer = 0.0

    def _find_puddle_play_target(self):
        """寻找 puddle_play 目标：水种植区位置

        检测是否有植物水分<50%且旁边有水种植区，返回水种植区网格坐标
        Returns: (grid_x, grid_y) 或 None
        """
        if not self.world:
            return None

        tile_map = self.world.tile_map
        for grid_y in range(len(tile_map)):
            for grid_x in range(len(tile_map[grid_y])):
                # 找水种植区
                if tile_map[grid_y][grid_x] == self.world.TILE_FARM:
                    if self.world.get_farm_type(grid_x, grid_y) != 1:
                        continue

                    # 检查周围四方向的非水种植区是否有缺水植物
                    adjacent_farms = self.world.get_adjacent_farm_tiles(grid_x, grid_y)
                    for adj_gx, adj_gy, adj_farm_type in adjacent_farms:
                        if adj_farm_type == 1:
                            continue  # 跳过水种植区
                        for crop in self.world.crop_list:
                            crop_gx, crop_gy = self.world.world_to_grid(
                                crop.x + crop.width / 2,
                                crop.y + crop.height / 2
                            )
                            crop_gx = math.floor(crop_gx)
                            crop_gy = math.floor(crop_gy)
                            if crop_gx == adj_gx and crop_gy == adj_gy:
                                if crop.water_level < 50:
                                    return (grid_x, grid_y)
        return None

    def _do_puddle_play(self):
        """执行 puddle_play：走到水种植区并触发浇水

        Returns: True 如果成功触发
        """
        if not self.world:
            return False

        # 寻找目标水种植区
        target = self._find_puddle_play_target()
        if not target:
            return False

        # 记录目标
        self.puddle_play_target = target
        self.puddle_play_active = True

        # 临时允许进入水种植区
        if hasattr(self, '_pet_manager_ref') and self._pet_manager_ref:
            self._pet_manager_ref.set_allow_water_access(True)
        elif hasattr(self, '_other_pets') and self._other_pets:
            # 通过其他引用找到 pet_manager（由 PetManager.update 设置）
            pass

        # 计算水种植区中心的世界坐标
        target_x, target_y = self.world.grid_to_world(
            target[0] + 0.5, target[1] + 0.5
        )

        # 获取当前位置
        center_x = self.x + self.get_sprite_width() / 2
        center_y = self.y + self.get_sprite_height() / 2

        # 寻路到水种植区
        zoom = 1.0  # 默认缩放
        path = self.find_path((center_x, center_y), (target_x, target_y), zoom)

        if path:
            self.path = path
            self.path_index = 0
            self.target_pos = (target_x, target_y)
            self.state = "walk"
            self.current_frame = 0
            self.animation_timer = 0.0
            return True
        else:
            # 无法寻路，直接传送到目标附近并播放动画
            self.x = target_x - self.get_sprite_width() / 2
            self.y = target_y - self.get_sprite_height() / 2
            self._start_puddle_play_animation()
            return True

    def _start_puddle_play_animation(self):
        """开始 puddle_play 动画"""
        self.state = "puddle_play"
        self.current_frame = 0
        self.animation_timer = 0.0
        self.path = []
        self.target_pos = None
        self.last_puddle_play_time = time.time()
        if hasattr(self, 'pet_data'):
            self.pet_data["last_puddle_play_time"] = self.last_puddle_play_time

    def _finish_puddle_play(self):
        """puddle_play 结束：给周围植物浇水并恢复正常状态"""
        if not self.puddle_play_active or not self.puddle_play_target:
            return

        target_x, target_y = self.puddle_play_target
        water_amount = 35

        # 给水种植区周围一格种植区的全部植物浇水
        adjacent_farms = self.world.get_adjacent_farm_tiles(target_x, target_y)
        for adj_gx, adj_gy, adj_farm_type in adjacent_farms:
            if adj_farm_type == 1:
                continue  # 跳过水种植区
            for crop in self.world.crop_list:
                crop_gx, crop_gy = self.world.world_to_grid(
                    crop.x + crop.width / 2,
                    crop.y + crop.height / 2
                )
                crop_gx = math.floor(crop_gx)
                crop_gy = math.floor(crop_gy)
                if crop_gx == adj_gx and crop_gy == adj_gy:
                    if crop.current_stage < 3 and crop.type != 1:
                        crop.water_level = min(100, crop.water_level + water_amount)

        print(f"[puddle_play] {self.pet_id} 浇水完成！目标水区({target_x},{target_y})，+{water_amount}水分")

        # 恢复状态
        self.puddle_play_active = False
        self.puddle_play_target = None

        # 恢复水种植区碰撞限制
        if hasattr(self, '_pet_manager_ref') and self._pet_manager_ref:
            self._pet_manager_ref.set_allow_water_access(False)

    def get_sprite_width(self):
        """获取当前精灵图宽度"""
        frames = self._images.get(self.pet_type, {}).get(self.state, [])
        if frames:
            frame_idx = self.current_frame % len(frames)
            total_scale = self.get_total_scale(self.pet_type)
            return frames[frame_idx].get_width() * total_scale
        return 40

    def get_sprite_height(self):
        """获取当前精灵图高度"""
        frames = self._images.get(self.pet_type, {}).get(self.state, [])
        if frames:
            frame_idx = self.current_frame % len(frames)
            total_scale = self.get_total_scale(self.pet_type)
            return frames[frame_idx].get_height() * total_scale
        return 40

    def move_towards_target(self, dt, zoom=1.0):
        """沿着路径移动（带实时碰撞检测）

        Args:
            dt: 时间增量
            zoom: 相机缩放倍率，用于碰撞检测
        """
        if not self.path or self.path_index >= len(self.path):
            # 路径走完或没有路径
            self.path = []
            self.path_index = 0
            self.target_pos = None
            # puddle_play 到达目标，开始动画
            if self.puddle_play_active:
                self._start_puddle_play_animation()
                return
            self._pick_idle_variant()
            self.idle_timer = random.uniform(10, 20)
            return

        # 获取当前路径点
        target_x, target_y = self.path[self.path_index]

        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 5:
            # 到达当前路径点
            self.x, self.y = target_x, target_y
            self.path_index += 1

            # 检查是否到达最终目标
            if self.path_index >= len(self.path):
                self.path = []
                self.path_index = 0
                self.target_pos = None
                # puddle_play 到达目标，开始动画
                if self.puddle_play_active:
                    self._start_puddle_play_animation()
                else:
                    self._pick_idle_variant()
                    self.idle_timer = random.uniform(10, 20)
        else:
            # 计算新位置，远距离用 run，近距离用 walk
            total_path_dist = sum(
                math.sqrt((self.path[i+1][0]-self.path[i][0])**2 + (self.path[i+1][1]-self.path[i][1])**2)
                for i in range(self.path_index, len(self.path)-1)
            ) + dist
            if "run" in self.available_states and total_path_dist > 200:
                self.state = "run"
                move_speed = self.speed * dt * 60 * 1.5
            elif "walk" in self.available_states:
                self.state = "walk"
                move_speed = self.speed * dt * 60
            else:
                move_speed = self.speed * dt * 60

            # 根据移动方向更新朝向
            if dx < 0:
                self.facing_left = True
            elif dx > 0:
                self.facing_left = False

            new_x = self.x + (dx / dist) * move_speed
            new_y = self.y + (dy / dist) * move_speed

            # 实时碰撞检测：检查新位置是否与其他宠物重叠
            if self._is_position_valid(new_x, new_y, zoom):
                self.x, self.y = new_x, new_y
            else:
                # 碰撞了，停止移动，等待后重新寻路
                self.path = []
                self.path_index = 0
                self.target_pos = None
                self._pick_idle_variant()
                self.idle_timer = random.uniform(5, 10)

    def choose_new_target(self, zoom=1.0):
        """使用 A* 寻路选择目标（带目标冲突检测）

        Args:
            zoom: 相机缩放倍率，用于碰撞检测
        """
        if not self.valid_area or not self.world:
            self.idle_timer = random.uniform(10, 20)
            return

        # 获取其他宠物的目标位置（用于避免冲突）
        other_pet_targets = set()
        if hasattr(self, '_other_pets'):
            for other_pet in self._other_pets:
                if other_pet != self and other_pet.target_pos:
                    # 将目标位置转换为网格坐标（用于比较）
                    grid = self.world.world_to_grid(other_pet.target_pos[0], other_pet.target_pos[1])
                    grid_key = (math.floor(grid[0]), math.floor(grid[1]))
                    other_pet_targets.add(grid_key)

        # 尝试多次寻找有效目标
        max_attempts = 15
        for _ in range(max_attempts):
            # 从有效区域中随机选择一个区块
            grid_x, grid_y = random.choice(self.valid_area)

            # 检查是否与其他宠物目标冲突
            if (grid_x, grid_y) in other_pet_targets:
                continue  # 跳过冲突目标

            # 转换为世界坐标（区块中心）
            world_x, world_y = self.world.grid_to_world(grid_x + 0.5, grid_y + 0.5)

            # 使用 A* 寻路
            start_pos = (self.x, self.y)
            goal_pos = (world_x, world_y)
            path = self.find_path(start_pos, goal_pos, zoom)

            if path and len(path) > 0:
                self.path = path
                self.path_index = 0
                self.target_pos = goal_pos
                return

        # 如果找不到有效路径，等待后再试
        self.idle_timer = random.uniform(10, 20)

    def _is_position_valid(self, x, y, zoom=1.0):
        """检查位置是否有效（宠物footprint不与任何物体footprint重叠）

        Args:
            x, y: 要检查的世界坐标
            zoom: 相机缩放倍率，默认 1.0
        """
        if not self.world:
            return True

        # 获取宠物在该位置的footprint
        # 临时设置位置来计算footprint
        old_x, old_y = self.x, self.y
        self.x, self.y = x, y
        pet_fp = self.get_footprint_world(zoom)
        self.x, self.y = old_x, old_y

        if not pet_fp:
            return True

        # 计算宠物的AABB（用于快速排除）
        pet_min_x = min(p[0] for p in pet_fp)
        pet_max_x = max(p[0] for p in pet_fp)
        pet_min_y = min(p[1] for p in pet_fp)
        pet_max_y = max(p[1] for p in pet_fp)

        # 检查目标位置是否在种植区内（用于跳过作物碰撞）
        target_grid = self.world.world_to_grid(x, y)
        target_gx, target_gy = math.floor(target_grid[0]), math.floor(target_grid[1])
        target_tile_type = self.world.get_tile_type(target_gx, target_gy)
        is_in_farm = (target_tile_type == self.world.TILE_FARM)

        # 检查是否与家具碰撞（先AABB过滤）
        for furniture in self.world.furniture_list:
            # 跳过无碰撞属性的家具（如地毯）
            if getattr(furniture, 'no_collision', False):
                continue

            if hasattr(furniture, 'get_footprint_world'):
                furniture_fp = furniture.get_footprint_world()
                if not furniture_fp:
                    continue

                # 快速AABB排除
                f_min_x = min(p[0] for p in furniture_fp)
                f_max_x = max(p[0] for p in furniture_fp)
                f_min_y = min(p[1] for p in furniture_fp)
                f_max_y = max(p[1] for p in furniture_fp)

                if pet_max_x < f_min_x or pet_min_x > f_max_x or pet_max_y < f_min_y or pet_min_y > f_max_y:
                    continue  # AABB不重叠，跳过

                # AABB重叠，进行精确检测
                if self._polygons_overlap_fast(pet_fp, furniture_fp, pet_min_x, pet_max_x, pet_min_y, pet_max_y, f_min_x, f_max_x, f_min_y, f_max_y):
                    return False

        # 检查是否与作物碰撞（先AABB过滤）
        # 注意：宠物在种植区内时，跳过作物碰撞检测，允许宠物穿过作物
        if not is_in_farm:
            for crop in self.world.crop_list:
                if hasattr(crop, 'get_footprint_world'):
                    crop_fp = crop.get_footprint_world()
                    if not crop_fp:
                        continue

                    # 快速AABB排除
                    c_min_x = min(p[0] for p in crop_fp)
                    c_max_x = max(p[0] for p in crop_fp)
                    c_min_y = min(p[1] for p in crop_fp)
                    c_max_y = max(p[1] for p in crop_fp)

                    if pet_max_x < c_min_x or pet_min_x > c_max_x or pet_max_y < c_min_y or pet_min_y > c_max_y:
                        continue  # AABB不重叠，跳过

                    # AABB重叠，进行精确检测
                    if self._polygons_overlap_fast(pet_fp, crop_fp, pet_min_x, pet_max_x, pet_min_y, pet_max_y, c_min_x, c_max_x, c_min_y, c_max_y):
                        return False

        # 检查是否与其他宠物碰撞（先AABB过滤）
        if hasattr(self, '_other_pets'):
            for other_pet in self._other_pets:
                if other_pet != self:
                    other_fp = other_pet.get_footprint_world(zoom)
                    if not other_fp:
                        continue

                    # 快速AABB排除
                    o_min_x = min(p[0] for p in other_fp)
                    o_max_x = max(p[0] for p in other_fp)
                    o_min_y = min(p[1] for p in other_fp)
                    o_max_y = max(p[1] for p in other_fp)

                    if pet_max_x < o_min_x or pet_min_x > o_max_x or pet_max_y < o_min_y or pet_min_y > o_max_y:
                        continue  # AABB不重叠，跳过

                    # AABB重叠，进行精确检测
                    if self._polygons_overlap_fast(pet_fp, other_fp, pet_min_x, pet_max_x, pet_min_y, pet_max_y, o_min_x, o_max_x, o_min_y, o_max_y):
                        return False

        return True

    def _polygons_overlap_fast(self, poly1, poly2, min1_x, max1_x, min1_y, max1_y, min2_x, max2_x, min2_y, max2_y):
        """检测两个多边形是否重叠（使用预计算的AABB）"""
        for point in poly1:
            if Pet.point_in_polygon(point, poly2):
                return True
        for point in poly2:
            if Pet.point_in_polygon(point, poly1):
                return True
        return False

    # ==================== A* 寻路 ====================

    def find_path(self, start_pos, goal_pos, zoom=1.0):
        """A* 寻路算法（优化版）

        Args:
            start_pos: 起点世界坐标 (x, y)
            goal_pos: 终点世界坐标 (x, y)
            zoom: 相机缩放倍率，用于碰撞检测
        """
        if not self.world or not self.valid_area:
            return None

        # 转换为网格坐标
        start_grid = self.world.world_to_grid(start_pos[0], start_pos[1])
        goal_grid = self.world.world_to_grid(goal_pos[0], goal_pos[1])

        start_grid = (math.floor(start_grid[0]), math.floor(start_grid[1]))
        goal_grid = (math.floor(goal_grid[0]), math.floor(goal_grid[1]))

        # 检查起点和终点是否有效
        if not self._is_grid_valid(start_grid[0], start_grid[1], zoom):
            return None
        if not self._is_grid_valid(goal_grid[0], goal_grid[1], zoom):
            return None

        # 如果起点就是终点
        if start_grid == goal_grid:
            return [goal_pos]

        # A* 算法（使用优先队列优化）
        import heapq
        open_set = []
        closed_set = set()
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: self._heuristic(start_grid, goal_grid)}

        heapq.heappush(open_set, (f_score[start_grid], start_grid))

        # 最大搜索节点数（防止无限搜索）
        max_nodes = 100
        nodes_explored = 0

        while open_set and nodes_explored < max_nodes:
            # 弹出 f_score 最小的节点
            current_f, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            if current == goal_grid:
                # 找到路径，重建路径
                return self._reconstruct_path(came_from, current)

            closed_set.add(current)
            nodes_explored += 1

            # 检查所有邻居（8方向）
            for dx, dy in [(-1, -1), (-1, 0), (-1, 1),
                           (0, -1),          (0, 1),
                           (1, -1),  (1, 0),  (1, 1)]:
                neighbor = (current[0] + dx, current[1] + dy)

                if neighbor in closed_set:
                    continue

                if not self._is_grid_valid(neighbor[0], neighbor[1], zoom):
                    continue

                # 计算移动代价（对角线移动代价更高）
                move_cost = 1.414 if (dx != 0 and dy != 0) else 1.0
                tentative_g = g_score[current] + move_cost

                if tentative_g < g_score.get(neighbor, float('inf')):
                    # 找到更优路径
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        # 没有找到路径
        return None

    def _heuristic(self, a, b):
        """启发式函数（欧几里得距离）"""
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def _is_grid_valid(self, grid_x, grid_y, zoom=1.0):
        """检查网格坐标是否有效（不使用缓存，避免其他宠物移动后的 stale 数据）

        Args:
            grid_x, grid_y: 网格坐标
            zoom: 相机缩放倍率，用于碰撞检测
        """
        if not self.valid_area:
            return False

        # 检查是否在有效区域内
        if (grid_x, grid_y) not in self.valid_area:
            return False

        # 实时检测（不缓存，因为其他宠物的位置会变化）
        # 获取网格中心的世界坐标
        center_x, center_y = self.world.grid_to_world(grid_x + 0.5, grid_y + 0.5)

        # 转换为宠物的左上角坐标
        frames = self._images.get(self.pet_type, {}).get("idle", [])
        if frames:
            img_w, img_h = frames[0].get_size()
            total_scale = self.get_total_scale(self.pet_type)
            state_scale = Pet.get_state_config(self.pet_type, "idle").get("scale", 1.0)
            scaled_w = img_w * total_scale * zoom * state_scale
            scaled_h = img_h * total_scale * zoom * state_scale
            top_left_x = center_x - scaled_w / 2
            top_left_y = center_y - scaled_h / 2
            return self._is_position_valid(top_left_x, top_left_y, zoom)
        else:
            return self._is_position_valid(center_x, center_y, zoom)

    def _reconstruct_path(self, came_from, current):
        """重建路径"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()

        # 转换为世界坐标路径
        # 注意：宠物的 (x, y) 是精灵图左上角，需要将网格中心转换为左上角
        world_path = []
        for grid_x, grid_y in path:
            # 获取网格中心的世界坐标
            center_x, center_y = self.world.grid_to_world(grid_x + 0.5, grid_y + 0.5)

            # 转换为宠物的左上角坐标
            frames = self._images.get(self.pet_type, {}).get("idle", [])
            if frames:
                img_w, img_h = frames[0].get_size()
                total_scale = self.get_total_scale(self.pet_type)
                state_scale = Pet.get_state_config(self.pet_type, "idle").get("scale", 1.0)
                # 渲染时的缩放尺寸（与 get_scaled_frame 一致）
                scaled_w = img_w * total_scale * state_scale
                scaled_h = img_h * total_scale * state_scale
                # 左上角 = 中心 - 宽高的一半
                top_left_x = center_x - scaled_w / 2
                top_left_y = center_y - scaled_h / 2
                world_path.append((top_left_x, top_left_y))
            else:
                world_path.append((center_x, center_y))

        return world_path

    def update_decay(self, dt):
        """更新饱腹度和好感度衰减"""
        self.decay_timer += dt

        # 每小时检查一次
        if self.decay_timer >= self.decay_check_interval:
            self.decay_timer = 0.0

            # 饱腹度衰减：每小时-10
            self.satiety = max(0, self.satiety - 10)
            self.pet_data["satiety"] = self.satiety

            # 好感度衰减：未互动>24h，每小时-1（Lv5不衰减）
            current_time = time.time()
            hours_since_interact = (current_time - self.last_interaction_time) / 3600

            if hours_since_interact > 24 and self.level < 5:
                self.happiness = max(0, self.happiness - 1)
                self.pet_data["happiness"] = self.happiness

        # 不再强制切换到 hungry 状态，改为在 _pick_idle_variant 中随机触发

    def update_particles(self, dt):
        """更新粒子效果"""
        # 更新现有粒子
        for particle in self.particles[:]:
            particle.update(dt)
            if particle.is_dead():
                self.particles.remove(particle)

    def feed(self, satiety_gain: int = 20, happiness_gain: int = 1):
        """喂食宠物

        Args:
            satiety_gain: 饱腹度增加量
            happiness_gain: 好感度增加量
        """
        # 检查饱腹度是否已满
        if self.satiety >= 100:
            return False, 0

        # 应用效果
        self.satiety = min(100, self.satiety + satiety_gain)
        self.happiness = min(100, self.happiness + happiness_gain)

        # 更新等级（好感度达到100时升级）
        reward_gold = 0
        if self.happiness >= 100 and self.level < 5:
            self.level += 1
            self.happiness = 0  # 升级后清零
            reward_gold = self.get_reward_gold()
            # 发放金币奖励
            if self.world and hasattr(self.world, 'game_manager'):
                self.world.game_manager.add_coins(reward_gold)

        # 保存数据
        self.pet_data["satiety"] = self.satiety
        self.pet_data["happiness"] = self.happiness
        self.pet_data["level"] = self.level

        # 切换到开心状态
        if "happy" in self.available_states:
            self.state = "happy"
            self.idle_timer = 3  # 开心3秒

        return True, reward_gold

    def pet(self):
        """抚摸宠物"""
        current_time = time.time()

        # 检查冷却时间（4小时）
        if current_time - self.last_petting_time < self.petting_cooldown:
            return False, 0

        # 应用效果
        self.happiness = min(100, self.happiness + 5)

        # 更新等级（好感度达到100时升级）
        reward_gold = 0
        if self.happiness >= 100 and self.level < 5:
            self.level += 1
            self.happiness = 0  # 升级后清零
            reward_gold = self.get_reward_gold()
            # 发放金币奖励
            if self.world and hasattr(self.world, 'game_manager'):
                self.world.game_manager.add_coins(reward_gold)

        # 更新互动时间
        self.last_interaction_time = current_time
        self.last_petting_time = current_time

        # 保存数据
        self.pet_data["happiness"] = self.happiness
        self.pet_data["level"] = self.level
        self.pet_data["last_interaction_time"] = current_time
        self.pet_data["last_petting_time"] = current_time

        # 生成爱心粒子
        self.spawn_love_particles()

        return True, reward_gold

    def spawn_love_particles(self):
        """生成爱心粒子"""
        for i in range(5):
            offset_x = random.uniform(-20, 20)
            offset_y = random.uniform(-30, -10)
            particle = LoveParticle(self.x + offset_x, self.y + offset_y)
            self.particles.append(particle)

    def render(self, screen, camera):
        """渲染宠物"""
        # 获取当前帧
        frames = self._images.get(self.pet_type, {}).get(self.state, [])
        if not frames:
            return

        frame_idx = self.current_frame % len(frames)
        zoom = camera.zoom

        # 获取缩放后的帧
        scaled_frame = self.get_scaled_frame(self.pet_type, self.state, frame_idx, zoom)
        if not scaled_frame:
            return

        # 根据朝向水平翻转（精灵图默认向左）
        if not self.facing_left:
            scaled_frame = pygame.transform.flip(scaled_frame, True, False)

        # 转换为屏幕坐标
        screen_x, screen_y = camera.world_to_screen((self.x, self.y))

        # 应用配置中的偏移量
        state_config = Pet.get_state_config(self.pet_type, self.state)
        offset_x = state_config.get("offset_x", 0)
        offset_y = state_config.get("offset_y", 0)

        # 渲染
        screen.blit(scaled_frame, (int(screen_x + offset_x), int(screen_y + offset_y)))

        # 渲染粒子
        for particle in self.particles:
            particle.render(screen, camera)

    def is_clicked_at(self, world_pos: tuple, camera) -> bool:
        """检查点击位置是否在宠物身上（像素级检测）"""
        # 获取当前帧的原始精灵图
        frames = self._images.get(self.pet_type, {}).get(self.state, [])
        if not frames:
            return False

        frame_idx = self.current_frame % len(frames)
        sprite = frames[frame_idx]

        # 获取缩放因子
        zoom = camera.zoom
        total_scale = self.get_total_scale(self.pet_type)

        # 精灵图在屏幕上的位置（与 render 方法一致）
        screen_x, screen_y = camera.world_to_screen((self.x, self.y))

        # 缩放后的精灵图尺寸
        state_scale = Pet.get_state_config(self.pet_type, self.state).get("scale", 1.0)
        target_w = max(1, int(sprite.get_width() * zoom * total_scale * state_scale))
        target_h = max(1, int(sprite.get_height() * zoom * total_scale * state_scale))

        # 精灵图左上角（屏幕坐标）
        sprite_left = screen_x
        sprite_top = screen_y

        # 屏幕点击坐标 → 缩放后的精灵图像素坐标
        click_screen_x, click_screen_y = camera.world_to_screen(world_pos)
        sprite_px = int((click_screen_x - sprite_left) * sprite.get_width() / target_w)
        sprite_py = int((click_screen_y - sprite_top) * sprite.get_height() / target_h)

        # 检查是否在精灵图范围内
        if 0 <= sprite_px < sprite.get_width() and 0 <= sprite_py < sprite.get_height():
            # 像素级检测：检查 alpha 通道
            alpha = sprite.get_at((sprite_px, sprite_py)).a
            if alpha > 0:
                return True

        return False

    def get_happiness_level(self):
        """获取好感度等级和称号"""
        level_titles = {
            0: "新伙伴",
            1: "普通伙伴",
            2: "伙伴",
            3: "好朋友",
            4: "亲密伙伴",
            5: "最佳伙伴"
        }
        title = level_titles.get(self.level, "新伙伴")
        return self.level, title

    def get_reward_gold(self):
        """获取奖励金币"""
        level_rewards = {
            0: 0,
            1: 100,
            2: 200,
            3: 400,
            4: 800,
            5: 1000
        }
        return level_rewards.get(self.level, 0)


class LoveParticle:
    """爱心粒子"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.lifetime = 1.0  # 生命时间（秒）
        self.age = 0.0
        self.vx = random.uniform(-20, 20)  # 水平速度
        self.vy = random.uniform(-30, -10)  # 垂直速度（向上飘）
        self.size = random.uniform(3, 6)  # 爱心大小

    def update(self, dt):
        """更新粒子"""
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 20 * dt  # 重力

    def is_dead(self):
        """检查粒子是否死亡"""
        return self.age >= self.lifetime

    def render(self, screen, camera):
        """渲染爱心粒子"""
        if self.is_dead():
            return

        # 转换为屏幕坐标
        screen_x, screen_y = camera.world_to_screen((self.x, self.y))

        # 计算透明度（逐渐消失）
        alpha = int(255 * (1 - self.age / self.lifetime))

        # 绘制爱心（简化版：用两个圆和一个三角形）
        size = int(self.size)
        if size < 1:
            return

        # 创建临时 Surface 用于透明度
        temp_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)

        # 爱心颜色（粉色）
        color = (255, 105, 180, alpha)

        # 绘制两个圆（爱心的两个瓣）
        pygame.draw.circle(temp_surface, color, (size // 2, size // 2), size // 2)
        pygame.draw.circle(temp_surface, color, (size * 3 // 2, size // 2), size // 2)

        # 绘制三角形（爱心的底部）
        points = [
            (0, size // 2),
            (size, size * 2),
            (size * 2, size // 2)
        ]
        pygame.draw.polygon(temp_surface, color, points)

        # 渲染到屏幕
        screen.blit(temp_surface, (int(screen_x - size), int(screen_y - size)))
