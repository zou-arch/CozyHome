"""
UI系统 - 状态栏、底部按钮、菜单
"""
import pygame
import os
import time
import math
from ..entities.pet import Pet
from .tutorial import Tutorial

class UI:
    """UI类"""

    def __init__(self, screen: pygame.Surface, game_manager, world, camera):
        self.screen = screen
        self.game_manager = game_manager
        self.world = world
        self.camera = camera
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

        # 字体（根据屏幕大小调整）
        pygame.font.init()

        # 根据屏幕宽度计算字体大小
        base_font_size = max(12, min(16, self.screen_width // 40))
        self.font_small = self.load_chinese_font(base_font_size)
        self.font_medium = self.load_chinese_font(int(base_font_size * 1.25))
        self.font_large = self.load_chinese_font(int(base_font_size * 1.75))

        # 编辑模式工具
        self._placing_furniture = False
        self._placing_furniture_id = None
        self._placing_pos = (0, 0)

        # 帧率相关
        self.clock = pygame.time.Clock()
        self.fps = 0

        # 加载UI图标
        self.ui_icons = {}
        self.load_ui_icons()

        # 初始化底部按钮
        self.init_buttons()

        # 初始化新手引导
        self.init_tutorial()

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> list:
        """文字自动换行"""
        lines = []
        current_line = ""

        for char in text:
            test_line = current_line + char
            text_width = font.size(test_line)[0]

            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

        return lines

    def load_chinese_font(self, size: int):
        """加载中文字体"""
        # Windows 系统中文字体路径
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
            "C:/Windows/Fonts/msyhbd.ttc",  # 微软雅黑粗体
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return pygame.font.Font(font_path, size)
                except:
                    continue

        # 如果找不到中文字体，使用默认字体
        print("警告：未找到中文字体，使用默认字体")
        return pygame.font.Font(None, size)

    def init_buttons(self):
        """初始化底部按钮（自适应屏幕宽度）"""
        # 底部按钮（带图标）
        btn_y = self.screen_height - 30  # 距离底部30像素
        btn_h = 25
        btn_w = 40
        gap = 10

        # 计算按钮总数和总宽度
        button_configs = [
            {"text": "背包", "action": "inventory", "icon": "inventory", "w": btn_w},
            {"text": "商店", "action": "shop", "icon": "shop", "w": btn_w},
            {"text": "设置", "action": "settings", "icon": "settings", "w": btn_w},
            {"text": "编辑", "action": "edit_mode", "icon": "edit_mode", "w": btn_w},
        ]

        total_w = sum(b["w"] for b in button_configs) + gap * (len(button_configs) - 1)
        start_x = (self.screen_width - total_w) // 2  # 居中对齐

        self.buttons = []
        x = start_x
        for config in button_configs:
            self.buttons.append({
                "text": config["text"],
                "rect": pygame.Rect(x, btn_y, config["w"], btn_h),
                "action": config["action"],
                "icon": config["icon"],
            })
            x += config["w"] + gap

        # 当前显示的菜单
        self.current_menu = None
        self.menu_items = []
        self.menu_rect = pygame.Rect(0, 0, 0, 0)

        # 选中物体的信息
        self.selected_info = None

        # 菜单滚动相关
        self.menu_scroll_offset = 0
        self.menu_max_scroll = 0

        # 编辑模式状态
        self.is_edit_mode = False

        # 种子选择状态
        self.selected_seed = None  # 当前选中的种子ID

        # 种子预览图缓存
        self.seed_previews = {}
        self.load_seed_previews()

        # 作物信息预览缓存（避免每帧 smoothscale）
        self._crop_info_cache = {}  # {(crop_id, size): scaled_surface}

        # 宠物命名输入状态
        self._rename_active = False
        self._rename_pet = None
        self._rename_text = ""
        self._rename_cursor_pos = 0
        self._rename_max_length = 10

        # 家具放置预览缓存（避免每帧 scale）
        self._placing_preview_cache = {}  # {(furniture_id, zoom_int, is_flipped): scaled_surface}

        # 通用图标缓存（避免每帧 smoothscale）
        self._icon_cache = {}  # {(preview_id, size): scaled_surface}

        # 种子选择器状态（发散线条交互）
        self.seed_selector_active = False
        self.seed_selector_grid = None
        self.seed_selector_center = None
        self.seed_selector_lines = []
        self.seed_selector_direction = None
        self.seed_selector_farm_type = -1
        self.seed_selector_slot_idx = -1

        # 地板样式选择器状态（发散线条交互）
        self.floor_selector_active = False
        self.floor_selector_grid = None  # (grid_x, grid_y)
        self.floor_selector_center = None  # 屏幕中心坐标
        self.floor_selector_lines = []  # 三条线的终点坐标和样式信息
        self.floor_selector_direction = None  # 发散方向 (dx, dy)
        self.last_camera_zoom = 1.0  # 记录上次的缩放值，用于检测缩放变化

        # 喂食菜单状态
        self.feed_menu_active = False
        self.feed_menu_pet_id = None  # 目标宠物ID
        self.feed_menu_items = []  # 可喂食的物品列表
        self.feed_menu_selected_idx = 0  # 选中的物品索引
        self.feed_menu_scroll = 0  # 滚动偏移
        self._feed_menu_rect = None  # 菜单区域rect
        self._feed_confirm_rect = None  # 确认按钮rect
        self._feed_close_rect = None  # 关闭按钮rect
        self._feed_item_rects = []  # 物品列表rect

        # 解锁区块状态
        self._unlock_pending = None  # 待解锁的区块坐标 (grid_x, grid_y)
        self._unlock_cost = 0  # 解锁所需金币
        self._unlock_count = 0  # 已解锁区块数量

        # 商店界面状态
        self.shop_category = "seed"  # 当前分类: seed/pet/furniture
        self.shop_selected_idx = 0   # 当前选中的商品索引
        self._shop_tab_rects = {}    # 标签按钮位置
        self._shop_item_rects = []   # 商品格子位置
        self._shop_close_rect = None # 关闭按钮位置
        self._shop_buy_rect = None   # 购买按钮位置

        # 初始化设置面板
        self._init_settings_panel()

    def _init_settings_panel(self):
        """初始化设置面板"""
        from .settings_panel import SettingsPanel
        self.settings_panel = SettingsPanel(self.screen_width, self.screen_height)

    def init_tutorial(self):
        """初始化新手引导（在init_buttons之后调用）"""
        self.tutorial = Tutorial(self.screen, self.game_manager)

    def get_cached_icon(self, preview, size, preview_id=None):
        """获取缓存的图标（避免每帧 smoothscale）"""
        # 使用 preview 对象的 id 作为缓存键，确保不同 stage 的图不会混淆
        cache_key = (id(preview), size)

        if cache_key not in self._icon_cache:
            # 缓存大小限制
            if len(self._icon_cache) > 100:
                self._icon_cache.clear()

            self._icon_cache[cache_key] = pygame.transform.smoothscale(preview, (size, size))

        return self._icon_cache[cache_key]

    def load_seed_previews(self):
        """加载种子和果实预览图"""
        from ..entities.crop import Crop
        sprites_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sprites", "crops")

        self.seed_previews = {}    # 种子预览（stage0）
        self.harvest_previews = {} # 果实预览（stage3）

        for crop_id in Crop.CROP_DATA:
            # 种子预览：stage0
            seed_path = os.path.join(sprites_dir, f"{crop_id}_stage0.png")
            if os.path.exists(seed_path):
                try:
                    img = pygame.image.load(seed_path).convert_alpha()
                    preview_size = max(16, min(20, self.screen_width // 40))
                    self.seed_previews[crop_id] = pygame.transform.smoothscale(img, (preview_size, preview_size))
                except Exception:
                    pass

            # 果实预览：stage3（成熟）
            harvest_path = os.path.join(sprites_dir, f"{crop_id}_stage3.png")
            if os.path.exists(harvest_path):
                try:
                    img = pygame.image.load(harvest_path).convert_alpha()
                    preview_size = max(16, min(20, self.screen_width // 40))
                    self.harvest_previews[crop_id] = pygame.transform.smoothscale(img, (preview_size, preview_size))
                except Exception:
                    pass

    def load_ui_icons(self):
        """加载UI图标"""
        icons_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sprites", "ui")
        self.ui_icons = {}

        icon_mapping = {
            "bag_icon.png": "inventory",
            "shop_icon.png": "shop",
            "settings_icon.png": "settings",
            "edit_icon.png": "edit_mode",
            "in_edit_icon.png": "in_edit_mode",
            "coin_icon.png": "coin",
            "water_icon.png": "water",
            "sunny_icon.png": "sunny",
            "harvest_icon.png": "harvest",
            "close_icon.png": "close",
            "confirm_icon.png": "confirm",
            "back_icon.png": "back",
            "running_icon.png": "rain",
        }

        for filename, action in icon_mapping.items():
            file_path = os.path.join(icons_dir, filename)
            if os.path.exists(file_path):
                try:
                    img = pygame.image.load(file_path).convert_alpha()
                    # 保持比例缩放到24x24区域内
                    w, h = img.get_size()
                    ratio = min(24 / w, 24 / h)
                    new_w = int(w * ratio)
                    new_h = int(h * ratio)
                    scaled = pygame.transform.smoothscale(img, (new_w, new_h))
                    # 创建图标大小的透明表面，居中放置
                    icon_size = max(20, min(24, self.screen_width // 30))
                    icon = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
                    offset_x = (icon_size - new_w) // 2
                    offset_y = (icon_size - new_h) // 2
                    icon.blit(scaled, (offset_x, offset_y))
                    self.ui_icons[action] = icon
                except Exception as e:
                    print(f"加载UI图标失败: {filename}, {e}")

        # 加载背包背景图
        bag_bg_path = os.path.join(icons_dir, "bag_background.jpg")
        self.bag_background = None
        if os.path.exists(bag_bg_path):
            try:
                self.bag_background = pygame.image.load(bag_bg_path).convert()
            except Exception as e:
                print(f"加载背包背景失败: {e}")

        # 加载家具放置菜单背景图
        fsm_bg_path = os.path.join(icons_dir, "f_s_m_background.png")
        self.fsm_background = None
        if os.path.exists(fsm_bg_path):
            try:
                self.fsm_background = pygame.image.load(fsm_bg_path).convert()
            except Exception as e:
                print(f"加载家具放置菜单背景失败: {e}")

    def handle_click(self, screen_pos: tuple) -> bool:
        """处理点击"""
        x, y = screen_pos

        # 检查重命名对话框（最高优先级）
        if self._rename_active:
            return self._handle_rename_click(screen_pos)

        # 检查喂食菜单（优先级最高，在状态栏之前）
        if self.feed_menu_active:
            return self.handle_feed_menu_click(screen_pos)

        # 检查顶部状态栏区域（0-30像素高度）
        if y < 30:
            # 点击顶部状态栏，关闭任何打开的菜单
            if self.current_menu:
                self.close_menu()
            return True  # 阻止拖拽，但不执行操作

        # 检查选择器（优先级最高）
        if self.seed_selector_active:
            # 区分是宠物操作、作物操作还是种子选择
            if hasattr(self, '_action_pet') and self._action_pet:
                return self.handle_pet_interaction_click(screen_pos)
            elif hasattr(self, '_action_crop') and self._action_crop:
                return self.handle_crop_action_click(screen_pos)
            else:
                return self.handle_seed_selector_click(screen_pos)

        # 检查地板样式选择器（优先级第二）
        if self.floor_selector_active:
            return self.handle_floor_selector_click(screen_pos)

        # 检查底部按钮区域（距离底部30像素以上）
        if y > self.screen_height - 30:
            # 点击底部按钮区域，关闭任何打开的菜单
            if self.current_menu:
                self.close_menu()
            # 编辑模式下：检查编辑工具按钮
            if self.is_edit_mode:
                if self.handle_edit_tool_click(screen_pos):
                    return True
            else:
                for button in self.buttons:
                    if button["rect"].collidepoint(x, y):
                        self.handle_button_click(button["action"])
                        return True
            return True  # 阻止拖拽

        # 检查菜单
        if self.current_menu:
            if self.current_menu == "inventory":
                return self.handle_inventory_click(screen_pos)
            elif self.current_menu == "furniture_place":
                return self.handle_furniture_place_click(screen_pos)
            elif self.current_menu == "shop":
                return self.handle_shop_click(screen_pos)
            return self.handle_menu_click(screen_pos)

        return False

    def is_ui_area(self, screen_pos: tuple) -> bool:
        """检查点击是否在UI区域内（顶部状态栏或底部按钮栏）"""
        x, y = screen_pos
        # 顶部状态栏
        if y < 30:
            return True
        # 底部按钮栏（整个灰色区域都是UI）
        if y > self.screen_height - 30:
            return True
        return False

    def handle_button_click(self, action: str):
        """处理按钮点击"""
        if action == "inventory":
            self.show_inventory_menu()
        elif action == "shop":
            self.show_shop_menu()
        elif action == "settings":
            self.show_settings_menu()
        elif action == "edit_mode":
            self.toggle_edit_mode()

    def show_inventory_menu(self):
        """显示背包菜单（新版：图标列表 + 详情面板）"""
        self.current_menu = "inventory"

        # 背包界面状态
        self.inv_category = "fruit"  # 当前分类: fruit/seed/pet/furniture
        self.inv_selected_idx = 0    # 当前选中的物品索引
        self.inv_scroll_offset = 0   # 列表滚动偏移
        self._inv_sell_qty = 1       # 出售数量
        self._inv_dragging_slider = False  # 滑动条拖动状态
        self._inv_detail_scroll = 0  # 详情面板滚动偏移

        # 界面布局（自适应屏幕，避开顶部和底部UI区域）
        margin = 40
        panel_w = self.screen_width - margin * 2
        panel_h = self.screen_height - 32 - 40  # 避开顶部和底部栏
        self.menu_rect = pygame.Rect(margin, 32, panel_w, panel_h)

        # 加载家具预览（如果有）
        self._load_furniture_previews()

    def show_furniture_place_menu(self):
        """显示家具放置菜单（编辑模式下放置家具）"""
        self.current_menu = "furniture_place"

        # 家具选择界面状态（从存档恢复上次选的分类）
        self._fp_category = self.game_manager.ui_settings.get("fp_category", "all")
        self._fp_selected_idx = 0
        self._fp_list_scroll = 0

        # 界面布局（自适应屏幕）
        margin = 40
        panel_w = self.screen_width - margin * 2
        panel_h = self.screen_height - 32 - 40  # 避开顶部和底部栏
        self.menu_rect = pygame.Rect(margin, 32, panel_w, panel_h)

        # 加载家具预览
        self._load_furniture_previews()

    def get_fp_items(self):
        """获取放置菜单中的家具列表（按分类筛选）"""
        from ..entities.furniture import Furniture

        items = []
        furniture = self.game_manager.unlocked_furniture

        # 按id统计数量
        furniture_counts = {}
        for furniture_id in furniture:
            furniture_counts[furniture_id] = furniture_counts.get(furniture_id, 0) + 1

        # 按分类筛选
        for furniture_id, count in furniture_counts.items():
            furniture_data = Furniture.FURNITURE_DATA.get(furniture_id, {})
            obj_type = furniture_data.get("type", "ground")

            # 分类映射
            category_map = {
                "ground": "ground",
                "surface": "surface",
                "surface_wall": "surface_wall",
                "wall_surface": "surface_wall",  # 墙面归入可放置类
                "wall_mount": "wall_mount",
            }
            category = category_map.get(obj_type, "ground")

            if self._fp_category == "all" or category == self._fp_category:
                items.append({
                    "id": furniture_id,
                    "name": furniture_data.get("name", furniture_id),
                    "type": "furniture",
                    "amount": count,
                    "preview": self.furniture_previews.get(furniture_id),
                })

        return items

    def _load_furniture_previews(self):
        """加载家具预览图（使用正确的精灵图）"""
        # 每次打开背包都刷新，确保图片已加载
        self.furniture_previews = {}
        from ..entities.furniture import Furniture
        import os

        # 确保家具图片已预加载
        Furniture.load_all_images()

        sprites_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sprites", "furniture")

        for furniture_id in Furniture.FURNITURE_DATA:
            # 优先使用预加载的图片
            if furniture_id in Furniture._images:
                img = Furniture._images[furniture_id]
                # 缩放到预览大小（自适应屏幕）
                preview_size = max(20, min(24, self.screen_width // 30))
                preview = pygame.transform.smoothscale(img, (preview_size, preview_size))
                self.furniture_previews[furniture_id] = preview
            else:
                # 尝试从文件加载
                img_path = os.path.join(sprites_dir, f"{furniture_id}.png")
                if os.path.exists(img_path):
                    img = pygame.image.load(img_path).convert_alpha()
                    preview_size = max(20, min(24, self.screen_width // 30))
                    preview = pygame.transform.smoothscale(img, (preview_size, preview_size))
                    self.furniture_previews[furniture_id] = preview
                else:
                    # 使用色块
                    data = Furniture.FURNITURE_DATA[furniture_id]
                    preview_size = max(20, min(24, self.screen_width // 30))
                    surf = pygame.Surface((preview_size, preview_size), pygame.SRCALPHA)
                    color = data.get("color", (128, 128, 128))
                    margin = max(2, preview_size // 10)
                    pygame.draw.rect(surf, color, (margin, margin, preview_size - margin*2, preview_size - margin*2))
                    pygame.draw.rect(surf, (50, 50, 50), (margin, margin, preview_size - margin*2, preview_size - margin*2), 1)
                    self.furniture_previews[furniture_id] = surf

    def get_inv_items(self):
        """获取当前分类的物品列表"""
        from ..entities.crop import Crop
        from ..entities.furniture import Furniture

        items = []
        inventory = self.game_manager.inventory
        seeds = inventory.get("seeds", {})
        harvests = inventory.get("harvests", {})

        if self.inv_category == "fruit":
            # 果实：收获的作物（用成熟阶段图片）
            for crop_id, amount in harvests.items():
                if amount > 0:
                    crop_data = Crop.CROP_DATA.get(crop_id, {})
                    items.append({
                        "id": crop_id,
                        "name": crop_data.get("name", crop_id),
                        "type": "fruit",
                        "amount": amount,
                        "sell_price": crop_data.get("sell_price", 0),
                        "preview": self.harvest_previews.get(crop_id),
                        "farm_type": crop_data.get("type", 0),
                    })

        elif self.inv_category == "seed":
            # 种子：商店购买的种子（用种子阶段图片）
            for crop_id, amount in seeds.items():
                if amount > 0:
                    crop_data = Crop.CROP_DATA.get(crop_id, {})
                    items.append({
                        "id": crop_id,
                        "name": crop_data.get("name", crop_id) + "种子",
                        "type": "seed",
                        "amount": amount,
                        "seed_price": crop_data.get("seed_price", 5),
                        "preview": self.seed_previews.get(crop_id),
                        "farm_type": crop_data.get("type", 0),
                    })

        elif self.inv_category == "pet":
            # 宠物列表
            pets = self.game_manager.inventory.get("pets", [])
            pet_counts = {}
            for pet_id in pets:
                pet_counts[pet_id] = pet_counts.get(pet_id, 0) + 1
            for pet_id, count in pet_counts.items():
                # 获取宠物名称（优先使用自定义名称）
                custom_name = pet_id
                if hasattr(self.world, 'pet_manager'):
                    if pet_id in self.world.pet_manager.pet_data:
                        custom_name = self.world.pet_manager.pet_data[pet_id].get('name', pet_id)
                items.append({
                    "id": pet_id,
                    "name": custom_name,
                    "type": "pet",
                    "amount": count,
                    "preview": self._get_pet_preview(pet_id),
                })

        elif self.inv_category == "furniture":
            # 家具（按id统计数量）
            furniture = self.game_manager.unlocked_furniture
            furniture_counts = {}
            for furniture_id in furniture:
                furniture_counts[furniture_id] = furniture_counts.get(furniture_id, 0) + 1
            for furniture_id, count in furniture_counts.items():
                furniture_data = Furniture.FURNITURE_DATA.get(furniture_id, {})
                items.append({
                    "id": furniture_id,
                    "name": furniture_data.get("name", furniture_id),
                    "type": "furniture",
                    "amount": count,
                    "preview": self.furniture_previews.get(furniture_id),
                })

        return items

    def show_shop_menu(self):
        """显示商店菜单"""
        self.current_menu = "shop"
        self.shop_selected_idx = 0
        self._shop_list_scroll = 0
        # 加载家具预览（如果切换到家具分类）
        if self.shop_category == "furniture":
            self._load_furniture_previews()

    def get_shop_items(self):
        """获取当前分类的商品列表"""
        from ..entities.crop import Crop

        items = []
        if self.shop_category == "seed":
            for seed_id in self.game_manager.unlocked_seeds:
                crop_data = Crop.CROP_DATA.get(seed_id, {})
                items.append({
                    "id": seed_id,
                    "name": crop_data.get("name", seed_id),
                    "type": "seed",
                    "price": crop_data.get("seed_price", 5),
                    "sell_price": crop_data.get("sell_price", 10),
                    "farm_type": crop_data.get("type", 0),
                    "preview": self.seed_previews.get(seed_id),
                })
        elif self.shop_category == "pet":
            for pet_id, pet_data in Pet.PET_DATA.items():
                shop_price = pet_data.get("shop_price", 0)
                if shop_price > 0:
                    items.append({
                        "id": pet_id,
                        "name": pet_data.get("name", pet_id),
                        "type": "pet",
                        "price": shop_price,
                        "intro": pet_data.get("intro", ""),
                        "preview": self._get_pet_preview(pet_id),
                    })
        elif self.shop_category == "furniture":
            from ..entities.furniture import Furniture
            for fid, fdata in Furniture.FURNITURE_DATA.items():
                shop_price = fdata.get("shop_price", 0)
                if shop_price > 0:
                    items.append({
                        "id": fid,
                        "name": fdata.get("name", fid),
                        "type": "furniture",
                        "price": shop_price,
                        "obj_type": fdata.get("type", "ground"),
                        "preview": self.furniture_previews.get(fid),
                    })
        return items

    def render_shop_menu(self):
        """渲染商店界面（模仿背包布局）"""
        from ..entities.crop import Crop

        # 界面尺寸
        margin = 40
        panel_x = margin
        panel_y = 32
        panel_w = self.screen_width - margin * 2
        panel_h = self.screen_height - panel_y - 40
        tab_h = 25
        list_w = int(panel_w * 0.65)
        info_w = panel_w - list_w - 15
        info_x = panel_x + list_w + 10

        # 背景
        if self.bag_background:
            scaled_bg = pygame.transform.smoothscale(self.bag_background, (panel_w, panel_h))
            self.screen.blit(scaled_bg, (panel_x, panel_y))
        else:
            pygame.draw.rect(self.screen, (45, 45, 55), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(self.screen, (80, 80, 100), (panel_x, panel_y, panel_w, panel_h), 2)

        # 关闭按钮
        close_rect = pygame.Rect(panel_x + panel_w - 25, panel_y + 3, 22, 22)
        if "close" in self.ui_icons:
            close_icon = self.ui_icons["close"]
            close_size = max(16, min(20, self.screen_width // 40))
            close_icon = pygame.transform.smoothscale(close_icon, (close_size, close_size))
            self.screen.blit(close_icon, close_rect)
        else:
            pygame.draw.rect(self.screen, (150, 80, 80), close_rect)
            text = self.font_small.render("X", True, (255, 255, 255))
            self.screen.blit(text, close_rect)
        self._shop_close_rect = close_rect

        # 标题 + 金币
        title = self.font_medium.render("商店", True, (255, 220, 100))
        self.screen.blit(title, (panel_x + 10, panel_y + 5))
        coin_text = self.font_small.render(f"金币: {self.game_manager.coins}", True, (255, 215, 0))
        self.screen.blit(coin_text, (panel_x + 60, panel_y + 8))

        # 分类标签
        categories = [("seed", "种子"), ("pet", "宠物"), ("furniture", "家具")]
        tab_x = panel_x + 150
        self._shop_tab_rects = {}
        for cat_id, cat_name in categories:
            tab_rect = pygame.Rect(tab_x, panel_y + 5, 45, 20)
            is_selected = (self.shop_category == cat_id)
            color = (100, 120, 160) if is_selected else (60, 60, 70)
            pygame.draw.rect(self.screen, color, tab_rect, border_radius=3)
            pygame.draw.rect(self.screen, (100, 100, 120), tab_rect, 1, border_radius=3)
            text = self.font_small.render(cat_name, True, (255, 255, 255) if is_selected else (150, 150, 150))
            text_rect = text.get_rect(center=tab_rect.center)
            self.screen.blit(text, text_rect)
            self._shop_tab_rects[cat_id] = tab_rect
            tab_x += 50

        # 获取商品列表
        items = self.get_shop_items()

        # 商品列表区域（左侧）
        list_rect = pygame.Rect(panel_x + 5, panel_y + tab_h + 5, list_w, panel_h - tab_h - 15)
        list_bg = pygame.Surface((list_w, panel_h - tab_h - 15), pygame.SRCALPHA)
        list_bg.fill((35, 35, 45, 150))
        self.screen.blit(list_bg, (panel_x + 5, panel_y + tab_h + 5))
        pygame.draw.rect(self.screen, (70, 70, 90), list_rect, 1)

        # 渲染商品网格
        self._shop_item_rects = []
        cell_size = max(50, min(65, self.screen_width // 12))
        cols = list_w // cell_size
        if cols < 1:
            cols = 1
        item_h = cell_size

        # 滚动支持
        if not hasattr(self, '_shop_list_scroll'):
            self._shop_list_scroll = 0
        visible_rows = list_rect.height // item_h
        total_rows = (len(items) + cols - 1) // cols
        max_scroll = max(0, total_rows - visible_rows)
        self._shop_list_scroll = max(0, min(self._shop_list_scroll, max_scroll))

        # 裁剪列表区域
        self.screen.set_clip(list_rect)

        for i in range(len(items)):
            item = items[i]
            row = i // cols
            col = i % cols
            cell_y = list_rect.y + 5 + (row - self._shop_list_scroll) * item_h
            cell_x = list_rect.x + 5 + col * cell_size

            if cell_y + item_h < list_rect.y or cell_y > list_rect.y + list_rect.height:
                continue

            cell_rect = pygame.Rect(cell_x, cell_y, cell_size - 4, cell_size - 4)
            if i == self.shop_selected_idx:
                pygame.draw.rect(self.screen, (70, 80, 110), cell_rect, border_radius=5)

            # 图标
            icon_size = max(36, min(48, self.screen_width // 16))
            icon_x = cell_x + (cell_size - 4 - icon_size) // 2
            icon_y = cell_y + 5

            preview = item.get("preview")
            if preview:
                cache_key = (f"shop_{item['id']}", icon_size)
                if cache_key not in self._icon_cache:
                    self._icon_cache[cache_key] = pygame.transform.smoothscale(preview, (icon_size, icon_size))
                scaled = self._icon_cache[cache_key]
                self.screen.blit(scaled, (icon_x, icon_y))
            else:
                pygame.draw.rect(self.screen, (100, 100, 100), (icon_x, icon_y, icon_size, icon_size), border_radius=5)

            # 价格条
            bar_h = 16
            bar_y = cell_y + cell_size - 4 - bar_h
            bar_rect = pygame.Rect(cell_x + 2, bar_y, cell_size - 8, bar_h)
            pygame.draw.rect(self.screen, (30, 30, 40, 180), bar_rect, border_radius=3)

            price_text = self.font_small.render(f"{item['price']}金", True, (255, 215, 0))
            text_rect = price_text.get_rect(center=bar_rect.center)
            self.screen.blit(price_text, text_rect)

            self._shop_item_rects.append((cell_rect, i))

        self.screen.set_clip(None)

        # 详情区域（右侧）
        info_rect = pygame.Rect(info_x, panel_y + tab_h + 5, info_w, panel_h - tab_h - 15)
        info_bg = pygame.Surface((info_w, panel_h - tab_h - 15), pygame.SRCALPHA)
        info_bg.fill((40, 40, 50, 150))
        self.screen.blit(info_bg, (info_x, panel_y + tab_h + 5))
        pygame.draw.rect(self.screen, (70, 70, 90), info_rect, 1)

        if items and self.shop_selected_idx < len(items):
            selected = items[self.shop_selected_idx]
            self._render_shop_detail(info_rect, selected)
        else:
            empty_text = self.font_small.render("无商品", True, (120, 120, 120))
            empty_rect = empty_text.get_rect(center=info_rect.center)
            self.screen.blit(empty_text, empty_rect)

    def _render_shop_detail(self, rect, item):
        """渲染商品详情"""
        x = rect.x + 5
        y = rect.y + 5

        # 图标（居中）
        icon_size = max(36, min(48, self.screen_width // 16))
        icon_x = x + (rect.width - 10 - icon_size) // 2
        preview = item.get("preview")
        if preview:
            big_icon = self.get_cached_icon(preview, icon_size, item.get("id"))
            self.screen.blit(big_icon, (icon_x, y))
        else:
            pygame.draw.rect(self.screen, (100, 100, 100), (icon_x, y, icon_size, icon_size), border_radius=5)
        y += icon_size + 5

        # 名称
        name_text = self.font_small.render(item["name"], True, (255, 255, 255))
        name_rect = name_text.get_rect(centerx=rect.centerx, top=y)
        self.screen.blit(name_text, name_rect)
        y += 20

        # 分隔线
        pygame.draw.line(self.screen, (60, 60, 70), (rect.x + 5, y), (rect.right - 5, y), 1)
        y += 5

        # 类型信息
        if item["type"] == "seed":
            farm_names = ["土生", "水生", "盆栽", "沙生"]
            farm_text = self.font_small.render(f"种植: {farm_names[item.get('farm_type', 0)]}", True, (150, 180, 150))
            self.screen.blit(farm_text, (rect.x + 5, y))
            y += 16
            sell_text = self.font_small.render(f"收获卖: {item.get('sell_price', 10)}金", True, (180, 180, 180))
            self.screen.blit(sell_text, (rect.x + 5, y))
            y += 16
        elif item["type"] == "pet":
            intro = item.get("intro", "")
            if intro:
                # 自动换行
                lines = []
                line = ""
                for ch in intro:
                    line += ch
                    if self.font_small.size(line)[0] > rect.width - 10:
                        lines.append(line[:-1])
                        line = ch
                if line:
                    lines.append(line)
                for line in lines[:3]:
                    intro_text = self.font_small.render(line, True, (150, 200, 150))
                    self.screen.blit(intro_text, (rect.x + 5, y))
                    y += 14
        elif item["type"] == "furniture":
            type_names = {"ground": "地面", "surface": "平面", "surface_wall": "地面+墙面", "wall_mount": "挂饰", "wall_surface": "墙面"}
            type_text = self.font_small.render(f"类型: {type_names.get(item.get('obj_type', ''), '未知')}", True, (150, 180, 150))
            self.screen.blit(type_text, (rect.x + 5, y))
            y += 16

        # 价格
        y += 5
        price_text = self.font_small.render(f"价格: {item['price']}金", True, (255, 215, 0))
        self.screen.blit(price_text, (rect.x + 5, y))
        y += 20

        # 购买按钮
        can_buy = self.game_manager.coins >= item["price"]
        btn_rect = pygame.Rect(rect.x + 5, y, rect.width - 10, 25)
        btn_color = (80, 130, 80) if can_buy else (80, 80, 80)
        pygame.draw.rect(self.screen, btn_color, btn_rect, border_radius=5)
        pygame.draw.rect(self.screen, (100, 100, 120), btn_rect, 1, border_radius=5)
        btn_text = self.font_small.render("购买", True, (255, 255, 255) if can_buy else (120, 120, 120))
        text_rect = btn_text.get_rect(center=btn_rect.center)
        self.screen.blit(btn_text, text_rect)
        self._shop_buy_rect = btn_rect if can_buy else None

    def show_settings_menu(self):
        """显示设置菜单"""
        self.current_menu = "settings"
        self.settings_panel.show()
        # 同步当前音量值
        from ..core.audio_manager import audio_manager
        self.settings_panel.set_bgm_volume(audio_manager.bgm_volume)
        self.settings_panel.set_sfx_volume(audio_manager.sfx_volume)

    def handle_menu_click(self, screen_pos: tuple) -> bool:
        """处理菜单点击"""
        x, y = screen_pos

        # 处理设置面板点击
        if self.current_menu == "settings":
            # 先让设置面板处理事件
            if self.settings_panel.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=screen_pos, button=1)):
                # 检查设置面板的action
                action = self.settings_panel.get_click_action(screen_pos)
                if action == "close":
                    self.close_menu()
                elif action == "save":
                    if hasattr(self.game_manager, 'save_manager'):
                        self.game_manager.save_manager.save_game()
                    self.close_menu()
                elif action == "load":
                    if hasattr(self.game_manager, 'save_manager'):
                        self.game_manager.save_manager.load_game()
                    self.close_menu()
                else:
                    # 滑块更新，同步音量
                    from ..core.audio_manager import audio_manager
                    audio_manager.set_bgm_volume(self.settings_panel.bgm_volume)
                    audio_manager.set_sfx_volume(self.settings_panel.sfx_volume)
                return True

        for item in self.menu_items:
            if item["rect"].collidepoint(x, y):
                action = item["action"]
                if action == "close":
                    self.close_menu()
                elif action == "save":
                    # 手动保存
                    if hasattr(self.game_manager, 'save_manager'):
                        self.game_manager.save_manager.save_game()
                    self.close_menu()
                elif action == "load":
                    # 手动加载
                    if hasattr(self.game_manager, 'save_manager'):
                        self.game_manager.save_manager.load_game()
                    self.close_menu()
                elif action == "buy_seed":
                    # 购买种子
                    self.buy_seed(item.get("item_id"), item.get("price", 0))
                elif action == "buy_pet":
                    # 购买宠物
                    self.buy_pet(item.get("item_id"), item.get("price", 0))
                elif action == "select_seed":
                    # 选择种子
                    self.selected_seed = item.get("crop_id")
                    print(f"选择种子: {self.selected_seed}")
                    self.show_inventory_menu()  # 刷新菜单显示
                elif action == "unlock_confirm":
                    # 确认解锁区块
                    self._execute_unlock()
                return True

        # 点击菜单外部关闭
        if not self.menu_rect.collidepoint(x, y):
            self.close_menu()
            return True

        return False

    def handle_shop_click(self, screen_pos: tuple) -> bool:
        """处理商店界面点击"""
        x, y = screen_pos

        # 关闭按钮
        if self._shop_close_rect and self._shop_close_rect.collidepoint(x, y):
            self.close_menu()
            return True

        # 标签切换
        for cat_id, tab_rect in self._shop_tab_rects.items():
            if tab_rect.collidepoint(x, y):
                if self.shop_category != cat_id:
                    self.shop_category = cat_id
                    self.shop_selected_idx = 0
                    self._shop_list_scroll = 0
                    # 切换到家具分类时加载预览
                    if cat_id == "furniture":
                        self._load_furniture_previews()
                return True

        # 商品选择
        for cell_rect, idx in self._shop_item_rects:
            if cell_rect.collidepoint(x, y):
                self.shop_selected_idx = idx
                return True

        # 购买按钮
        if self._shop_buy_rect and self._shop_buy_rect.collidepoint(x, y):
            items = self.get_shop_items()
            if items and self.shop_selected_idx < len(items):
                item = items[self.shop_selected_idx]
                if item["type"] == "seed":
                    self.buy_seed(item["id"], item["price"])
                elif item["type"] == "pet":
                    self.buy_pet(item["id"], item["price"])
                elif item["type"] == "furniture":
                    self.buy_furniture(item["id"], item["price"])
            return True

        # 点击外部关闭
        if not hasattr(self, 'menu_rect') or not self.menu_rect.collidepoint(x, y):
            self.close_menu()
            return True

        return False

    def buy_furniture(self, furniture_id: str, price: int):
        """购买家具"""
        if self.game_manager.spend_coins(price):
            if furniture_id not in self.game_manager.unlocked_furniture:
                self.game_manager.unlocked_furniture.append(furniture_id)
            print(f"购买了家具 {furniture_id}")
            # 刷新商店界面
            self.shop_selected_idx = 0
            # 自动保存
            if hasattr(self.game_manager, 'save_manager'):
                self.game_manager.save_manager.auto_save_on_action("购买家具")
        else:
            print("金币不足")

    def handle_inventory_click(self, screen_pos: tuple) -> bool:
        """处理背包界面点击"""
        x, y = screen_pos

        # 检查关闭按钮
        if hasattr(self, '_inv_close_rect') and self._inv_close_rect.collidepoint(x, y):
            self.close_menu()
            return True

        # 检查分类标签
        if hasattr(self, '_inv_tab_rects'):
            for cat_id, tab_rect in self._inv_tab_rects.items():
                if tab_rect.collidepoint(x, y):
                    self.inv_category = cat_id
                    self.inv_selected_idx = 0
                    return True

        # 检查物品列表点击
        if hasattr(self, '_inv_item_rects'):
            for item_rect, item_idx in self._inv_item_rects:
                if item_rect.collidepoint(x, y):
                    self.inv_selected_idx = item_idx
                    self._inv_sell_qty = 1  # 切换物品时重置数量
                    return True

        # 检查滑动条点击
        if hasattr(self, '_inv_slider_rect') and self._inv_slider_rect.collidepoint(x, y):
            self._inv_dragging_slider = True
            # 计算点击位置对应的数量
            items = self.get_inv_items()
            if items and self.inv_selected_idx < len(items):
                max_qty = items[self.inv_selected_idx]['amount']
                if max_qty > 1:
                    ratio = (x - self._inv_slider_rect.x) / self._inv_slider_rect.width
                    ratio = max(0, min(1, ratio))
                    self._inv_sell_qty = max(1, int(ratio * (max_qty - 1)) + 1)
            return True

        # 检查滑块拖动（更新位置）
        if hasattr(self, '_inv_dragging_slider') and self._inv_dragging_slider:
            if hasattr(self, '_inv_slider_rect'):
                items = self.get_inv_items()
                if items and self.inv_selected_idx < len(items):
                    max_qty = items[self.inv_selected_idx]['amount']
                    if max_qty > 1:
                        ratio = (x - self._inv_slider_rect.x) / self._inv_slider_rect.width
                        ratio = max(0, min(1, ratio))
                        self._inv_sell_qty = max(1, int(ratio * (max_qty - 1)) + 1)
            return True

        # 检查出售按钮
        if hasattr(self, '_inv_sell_rect') and self._inv_sell_rect.collidepoint(x, y):
            self._sell_selected_item()
            return True

        # 检查全部出售按钮
        if hasattr(self, '_inv_sell_all_rect') and self._inv_sell_all_rect.collidepoint(x, y):
            self._sell_all_selected_item()
            return True

        # 检查宠物释放/收回按钮
        if hasattr(self, '_inv_pet_btn_rect') and self._inv_pet_btn_rect.collidepoint(x, y):
            self._toggle_pet_release()
            return True

        # 检查宠物重命名按钮
        if hasattr(self, '_inv_pet_rename_rect') and self._inv_pet_rename_rect.collidepoint(x, y):
            self._show_rename_dialog()
            return True

        # 点击背包外部关闭
        if not self.menu_rect.collidepoint(x, y):
            self.close_menu()
            return True

        return False

    def _sell_selected_item(self):
        """出售选中的物品（按选择数量）"""
        items = self.get_inv_items()
        if not items or self.inv_selected_idx >= len(items):
            return

        item = items[self.inv_selected_idx]
        if item["type"] != "fruit":
            return

        crop_id = item["id"]
        harvests = self.game_manager.inventory.get("harvests", {})
        available = harvests.get(crop_id, 0)
        qty = min(self._inv_sell_qty, available)

        if qty > 0:
            harvests[crop_id] -= qty
            self.game_manager.inventory["harvests"] = harvests
            from ..entities.crop import Crop
            crop_data = Crop.CROP_DATA.get(crop_id, {})
            price = crop_data.get("sell_price", 5)
            total = price * qty
            self.game_manager.add_coins(total)
            print(f"出售了 {item['name']} x{qty}，获得 {total} 金币")
            if hasattr(self.game_manager, 'save_manager'):
                self.game_manager.save_manager.auto_save_on_action("出售")
            # 刷新显示，重置数量
            self._inv_sell_qty = 1
            self.inv_selected_idx = min(self.inv_selected_idx, max(0, len(self.get_inv_items()) - 1))

    def _sell_all_selected_item(self):
        """出售选中的物品（全部）"""
        items = self.get_inv_items()
        if not items or self.inv_selected_idx >= len(items):
            return

        item = items[self.inv_selected_idx]
        if item["type"] != "fruit":
            return

        crop_id = item["id"]
        harvests = self.game_manager.inventory.get("harvests", {})
        amount = harvests.get(crop_id, 0)
        if amount > 0:
            from ..entities.crop import Crop
            crop_data = Crop.CROP_DATA.get(crop_id, {})
            price = crop_data.get("sell_price", 5)
            total_price = price * amount
            harvests[crop_id] = 0
            self.game_manager.inventory["harvests"] = harvests
            self.game_manager.add_coins(total_price)
            print(f"全部出售 {item['name']} x{amount}，获得 {total_price} 金币")
            if hasattr(self.game_manager, 'save_manager'):
                self.game_manager.save_manager.auto_save_on_action("出售")
            # 刷新显示
            self.inv_selected_idx = min(self.inv_selected_idx, max(0, len(self.get_inv_items()) - 1))

    def _toggle_pet_release(self):
        """切换宠物释放/收回状态"""
        items = self.get_inv_items()
        if not items or self.inv_selected_idx >= len(items):
            return

        item = items[self.inv_selected_idx]
        if item["type"] != "pet":
            return

        pet_id = item['id']

        if not hasattr(self.world, 'pet_manager'):
            return

        # 检查当前状态
        is_released = False
        for pet in self.world.pet_manager.scene_pets:
            if pet.pet_id == pet_id:
                is_released = True
                break

        if is_released:
            # 收回宠物
            self.world.pet_manager.recall_pet(pet_id)
            print(f"收回了 {pet_id}")
        else:
            # 释放宠物
            self.world.pet_manager.release_pet(pet_id)
            print(f"释放了 {pet_id}")

        # 保存
        if hasattr(self.game_manager, 'save_manager'):
            self.game_manager.save_manager.auto_save_on_action("宠物释放/收回")

    def _show_rename_dialog(self):
        """显示宠物重命名对话框"""
        items = self.get_inv_items()
        if not items or self.inv_selected_idx >= len(items):
            return

        item = items[self.inv_selected_idx]
        if item["type"] != "pet":
            return

        # 获取当前宠物名称
        pet_id = item['id']
        current_name = item.get('name', pet_id)

        # 设置输入状态
        self._rename_active = True
        self._rename_pet_id = pet_id
        self._rename_text = current_name
        self._rename_cursor_pos = len(current_name)

    def _handle_rename_input(self, event):
        """处理重命名输入事件"""
        if not self._rename_active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                # 确认重命名
                self._confirm_rename()
                return True
            elif event.key == pygame.K_ESCAPE:
                # 取消重命名
                self._rename_active = False
                return True
            elif event.key == pygame.K_BACKSPACE:
                # 删除字符
                if self._rename_cursor_pos > 0:
                    self._rename_text = self._rename_text[:self._rename_cursor_pos-1] + self._rename_text[self._rename_cursor_pos:]
                    self._rename_cursor_pos -= 1
                return True
            elif event.key == pygame.K_LEFT:
                # 光标左移
                if self._rename_cursor_pos > 0:
                    self._rename_cursor_pos -= 1
                return True
            elif event.key == pygame.K_RIGHT:
                # 光标右移
                if self._rename_cursor_pos < len(self._rename_text):
                    self._rename_cursor_pos += 1
                return True
            elif event.unicode and len(self._rename_text) < self._rename_max_length:
                # 输入字符（限制长度）
                char = event.unicode
                if char.isprintable():
                    self._rename_text = self._rename_text[:self._rename_cursor_pos] + char + self._rename_text[self._rename_cursor_pos:]
                    self._rename_cursor_pos += 1
                return True

        return False

    def _confirm_rename(self):
        """确认重命名"""
        new_name = self._rename_text.strip()
        if not new_name:
            new_name = self._rename_pet_id  # 如果为空，使用默认ID

        # 更新宠物数据
        if hasattr(self.world, 'pet_manager'):
            if self._rename_pet_id in self.world.pet_manager.pet_data:
                self.world.pet_manager.pet_data[self._rename_pet_id]['name'] = new_name
                print(f"宠物重命名: {self._rename_pet_id} -> {new_name}")

                # 同步到场景中的宠物
                for pet in self.world.pet_manager.scene_pets:
                    if pet.pet_id == self._rename_pet_id:
                        pet.pet_data['name'] = new_name
                        break

        # 保存
        if hasattr(self.game_manager, 'save_manager'):
            self.game_manager.save_manager.auto_save_on_action("宠物重命名")

        # 关闭输入状态
        self._rename_active = False

    def _handle_rename_click(self, screen_pos: tuple) -> bool:
        """处理重命名对话框的点击"""
        if not self._rename_active:
            return False

        x, y = screen_pos

        # 检查确认按钮
        if hasattr(self, '_rename_confirm_rect') and self._rename_confirm_rect.collidepoint(x, y):
            self._confirm_rename()
            return True

        # 检查取消按钮
        if hasattr(self, '_rename_cancel_rect') and self._rename_cancel_rect.collidepoint(x, y):
            self._rename_active = False
            return True

        # 点击对话框外部也关闭
        return True

    def _render_rename_dialog(self):
        """渲染重命名对话框"""
        if not self._rename_active:
            return

        # 对话框尺寸
        dialog_w = 250
        dialog_h = 100
        dialog_x = (self.screen_width - dialog_w) // 2
        dialog_y = (self.screen_height - dialog_h) // 2

        # 半透明背景遮罩
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        # 对话框背景
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        pygame.draw.rect(self.screen, (50, 50, 60), dialog_rect, border_radius=8)
        pygame.draw.rect(self.screen, (100, 100, 120), dialog_rect, 2, border_radius=8)

        # 标题
        title = self.font_small.render("输入新名称", True, (255, 255, 255))
        title_rect = title.get_rect(centerx=dialog_rect.centerx, top=dialog_y + 10)
        self.screen.blit(title, title_rect)

        # 输入框
        input_rect = pygame.Rect(dialog_x + 20, dialog_y + 35, dialog_w - 40, 25)
        pygame.draw.rect(self.screen, (30, 30, 40), input_rect, border_radius=3)
        pygame.draw.rect(self.screen, (80, 80, 100), input_rect, 1, border_radius=3)

        # 输入文本
        input_text = self.font_small.render(self._rename_text, True, (255, 255, 255))
        # 裁剪超出部分
        text_rect = input_text.get_rect(midleft=(input_rect.x + 5, input_rect.centery))
        self.screen.set_clip(input_rect)
        self.screen.blit(input_text, text_rect)
        self.screen.set_clip(None)

        # 光标
        cursor_x = input_rect.x + 5 + text_rect.width
        if cursor_x < input_rect.right - 5:
            pygame.draw.line(self.screen, (255, 255, 255),
                           (cursor_x, input_rect.y + 4),
                           (cursor_x, input_rect.y + input_rect.height - 4), 1)

        # 提示文字
        hint = self.font_small.render(f"长度限制: {len(self._rename_text)}/{self._rename_max_length}", True, (150, 150, 150))
        hint_rect = hint.get_rect(centerx=dialog_rect.centerx, top=dialog_y + 65)
        self.screen.blit(hint, hint_rect)

        # 确认/取消按钮
        btn_y = dialog_y + dialog_h - 25
        btn_w = 60
        btn_h = 20

        # 确认按钮
        confirm_rect = pygame.Rect(dialog_x + 30, btn_y, btn_w, btn_h)
        pygame.draw.rect(self.screen, (80, 120, 80), confirm_rect, border_radius=3)
        confirm_text = self.font_small.render("确认", True, (200, 255, 200))
        confirm_text_rect = confirm_text.get_rect(center=confirm_rect.center)
        self.screen.blit(confirm_text, confirm_text_rect)
        self._rename_confirm_rect = confirm_rect

        # 取消按钮
        cancel_rect = pygame.Rect(dialog_x + dialog_w - 90, btn_y, btn_w, btn_h)
        pygame.draw.rect(self.screen, (120, 80, 80), cancel_rect, border_radius=3)
        cancel_text = self.font_small.render("取消", True, (255, 200, 200))
        cancel_text_rect = cancel_text.get_rect(center=cancel_rect.center)
        self.screen.blit(cancel_text, cancel_text_rect)
        self._rename_cancel_rect = cancel_rect

    def handle_inventory_drag(self, pos: tuple):
        """处理背包界面的拖动（用于滑动条）"""
        if not hasattr(self, '_inv_dragging_slider') or not self._inv_dragging_slider:
            return
        if not hasattr(self, '_inv_slider_rect'):
            return

        x, y = pos
        items = self.get_inv_items()
        if items and self.inv_selected_idx < len(items):
            max_qty = items[self.inv_selected_idx]['amount']
            if max_qty > 1:
                ratio = (x - self._inv_slider_rect.x) / self._inv_slider_rect.width
                ratio = max(0, min(1, ratio))
                self._inv_sell_qty = max(1, int(ratio * (max_qty - 1)) + 1)

    def scroll_inventory_detail(self, delta: int, mouse_pos: tuple = None):
        """滚动背包/家具放置面板"""
        if mouse_pos is None:
            return

        x, y = mouse_pos

        # 家具放置菜单滚动
        if self.current_menu == "furniture_place":
            if hasattr(self, '_fp_list_rect') and self._fp_list_rect.collidepoint(x, y):
                items = self.get_fp_items()
                cell_size = max(50, min(65, self.screen_width // 12))
                list_w = 390  # panel_w - 10
                cols = max(1, list_w // cell_size)
                item_h = cell_size
                total_rows = (len(items) + cols - 1) // cols if items else 0
                visible_rows = self._fp_list_rect.height // item_h
                max_scroll = max(0, total_rows - visible_rows)
                scroll_amount = 1 if delta > 0 else -1
                self._fp_list_scroll = max(0, min(max_scroll, self._fp_list_scroll - scroll_amount))
            return

        # 背包面板滚动
        # 判断鼠标在左侧面板还是右侧面板
        if hasattr(self, '_inv_list_rect') and self._inv_list_rect.collidepoint(x, y):
            # 左侧物品列表滚动
            if not hasattr(self, '_inv_list_scroll'):
                self._inv_list_scroll = 0
            items = self.get_inv_items()
            cell_size = max(50, min(65, self.screen_width // 12))  # 与渲染时的cell_size一致（自适应屏幕）
            margin = 40
            list_w = int((self.screen_width - margin * 2) * 0.65)  # 与渲染时的list_w一致
            cols = max(1, list_w // cell_size)
            item_h = cell_size
            total_rows = (len(items) + cols - 1) // cols if items else 0
            visible_rows = self._inv_list_rect.height // item_h
            max_scroll = max(0, total_rows - visible_rows)
            # 每次滚动一行
            scroll_amount = 1 if delta > 0 else -1
            self._inv_list_scroll = max(0, min(max_scroll, self._inv_list_scroll - scroll_amount))
        elif hasattr(self, '_inv_detail_rect') and self._inv_detail_rect.collidepoint(x, y):
            # 右侧详情面板滚动
            if not hasattr(self, '_inv_detail_scroll'):
                self._inv_detail_scroll = 0
            min_scroll = -100
            scroll_amount = 15 if delta > 0 else -15
            self._inv_detail_scroll = max(min_scroll, min(0, self._inv_detail_scroll + scroll_amount))

    def close_menu(self):
        """关闭菜单"""
        self.current_menu = None
        self.menu_items = []
        self.menu_scroll_offset = 0
        # 隐藏设置面板
        if hasattr(self, 'settings_panel'):
            self.settings_panel.hide()

    def _execute_unlock(self):
        """执行解锁区块操作"""
        if not hasattr(self, '_unlock_pending') or not self._unlock_pending:
            return

        grid_x, grid_y = self._unlock_pending
        cost = self._unlock_cost

        # 检查金币是否足够
        if self.game_manager.coins < cost:
            print(f"金币不足，需要 {cost}，当前 {self.game_manager.coins}")
            self.close_menu()
            return

        # 扣除金币
        if self.game_manager.spend_coins(cost):
            # 解锁区块
            if self.world.unlock_tile(grid_x, grid_y):
                # 记录已解锁区块
                tile_key = f"{grid_x},{grid_y}"
                if tile_key not in self.game_manager.unlocked_tiles:
                    self.game_manager.unlocked_tiles.append(tile_key)
                print(f"解锁成功: 区块({grid_x},{grid_y})，花费 {cost} 金币")

                # 自动保存
                if hasattr(self.game_manager, 'save_manager'):
                    self.game_manager.save_manager.auto_save_on_action("解锁区块")

        self._unlock_pending = None
        self._unlock_cost = 0
        self.close_menu()

    def show_floor_style_menu(self, grid_x: int, grid_y: int):
        """显示地板样式选择器（发散线条交互）"""
        # 计算木板在屏幕上的中心位置
        cx, cy = self.world.grid_to_world(grid_x + 0.5, grid_y + 0.5)
        # 使用 camera.world_to_screen 转换
        if self.camera:
            screen_x, screen_y = self.camera.world_to_screen((cx, cy))
        else:
            screen_x, screen_y = cx, cy

        self.floor_selector_active = True
        self.floor_selector_grid = (grid_x, grid_y)
        self.floor_selector_center = (screen_x, screen_y)

        # 计算最佳发散方向（哪边空间最多）
        direction = self._calc_best_direction(screen_x, screen_y)
        self.floor_selector_direction = direction

        # 计算三条线的终点
        self._calc_selector_lines()

    def show_farm_style_menu(self, grid_x: int, grid_y: int):
        """显示种植区样式选择器（发散线条交互）"""
        # 计算种植区在屏幕上的中心位置
        cx, cy = self.world.grid_to_world(grid_x + 0.5, grid_y + 0.5)
        # 使用 camera.world_to_screen 转换
        if self.camera:
            screen_x, screen_y = self.camera.world_to_screen((cx, cy))
        else:
            screen_x, screen_y = cx, cy

        # 复用地板选择器的状态，但修改样式列表
        self.floor_selector_active = True
        self.floor_selector_grid = (grid_x, grid_y)
        self.floor_selector_center = (screen_x, screen_y)

        # 计算最佳发散方向（哪边空间最多）
        direction = self._calc_best_direction(screen_x, screen_y)
        self.floor_selector_direction = direction

        # 计算四条线的终点（种植区有4种类型）
        self._calc_farm_selector_lines()

    def _calc_farm_selector_lines(self):
        """计算种植区四条发散线的终点"""
        if not self.floor_selector_center or not self.floor_selector_direction:
            return

        cx, cy = self.floor_selector_center
        dx, dy = self.floor_selector_direction

        import math

        # 计算基准角度
        base_angle = math.atan2(dy, dx)

        # 四条线的角度：-60, -20, +20, +60 度
        angles = [
            base_angle - math.radians(60),
            base_angle - math.radians(20),
            base_angle + math.radians(20),
            base_angle + math.radians(60)
        ]

        # 样式信息
        styles = [
            {"index": 0, "name": "土生"},
            {"index": 1, "name": "水生"},
            {"index": 2, "name": "盆栽"},
            {"index": 3, "name": "沙生"}
        ]

        # 边距
        preview_radius = max(20, min(25, self.screen_width // 30))  # 圆圈半径（自适应屏幕）
        preview_margin = preview_radius + 10
        top_margin = 40   # 顶部状态栏30 + 10
        bottom_margin = self.screen_height - 40  # 底部按钮栏 + 10
        left_margin = 10
        right_margin = self.screen_width - 10

        self.floor_selector_lines = []
        for i, (angle, style) in enumerate(zip(angles, styles)):
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            # 计算每条线在屏幕内的最大可用长度
            max_lengths = []
            if cos_a > 0.001:
                max_lengths.append((right_margin - preview_margin - cx) / cos_a)
            elif cos_a < -0.001:
                max_lengths.append((cx - left_margin - preview_margin) / (-cos_a))

            if sin_a > 0.001:
                max_lengths.append((bottom_margin - preview_margin - cy) / sin_a)
            elif sin_a < -0.001:
                max_lengths.append((cy - top_margin - preview_margin) / (-sin_a))

            # 取最小的可用长度
            available_length = min(max_lengths) if max_lengths else 60
            line_length = max(40, min(120, available_length))

            # click_pos 是圆圈中心位置（线条终点）
            click_x = cx + cos_a * line_length
            click_y = cy + sin_a * line_length

            # clamp确保不出界
            click_x = max(preview_margin, min(click_x, self.screen_width - preview_margin))
            click_y = max(top_margin + preview_margin, min(click_y, bottom_margin - preview_margin))

            # end 是线条终点，在圆圈边缘
            dist = math.sqrt((click_x - cx) ** 2 + (click_y - cy) ** 2)
            if dist > 0:
                end_x = cx + (click_x - cx) * (dist - preview_radius) / dist
                end_y = cy + (click_y - cy) * (dist - preview_radius) / dist
            else:
                end_x, end_y = click_x, click_y

            line_data = {
                "start": (cx, cy),
                "end": (end_x, end_y),
                "click_pos": (click_x, click_y),
                "style": style,
                "rect": pygame.Rect(click_x - preview_radius, click_y - preview_radius, preview_radius * 2, preview_radius * 2)
            }
            self.floor_selector_lines.append(line_data)

    def _calc_best_direction(self, center_x: float, center_y: float) -> tuple:
        """计算最佳发散方向（选择空间最多的方向）"""
        margin = 50  # 边距
        line_length = 100  # 线条长度

        # 计算四个方向的可用空间（考虑线条长度）
        space_left = center_x - margin - line_length
        space_right = self.screen_width - center_x - margin - line_length
        space_up = center_y - 30 - margin - line_length  # 顶部状态栏30px
        space_down = self.screen_height - center_y - 30 - margin - line_length  # 底部按钮栏30px

        # 过滤掉空间不足的方向（至少需要线条长度+边距）
        min_space = line_length + margin
        valid_spaces = {}
        if space_left >= min_space:
            valid_spaces['left'] = space_left
        if space_right >= min_space:
            valid_spaces['right'] = space_right
        if space_up >= min_space:
            valid_spaces['up'] = space_up
        if space_down >= min_space:
            valid_spaces['down'] = space_down

        # 如果没有足够空间的方向，使用默认方向（根据位置选择）
        if not valid_spaces:
            # 根据位置选择最可能的方向
            if center_x < self.screen_width / 2:
                best_dir = 'right'
            else:
                best_dir = 'left'
        else:
            # 选择空间最大的方向
            best_dir = max(valid_spaces, key=valid_spaces.get)

        # 返回方向向量
        directions = {
            'left': (-1, 0),
            'right': (1, 0),
            'up': (0, -1),
            'down': (0, 1)
        }

        return directions[best_dir]

    def _calc_selector_lines(self):
        """计算三条发散线的终点"""
        if not self.floor_selector_center or not self.floor_selector_direction:
            return

        cx, cy = self.floor_selector_center
        dx, dy = self.floor_selector_direction

        # 三条线的分散角度
        spread_angle = 45  # 增大角度，让圆圈更分开

        import math

        # 计算基准角度
        base_angle = math.atan2(dy, dx)

        # 三条线的角度：-spread_angle, 0, +spread_angle
        angles = [
            base_angle - math.radians(spread_angle),
            base_angle,
            base_angle + math.radians(spread_angle)
        ]

        # 样式信息
        styles = [
            {"index": 0, "name": "木地板"},
            {"index": 1, "name": "瓷砖"},
            {"index": 2, "name": "地毯"}
        ]

        # 边距（预览图半径+文字空间）
        preview_radius = max(20, min(25, self.screen_width // 30))  # 圆圈半径（自适应屏幕）
        preview_margin = preview_radius + 10
        top_margin = 40   # 顶部状态栏30 + 10
        bottom_margin = self.screen_height - 40  # 底部按钮栏 + 10
        left_margin = 10
        right_margin = self.screen_width - 10

        self.floor_selector_lines = []
        for i, (angle, style) in enumerate(zip(angles, styles)):
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            # 计算每条线在屏幕内的最大可用长度
            max_lengths = []
            if cos_a > 0.001:
                max_lengths.append((right_margin - preview_margin - cx) / cos_a)
            elif cos_a < -0.001:
                max_lengths.append((cx - left_margin - preview_margin) / (-cos_a))

            if sin_a > 0.001:
                max_lengths.append((bottom_margin - preview_margin - cy) / sin_a)
            elif sin_a < -0.001:
                max_lengths.append((cy - top_margin - preview_margin) / (-sin_a))

            # 取最小的可用长度
            available_length = min(max_lengths) if max_lengths else 60
            line_length = max(40, min(120, available_length))

            # click_pos 是圆圈中心位置（线条终点）
            click_x = cx + cos_a * line_length
            click_y = cy + sin_a * line_length

            # clamp确保不出界
            click_x = max(preview_margin, min(click_x, self.screen_width - preview_margin))
            click_y = max(top_margin + preview_margin, min(click_y, bottom_margin - preview_margin))

            # end 是线条终点，在圆圈边缘（不是穿过圆圈）
            # 线条从中心画到 click_pos 前方 preview_radius 处
            dist = math.sqrt((click_x - cx) ** 2 + (click_y - cy) ** 2)
            if dist > 0:
                end_x = cx + (click_x - cx) * (dist - preview_radius) / dist
                end_y = cy + (click_y - cy) * (dist - preview_radius) / dist
            else:
                end_x, end_y = click_x, click_y

            line_data = {
                "start": (cx, cy),
                "end": (end_x, end_y),
                "click_pos": (click_x, click_y),
                "style": style,
                "rect": pygame.Rect(click_x - preview_radius, click_y - preview_radius, preview_radius * 2, preview_radius * 2)
            }
            self.floor_selector_lines.append(line_data)

    def show_unlock_menu(self, grid_x: int, grid_y: int):
        """显示解锁确认对话框"""
        # 计算解锁价格
        unlock_count = self.world.get_unlocked_count()
        cost = self.world.get_unlock_cost(unlock_count)

        # 设置解锁待确认数据
        self._unlock_pending = (grid_x, grid_y)
        self._unlock_cost = cost
        self._unlock_count = unlock_count

        # 构建菜单项
        self.menu_items = [
            {"text": f"解锁区块({grid_x},{grid_y})", "rect": None, "action": None},
            {"text": f"需要: {cost} 金币", "rect": None, "action": None},
            {"text": f"当前: {self.game_manager.coins} 金币", "rect": None, "action": None},
            {"text": "确认解锁", "rect": None, "action": "unlock_confirm"},
            {"text": "取消", "rect": None, "action": "close"},
        ]

        # 计算菜单位置（居中）
        menu_width = min(180, self.screen_width - 20)
        menu_height = len(self.menu_items) * 25 + 20
        menu_x = (self.screen_width - menu_width) // 2
        menu_y = (self.screen_height - menu_height) // 2

        self.menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        self.current_menu = "unlock_confirm"
        self.menu_scroll_offset = 0
        self.menu_max_scroll = 0

    def show_seed_select_menu(self, farm_type: int, grid_x: int, grid_y: int, slot_idx: int):
        """显示种子选择器（发散线条交互）"""
        from ..entities.crop import Crop

        # 获取该种植区类型可种植的种子
        available_seeds = []
        for seed_id in self.game_manager.unlocked_seeds:
            crop_data = Crop.CROP_DATA.get(seed_id, {})
            if crop_data.get("type") == farm_type:
                seeds = self.game_manager.inventory.get("seeds", {})
                if seeds.get(seed_id, 0) > 0:
                    available_seeds.append({"id": seed_id, "name": crop_data["name"], "count": seeds[seed_id]})

        if not available_seeds:
            return

        # 计算屏幕中心位置
        cx, cy = self.world.grid_to_world(grid_x + 0.5, grid_y + 0.5)
        if self.camera:
            screen_x, screen_y = self.camera.world_to_screen((cx, cy))
        else:
            screen_x, screen_y = cx, cy

        self.seed_selector_active = True
        self.seed_selector_grid = (grid_x, grid_y)
        self.seed_selector_center = (screen_x, screen_y)
        self.seed_selector_farm_type = farm_type
        self.seed_selector_slot_idx = slot_idx

        # 计算发散方向
        direction = self._calc_best_direction(screen_x, screen_y)
        self.seed_selector_direction = direction

        # 计算线条
        self._calc_seed_selector_lines(available_seeds)

    def _calc_seed_selector_lines(self, available_seeds: list):
        """计算种子选择器的发散线条"""
        if not self.seed_selector_center or not self.seed_selector_direction:
            return

        import math

        cx, cy = self.seed_selector_center
        dx, dy = self.seed_selector_direction
        base_angle = math.atan2(dy, dx)

        n = len(available_seeds)
        if n == 0:
            return

        # 根据种子数量计算角度分布
        if n == 1:
            angles = [base_angle]
        elif n == 2:
            angles = [base_angle - math.radians(30), base_angle + math.radians(30)]
        elif n == 3:
            angles = [base_angle - math.radians(45), base_angle, base_angle + math.radians(45)]
        else:
            spread = min(90, n * 20)
            angles = [base_angle + math.radians(-spread + i * (2 * spread / (n - 1))) for i in range(n)]

        # 边距
        preview_radius = max(20, min(25, self.screen_width // 30))
        preview_margin = preview_radius + 10
        top_margin = 40
        bottom_margin = self.screen_height - 40
        left_margin = 10
        right_margin = self.screen_width - 10

        # 计算每条线的最大可用长度
        max_line_lengths = []
        for angle in angles:
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            max_lengths = []
            if cos_a > 0.001:
                max_lengths.append((right_margin - preview_margin - cx) / cos_a)
            elif cos_a < -0.001:
                max_lengths.append((cx - left_margin - preview_margin) / (-cos_a))
            if sin_a > 0.001:
                max_lengths.append((bottom_margin - preview_margin - cy) / sin_a)
            elif sin_a < -0.001:
                max_lengths.append((cy - top_margin - preview_margin) / (-sin_a))
            max_line_lengths.append(min(max_lengths) if max_lengths else 60)

        # 先放到最大长度，然后逐个调整避免重叠
        # 重叠从圆圈边缘计算：overlap = (2*radius) - center_distance
        # 允许最大重叠 = 20% * (2*radius) = 0.2 * 50 = 10px
        diameter = preview_radius * 2
        max_overlap = diameter * 0.2  # 10px

        # 初始位置：每条线用最大长度
        positions = []
        for i, angle in enumerate(angles):
            length = max_line_lengths[i]
            px = cx + math.cos(angle) * length
            py = cy + math.sin(angle) * length
            px = max(preview_margin, min(px, self.screen_width - preview_margin))
            py = max(top_margin + preview_margin, min(py, bottom_margin - preview_margin))
            positions.append([px, py])

        # 迭代调整：如果重叠超限，缩短较长的线
        for _ in range(10):  # 最多迭代10次
            adjusted = False
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    dist = math.sqrt((positions[i][0] - positions[j][0])**2 + (positions[i][1] - positions[j][1])**2)
                    overlap = diameter - dist
                    if overlap > max_overlap:
                        # 缩短两条线中较长的那条
                        d_i = math.sqrt((positions[i][0] - cx)**2 + (positions[i][1] - cy)**2)
                        d_j = math.sqrt((positions[j][0] - cx)**2 + (positions[j][1] - cy)**2)
                        shrink = (overlap - max_overlap) / 2 + 5  # 额外留5px余量
                        if d_i >= d_j:
                            # 缩短i
                            angle_i = math.atan2(positions[i][1] - cy, positions[i][0] - cx)
                            new_d = max(40, d_i - shrink)
                            positions[i][0] = cx + math.cos(angle_i) * new_d
                            positions[i][1] = cy + math.sin(angle_i) * new_d
                        else:
                            # 缩短j
                            angle_j = math.atan2(positions[j][1] - cy, positions[j][0] - cx)
                            new_d = max(40, d_j - shrink)
                            positions[j][0] = cx + math.cos(angle_j) * new_d
                            positions[j][1] = cy + math.sin(angle_j) * new_d
                        # 限制在屏幕内
                        positions[i][0] = max(preview_margin, min(positions[i][0], self.screen_width - preview_margin))
                        positions[i][1] = max(top_margin + preview_margin, min(positions[i][1], bottom_margin - preview_margin))
                        positions[j][0] = max(preview_margin, min(positions[j][0], self.screen_width - preview_margin))
                        positions[j][1] = max(top_margin + preview_margin, min(positions[j][1], bottom_margin - preview_margin))
                        adjusted = True
            if not adjusted:
                break

        self.seed_selector_lines = []
        for i, (angle, seed) in enumerate(zip(angles, available_seeds)):
            click_x, click_y = positions[i]

            dist = math.sqrt((click_x - cx) ** 2 + (click_y - cy) ** 2)
            if dist > 0:
                end_x = cx + (click_x - cx) * (dist - preview_radius) / dist
                end_y = cy + (click_y - cy) * (dist - preview_radius) / dist
            else:
                end_x, end_y = click_x, click_y

            # 获取预览图
            preview = self.seed_previews.get(seed["id"])

            line_data = {
                "start": (cx, cy),
                "end": (end_x, end_y),
                "click_pos": (click_x, click_y),
                "seed": seed,
                "preview": preview,
                "rect": pygame.Rect(click_x - preview_radius, click_y - preview_radius, preview_radius * 2, preview_radius * 2)
            }
            self.seed_selector_lines.append(line_data)

    def handle_seed_selector_click(self, screen_pos: tuple) -> bool:
        """处理种子选择器的点击"""
        if not self.seed_selector_active:
            return False

        x, y = screen_pos

        for i, line in enumerate(self.seed_selector_lines):
            collide = line["rect"].collidepoint(x, y)
            if collide:
                seed = line["seed"]
                self.game_manager.selected_seeds[str(self.seed_selector_farm_type)] = seed["id"]
                if hasattr(self.game_manager, 'save_manager'):
                    self.game_manager.save_manager.auto_save_on_action("选择种子")
                self.close_seed_selector()
                return True

        self.close_seed_selector()
        return True

    def close_seed_selector(self):
        """关闭种子选择器"""
        self.seed_selector_active = False
        self.seed_selector_grid = None
        self.seed_selector_center = None
        self.seed_selector_lines = []
        self.seed_selector_direction = None
        self.seed_selector_farm_type = -1
        self.seed_selector_slot_idx = -1
        # 清除宠物选中状态
        if hasattr(self, '_action_pet') and self._action_pet:
            self._action_pet = None
            if hasattr(self.world, 'selected_object'):
                self.world.selected_object = None
            self.selected_info = None

    def handle_feed_menu_click(self, screen_pos):
        """处理喂食菜单点击"""
        if not self.feed_menu_active:
            return False

        x, y = screen_pos

        # 检查关闭按钮
        if self._feed_close_rect and self._feed_close_rect.collidepoint(x, y):
            self.close_feed_menu()
            return True

        # 检查确认按钮
        if self._feed_confirm_rect and self._feed_confirm_rect.collidepoint(x, y):
            if self.feed_menu_items and 0 <= self.feed_menu_selected_idx < len(self.feed_menu_items):
                selected = self.feed_menu_items[self.feed_menu_selected_idx]
                self._confirm_feed(selected['id'])
            return True

        # 检查物品列表点击
        if hasattr(self, '_feed_item_rects'):
            for item_rect, idx in self._feed_item_rects:
                if item_rect.collidepoint(x, y):
                    self.feed_menu_selected_idx = idx
                    return True

        # 点击菜单外部关闭
        if self._feed_menu_rect and not self._feed_menu_rect.collidepoint(x, y):
            self.close_feed_menu()
            return True

        # 点击菜单内部但没有点击到任何元素，也返回True阻止后续处理
        if self._feed_menu_rect and self._feed_menu_rect.collidepoint(x, y):
            return True

        return False

    def _confirm_feed(self, crop_id):
        """确认喂食"""
        if hasattr(self.world, 'pet_manager') and hasattr(self.game_manager, 'inventory'):
            success, msg = self.world.pet_manager.feed_pet_with_crop(
                self.feed_menu_pet_id, crop_id, self.game_manager.inventory
            )
            print(msg)
            if success:
                # 保存
                if hasattr(self.game_manager, 'save_manager'):
                    self.game_manager.save_manager.auto_save_on_action("喂食宠物")
        self.close_feed_menu()

    def show_feed_menu(self, pet_id):
        """显示喂食菜单"""
        self.feed_menu_active = True
        self.feed_menu_pet_id = pet_id
        self.feed_menu_selected_idx = 0
        self.feed_menu_scroll = 0

        # 暂停宠物移动
        if hasattr(self.world, 'pet_manager'):
            for pet in self.world.pet_manager.scene_pets:
                if pet.pet_id == pet_id:
                    pet.paused = True
                    break

        # 获取可喂食的作物列表
        if hasattr(self.world, 'pet_manager') and hasattr(self.game_manager, 'inventory'):
            self.feed_menu_items = self.world.pet_manager.get_feedable_crops_from_inventory(
                self.game_manager.inventory
            )
        else:
            self.feed_menu_items = []

        # 菜单布局（居中的面板）
        panel_w = min(250, self.screen_width - 80)
        panel_h = min(300, self.screen_height - 100)
        panel_x = (self.screen_width - panel_w) // 2
        panel_y = (self.screen_height - panel_h) // 2
        self._feed_menu_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    def close_feed_menu(self):
        """关闭喂食菜单"""
        # 恢复宠物移动
        if self.feed_menu_pet_id and hasattr(self.world, 'pet_manager'):
            for pet in self.world.pet_manager.scene_pets:
                if pet.pet_id == self.feed_menu_pet_id:
                    pet.paused = False
                    break

        self.feed_menu_active = False
        self.feed_menu_pet_id = None
        self.feed_menu_items = []
        self._feed_menu_rect = None
        self._feed_confirm_rect = None
        self._feed_close_rect = None
        self._feed_item_rects = []

    def scroll_feed_menu(self, direction):
        """滚动喂食菜单物品列表"""
        if not self.feed_menu_active:
            return

        item_h = 40
        list_h = self._feed_menu_rect.height - 90 if self._feed_menu_rect else 200
        visible_count = max(1, list_h // item_h)
        max_scroll = max(0, len(self.feed_menu_items) - visible_count)

        # 方向取反：向上滚轮显示更早的物品
        self.feed_menu_scroll -= direction
        self.feed_menu_scroll = max(0, min(self.feed_menu_scroll, max_scroll))

    def show_crop_action_menu(self, crop):
        """显示作物操作选择器（浇水）"""
        import math

        # 计算作物屏幕位置
        if self.camera:
            screen_x, screen_y = self.camera.world_to_screen((crop.x, crop.y))
        else:
            screen_x, screen_y = crop.x, crop.y

        # 复用 seed_selector 状态
        self.seed_selector_active = True
        self.seed_selector_center = (screen_x, screen_y)
        self.seed_selector_lines = []

        # 计算发散方向
        direction = self._calc_best_direction(screen_x, screen_y)
        dx, dy = direction
        base_angle = math.atan2(dy, dx)

        # 根据水分决定显示哪些操作
        actions = []
        if crop.water_level < 80:
            # 水分不满，显示浇水
            actions.append({"id": "water", "name": "浇水", "color": (100, 150, 255)})

        # 如果没有可执行的操作，直接关闭
        if not actions:
            return

        n = len(actions)
        if n == 1:
            angles = [base_angle]
        elif n == 2:
            angles = [base_angle - math.radians(25), base_angle + math.radians(25)]
        elif n == 3:
            angles = [base_angle - math.radians(40), base_angle, base_angle + math.radians(40)]

        preview_radius = max(20, min(25, self.screen_width // 30))
        preview_margin = preview_radius + 10
        top_margin = 40
        bottom_margin = self.screen_height - 40
        left_margin = 10
        right_margin = self.screen_width - 10

        self.seed_selector_lines = []
        for i, (angle, action) in enumerate(zip(angles, actions)):
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            max_lengths = []
            if cos_a > 0.001:
                max_lengths.append((right_margin - preview_margin - screen_x) / cos_a)
            elif cos_a < -0.001:
                max_lengths.append((screen_x - left_margin - preview_margin) / (-cos_a))
            if sin_a > 0.001:
                max_lengths.append((bottom_margin - preview_margin - screen_y) / sin_a)
            elif sin_a < -0.001:
                max_lengths.append((screen_y - top_margin - preview_margin) / (-sin_a))

            available_length = min(max_lengths) if max_lengths else 60
            line_length = max(40, min(100, available_length))

            click_x = screen_x + cos_a * line_length
            click_y = screen_y + sin_a * line_length
            click_x = max(preview_margin, min(click_x, self.screen_width - preview_margin))
            click_y = max(top_margin + preview_margin, min(click_y, bottom_margin - preview_margin))

            dist = math.sqrt((click_x - screen_x) ** 2 + (click_y - screen_y) ** 2)
            if dist > 0:
                end_x = screen_x + (click_x - screen_x) * (dist - preview_radius) / dist
                end_y = screen_y + (click_y - screen_y) * (dist - preview_radius) / dist
            else:
                end_x, end_y = click_x, click_y

            line_data = {
                "start": (screen_x, screen_y),
                "end": (end_x, end_y),
                "click_pos": (click_x, click_y),
                "action": action,
                "rect": pygame.Rect(click_x - preview_radius, click_y - preview_radius, preview_radius * 2, preview_radius * 2)
            }
            self.seed_selector_lines.append(line_data)

        # 保存作物引用
        self._action_crop = crop

    def handle_crop_action_click(self, screen_pos: tuple) -> bool:
        """处理作物操作选择器的点击"""
        if not self.seed_selector_active or not hasattr(self, '_action_crop'):
            return False

        x, y = screen_pos

        for line in self.seed_selector_lines:
            if line["rect"].collidepoint(x, y):
                action = line["action"]["id"]
                crop = self._action_crop

                if action == "water":
                    water_cost = 10
                    if self.game_manager.water >= water_cost:
                        self.game_manager.water -= water_cost
                        crop.water(40)
                        if hasattr(self.game_manager, 'save_manager'):
                            self.game_manager.save_manager.auto_save_on_action("浇水")
                elif action == "fertilize":
                    crop.fertilize()

                self.close_seed_selector()
                self._action_crop = None
                return True

        self.close_seed_selector()
        self._action_crop = None
        return True

    def show_pet_interaction_menu(self, pet):
        """显示宠物交互菜单"""
        if not pet or not self.camera:
            return

        # 停止宠物移动
        pet.target_pos = None
        pet.path = []
        pet.path_index = 0
        pet.state = "idle"

        # 更新选中信息（显示顶部信息栏）
        self.update_selected_info(pet)

        # 计算宠物 footprint 中心的屏幕位置
        world_fp = pet.get_footprint_world()
        if world_fp:
            center_x = sum(p[0] for p in world_fp) / len(world_fp)
            center_y = sum(p[1] for p in world_fp) / len(world_fp)
        else:
            center_x, center_y = pet.x, pet.y
        screen_x, screen_y = self.camera.world_to_screen((center_x, center_y))

        # 复用 seed_selector 状态
        self.seed_selector_active = True
        self.seed_selector_center = (screen_x, screen_y)
        self.seed_selector_lines = []

        # 计算发散方向
        direction = self._calc_best_direction(screen_x, screen_y)
        dx, dy = direction
        base_angle = math.atan2(dy, dx)

        # 宠物交互操作
        actions = [
            {"id": "pet", "name": "抚摸", "color": (255, 150, 200)},
            {"id": "feed", "name": "喂食", "color": (255, 200, 100)},
            {"id": "recall", "name": "收回", "color": (200, 200, 200)},
        ]

        n = len(actions)
        if n == 1:
            angles = [base_angle]
        elif n == 2:
            angles = [base_angle - math.radians(30), base_angle + math.radians(30)]
        elif n == 3:
            angles = [base_angle - math.radians(45), base_angle, base_angle + math.radians(45)]
        else:
            spread = min(90, n * 20)
            angles = [base_angle + math.radians(-spread + i * (2 * spread / (n - 1))) for i in range(n)]

        # 边距（与种植物选择器一致）
        preview_radius = max(20, min(25, self.screen_width // 30))
        preview_margin = preview_radius + 10
        top_margin = 40
        bottom_margin = self.screen_height - 40
        left_margin = 10
        right_margin = self.screen_width - 10

        # 计算每条线的最大可用长度
        max_line_lengths = []
        for angle in angles:
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            max_lengths = []
            if cos_a > 0.001:
                max_lengths.append((right_margin - preview_margin - screen_x) / cos_a)
            elif cos_a < -0.001:
                max_lengths.append((screen_x - left_margin - preview_margin) / (-cos_a))
            if sin_a > 0.001:
                max_lengths.append((bottom_margin - preview_margin - screen_y) / sin_a)
            elif sin_a < -0.001:
                max_lengths.append((screen_y - top_margin - preview_margin) / (-sin_a))
            max_line_lengths.append(min(max_lengths) if max_lengths else 60)

        # 初始位置：每条线用最大长度
        positions = []
        for i, angle in enumerate(angles):
            length = max_line_lengths[i]
            px = screen_x + math.cos(angle) * length
            py = screen_y + math.sin(angle) * length
            px = max(preview_margin, min(px, self.screen_width - preview_margin))
            py = max(top_margin + preview_margin, min(py, bottom_margin - preview_margin))
            positions.append([px, py])

        # 重叠检测和调整（与种植物选择器一致）
        diameter = preview_radius * 2
        max_overlap = diameter * 0.2  # 允许最大重叠 20%

        # 迭代调整：如果重叠超限，缩短较长的线
        for _ in range(10):
            adjusted = False
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    dist = math.sqrt((positions[i][0] - positions[j][0])**2 + (positions[i][1] - positions[j][1])**2)
                    overlap = diameter - dist
                    if overlap > max_overlap:
                        # 缩短两条线中较长的那条
                        d_i = math.sqrt((positions[i][0] - screen_x)**2 + (positions[i][1] - screen_y)**2)
                        d_j = math.sqrt((positions[j][0] - screen_x)**2 + (positions[j][1] - screen_y)**2)
                        shrink = (overlap - max_overlap) / 2 + 5  # 额外留5px余量
                        if d_i >= d_j:
                            angle_i = math.atan2(positions[i][1] - screen_y, positions[i][0] - screen_x)
                            new_d = max(40, d_i - shrink)
                            positions[i][0] = screen_x + math.cos(angle_i) * new_d
                            positions[i][1] = screen_y + math.sin(angle_i) * new_d
                        else:
                            angle_j = math.atan2(positions[j][1] - screen_y, positions[j][0] - screen_x)
                            new_d = max(40, d_j - shrink)
                            positions[j][0] = screen_x + math.cos(angle_j) * new_d
                            positions[j][1] = screen_y + math.sin(angle_j) * new_d
                        # 限制在屏幕内
                        positions[i][0] = max(preview_margin, min(positions[i][0], self.screen_width - preview_margin))
                        positions[i][1] = max(top_margin + preview_margin, min(positions[i][1], bottom_margin - preview_margin))
                        positions[j][0] = max(preview_margin, min(positions[j][0], self.screen_width - preview_margin))
                        positions[j][1] = max(top_margin + preview_margin, min(positions[j][1], bottom_margin - preview_margin))
                        adjusted = True
            if not adjusted:
                break

        self.seed_selector_lines = []
        for i, (angle, action) in enumerate(zip(angles, actions)):
            click_x, click_y = positions[i]

            dist = math.sqrt((click_x - screen_x) ** 2 + (click_y - screen_y) ** 2)
            if dist > 0:
                end_x = screen_x + (click_x - screen_x) * (dist - preview_radius) / dist
                end_y = screen_y + (click_y - screen_y) * (dist - preview_radius) / dist
            else:
                end_x, end_y = click_x, click_y

            line_data = {
                "start": (screen_x, screen_y),
                "end": (end_x, end_y),
                "click_pos": (click_x, click_y),
                "color": action["color"],
                "action": action,
                "rect": pygame.Rect(click_x - preview_radius, click_y - preview_radius, preview_radius * 2, preview_radius * 2)
            }
            self.seed_selector_lines.append(line_data)

        # 保存宠物引用
        self._action_pet = pet

    def handle_pet_interaction_click(self, screen_pos: tuple) -> bool:
        """处理宠物交互选择器的点击"""
        if not self.seed_selector_active or not hasattr(self, '_action_pet'):
            return False

        x, y = screen_pos

        for line in self.seed_selector_lines:
            if line["rect"].collidepoint(x, y):
                action = line["action"]["id"]
                pet = self._action_pet

                if action == "pet":
                    # 抚摸宠物
                    result, reward_gold = pet.pet()
                    if result:
                        print(f"抚摸了 {pet.pet_id}，好感度: {pet.happiness}，等级: {pet.level}")
                        if reward_gold > 0:
                            print(f"升级奖励: {reward_gold} 金币")
                    else:
                        print(f"抚摸冷却中")
                    # 抚摸后也关闭选择器
                    self.close_seed_selector()
                    self._action_pet = None
                elif action == "feed":
                    # 打开喂食菜单（暂时隐藏发散器，不取消选择）
                    self.show_feed_menu(pet.pet_id)
                    # 不关闭选择器，只是隐藏渲染
                elif action == "recall":
                    # 收回宠物
                    if hasattr(self.world, 'pet_manager'):
                        self.world.pet_manager.recall_pet(pet.pet_id)
                        print(f"收回了 {pet.pet_id}")
                        # 保存
                        if hasattr(self.game_manager, 'save_manager'):
                            self.game_manager.save_manager.auto_save_on_action("收回宠物")
                    # 收回后关闭选择器
                    self.close_seed_selector()
                    self._action_pet = None
                return True

        self.close_seed_selector()
        self._action_pet = None
        return True

    def handle_floor_selector_click(self, screen_pos: tuple) -> bool:
        """处理地板样式选择器的点击"""
        if not self.floor_selector_active:
            return False

        x, y = screen_pos

        # 检查是否点击了某个线条末端
        for i, line in enumerate(self.floor_selector_lines):
            rect = line["rect"]
            click_pos = line["click_pos"]
            collide = rect.collidepoint(x, y)
            if collide:
                # 选择这个样式
                style_index = line["style"]["index"]
                self.set_floor_style(style_index)
                return True

        # 点击其他地方关闭选择器
        self.close_floor_selector()
        return True

    def close_floor_selector(self):
        """关闭地板样式选择器"""
        self.floor_selector_active = False
        self.floor_selector_grid = None
        self.floor_selector_center = None
        self.floor_selector_lines = []
        self.floor_selector_direction = None

    def set_floor_style(self, style_index: int):
        """设置地板或种植区样式"""

        # 检查是否是种植区选择器
        if self.floor_selector_grid:
            grid_x, grid_y = self.floor_selector_grid
            tile_type = self.world.get_tile_type(grid_x, grid_y)

            if tile_type == self.world.TILE_FARM:
                # 种植区样式 - 检查是否已有作物
                if self.world.count_crops_in_block(grid_x, grid_y) > 0:
                    self.close_floor_selector()
                    return
                self.world.farm_styles[(grid_x, grid_y)] = style_index
                self.close_floor_selector()
                # 自动保存
                if hasattr(self.game_manager, 'save_manager'):
                    self.game_manager.save_manager.auto_save_on_action("设置种植区样式")
                return

        # 地板样式
        if hasattr(self, 'selected_grid'):
            grid_x, grid_y = self.selected_grid
            self.world.floor_styles[(grid_x, grid_y)] = style_index
            self.close_menu()
            # 自动保存
            if hasattr(self.game_manager, 'save_manager'):
                self.game_manager.save_manager.auto_save_on_action("设置地板样式")
        elif self.floor_selector_grid:
            grid_x, grid_y = self.floor_selector_grid
            self.world.floor_styles[(grid_x, grid_y)] = style_index
            self.close_floor_selector()
            # 自动保存
            if hasattr(self.game_manager, 'save_manager'):
                self.game_manager.save_manager.auto_save_on_action("设置地板样式")
        else:
            pass

    def buy_seed(self, seed_id: str, price: int):
        """购买种子"""
        if self.game_manager.spend_coins(price):
            # 添加到种子背包
            seeds = self.game_manager.inventory.get("seeds", {})
            seeds[seed_id] = seeds.get(seed_id, 0) + 1
            self.game_manager.inventory["seeds"] = seeds
            print(f"购买了 {seed_id} 种子")
            # 刷新商店界面
            self.show_shop_menu()
            # 自动保存
            if hasattr(self.game_manager, 'save_manager'):
                self.game_manager.save_manager.auto_save_on_action("购买种子")
        else:
            print("金币不足")

    def buy_pet(self, pet_id: str, price: int):
        """购买宠物"""
        if self.game_manager.spend_coins(price):
            # 添加到宠物列表
            pets = self.game_manager.inventory.get("pets", [])
            if pet_id not in pets:
                pets.append(pet_id)
                self.game_manager.inventory["pets"] = pets
            print(f"购买了宠物 {pet_id}")
            # 刷新商店界面
            self.show_shop_menu()
            # 自动保存
            if hasattr(self.game_manager, 'save_manager'):
                self.game_manager.save_manager.auto_save_on_action("购买宠物")
        else:
            print("金币不足")

    def _get_pet_preview(self, pet_id):
        """获取宠物预览图（带缓存）"""
        # 检查缓存
        if not hasattr(self, '_pet_preview_cache'):
            self._pet_preview_cache = {}

        if pet_id in self._pet_preview_cache:
            return self._pet_preview_cache[pet_id]


        # 确保图片已加载
        Pet.load_all_images()

        # pet_id 可能是实例ID（如 golden_retriever_1），需要获取宠物类型
        pet_type = pet_id
        if hasattr(self.world, 'pet_manager'):
            pet_data = self.world.pet_manager.pet_data.get(pet_id, {})
            pet_type = pet_data.get("pet_type", pet_id)

        # 从缓存获取（使用宠物类型）
        images = Pet._images.get(pet_type, {})
        idle_frames = images.get("idle", [])

        if idle_frames:
            img = idle_frames[0]  # 使用第一帧
            # 缩放到合适的预览大小
            img_w, img_h = img.get_size()
            preview_size = 40
            scale = min(preview_size / img_w, preview_size / img_h)
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))
            preview = pygame.transform.scale(img, (new_w, new_h))
            self._pet_preview_cache[pet_id] = preview
            return preview

        return None

    def time_skip(self, hours: int):
        """模拟时间流逝（测试用）"""
        import time
        skip_seconds = hours * 3600
        for crop in self.world.crop_list:
            crop.start_time -= skip_seconds
            crop.update()  # 立即更新阶段
        print(f"模拟时间流逝 {hours}h，{len(self.world.crop_list)} 株作物已更新")

    def toggle_edit_mode(self):
        """切换编辑模式"""
        # 切换编辑模式状态
        self.is_edit_mode = not getattr(self, 'is_edit_mode', False)

        # 同步到输入处理器
        if hasattr(self, 'input_handler'):
            self.input_handler.is_edit_mode = self.is_edit_mode
            # 退出编辑模式时，取消选中
            if not self.is_edit_mode:
                self.input_handler.selected_object = None

        # 【修复】退出编辑模式时，取消放置模式
        if not self.is_edit_mode:
            if hasattr(self, '_placing_furniture') and self._placing_furniture:
                self._placing_furniture = False
                self._placing_furniture_id = None
                print(f"退出编辑模式，取消放置模式")

        # 同步到所有家具
        if hasattr(self.world, 'furniture_list'):
            for furniture in self.world.furniture_list:
                furniture.set_edit_mode(self.is_edit_mode)

        # 退出编辑模式时，取消所有选中
        if not self.is_edit_mode and hasattr(self.world, 'deselect_all'):
            self.world.deselect_all()

        # 编辑模式下收回/放出宠物
        if hasattr(self.world, 'pet_manager'):
            if self.is_edit_mode:
                self.world.pet_manager.enter_edit_mode()
            else:
                self.world.pet_manager.exit_edit_mode()

        # 保存宠物数据
        if hasattr(self.game_manager, 'save_manager'):
            self.game_manager.save_manager.auto_save_on_action("编辑模式切换")

        print(f"编辑模式: {'开启' if self.is_edit_mode else '关闭'}")

    def update_selected_info(self, obj):
        """更新选中物体的信息"""
        self.selected_info = None
        if obj:
            # 宠物类型检查（优先，因为 Pet 没有 name 属性）
            if hasattr(obj, 'pet_id') and hasattr(obj, 'happiness'):
                # 宠物详细信息
                info = {"name": "", "type": "pet", "pet_id": obj.pet_id}

                # 宠物名称（优先使用自定义名称）
                custom_name = obj.pet_data.get('name', obj.pet_type) if hasattr(obj, 'pet_data') else obj.pet_type
                info["name"] = custom_name if custom_name else Pet.get_name(obj.pet_type)

                # 好感度
                info["happiness"] = obj.happiness
                level, level_name = obj.get_happiness_level()
                info["level"] = level
                info["level_name"] = level_name

                # 饱腹度
                info["satiety"] = obj.satiety

                # 状态
                state_names = {
                    "idle": "闲逛",
                    "walk": "走动",
                    "hungry": "饥饿",
                    "happy": "开心",
                    "sleep": "睡觉",
                    "run": "跑动",
                    "special": "特殊"
                }
                info["state"] = state_names.get(obj.state, obj.state)

                # 宠物图标
                from ..entities.pet import Pet
                Pet.load_all_images()
                images = Pet._images.get(obj.pet_type, {})
                idle_frames = images.get("idle", [])
                if idle_frames:
                    info["icon"] = idle_frames[0]

                info["hint"] = f"Lv{level} {level_name} | 好感: {int(obj.happiness)} | 饱腹: {int(obj.satiety)}"
                self.selected_info = info
                return

            # 其他类型检查
            if hasattr(obj, 'name'):
                info = {"name": obj.name}
                # 蓄水器特殊处理
                if hasattr(obj, 'furniture_id') and obj.furniture_id == "waterstorage":
                    info["type"] = "waterstorage"
                    water_stored = getattr(obj, 'water_stored', 0)
                    max_water = getattr(obj, 'max_water', 400)
                    info["water_stored"] = water_stored
                    info["max_water"] = max_water
                    if water_stored >= max_water:
                        info["hint"] = "已满 | 点击收取"
                    elif water_stored > 0:
                        info["hint"] = f"{water_stored}/{max_water} | 点击收取"
                    else:
                        info["hint"] = "等待下雨..."
                # 只有台灯类家具才显示开关灯提示
                elif hasattr(obj, 'is_light') and obj.is_light:
                    info["type"] = "furniture"
                    info["hint"] = "点击开灯/关灯"
                elif hasattr(obj, 'current_stage'):
                    # 作物详细信息
                    import time
                    from ..entities.crop import Crop

                    info["type"] = "crop"
                    stages = ["种子", "幼苗", "成长", "成熟"]
                    info["stage"] = stages[obj.current_stage]
                    info["stage_idx"] = obj.current_stage
                    info["water"] = obj.water_level
                    info["crop_id"] = obj.crop_id

                    # 水分状态
                    if obj.type == 1:  # 水生
                        info["water_status"] = "永久湿润"
                    elif obj.water_level >= 80:
                        info["water_status"] = "湿润"
                    elif obj.water_level >= 40:
                        info["water_status"] = "正常"
                    elif obj.water_level > 0:
                        info["water_status"] = "干渴"
                    else:
                        info["water_status"] = "枯萎"

                    # 作物图标
                    if obj.crop_id in Crop._sprite_cache and Crop._sprite_cache[obj.crop_id]:
                        sprites = Crop._sprite_cache[obj.crop_id]
                        if obj.current_stage < len(sprites) and sprites[obj.current_stage]:
                            info["icon"] = sprites[obj.current_stage]

                    # 收获代币
                    crop_data = Crop.CROP_DATA.get(obj.crop_id, {})
                    info["sell_price"] = crop_data.get("sell_price", 0)
                    info["fertilized"] = obj.is_fertilized

                    # 生长进度
                    if obj.current_stage < 3:
                        info["growth_progress"] = obj.growth_progress
                    else:
                        info["growth_progress"] = 1.0

                    # 距离成熟时间
                    if obj.current_stage < 3:
                        now = time.time()
                        elapsed = now - obj.start_time
                        growth_rate = 1.0
                        if obj.water_level >= 80:
                            growth_rate += 0.3
                        elif obj.water_level >= 40:
                            growth_rate += 0.15
                        elif obj.water_level > 0:
                            growth_rate -= 0.2
                        else:
                            growth_rate = 0
                        if obj.is_fertilized:
                            growth_rate += 0.5

                        stage_seconds = obj.growth_time * 3600
                        total_elapsed = elapsed * growth_rate
                        stages_done = int(total_elapsed / stage_seconds)
                        if stages_done < 3:
                            stage_elapsed = total_elapsed % stage_seconds
                            remaining = max(0, stage_seconds - stage_elapsed)
                            hours = int(remaining // 3600)
                            minutes = int((remaining % 3600) // 60)
                            info["time_left"] = f"{hours}h{minutes:02d}m"
                        else:
                            info["time_left"] = "已成熟"
                    else:
                        info["time_left"] = "已成熟"

                    info["hint"] = f"{info['stage']} | {info['water_status']}"
                self.selected_info = info

    def update(self):
        """更新UI"""
        # 更新帧率
        self.fps = self.clock.get_fps()

        # 检测缩放变化，关闭选择器
        if self.camera:
            current_zoom = self.camera.zoom
            if abs(current_zoom - self.last_camera_zoom) > 0.001:
                if self.floor_selector_active:
                    self.close_floor_selector()
                if self.seed_selector_active:
                    self.close_seed_selector()
            self.last_camera_zoom = current_zoom

        # 更新选中物体信息
        if self.world.selected_object:
            self.update_selected_info(self.world.selected_object)
        else:
            self.selected_info = None

    def render(self):
        """渲染UI"""
        # 渲染顶部状态栏
        self.render_top_bar()

        # 渲染底部按钮
        self.render_bottom_buttons()

        # 渲染选中物体信息（非植物）
        self.render_selected_info()

        # 渲染帧率（右上角）
        self.render_fps()

        # 渲染菜单
        if self.current_menu == "inventory":
            self.render_inventory()
        elif self.current_menu == "furniture_place":
            self.render_furniture_place_menu()
        elif self.current_menu == "shop":
            self.render_shop_menu()
        elif self.current_menu:
            self.render_menu()

        # 渲染喂食菜单
        if self.feed_menu_active:
            self.render_feed_menu()

        # 渲染种子选择器（喂食菜单打开时隐藏）
        if self.seed_selector_active and not self.feed_menu_active:
            self.render_seed_selector()

        # 渲染地板样式选择器
        if self.floor_selector_active:
            self.render_floor_selector()

        # 渲染植物详细信息面板（最后渲染，确保不被遮挡）
        self.render_crop_detail_panel()

        # 渲染宠物详细信息面板
        self.render_pet_detail_panel()

        # 渲染放置模式预览
        if hasattr(self, '_placing_furniture') and self._placing_furniture:
            self.render_placing_furniture_preview()

        # 渲染编辑模式提示
        if self.is_edit_mode:
            self.render_edit_mode_hint()

        # 渲染重命名对话框
        if self._rename_active:
            self._render_rename_dialog()

        # 渲染设置面板（最顶层）
        if self.current_menu == "settings":
            self.settings_panel.render(self.screen)

        # 渲染新手引导（最顶层）
        if self.tutorial.active:
            self.tutorial.update()
            self.tutorial.render()

    def render_top_bar(self):
        """渲染顶部状态栏"""
        # 渐变背景（更柔和的深色渐变）
        for y in range(30):
            alpha = 220 - y * 3
            color = (25, 28, 35, max(120, alpha))
            pygame.draw.line(self.screen, color[:3], (0, y), (self.screen_width, y))

        # 底部边线（带发光效果）
        pygame.draw.line(self.screen, (60, 65, 80), (0, 28), (self.screen_width, 28), 1)
        pygame.draw.line(self.screen, (90, 95, 110), (0, 29), (self.screen_width, 29), 1)

        x = 8

        # 金币图标 + 数量
        if "coin" in self.ui_icons:
            coin_icon = self.ui_icons["coin"]
            self.screen.blit(coin_icon, (x, 4))
        x += 22
        coins_text = self.font_medium.render(f"{self.game_manager.coins}", True, (255, 215, 0))
        self.screen.blit(coins_text, (x, 5))
        x += coins_text.get_width() + 15

        # 分隔点
        pygame.draw.circle(self.screen, (60, 65, 75), (x, 15), 2)
        x += 12

        # 水图标 + 数量
        if "water" in self.ui_icons:
            water_icon = self.ui_icons["water"]
            self.screen.blit(water_icon, (x, 4))
        x += 22
        water_text = self.font_medium.render(f"{self.game_manager.water}", True, (100, 180, 255))
        self.screen.blit(water_text, (x, 5))
        x += water_text.get_width() + 15

        # 分隔点
        pygame.draw.circle(self.screen, (60, 65, 75), (x, 15), 2)
        x += 12

        # 天气图标 + 文字
        if hasattr(self, 'world') and hasattr(self.world, 'weather'):
            weather_name = self.world.weather.get_weather_name()
            if weather_name == "雨天":
                weather_color = (100, 180, 255)
                if "rain" in self.ui_icons:
                    weather_icon = self.ui_icons["rain"]
                    self.screen.blit(weather_icon, (x, 4))
            else:
                weather_color = (255, 200, 50)
                if "sunny" in self.ui_icons:
                    weather_icon = self.ui_icons["sunny"]
                    self.screen.blit(weather_icon, (x, 4))
            x += 22
            weather_text = self.font_medium.render(weather_name, True, weather_color)
            self.screen.blit(weather_text, (x, 5))
            x += weather_text.get_width() + 15

        # 分隔点
        pygame.draw.circle(self.screen, (60, 65, 75), (x, 15), 2)
        x += 12

        # 游戏时间显示（没有选中物体时才显示，每分钟更新一次）
        if not self.selected_info:
            import time as _time
            current_real_minute = int(_time.time() % 3600 / 60)
            if not hasattr(self, '_time_cache_minute') or self._time_cache_minute != current_real_minute:
                self._time_cache_minute = current_real_minute
                from ..core.lighting import LightingManager
                gh, gm = LightingManager.get_game_time()
                time_str = f"{gh:02d}:{gm:02d}"
                t = gh * 60 + gm
                if t < 240 or t >= 1200:
                    time_color = (150, 180, 255)
                elif t < 960:
                    time_color = (255, 255, 255)
                else:
                    time_color = (255, 180, 100)
                self._time_cache_surface = self.font_medium.render(time_str, True, time_color)
            self.screen.blit(self._time_cache_surface, (x, 5))

        # 选中植物信息（右侧紧凑显示）
        if self.selected_info and self.selected_info.get("type") == "crop":
            self.render_crop_info_top_bar()
        # 选中宠物信息（右侧紧凑显示）
        elif self.selected_info and self.selected_info.get("type") == "pet":
            self.render_pet_info_top_bar()

    def render_crop_info_top_bar(self):
        """在顶部栏右侧紧凑显示选中植物信息"""
        info = self.selected_info
        x_start = 280  # 从右侧开始

        # 作物图标（小尺寸，带缓存）
        crop_icon = info.get("icon")
        if crop_icon:
            small_icon_size = max(16, min(20, self.screen_width // 40))
            crop_id = info.get("crop_id", "")
            stage_idx = info.get("stage_idx", 0)
            cache_key = (crop_id, small_icon_size)

            if cache_key not in self._crop_info_cache:
                # 获取有效区域并裁剪
                from ..entities.crop import Crop
                bbox = Crop.get_sprite_bbox(crop_id, stage_idx)
                if bbox:
                    x, y, w, h = bbox
                    # 安全检查：bbox 不能超出图片范围
                    img_w, img_h = crop_icon.get_size()
                    x = max(0, min(x, img_w - 1))
                    y = max(0, min(y, img_h - 1))
                    w = min(w, img_w - x)
                    h = min(h, img_h - y)
                    if w > 0 and h > 0:
                        cropped_icon = crop_icon.subsurface((x, y, w, h))
                        # 保持宽高比缩放
                        sprite_ratio = h / w
                        if sprite_ratio > 1:
                            icon_h = small_icon_size
                            icon_w = max(1, int(icon_h / sprite_ratio))
                        else:
                            icon_w = small_icon_size
                            icon_h = max(1, int(icon_w * sprite_ratio))
                        self._crop_info_cache[cache_key] = pygame.transform.smoothscale(cropped_icon, (icon_w, icon_h))
                    else:
                        self._crop_info_cache[cache_key] = pygame.transform.smoothscale(crop_icon, (small_icon_size, small_icon_size))
                else:
                    self._crop_info_cache[cache_key] = pygame.transform.smoothscale(crop_icon, (small_icon_size, small_icon_size))

            small_icon = self._crop_info_cache[cache_key]
            self.screen.blit(small_icon, (x_start, 5))
            x_start += 22

        # 名称 + 阶段
        name = info.get("name", "")
        stage = info.get("stage", "")
        name_text = self.font_small.render(f"{name}({stage})", True, (255, 255, 255))
        self.screen.blit(name_text, (x_start, 7))
        x_start += name_text.get_width() + 5

        # 水分
        water = info.get("water", 0)
        water_color = (100, 200, 255) if water > 40 else (255, 150, 50) if water > 0 else (150, 150, 150)
        water_text = self.font_small.render(f"{int(water)}%", True, water_color)
        self.screen.blit(water_text, (x_start, 7))

    def render_pet_info_top_bar(self):
        """在顶部栏右侧紧凑显示选中宠物信息（与crop统一位置）"""
        info = self.selected_info
        x_start = 280  # 与crop统一位置

        # 宠物图标（小尺寸，带缓存）
        pet_icon = info.get("icon")
        if pet_icon:
            small_icon_size = max(16, min(20, self.screen_width // 40))
            pet_id = info.get("pet_id", "")
            cache_key = (f"pet_{pet_id}", small_icon_size)

            if cache_key not in self._crop_info_cache:
                # 获取有效区域并裁剪
                from ..entities.pet import Pet
                bbox = Pet.get_sprite_bbox(pet_id, "idle", 0)
                if bbox:
                    x, y, w, h = bbox
                    # 安全检查：bbox 不能超出图片范围
                    img_w, img_h = pet_icon.get_size()
                    x = max(0, min(x, img_w - 1))
                    y = max(0, min(y, img_h - 1))
                    w = min(w, img_w - x)
                    h = min(h, img_h - y)
                    if w > 0 and h > 0:
                        cropped_icon = pet_icon.subsurface((x, y, w, h))
                        # 保持宽高比缩放
                        sprite_ratio = h / w
                        if sprite_ratio > 1:
                            icon_h = small_icon_size
                            icon_w = max(1, int(icon_h / sprite_ratio))
                        else:
                            icon_w = small_icon_size
                            icon_h = max(1, int(icon_w * sprite_ratio))
                        self._crop_info_cache[cache_key] = pygame.transform.smoothscale(cropped_icon, (icon_w, icon_h))
                    else:
                        self._crop_info_cache[cache_key] = pygame.transform.smoothscale(pet_icon, (small_icon_size, small_icon_size))
                else:
                    self._crop_info_cache[cache_key] = pygame.transform.smoothscale(pet_icon, (small_icon_size, small_icon_size))

            small_icon = self._crop_info_cache[cache_key]
            self.screen.blit(small_icon, (x_start, 5))
            x_start += 22

        # 名称
        name = info.get("name", "")
        display_name = name[:5] if len(name) > 5 else name
        name_text = self.font_small.render(display_name, True, (255, 255, 255))
        self.screen.blit(name_text, (x_start, 7))
        x_start += name_text.get_width() + 5  # 与crop统一间距

        # 好感度文字（与crop的水分显示方式一致）
        happiness = info.get("happiness", 0)
        level = info.get("level", 1)
        happy_text = self.font_small.render(f"{level}级", True, (255, 200, 100))
        self.screen.blit(happy_text, (x_start, 7))

    def render_crop_detail_panel(self):
        """渲染植物详细信息面板（顶部栏下方）"""
        if not self.selected_info or self.selected_info.get("type") != "crop":
            return

        info = self.selected_info
        panel_h = 32
        panel_y = 30

        # 面板背景（渐变效果）
        for y in range(panel_y, panel_y + panel_h):
            alpha = 180 - (y - panel_y) * 2
            color = (35, 38, 48, max(140, alpha))
            pygame.draw.line(self.screen, color[:3], (0, y), (self.screen_width, y))

        # 顶部边线
        pygame.draw.line(self.screen, (70, 75, 90), (0, panel_y), (self.screen_width, panel_y), 1)

        x = 8

        # 水分进度条
        water = info.get("water", 0)
        water_label = self.font_small.render("水分", True, (140, 170, 190))
        self.screen.blit(water_label, (x, panel_y + 8))
        x += 38

        # 进度条背景
        bar_w = 55
        bar_h = 8
        bar_y = panel_y + 10

        # 圆角进度条背景
        pygame.draw.rect(self.screen, (50, 55, 65), (x, bar_y, bar_w, bar_h), border_radius=4)

        # 进度条填充
        fill_w = int(bar_w * water / 100)
        if water > 40:
            bar_color = (70, 170, 245)
        elif water > 0:
            bar_color = (245, 170, 45)
        else:
            bar_color = (180, 70, 70)
        if fill_w > 0:
            pygame.draw.rect(self.screen, bar_color, (x, bar_y, fill_w, bar_h), border_radius=4)

        x += bar_w + 8

        # 水分状态文字
        water_status = info.get("water_status", "")
        if water > 40:
            ws_color = (90, 190, 245)
        elif water > 0:
            ws_color = (245, 170, 45)
        else:
            ws_color = (180, 90, 90)
        status_text = self.font_small.render(water_status, True, ws_color)
        self.screen.blit(status_text, (x, panel_y + 8))
        x += status_text.get_width() + 12

        # 分隔线
        pygame.draw.line(self.screen, (65, 70, 85), (x, panel_y + 6), (x, panel_y + panel_h - 6), 1)
        x += 10

        # 生长进度条
        growth = info.get("growth_progress", 0)
        stage = info.get("stage_idx", 0)
        growth_label = self.font_small.render("生长", True, (140, 190, 140))
        self.screen.blit(growth_label, (x, panel_y + 8))
        x += 38

        # 圆角进度条
        pygame.draw.rect(self.screen, (50, 55, 65), (x, bar_y, bar_w, bar_h), border_radius=4)
        stage_fill = (stage + growth) / 4 * bar_w
        if stage_fill > 0:
            pygame.draw.rect(self.screen, (90, 190, 90), (x, bar_y, int(stage_fill), bar_h), border_radius=4)

        x += bar_w + 8

        # 距离成熟时间
        time_left = info.get("time_left", "")
        time_text = self.font_small.render(time_left, True, (190, 190, 140))
        self.screen.blit(time_text, (x, panel_y + 8))
        x += time_text.get_width() + 12

        # 分隔线
        pygame.draw.line(self.screen, (65, 70, 85), (x, panel_y + 6), (x, panel_y + panel_h - 6), 1)
        x += 10

        # 收获代币
        sell_price = info.get("sell_price", 0)
        if "coin" in self.ui_icons:
            mini_size = max(10, min(12, self.screen_width // 60))
            mini_coin = pygame.transform.smoothscale(self.ui_icons["coin"], (mini_size, mini_size))
            self.screen.blit(mini_coin, (x, panel_y + 10))
            x += 14
        price_text = self.font_small.render(f"+{sell_price}", True, (255, 210, 0))
        self.screen.blit(price_text, (x, panel_y + 8))
        x += price_text.get_width() + 12

        # 施肥状态
        fertilized = info.get("fertilized", False)
        if fertilized:
            fert_text = self.font_small.render("已施肥", True, (245, 195, 90))
            self.screen.blit(fert_text, (x, panel_y + 8))

    def render_pet_detail_panel(self):
        """渲染宠物详细信息面板（顶部栏下方）"""
        if not self.selected_info or self.selected_info.get("type") != "pet":
            return

        info = self.selected_info
        panel_h = 32
        panel_y = 32  # 在顶部栏下方（顶部栏高度30 + 2px间距）

        # 面板背景（渐变效果）
        for y in range(panel_y, panel_y + panel_h):
            alpha = 180 - (y - panel_y) * 2
            color = (35, 38, 48, max(140, alpha))
            pygame.draw.line(self.screen, color[:3], (0, y), (self.screen_width, y))

        # 顶部边线
        pygame.draw.line(self.screen, (70, 75, 90), (0, panel_y), (self.screen_width, panel_y), 1)

        x = 8

        # 好感度进度条
        happiness = info.get("happiness", 0)
        happy_label = self.font_small.render("好感", True, (140, 170, 190))
        self.screen.blit(happy_label, (x, panel_y + 8))
        x += 38

        # 进度条背景
        bar_w = 55
        bar_h = 8
        bar_y = panel_y + 10

        pygame.draw.rect(self.screen, (50, 55, 65), (x, bar_y, bar_w, bar_h), border_radius=4)

        # 进度条填充
        fill_w = int(bar_w * happiness / 100)
        if happiness >= 80:
            bar_color = (255, 200, 50)  # 金色
        elif happiness >= 50:
            bar_color = (100, 200, 100)  # 绿色
        else:
            bar_color = (200, 150, 100)  # 棕色
        if fill_w > 0:
            pygame.draw.rect(self.screen, bar_color, (x, bar_y, fill_w, bar_h), border_radius=4)

        x += bar_w + 8

        # 等级文字
        level = info.get("level", 0)
        level_name = info.get("level_name", "")
        level_text = self.font_small.render(f"Lv{level} {level_name}", True, (190, 190, 140))
        self.screen.blit(level_text, (x, panel_y + 8))
        x += level_text.get_width() + 12

        # 分隔线
        pygame.draw.line(self.screen, (65, 70, 85), (x, panel_y + 6), (x, panel_y + panel_h - 6), 1)
        x += 10

        # 饱腹度进度条
        satiety = info.get("satiety", 50)
        satiety_label = self.font_small.render("饱腹", True, (140, 170, 190))
        self.screen.blit(satiety_label, (x, panel_y + 8))
        x += 38

        pygame.draw.rect(self.screen, (50, 55, 65), (x, bar_y, bar_w, bar_h), border_radius=4)

        fill_w = int(bar_w * satiety / 100)
        if satiety > 70:
            bar_color = (100, 200, 100)  # 绿色
        elif satiety > 40:
            bar_color = (255, 200, 100)  # 黄色
        else:
            bar_color = (255, 100, 100)  # 红色
        if fill_w > 0:
            pygame.draw.rect(self.screen, bar_color, (x, bar_y, fill_w, bar_h), border_radius=4)

        x += bar_w + 8

        # 状态文字
        state = info.get("state", "")
        state_text = self.font_small.render(state, True, (190, 190, 140))
        self.screen.blit(state_text, (x, panel_y + 8))

    def render_bottom_buttons(self):
        """渲染底部按钮（编辑模式下替换为编辑工具栏）"""
        # 底部栏起始Y坐标（距离底部30像素）
        bar_start_y = self.screen_height - 30

        # 渐变背景
        for y in range(bar_start_y, self.screen_height):
            alpha = 140 + (y - bar_start_y) * 2  # 从140渐变到200
            color = (30, 30, 40, min(200, alpha))
            pygame.draw.line(self.screen, color[:3], (0, y), (self.screen_width, y))
        # 顶部边线
        pygame.draw.line(self.screen, (80, 80, 100), (0, bar_start_y), (self.screen_width, bar_start_y), 1)

        if self.is_edit_mode:
            # 编辑模式：显示编辑工具按钮
            self._render_edit_tools_in_bottom_bar()
        else:
            # 正常模式：显示常规按钮
            for button in self.buttons:
                # 按钮背景
                pygame.draw.rect(self.screen, (80, 80, 80), button["rect"])
                pygame.draw.rect(self.screen, (120, 120, 120), button["rect"], 1)

                # 优先使用图标，没有图标则用文字
                icon_key = button.get("icon")
                if icon_key and icon_key in self.ui_icons:
                    icon = self.ui_icons[icon_key]
                    icon_rect = icon.get_rect(center=button["rect"].center)
                    self.screen.blit(icon, icon_rect)
                else:
                    # 按钮文字
                    text = self.font_small.render(button["text"], True, (255, 255, 255))
                    text_rect = text.get_rect(center=button["rect"].center)
                    self.screen.blit(text, text_rect)

    def _render_edit_tools_in_bottom_bar(self):
        """在底部栏位置渲染编辑工具按钮"""
        tools = [
            ("select", "选择"),
            ("move", "移动"),
            ("place", "放置"),
            ("remove", "收回"),
            ("flip", "翻转"),
        ]

        btn_y = self.screen_height - 30  # 距离底部30像素
        btn_h = 25
        btn_w = 48
        gap = 6
        total_w = len(tools) * btn_w + (len(tools) - 1) * gap
        start_x = (self.screen_width - total_w) // 2

        current_tool = getattr(self.input_handler, 'edit_tool', 'select') if self.input_handler else 'select'
        self._edit_tool_rects = {}

        for i, (tool_id, tool_name) in enumerate(tools):
            rect = pygame.Rect(start_x + i * (btn_w + gap), btn_y, btn_w, btn_h)
            self._edit_tool_rects[tool_id] = rect

            # 背景
            is_selected = (tool_id == current_tool)
            color = (100, 120, 160) if is_selected else (80, 80, 80)
            pygame.draw.rect(self.screen, color, rect, border_radius=3)
            border_color = (140, 160, 200) if is_selected else (120, 120, 120)
            pygame.draw.rect(self.screen, border_color, rect, 1, border_radius=3)

            # 文字
            text = self.font_small.render(tool_name, True, (255, 255, 255) if is_selected else (180, 180, 180))
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

        # 退出编辑模式按钮（右侧）
        exit_w = 56
        exit_rect = pygame.Rect(self.screen_width - exit_w - 10, btn_y, exit_w, btn_h)
        self._edit_exit_rect = exit_rect
        pygame.draw.rect(self.screen, (140, 60, 60), exit_rect, border_radius=3)
        pygame.draw.rect(self.screen, (180, 80, 80), exit_rect, 1, border_radius=3)
        exit_text = self.font_small.render("退出", True, (255, 255, 255))
        exit_text_rect = exit_text.get_rect(center=exit_rect.center)
        self.screen.blit(exit_text, exit_text_rect)

    def render_selected_info(self):
        """渲染选中物体信息（非植物类型，非宠物类型）"""
        # 宠物和植物使用专门的渲染方法，这里只处理家具
        if self.selected_info and self.selected_info.get("type") not in ("crop", "pet"):
            # 在顶部栏显示选中家具信息
            x = 320

            # 选中指示器（小三角）
            pygame.draw.polygon(self.screen, (100, 180, 255), [
                (x, 12), (x + 6, 15), (x, 18)
            ])
            x += 10

            # 家具名称
            name = self.selected_info.get("name", "")
            name_text = self.font_medium.render(name, True, (220, 230, 245))
            self.screen.blit(name_text, (x, 2))
            x += name_text.get_width() + 10

            # 提示信息
            hint = self.selected_info.get("hint", "")
            if hint:
                hint_text = self.font_small.render(hint, True, (160, 170, 185))
                self.screen.blit(hint_text, (x, 8))

    def render_fps(self):
        """渲染帧率（右上角）"""
        fps_text = self.font_small.render(f"FPS: {int(self.fps)}", True, (255, 255, 255))
        fps_rect = fps_text.get_rect(topright=(self.screen_width - 10, 5))
        self.screen.blit(fps_text, fps_rect)

    def render_placing_furniture_preview(self):
        """渲染放置模式的家具预览（跟随手指，用footprint多边形画边框）"""
        from ..entities.furniture import Furniture

        if not hasattr(self, '_placing_furniture_id') or not self._placing_furniture_id:
            return

        # 获取预览图片
        img = Furniture._images.get(self._placing_furniture_id)
        if not img:
            return

        # 计算屏幕位置
        if hasattr(self, '_placing_pos') and self.camera:
            world_x, world_y = self._placing_pos
            screen_x, screen_y = self.camera.world_to_screen((world_x, world_y))
        else:
            # 使用鼠标位置
            screen_x, screen_y = pygame.mouse.get_pos()

        # 缩放图片（应用缩放倍率：基础缩放 × 额外缩放，带缓存）
        zoom = self.camera.zoom if self.camera else 1.0
        zoom_int = int(zoom * 100)
        cache_key = (self._placing_furniture_id, zoom_int, False)

        if cache_key not in self._placing_preview_cache:
            # 缓存大小限制
            if len(self._placing_preview_cache) > 20:
                self._placing_preview_cache.clear()

            img_w, img_h = img.get_size()
            total_scale = Furniture.get_total_scale(self._placing_furniture_id)
            scaled_w = int(img_w * zoom * total_scale)
            scaled_h = int(img_h * zoom * total_scale)
            preview = pygame.transform.scale(img, (scaled_w, scaled_h))
            preview.set_alpha(128)
            self._placing_preview_cache[cache_key] = preview

        preview = self._placing_preview_cache[cache_key]
        scaled_w, scaled_h = preview.get_size()
        draw_x = screen_x - scaled_w // 2
        draw_y = screen_y - scaled_h // 2
        self.screen.blit(preview, (draw_x, draw_y))

        # 用 footprint/wall_surface 多边形绘制边框
        from ..entities.furniture import Furniture as FurnitureCls
        # 检查是否是墙挂物品
        furniture_data = FurnitureCls.FURNITURE_DATA.get(self._placing_furniture_id, {})
        obj_type = furniture_data.get("type", "ground")

        if obj_type == "wall_mount":
            # 墙挂物品：使用 wall_surface 数据
            ws_data = self.world.collision.get_wall_surface(self._placing_furniture_id)
            if ws_data and len(ws_data) >= 3:
                scale = FurnitureCls.get_total_scale(self._placing_furniture_id)
                origin_x = screen_x - scaled_w // 2
                origin_y = screen_y - scaled_h // 2
                screen_ws = [(origin_x + px * scale * zoom, origin_y + py * scale * zoom) for px, py in ws_data]
                pygame.draw.polygon(self.screen, (0, 255, 0), screen_ws, 2)
            else:
                pygame.draw.rect(self.screen, (0, 255, 0), (draw_x, draw_y, scaled_w, scaled_h), 2)
        else:
            # 普通家具：使用 footprint 数据
            fp_data = self.world.collision.get_footprint(self._placing_furniture_id)
            if fp_data and len(fp_data) >= 3:
                scale = FurnitureCls.get_total_scale(self._placing_furniture_id)
                # footprint 坐标是原始精灵图像素，需乘以 SCALE * EXTRA_SCALE 对齐缩放后的精灵图
                origin_x = screen_x - scaled_w // 2
                origin_y = screen_y - scaled_h // 2
                screen_fp = [(origin_x + px * scale * zoom, origin_y + py * scale * zoom) for px, py in fp_data]
                pygame.draw.polygon(self.screen, (0, 255, 0), screen_fp, 2)
            else:
                # 无 footprint 数据时退回矩形
                pygame.draw.rect(self.screen, (0, 255, 0), (draw_x, draw_y, scaled_w, scaled_h), 2)

        # 提示文字
        hint = self.font_small.render("点击确认放置", True, (255, 255, 100))
        hint_rect = hint.get_rect(centerx=screen_x, top=draw_y + scaled_h + 5)
        self.screen.blit(hint, hint_rect)

    def render_edit_mode_hint(self):
        """渲染编辑模式提示（工具栏已移至底部栏）"""
        # 根据当前工具显示提示
        if hasattr(self, '_placing_furniture') and self._placing_furniture:
            # 放置模式
            hint_text = "[放置模式] 移动手指调整位置 | 点击确认放置"
        else:
            tool = getattr(self.input_handler, 'edit_tool', 'select') if self.input_handler else 'select'
            hints = {
                "select": "点击家具选中 | 点击地板切换样式",
                "move": "拖拽家具移动位置",
                "place": "选择要放置的家具",
                "remove": "点击家具收回仓库",
                "flip": "点击家具镜像翻转",
            }
            hint_text = hints.get(tool, "")

        # 在顶部状态栏下方显示提示
        hint_bg = pygame.Surface((self.screen_width, 16), pygame.SRCALPHA)
        hint_bg.fill((50, 50, 80, 160))
        self.screen.blit(hint_bg, (0, 30))
        text = self.font_small.render(hint_text, True, (255, 255, 100))
        text_rect = text.get_rect(centerx=self.screen_width // 2, centery=30 + 8)
        self.screen.blit(text, text_rect)

    def handle_edit_tool_click(self, screen_pos: tuple) -> bool:
        """处理编辑工具栏点击"""
        x, y = screen_pos

        # 退出编辑模式按钮
        if hasattr(self, '_edit_exit_rect') and self._edit_exit_rect.collidepoint(x, y):
            self.toggle_edit_mode()
            return True

        if not hasattr(self, '_edit_tool_rects'):
            return False

        for tool_id, rect in self._edit_tool_rects.items():
            if rect.collidepoint(x, y):
                # 切换工具前，关闭任何打开的菜单
                if self.current_menu:
                    self.close_menu()
                if self.input_handler:
                    self.input_handler.set_edit_tool(tool_id)
                # 放置工具：直接打开家具选择菜单
                if tool_id == "place":
                    self.show_furniture_place_menu()
                return True
        return False

    def render_inventory(self):
        """渲染背包界面（新版）"""
        if not hasattr(self, 'inv_category'):
            return

        from ..entities.crop import Crop

        # 界面尺寸（自适应屏幕，避开顶部和底部UI）
        margin = 40
        panel_x = margin
        panel_y = 32
        panel_w = self.screen_width - margin * 2
        panel_h = self.screen_height - panel_y - 40  # 避开底部栏
        tab_h = 25
        list_w = int(panel_w * 0.65)  # 左侧65%
        info_w = panel_w - list_w - 15  # 右侧（留10px边距）
        info_x = panel_x + list_w + 10

        # 背景（使用背景图片或纯色）
        if self.bag_background:
            scaled_bg = pygame.transform.smoothscale(self.bag_background, (panel_w, panel_h))
            self.screen.blit(scaled_bg, (panel_x, panel_y))
        else:
            pygame.draw.rect(self.screen, (45, 45, 55), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(self.screen, (80, 80, 100), (panel_x, panel_y, panel_w, panel_h), 2)

        # 关闭按钮（右上角）
        close_rect = pygame.Rect(panel_x + panel_w - 25, panel_y + 3, 22, 22)
        if "close" in self.ui_icons:
            close_icon = self.ui_icons["close"]
            close_size = max(16, min(20, self.screen_width // 40))
            close_icon = pygame.transform.smoothscale(close_icon, (close_size, close_size))
            self.screen.blit(close_icon, close_rect)
        else:
            pygame.draw.rect(self.screen, (150, 80, 80), close_rect)
            text = self.font_small.render("X", True, (255, 255, 255))
            self.screen.blit(text, close_rect)
        self._inv_close_rect = close_rect

        # 标题
        title = self.font_medium.render("背包", True, (255, 220, 100))
        self.screen.blit(title, (panel_x + 10, panel_y + 5))

        # 分类标签
        categories = [
            ("fruit", "果实"),
            ("seed", "种子"),
            ("pet", "宠物"),
            ("furniture", "家具"),
        ]
        tab_x = panel_x + 70
        self._inv_tab_rects = {}
        for cat_id, cat_name in categories:
            tab_rect = pygame.Rect(tab_x, panel_y + 5, 45, 20)
            is_selected = (self.inv_category == cat_id)
            color = (100, 120, 160) if is_selected else (60, 60, 70)
            pygame.draw.rect(self.screen, color, tab_rect, border_radius=3)
            pygame.draw.rect(self.screen, (100, 100, 120), tab_rect, 1, border_radius=3)
            text = self.font_small.render(cat_name, True, (255, 255, 255) if is_selected else (150, 150, 150))
            text_rect = text.get_rect(center=tab_rect.center)
            self.screen.blit(text, text_rect)
            self._inv_tab_rects[cat_id] = tab_rect
            tab_x += 50

        # 获取物品列表
        items = self.get_inv_items()

        # 物品列表区域（左侧）
        list_rect = pygame.Rect(panel_x + 5, panel_y + tab_h + 5, list_w, panel_h - tab_h - 15)
        self._inv_list_rect = list_rect  # 保存用于滚动判断
        # 半透明背景
        list_bg = pygame.Surface((list_w, panel_h - tab_h - 15), pygame.SRCALPHA)
        list_bg.fill((35, 35, 45, 150))
        self.screen.blit(list_bg, (panel_x + 5, panel_y + tab_h + 5))
        pygame.draw.rect(self.screen, (70, 70, 90), list_rect, 1)

        # 渲染物品图标列表（支持滚动）
        self._inv_item_rects = []
        cell_size = max(50, min(65, self.screen_width // 12))  # 每个格子大小（自适应屏幕）
        cols = list_w // cell_size  # 每行列数
        if cols < 1:
            cols = 1
        item_h = cell_size
        visible_rows = list_rect.height // item_h
        total_rows = (len(items) + cols - 1) // cols

        # 计算滚动偏移
        if not hasattr(self, '_inv_list_scroll'):
            self._inv_list_scroll = 0
        max_scroll = max(0, total_rows - visible_rows)
        self._inv_list_scroll = max(0, min(self._inv_list_scroll, max_scroll))

        # 裁剪左侧列表区域
        self.screen.set_clip(list_rect)

        for i in range(len(items)):
            item = items[i]
            row = i // cols
            col = i % cols

            # 计算位置（应用滚动）
            cell_y = list_rect.y + 5 + (row - self._inv_list_scroll) * item_h
            cell_x = list_rect.x + 5 + col * cell_size

            # 跳过不在可视区域的项
            if cell_y + item_h < list_rect.y or cell_y > list_rect.y + list_rect.height:
                continue

            # 选中高亮
            cell_rect = pygame.Rect(cell_x, cell_y, cell_size - 4, cell_size - 4)
            if i == self.inv_selected_idx:
                pygame.draw.rect(self.screen, (70, 80, 110), cell_rect, border_radius=5)

            # 物品图标
            icon_size = max(36, min(48, self.screen_width // 16))
            icon_x = cell_x + (cell_size - 4 - icon_size) // 2
            icon_y = cell_y + 5

            preview = item.get("preview")
            if preview:
                # 对于宠物，使用 pet_id 作为缓存键（更稳定）
                if item.get("type") == "pet":
                    cache_key = (f"pet_{item.get('id')}", icon_size)
                    if cache_key not in self._icon_cache:
                        self._icon_cache[cache_key] = pygame.transform.smoothscale(preview, (icon_size, icon_size))
                    scaled = self._icon_cache[cache_key]
                else:
                    scaled = self.get_cached_icon(preview, icon_size, item.get("id"))
                self.screen.blit(scaled, (icon_x, icon_y))
            elif item["type"] == "pet":
                color = item.get("color", (200, 200, 200))
                pygame.draw.rect(self.screen, color, (icon_x, icon_y, icon_size, icon_size), border_radius=5)
            else:
                pygame.draw.rect(self.screen, (100, 100, 100), (icon_x, icon_y, icon_size, icon_size), border_radius=5)

            # 数量条（底部深色背景）
            amount = item['amount']
            bar_h = 16
            bar_y = cell_y + cell_size - 4 - bar_h
            bar_rect = pygame.Rect(cell_x + 2, bar_y, cell_size - 8, bar_h)
            pygame.draw.rect(self.screen, (30, 30, 40, 180), bar_rect, border_radius=3)

            # 数量文字（居中）
            amount_text = self.font_small.render(str(amount), True, (255, 255, 255))
            text_rect = amount_text.get_rect(center=bar_rect.center)
            self.screen.blit(amount_text, text_rect)

            # 存储rect和对应的item索引
            self._inv_item_rects.append((cell_rect, i))

        self.screen.set_clip(None)

        # 详情区域（右侧）
        info_rect = pygame.Rect(info_x, panel_y + tab_h + 5, info_w, panel_h - tab_h - 15)
        # 半透明背景
        info_bg = pygame.Surface((info_w, panel_h - tab_h - 15), pygame.SRCALPHA)
        info_bg.fill((40, 40, 50, 150))
        self.screen.blit(info_bg, (info_x, panel_y + tab_h + 5))
        pygame.draw.rect(self.screen, (70, 70, 90), info_rect, 1)

        # 设置裁剪区域（支持滚动）
        clip_rect = pygame.Rect(info_rect.x + 1, info_rect.y + 1, info_rect.width - 2, info_rect.height - 2)
        self.screen.set_clip(clip_rect)

        if items and self.inv_selected_idx < len(items):
            selected = items[self.inv_selected_idx]
            self._inv_detail_rect = info_rect
            self._render_inv_detail(info_rect, selected)
        else:
            empty_text = self.font_small.render("无物品", True, (120, 120, 120))
            empty_rect = empty_text.get_rect(center=info_rect.center)
            self.screen.blit(empty_text, empty_rect)

        self.screen.set_clip(None)

    def _render_inv_detail(self, rect, item):
        """渲染物品详情（紧凑布局，支持滚动）"""
        from ..entities.crop import Crop

        x = rect.x + 5
        y = rect.y + 5 + self._inv_detail_scroll

        # 物品图标（居中）
        icon_size = max(36, min(48, self.screen_width // 16))
        icon_x = x + (rect.width - 10 - icon_size) // 2
        preview = item.get("preview")
        if preview:
            big_icon = self.get_cached_icon(preview, icon_size, item.get("id"))
            self.screen.blit(big_icon, (icon_x, y))
        elif item["type"] == "pet":
            color = item.get("color", (200, 200, 200))
            pygame.draw.rect(self.screen, color, (icon_x, y, icon_size, icon_size), border_radius=5)
        y += icon_size + 5

        # 物品名称（居中）
        name = item["name"]
        name_text = self.font_small.render(name, True, (255, 255, 255))
        name_rect = name_text.get_rect(centerx=rect.centerx, top=y)
        self.screen.blit(name_text, name_rect)
        y += 18

        # 数量
        amount_text = self.font_small.render(f"x{item['amount']}", True, (180, 180, 180))
        amount_rect = amount_text.get_rect(centerx=rect.centerx, top=y)
        self.screen.blit(amount_text, amount_rect)
        y += 18

        # 分隔线
        pygame.draw.line(self.screen, (60, 60, 70), (rect.x + 5, y), (rect.right - 5, y), 1)
        y += 5

        # 根据类型显示不同信息
        if item["type"] in ["fruit", "seed"]:
            farm_type = item.get("farm_type", 0)
            farm_names = ["土生", "水生", "盆栽", "沙生"]
            farm_text = self.font_small.render(farm_names[farm_type], True, (150, 180, 150))
            self.screen.blit(farm_text, (rect.x + 5, y))
            y += 16

            if item["type"] == "fruit":
                price = item.get('sell_price', 0)
                price_text = self.font_small.render(f"{price}金/个", True, (255, 215, 0))
                self.screen.blit(price_text, (rect.x + 5, y))
                y += 20

                # 数量滑动条
                if not hasattr(self, '_inv_sell_qty'):
                    self._inv_sell_qty = 1
                max_qty = item['amount']
                self._inv_sell_qty = max(1, min(self._inv_sell_qty, max_qty))

                slider_x = rect.x + 5
                slider_y = y + 5  # 往下移动5px避免重叠
                slider_w = rect.width - 10
                slider_h = 6

                # 滑动条背景
                self._inv_slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)
                pygame.draw.rect(self.screen, (60, 60, 70), (slider_x, slider_y, slider_w, slider_h), border_radius=3)

                # 滑动条填充
                if max_qty > 1:
                    fill_ratio = (self._inv_sell_qty - 1) / (max_qty - 1)
                else:
                    fill_ratio = 0
                fill_w = int(slider_w * fill_ratio)
                pygame.draw.rect(self.screen, (100, 150, 100), (slider_x, slider_y, fill_w, slider_h), border_radius=3)

                # 滑块
                handle_w = 10
                handle_x = slider_x + fill_ratio * (slider_w - handle_w)
                self._inv_slider_handle_rect = pygame.Rect(int(handle_x), slider_y - 2, handle_w, slider_h + 4)
                pygame.draw.rect(self.screen, (200, 200, 200), self._inv_slider_handle_rect, border_radius=3)

                y = slider_y + slider_h + 8  # 滑动条下方留间距

                # 数量 + 总价（一行）
                qty_total = f"{self._inv_sell_qty}个={price * self._inv_sell_qty}金"
                qty_text = self.font_small.render(qty_total, True, (255, 220, 100))
                qty_rect = qty_text.get_rect(centerx=rect.centerx, top=y)
                self.screen.blit(qty_text, qty_rect)
                y += 18

                # 出售按钮（全宽）
                self._inv_sell_rect = pygame.Rect(rect.x + 5, y, rect.width - 10, 20)
                pygame.draw.rect(self.screen, (100, 80, 60), self._inv_sell_rect, border_radius=3)
                sell_text = self.font_small.render("出售", True, (255, 220, 150))
                sell_rect = sell_text.get_rect(center=self._inv_sell_rect.center)
                self.screen.blit(sell_text, sell_rect)
                y += 24

                # 全部出售按钮（全宽）
                self._inv_sell_all_rect = pygame.Rect(rect.x + 5, y, rect.width - 10, 20)
                pygame.draw.rect(self.screen, (80, 100, 80), self._inv_sell_all_rect, border_radius=3)
                sell_all_text = self.font_small.render("全部出售", True, (200, 255, 200))
                sell_all_rect = sell_all_text.get_rect(center=self._inv_sell_all_rect.center)
                self.screen.blit(sell_all_text, sell_all_rect)
            else:
                price_text = self.font_small.render(f"种子价: {item.get('seed_price', 5)}金", True, (200, 200, 150))
                self.screen.blit(price_text, (rect.x + 5, y))

        elif item["type"] == "pet":
            # 宠物详情 - 简单介绍
            intro = Pet.get_intro(item['id']) or '这是一只宠物'
            intro_text = self.font_small.render(intro, True, (150, 200, 150))
            self.screen.blit(intro_text, (rect.x + 5, y))
            y += 16

            # 释放/收回按钮
            pet_id = item['id']
            is_released = False
            if hasattr(self.world, 'pet_manager'):
                for pet in self.world.pet_manager.scene_pets:
                    if pet.pet_id == pet_id:
                        is_released = True
                        break

            btn_text = "收回" if is_released else "释放"
            btn_color = (150, 100, 100) if is_released else (100, 150, 100)
            self._inv_pet_btn_rect = pygame.Rect(rect.x + 5, y, rect.width - 10, 20)
            pygame.draw.rect(self.screen, btn_color, self._inv_pet_btn_rect, border_radius=3)
            btn_text_surf = self.font_small.render(btn_text, True, (255, 255, 255))
            btn_text_rect = btn_text_surf.get_rect(center=self._inv_pet_btn_rect.center)
            self.screen.blit(btn_text_surf, btn_text_rect)
            y += 24

            # 重命名按钮
            self._inv_pet_rename_rect = pygame.Rect(rect.x + 5, y, rect.width - 10, 20)
            pygame.draw.rect(self.screen, (100, 100, 150), self._inv_pet_rename_rect, border_radius=3)
            rename_text = self.font_small.render("重命名", True, (200, 200, 255))
            rename_text_rect = rename_text.get_rect(center=self._inv_pet_rename_rect.center)
            self.screen.blit(rename_text, rename_text_rect)

        elif item["type"] == "furniture":
            from ..entities.furniture import Furniture
            desc = Furniture.get_description(item["id"])
            # 自动换行显示描述
            max_width = rect.width - 10  # 最大宽度
            lines = self._wrap_text(desc, self.font_small, max_width)
            for i, line in enumerate(lines[:3]):  # 最多显示3行
                line_text = self.font_small.render(line, True, (150, 180, 200))
                self.screen.blit(line_text, (rect.x + 5, y + i * 16))

    def render_furniture_place_menu(self):
        """渲染家具放置菜单"""
        if not hasattr(self, '_fp_category'):
            return

        from ..entities.furniture import Furniture

        # 界面尺寸（自适应屏幕）
        margin = 40
        panel_x = margin
        panel_y = 32
        panel_w = self.screen_width - margin * 2
        panel_h = self.screen_height - panel_y - 40  # 避开底部栏
        tab_h = 25
        list_w = panel_w - 10  # 全宽列表

        # 背景（使用专用背景图，等比缩放适应面板，不拉伸）
        if self.fsm_background:
            bg_w, bg_h = self.fsm_background.get_size()
            scale = min(panel_w / bg_w, panel_h / bg_h)
            new_w, new_h = int(bg_w * scale), int(bg_h * scale)
            scaled_bg = pygame.transform.smoothscale(self.fsm_background, (new_w, new_h))
            self.screen.blit(scaled_bg, (panel_x, panel_y))
        elif self.bag_background:
            scaled_bg = pygame.transform.smoothscale(self.bag_background, (panel_w, panel_h))
            self.screen.blit(scaled_bg, (panel_x, panel_y))
        else:
            pygame.draw.rect(self.screen, (45, 45, 55), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(self.screen, (80, 80, 100), (panel_x, panel_y, panel_w, panel_h), 2)

        # 关闭按钮
        close_rect = pygame.Rect(panel_x + panel_w - 25, panel_y + 3, 22, 22)
        if "close" in self.ui_icons:
            close_icon = self.ui_icons["close"]
            close_size = max(16, min(20, self.screen_width // 40))
            close_icon = pygame.transform.smoothscale(close_icon, (close_size, close_size))
            self.screen.blit(close_icon, close_rect)
        else:
            pygame.draw.rect(self.screen, (150, 80, 80), close_rect)
            text = self.font_small.render("X", True, (255, 255, 255))
            self.screen.blit(text, close_rect)
        self._fp_close_rect = close_rect

        # 标题
        title = self.font_medium.render("选择家具", True, (255, 220, 100))
        self.screen.blit(title, (panel_x + 10, panel_y + 5))

        # 分类标签（按物体类型）
        categories = [
            ("all", "全部"),
            ("ground", "地面"),
            ("surface", "平面"),
            ("surface_wall", "可挂"),
            ("wall_mount", "墙挂"),
        ]
        tab_x = panel_x + 80
        self._fp_tab_rects = {}
        for cat_id, cat_name in categories:
            tab_rect = pygame.Rect(tab_x, panel_y + 5, 45, 20)
            is_selected = (self._fp_category == cat_id)
            color = (100, 120, 160) if is_selected else (60, 60, 70)
            pygame.draw.rect(self.screen, color, tab_rect, border_radius=3)
            pygame.draw.rect(self.screen, (100, 100, 120), tab_rect, 1, border_radius=3)
            text = self.font_small.render(cat_name, True, (255, 255, 255) if is_selected else (150, 150, 150))
            text_rect = text.get_rect(center=tab_rect.center)
            self.screen.blit(text, text_rect)
            self._fp_tab_rects[cat_id] = tab_rect
            tab_x += 50

        # 获取家具列表
        items = self.get_fp_items()

        # 物品列表区域
        list_rect = pygame.Rect(panel_x + 5, panel_y + tab_h + 5, list_w, panel_h - tab_h - 15)
        self._fp_list_rect = list_rect
        # 半透明背景
        list_bg = pygame.Surface((list_w, panel_h - tab_h - 15), pygame.SRCALPHA)
        list_bg.fill((35, 35, 45, 150))
        self.screen.blit(list_bg, (panel_x + 5, panel_y + tab_h + 5))
        pygame.draw.rect(self.screen, (70, 70, 90), list_rect, 1)

        # 渲染家具图标列表
        self._fp_item_rects = []
        cell_size = max(50, min(65, self.screen_width // 12))
        cols = list_w // cell_size
        if cols < 1:
            cols = 1
        item_h = cell_size
        visible_rows = list_rect.height // item_h
        total_rows = (len(items) + cols - 1) // cols if items else 0

        # 计算滚动偏移
        max_scroll = max(0, total_rows - visible_rows)
        self._fp_list_scroll = max(0, min(self._fp_list_scroll, max_scroll))

        # 裁剪列表区域
        self.screen.set_clip(list_rect)

        for i in range(len(items)):
            item = items[i]
            row = i // cols
            col = i % cols

            # 计算位置
            cell_y = list_rect.y + 5 + (row - self._fp_list_scroll) * item_h
            cell_x = list_rect.x + 5 + col * cell_size

            # 跳过不可见项
            if cell_y + item_h < list_rect.y or cell_y > list_rect.y + list_rect.height:
                continue

            # 选中高亮
            cell_rect = pygame.Rect(cell_x, cell_y, cell_size - 4, cell_size - 4)
            if i == self._fp_selected_idx:
                pygame.draw.rect(self.screen, (70, 80, 110), cell_rect, border_radius=5)

            # 物品图标
            icon_size = max(36, min(48, self.screen_width // 16))
            icon_x = cell_x + (cell_size - 4 - icon_size) // 2
            icon_y = cell_y + 5

            preview = item.get("preview")
            if preview:
                scaled = self.get_cached_icon(preview, icon_size, item.get("id"))
                self.screen.blit(scaled, (icon_x, icon_y))
            else:
                pygame.draw.rect(self.screen, (100, 100, 100), (icon_x, icon_y, icon_size, icon_size), border_radius=5)

            # 数量条
            amount = item['amount']
            bar_h = 16
            bar_y = cell_y + cell_size - 4 - bar_h
            bar_rect = pygame.Rect(cell_x + 2, bar_y, cell_size - 8, bar_h)
            pygame.draw.rect(self.screen, (30, 30, 40, 180), bar_rect, border_radius=3)

            # 数量文字
            amount_text = self.font_small.render(str(amount), True, (255, 255, 255))
            text_rect = amount_text.get_rect(center=bar_rect.center)
            self.screen.blit(amount_text, text_rect)

            # 存储rect和对应的item索引
            self._fp_item_rects.append((cell_rect, i))

        self.screen.set_clip(None)

    def handle_furniture_place_click(self, screen_pos: tuple) -> bool:
        """处理家具放置菜单点击"""
        x, y = screen_pos

        # 检查关闭按钮
        if hasattr(self, '_fp_close_rect') and self._fp_close_rect.collidepoint(x, y):
            self.close_menu()
            return True

        # 检查分类标签
        if hasattr(self, '_fp_tab_rects'):
            for cat_id, tab_rect in self._fp_tab_rects.items():
                if tab_rect.collidepoint(x, y):
                    self._fp_category = cat_id
                    self.game_manager.ui_settings["fp_category"] = cat_id  # 持久化到存档
                    self._fp_selected_idx = 0
                    return True

        # 检查家具列表点击
        if hasattr(self, '_fp_item_rects'):
            for item_rect, item_idx in self._fp_item_rects:
                if item_rect.collidepoint(x, y):
                    self._fp_selected_idx = item_idx
                    # 双击或再次点击确认放置
                    items = self.get_fp_items()
                    if items and item_idx < len(items):
                        selected = items[item_idx]
                        self._place_furniture(selected['id'])
                    return True

        # 点击外部关闭
        if not self.menu_rect.collidepoint(x, y):
            self.close_menu()
            return True

        return False

    def _place_furniture(self, furniture_id: str):
        """进入放置模式"""
        # 关闭菜单
        self.close_menu()
        # 进入放置模式
        self._placing_furniture = True
        self._placing_furniture_id = furniture_id
        self._placing_pos = (0, 0)  # 初始位置
        # 加载要放置的家具图片
        from ..entities.furniture import Furniture
        Furniture.load_all_images()
        print(f"进入放置模式: {furniture_id}")

    def render_menu(self):
        """渲染菜单（支持滚动和边界检测）"""
        if not self.menu_items:
            return

        # 计算菜单内容高度
        content_height = len(self.menu_items) * 25 + 20
        menu_height = min(content_height, self.screen_height - 40)  # 最大高度为屏幕高度-40

        # 计算菜单宽度（自适应屏幕）
        menu_width = min(200, self.screen_width - 20)

        # 计算菜单位置（居中，不超出屏幕）
        menu_x = max(10, min((self.screen_width - menu_width) // 2, self.screen_width - menu_width - 10))
        menu_y = max(10, min((self.screen_height - menu_height) // 2, self.screen_height - menu_height - 10))

        # 更新菜单矩形
        self.menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)

        # 绘制菜单背景
        pygame.draw.rect(self.screen, (60, 60, 60), self.menu_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), self.menu_rect, 2)

        # 设置裁剪区域（防止内容溢出）
        clip_rect = pygame.Rect(menu_x + 2, menu_y + 2, menu_width - 4, menu_height - 4)
        self.screen.set_clip(clip_rect)

        # 绘制菜单项（带滚动偏移）
        for i, item in enumerate(self.menu_items):
            # 计算项的位置（应用滚动偏移）
            item_y = menu_y + 10 + i * 25 + self.menu_scroll_offset

            # 跳过不在可视区域内的项
            if item_y + 25 < menu_y or item_y > menu_y + menu_height:
                continue

            # 更新item的rect位置
            item_rect = pygame.Rect(menu_x + 10, item_y, menu_width - 20, 22)
            item["rect"] = item_rect

            # 按钮背景（如果有action）
            if item["action"]:
                pygame.draw.rect(self.screen, (80, 80, 80), item_rect)
                pygame.draw.rect(self.screen, (120, 120, 120), item_rect, 1)

            # 预览图（如果有）
            preview = item.get("preview")
            icon_key = item.get("icon")

            if preview:
                preview_rect = preview.get_rect(midleft=(item_rect.left + 3, item_rect.centery))
                self.screen.blit(preview, preview_rect)
                # 文字在预览图右边
                text = self.font_small.render(item["text"], True, (255, 255, 255))
                text_rect = text.get_rect(midleft=(item_rect.left + 28, item_rect.centery))
                self.screen.blit(text, text_rect)
            elif icon_key and icon_key in self.ui_icons:
                # 使用UI图标
                icon = self.ui_icons[icon_key]
                icon_rect = icon.get_rect(midleft=(item_rect.left + 3, item_rect.centery))
                self.screen.blit(icon, icon_rect)
                # 文字在图标右边
                text = self.font_small.render(item["text"], True, (255, 255, 255))
                text_rect = text.get_rect(midleft=(item_rect.left + 28, item_rect.centery))
                self.screen.blit(text, text_rect)
            else:
                # 文字
                text = self.font_small.render(item["text"], True, (255, 255, 255))
                text_rect = text.get_rect(center=item_rect.center)
                self.screen.blit(text, text_rect)

        # 取消裁剪
        self.screen.set_clip(None)

        # 计算最大滚动量
        self.menu_max_scroll = max(0, content_height - menu_height)

        # 如果内容超出菜单高度，绘制滚动条
        if content_height > menu_height:
            scrollbar_height = max(20, int(menu_height * menu_height / content_height))
            scrollbar_y = menu_y + 5 - int(self.menu_scroll_offset * menu_height / content_height)
            pygame.draw.rect(self.screen, (150, 150, 150),
                           (menu_x + menu_width - 12, scrollbar_y, 8, scrollbar_height))

    def scroll_menu(self, direction: int):
        """滚动菜单"""
        self.menu_scroll_offset += direction * 20
        # 限制滚动范围
        self.menu_scroll_offset = max(-self.menu_max_scroll, min(0, self.menu_scroll_offset))

    def render_floor_selector(self):
        """渲染地板/种植区样式选择器（发散线条）"""
        if not self.floor_selector_active or not self.floor_selector_lines:
            return

        # 获取样式图片
        floor_images = self.world.floor_images if hasattr(self.world, 'floor_images') else {}
        farm_images = self.world.farm_images if hasattr(self.world, 'farm_images') else {}

        # 判断是地板还是种植区选择器
        is_farm = False
        if self.floor_selector_grid:
            grid_x, grid_y = self.floor_selector_grid
            tile_type = self.world.get_tile_type(grid_x, grid_y)
            if tile_type == self.world.TILE_FARM:
                is_farm = True

        preview_radius = max(20, min(25, self.screen_width // 30))  # 圆圈半径（自适应屏幕）

        # 绘制发散线
        for i, line in enumerate(self.floor_selector_lines):
            start = line["start"]
            end = line["end"]  # 线条终点（在圆圈边缘）
            click_pos = line["click_pos"]  # 圆圈中心
            style_index = line["style"]["index"]

            # 绘制线条（从中心到圆圈边缘）
            pygame.draw.line(self.screen, (200, 200, 200),
                           (int(start[0]), int(start[1])),
                           (int(end[0]), int(end[1])), 2)

            # 绘制圆圈背景
            pygame.draw.circle(self.screen, (80, 80, 80),
                             (int(click_pos[0]), int(click_pos[1])), preview_radius)
            pygame.draw.circle(self.screen, (150, 150, 150),
                             (int(click_pos[0]), int(click_pos[1])), preview_radius, 2)

            # 在圆圈内绘制样式预览图
            preview_size = max(28, min(36, self.screen_width // 22))  # 预览图大小（自适应屏幕）

            # 选择正确的图片库
            if is_farm:
                images = farm_images
            else:
                images = floor_images

            if style_index in images:
                # 使用图片作为预览
                preview_img = images[style_index]
                # 确保图片有正确的alpha通道
                if preview_img.get_flags() & pygame.SRCALPHA:
                    scaled_preview = pygame.transform.smoothscale(preview_img, (preview_size, preview_size))
                else:
                    scaled_preview = pygame.transform.smoothscale(preview_img, (preview_size, preview_size))
                    scaled_preview = scaled_preview.convert_alpha()
                # 渲染在圆圈中心
                preview_rect = scaled_preview.get_rect(center=(click_pos[0], click_pos[1]))
                self.screen.blit(scaled_preview, preview_rect)
            else:
                # 如果没有图片，绘制一个菱形预览
                diamond_points = [
                    (click_pos[0], click_pos[1] - preview_size//2),  # 上
                    (click_pos[0] + preview_size//2, click_pos[1]),  # 右
                    (click_pos[0], click_pos[1] + preview_size//2),  # 下
                    (click_pos[0] - preview_size//2, click_pos[1])   # 左
                ]
                # 根据样式选择颜色
                if is_farm:
                    colors = [(139, 90, 43), (100, 150, 255), (200, 150, 100), (240, 220, 160)]  # 土生、水生、盆栽、沙生
                else:
                    colors = [(180, 150, 120), (200, 200, 210), (150, 100, 100)]  # 木地板、瓷砖、地毯
                color = colors[style_index] if style_index < len(colors) else (100, 100, 100)
                pygame.draw.polygon(self.screen, color, diamond_points)
                pygame.draw.polygon(self.screen, (50, 50, 50), diamond_points, 2)

            # 绘制样式名称（在圆圈下方）
            style_name = line["style"]["name"]
            text = self.font_small.render(style_name, True, (255, 255, 255))
            text_rect = text.get_rect(center=(click_pos[0], click_pos[1] + preview_radius + 12))
            self.screen.blit(text, text_rect)

        # 绘制中心点高亮
        if self.floor_selector_center:
            cx, cy = self.floor_selector_center
            pygame.draw.circle(self.screen, (255, 255, 0),
                             (int(cx), int(cy)), 2)
            pygame.draw.circle(self.screen, (200, 200, 0),
                             (int(cx), int(cy)), 2, 1)

    def render_seed_selector(self):
        """渲染种子/作物操作选择器（发散线条）"""
        if not self.seed_selector_active or not self.seed_selector_lines:
            return

        preview_radius = max(20, min(25, self.screen_width // 30))

        for line in self.seed_selector_lines:
            start = line["start"]
            end = line["end"]
            click_pos = line["click_pos"]

            # 绘制线条
            pygame.draw.line(self.screen, (200, 200, 200),
                           (int(start[0]), int(start[1])),
                           (int(end[0]), int(end[1])), 2)

            # 绘制圆圈背景
            pygame.draw.circle(self.screen, (80, 80, 80),
                             (int(click_pos[0]), int(click_pos[1])), preview_radius)
            pygame.draw.circle(self.screen, (150, 150, 150),
                             (int(click_pos[0]), int(click_pos[1])), preview_radius, 2)

            # 区分种子选择器和作物操作选择器
            if "seed" in line:
                # 种子选择器：显示种子预览图
                seed = line["seed"]
                preview = line.get("preview")
                preview_size = max(28, min(36, self.screen_width // 22))
                if preview:
                    scaled = self.get_cached_icon(preview, preview_size, seed.get("id"))
                    rect = scaled.get_rect(center=(click_pos[0], click_pos[1]))
                    self.screen.blit(scaled, rect)
                else:
                    pygame.draw.circle(self.screen, (100, 200, 100),
                                     (int(click_pos[0]), int(click_pos[1])), preview_size // 2)
                name_text = self.font_small.render(seed["name"], True, (255, 255, 255))
                name_rect = name_text.get_rect(center=(click_pos[0], click_pos[1] + preview_radius + 12))
                self.screen.blit(name_text, name_rect)
                count_text = self.font_small.render(f"x{seed['count']}", True, (200, 200, 200))
                count_rect = count_text.get_rect(center=(click_pos[0], click_pos[1] + preview_radius + 28))
                self.screen.blit(count_text, count_rect)
            elif "action" in line:
                # 作物操作选择器：显示图标
                action = line["action"]
                action_id = action.get("id", "")
                # 尝试使用UI图标
                if action_id in self.ui_icons:
                    icon = self.ui_icons[action_id]
                    icon_size = max(28, min(36, self.screen_width // 22))
                    icon = self.get_cached_icon(icon, icon_size, action_id)
                    rect = icon.get_rect(center=(click_pos[0], click_pos[1]))
                    self.screen.blit(icon, rect)
                else:
                    # 回退到彩色圆形
                    color = action.get("color", (200, 200, 200))
                    pygame.draw.circle(self.screen, color,
                                     (int(click_pos[0]), int(click_pos[1])), 15)
                    pygame.draw.circle(self.screen, (50, 50, 50),
                                     (int(click_pos[0]), int(click_pos[1])), 15, 2)
                # 绘制操作名称
                name_text = self.font_small.render(action["name"], True, (255, 255, 255))
                name_rect = name_text.get_rect(center=(click_pos[0], click_pos[1] + preview_radius + 12))
                self.screen.blit(name_text, name_rect)

        # 绘制中心点高亮
        if self.seed_selector_center:
            cx, cy = self.seed_selector_center
            pygame.draw.circle(self.screen, (255, 255, 0),
                             (int(cx), int(cy)), 2)
            pygame.draw.circle(self.screen, (200, 200, 0),
                             (int(cx), int(cy)), 2, 1)

    def render_feed_menu(self):
        """渲染喂食菜单面板"""
        if not self.feed_menu_active or not self._feed_menu_rect:
            return

        rect = self._feed_menu_rect

        # 半透明背景遮罩
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        # 面板背景
        pygame.draw.rect(self.screen, (45, 45, 55), rect, border_radius=8)
        pygame.draw.rect(self.screen, (80, 80, 100), rect, 2, border_radius=8)

        # 标题
        title = self.font_medium.render("选择喂食物品", True, (255, 220, 100))
        title_x = rect.x + (rect.width - title.get_width()) // 2
        self.screen.blit(title, (title_x, rect.y + 10))

        # 物品列表区域
        list_y = rect.y + 40
        list_h = rect.height - 90  # 留出标题和按钮空间
        item_h = 40

        # 裁剪列表区域
        list_rect = pygame.Rect(rect.x + 5, list_y, rect.width - 10, list_h)
        self.screen.set_clip(list_rect)

        self._feed_item_rects = []

        if not self.feed_menu_items:
            # 没有可喂食的物品
            empty_text = self.font_small.render("背包中没有可喂食的物品", True, (150, 150, 150))
            text_rect = empty_text.get_rect(center=(rect.centerx, list_y + list_h // 2))
            self.screen.blit(empty_text, text_rect)
        else:
            for i, item in enumerate(self.feed_menu_items):
                item_y = list_y + 5 + (i - self.feed_menu_scroll) * item_h
                if item_y + item_h < list_y or item_y > list_y + list_h:
                    continue

                item_rect = pygame.Rect(rect.x + 10, item_y, rect.width - 20, item_h - 4)

                # 选中高亮
                if i == self.feed_menu_selected_idx:
                    pygame.draw.rect(self.screen, (70, 80, 110), item_rect, border_radius=5)

                # 物品图标（使用成熟果实图 stage3）
                icon_size = 32
                icon = self.harvest_previews.get(item['id'])
                if icon:
                    scaled = pygame.transform.smoothscale(icon, (icon_size, icon_size))
                    self.screen.blit(scaled, (item_rect.x + 5, item_rect.y + (item_h - icon_size) // 2))

                # 物品名称和数量
                from ..entities.crop import Crop
                crop_data = Crop.CROP_DATA.get(item['id'], {})
                name = crop_data.get("name", item['id'])
                name_text = self.font_small.render(f"{name} x{item['quantity']}", True, (255, 255, 255))
                self.screen.blit(name_text, (item_rect.x + 45, item_rect.y + (item_h - name_text.get_height()) // 2))

                self._feed_item_rects.append((item_rect, i))

        self.screen.set_clip(None)

        # 确认按钮
        btn_w = 80
        btn_h = 30
        btn_y = rect.y + rect.height - 40
        confirm_x = rect.x + rect.width // 2 - btn_w - 10
        self._feed_confirm_rect = pygame.Rect(confirm_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(self.screen, (80, 160, 80), self._feed_confirm_rect, border_radius=5)
        confirm_text = self.font_small.render("确认", True, (255, 255, 255))
        text_rect = confirm_text.get_rect(center=self._feed_confirm_rect.center)
        self.screen.blit(confirm_text, text_rect)

        # 关闭按钮
        close_x = rect.x + rect.width // 2 + 10
        self._feed_close_rect = pygame.Rect(close_x, btn_y, btn_w, btn_h)
        pygame.draw.rect(self.screen, (150, 80, 80), self._feed_close_rect, border_radius=5)
        close_text = self.font_small.render("关闭", True, (255, 255, 255))
        text_rect = close_text.get_rect(center=self._feed_close_rect.center)
        self.screen.blit(close_text, text_rect)
