"""
宠物管理器 - 管理所有宠物的行为、碰撞和渲染
"""
import pygame
import random
import math
import time
from ..entities.pet import Pet


class PetManager:
    """宠物管理器"""

    def __init__(self, world):
        """初始化宠物管理器"""
        self.world = world
        self.scene_pets = []  # 场景中的宠物列表
        self.pet_data = {}  # 所有宠物数据 {instance_id: pet_data_dict}
        self.active_pets = []  # 已释放的宠物实例ID列表

        # 加载宠物精灵图和 footprint
        Pet.load_config()  # 先加载配置
        Pet.load_all_images()
        Pet.load_all_footprints()

        # 有效巡逻区域缓存
        self._valid_patrol_area = None
        self._last_edit_mode = False

        # 重叠检测计时器（每5秒检查一次）
        self._overlap_check_timer = 0.0
        self._overlap_check_interval = 5.0  # 秒

        # 宠物计数器（用于生成唯一ID）
        self._pet_counter = {}  # {pet_type: count}

        # 水种植区临时通行标志（puddle_play 使用）
        self.allow_water_access = False

    def _generate_instance_id(self, pet_type):
        """为宠物生成唯一实例ID"""
        if pet_type not in self._pet_counter:
            self._pet_counter[pet_type] = 0
        self._pet_counter[pet_type] += 1
        return f"{pet_type}_{self._pet_counter[pet_type]}"

    def _get_pet_type(self, instance_id):
        """从实例ID获取宠物类型"""
        # 实例ID格式：pet_type_数字，如 golden_retriever_1
        # 先检查是否是已知的宠物类型（完整匹配）
        if instance_id in Pet._images or instance_id in Pet.PET_CONFIG:
            return instance_id
        # 尝试去掉末尾的 _数字 后缀
        last_underscore = instance_id.rfind('_')
        if last_underscore > 0:
            suffix = instance_id[last_underscore + 1:]
            if suffix.isdigit():
                return instance_id[:last_underscore]
        return instance_id

    def _is_old_format_id(self, pet_id):
        """检查是否是旧格式的宠物ID（没有数字后缀）"""
        last_underscore = pet_id.rfind('_')
        if last_underscore > 0:
            suffix = pet_id[last_underscore + 1:]
            return not suffix.isdigit()
        return True

    def load_pets_from_save(self, save_data):
        """从存档数据加载宠物"""
        pets_data = save_data.get("pets", {})
        inventory_pets = save_data.get("inventory", {}).get("pets", [])

        # 兼容旧格式（只是宠物类型ID列表）
        if isinstance(pets_data, list):
            # 旧格式：["golden_retriever", "blue_cat"]
            # 转换为新格式：为每只宠物生成唯一实例ID
            self.active_pets = []
            self.pet_data = {}
            for pet_type in pets_data:
                instance_id = self._generate_instance_id(pet_type)
                self.active_pets.append(instance_id)
                self.pet_data[instance_id] = {
                    "pet_type": pet_type,
                    "name": pet_type,
                    "happiness": 0,
                    "satiety": 50,
                    "level": 0,
                    "x": 0,
                    "y": 0,
                    "is_released": True,
                    "last_interaction_time": 0,
                    "last_petting_time": 0,
                    "last_puddle_play_time": 0
                }
        elif isinstance(pets_data, dict):
            # 新格式：{"active_pets": [...], "pet_data": {...}}
            old_active = pets_data.get("active_pets", [])
            old_pet_data = pets_data.get("pet_data", {})
            self.active_pets = []
            self.pet_data = {}

            # 检查是否需要转换旧格式ID
            for old_id in old_active:
                if self._is_old_format_id(old_id):
                    # 旧格式：需要转换为实例ID
                    instance_id = self._generate_instance_id(old_id)
                    self.active_pets.append(instance_id)
                    # 从旧 pet_data 中迁移数据
                    data = old_pet_data.get(old_id, {})
                    data["pet_type"] = old_id
                    self.pet_data[instance_id] = data
                else:
                    # 新格式：直接使用
                    self.active_pets.append(old_id)
                    if old_id in old_pet_data:
                        self.pet_data[old_id] = old_pet_data[old_id]

            # 迁移不在 active_pets 中的 pet_data
            for old_id, data in old_pet_data.items():
                if old_id not in self.pet_data:
                    if self._is_old_format_id(old_id):
                        instance_id = self._generate_instance_id(old_id)
                        data["pet_type"] = old_id
                        self.pet_data[instance_id] = data
                    else:
                        self.pet_data[old_id] = data

            # 确保每只宠物都有 pet_type 字段
            for instance_id, data in self.pet_data.items():
                if "pet_type" not in data:
                    data["pet_type"] = self._get_pet_type(instance_id)
        else:
            # 没有顶层 pets 数据，不自动释放任何宠物
            self.active_pets = []
            self.pet_data = {}

        # 兼容旧的 inventory.pets 格式（宠物类型列表）
        # 转换为新的实例ID格式
        new_inventory_pets = []
        for pet_id in inventory_pets:
            # 如果已经是实例ID格式（直接存在于 pet_data 中），直接使用
            if pet_id in self.pet_data:
                new_inventory_pets.append(pet_id)
            elif not self._is_old_format_id(pet_id):
                # 新格式ID但不在 pet_data 中，直接使用
                new_inventory_pets.append(pet_id)
            else:
                # 旧格式：宠物类型，需要生成实例ID
                # 检查是否已经在 pet_data 中（作为旧格式key）
                found = False
                for existing_id in self.pet_data.keys():
                    existing_type = self.pet_data[existing_id].get("pet_type", self._get_pet_type(existing_id))
                    if existing_type == pet_id or existing_id == pet_id:
                        new_inventory_pets.append(existing_id)
                        found = True
                        break
                if not found:
                    # 创建新的实例ID
                    instance_id = self._generate_instance_id(pet_id)
                    new_inventory_pets.append(instance_id)
                    self.pet_data[instance_id] = {
                        "pet_type": pet_id,
                        "name": pet_id,
                        "happiness": 0,
                        "satiety": 50,
                        "level": 0,
                        "x": 0,
                        "y": 0,
                        "is_released": False,
                        "last_interaction_time": 0,
                        "last_petting_time": 0,
                        "last_puddle_play_time": 0
                    }

        # 确保 inventory.pets 中的所有宠物都有 pet_data（但不自动释放）
        for pet_id in new_inventory_pets:
            if pet_id not in self.pet_data:
                pet_type = self._get_pet_type(pet_id)
                self.pet_data[pet_id] = {
                    "pet_type": pet_type,
                    "name": pet_type,
                    "happiness": 0,
                    "satiety": 50,
                    "level": 0,
                    "x": 0,
                    "y": 0,
                    "is_released": False,
                    "last_interaction_time": 0,
                    "last_petting_time": 0,
                    "last_puddle_play_time": 0
                }

        # 更新 inventory.pets 为新格式
        if save_data.get("inventory"):
            save_data["inventory"]["pets"] = new_inventory_pets

        print(f"PetManager 加载: active_pets={self.active_pets}")

        # 释放 active_pets 到场景
        for pet_id in self.active_pets:
            if pet_id in self.pet_data:
                self.release_pet(pet_id)

    def get_save_data(self):
        """获取存档数据"""
        # 更新所有场景宠物的位置数据
        for pet in self.scene_pets:
            if pet.pet_id in self.pet_data:
                self.pet_data[pet.pet_id]["x"] = pet.x
                self.pet_data[pet.pet_id]["y"] = pet.y
                self.pet_data[pet.pet_id]["happiness"] = pet.happiness
                self.pet_data[pet.pet_id]["satiety"] = pet.satiety
                self.pet_data[pet.pet_id]["level"] = pet.level
                self.pet_data[pet.pet_id]["last_interaction_time"] = pet.last_interaction_time
                self.pet_data[pet.pet_id]["last_petting_time"] = pet.last_petting_time
                self.pet_data[pet.pet_id]["last_puddle_play_time"] = pet.last_puddle_play_time

        return {
            "active_pets": self.active_pets,
            "pet_data": self.pet_data
        }

    def release_pet(self, pet_id, grid_x=None, grid_y=None):
        """释放宠物到场景"""
        pet_data = self.pet_data.get(pet_id)
        if not pet_data:
            return False

        # 获取宠物类型（用于获取图片和缩放）
        pet_type = pet_data.get("pet_type", self._get_pet_type(pet_id))

        # 如果没有指定位置，随机选择一个可用区块（避免与其他宠物重叠）
        if grid_x is None or grid_y is None:
            grid_x, grid_y = self._find_safe_release_point()

        if grid_x is None or grid_y is None:
            return False  # 没有可用位置

        # 获取网格中心的世界坐标
        center_x, center_y = self.world.grid_to_world(grid_x + 0.5, grid_y + 0.5)

        # 转换为宠物的左上角坐标
        # 宠物的 (x, y) 是精灵图左上角，需要将中心转换为左上角
        from ..entities.pet import Pet
        frames = Pet._images.get(pet_type, {}).get("idle", [])
        if frames:
            img_w, img_h = frames[0].get_size()
            total_scale = Pet.get_total_scale(pet_type)
            scaled_w = img_w * total_scale
            scaled_h = img_h * total_scale
            top_left_x = center_x - scaled_w / 2
            top_left_y = center_y - scaled_h / 2
            pet_data["x"] = top_left_x
            pet_data["y"] = top_left_y
        else:
            pet_data["x"] = center_x
            pet_data["y"] = center_y

        pet_data["is_released"] = True

        # 添加到场景宠物列表
        pet = Pet(pet_id, pet_data)
        self.scene_pets.append(pet)

        # 确保在 active_pets 列表中
        if pet_id not in self.active_pets:
            self.active_pets.append(pet_id)

        return True

    def _find_safe_release_point(self):
        """随机选择一个安全的释放位置（不与其他宠物重叠）"""
        if self._valid_patrol_area is None:
            self._update_valid_patrol_area()

        if not self._valid_patrol_area:
            return None, None

        # 获取已占用的区块
        occupied_grids = set()
        for pet in self.scene_pets:
            grid = self.world.world_to_grid(pet.x, pet.y)
            occupied_grids.add((math.floor(grid[0]), math.floor(grid[1])))

        # 尝试多次找到未占用的位置
        max_attempts = 20
        for _ in range(max_attempts):
            grid_x, grid_y = random.choice(self._valid_patrol_area)
            if (grid_x, grid_y) not in occupied_grids:
                return grid_x, grid_y

        # 如果找不到未占用的位置，使用原来的随机选择
        return self._find_random_release_point()

    def recall_pet(self, pet_id):
        """收回宠物到背包"""
        pet_data = self.pet_data.get(pet_id)
        if not pet_data:
            return False

        # 先同步宠物位置数据
        for pet in self.scene_pets:
            if pet.pet_id == pet_id:
                pet_data["x"] = pet.x
                pet_data["y"] = pet.y
                pet_data["happiness"] = pet.happiness
                pet_data["satiety"] = pet.satiety
                pet_data["level"] = pet.level
                pet_data["last_interaction_time"] = pet.last_interaction_time
                pet_data["last_petting_time"] = pet.last_petting_time
                pet_data["last_puddle_play_time"] = pet.last_puddle_play_time
                break

        pet_data["is_released"] = False

        # 从活跃列表和场景移除
        if pet_id in self.active_pets:
            self.active_pets.remove(pet_id)
        self.scene_pets = [p for p in self.scene_pets if p.pet_id != pet_id]

        return True

    def enter_edit_mode(self):
        """进入编辑模式 - 暂时收回所有宠物"""
        # 先同步宠物所有数据
        for pet in self.scene_pets:
            if pet.pet_id in self.pet_data:
                self.pet_data[pet.pet_id]["x"] = pet.x
                self.pet_data[pet.pet_id]["y"] = pet.y
                self.pet_data[pet.pet_id]["happiness"] = pet.happiness
                self.pet_data[pet.pet_id]["satiety"] = pet.satiety
                self.pet_data[pet.pet_id]["level"] = pet.level
                self.pet_data[pet.pet_id]["last_interaction_time"] = pet.last_interaction_time
                self.pet_data[pet.pet_id]["last_petting_time"] = pet.last_petting_time
                self.pet_data[pet.pet_id]["last_puddle_play_time"] = pet.last_puddle_play_time
        self.scene_pets.clear()
        self._is_edit_mode = True

    def exit_edit_mode(self):
        """退出编辑模式 - 重新放出宠物（带安全检查，避免重叠）"""
        self._is_edit_mode = False

        # 确保有效巡逻区域已更新
        self._valid_patrol_area = None
        self._update_valid_patrol_area()

        for pet_id in self.active_pets:
            pet_data = self.pet_data.get(pet_id)
            if pet_data and pet_data.get("is_released", False):
                # 检查当前位置是否安全（不与其他宠物重叠）
                test_pet = Pet(pet_id, pet_data)
                if self._is_position_safe(test_pet.x, test_pet.y, test_pet):
                    # 位置安全，直接添加
                    self.scene_pets.append(test_pet)
                else:
                    # 位置不安全，寻找安全位置
                    grid_x, grid_y = self._find_safe_release_point()
                    if grid_x is not None and grid_y is not None:
                        world_x, world_y = self.world.grid_to_world(grid_x + 0.5, grid_y + 0.5)
                        pet_data["x"] = world_x
                        pet_data["y"] = world_y
                        test_pet.x = world_x
                        test_pet.y = world_y
                    self.scene_pets.append(test_pet)

    def update(self, dt, camera):
        """更新所有宠物"""
        # 编辑模式检查由 UI.toggle_edit_mode() 处理，这里只检查状态
        is_edit_mode = getattr(self, '_is_edit_mode', False)

        # 如果在编辑模式，不更新宠物
        if is_edit_mode:
            return

        # 更新有效巡逻区域缓存
        self._update_valid_patrol_area()

        # 获取相机缩放倍率（用于碰撞检测）
        zoom = camera.zoom if camera else 1.0

        # 更新所有场景宠物
        for pet in self.scene_pets:
            # 传入有效区域给宠物
            pet.valid_area = self._valid_patrol_area
            pet.world = self.world
            pet._other_pets = self.scene_pets  # 用于宠物间碰撞检测
            pet._pet_manager_ref = self  # 用于 puddle_play 水种植区通行
            pet.update(dt, zoom)

        # 定期检查宠物重叠并分离
        self._overlap_check_timer += dt
        if self._overlap_check_timer >= self._overlap_check_interval:
            self._overlap_check_timer = 0.0
            self._check_and_separate_overlapping_pets(zoom)

    def _update_valid_patrol_area(self):
        """更新有效巡逻区域"""
        if self._valid_patrol_area is not None:
            return  # 已经缓存了

        valid_cells = []

        for grid_y in range(len(self.world.tile_map)):
            for grid_x in range(len(self.world.tile_map[grid_y])):
                tile_type = self.world.tile_map[grid_y][grid_x]

                # 跳过未解锁区域
                if tile_type < 0:
                    continue

                # 跳过水种植区（allow_water_access 时临时允许）
                if tile_type == self.world.TILE_FARM:
                    farm_type = self.world.farm_styles.get((grid_x, grid_y), 0)
                    if farm_type == 1 and not self.allow_water_access:
                        continue

                valid_cells.append((grid_x, grid_y))

        self._valid_patrol_area = valid_cells

    def set_allow_water_access(self, allow: bool):
        """设置是否允许临时进入水种植区"""
        self.allow_water_access = allow
        self._valid_patrol_area = None  # 强制刷新缓存

    def _check_and_separate_overlapping_pets(self, zoom=1.0):
        """检查并分离重叠的宠物

        Args:
            zoom: 相机缩放倍率
        """
        if len(self.scene_pets) < 2:
            return

        # 检查所有宠物对
        for i in range(len(self.scene_pets)):
            for j in range(i + 1, len(self.scene_pets)):
                pet_a = self.scene_pets[i]
                pet_b = self.scene_pets[j]

                # 检查是否重叠
                if self._pets_overlap(pet_a, pet_b, zoom):
                    # 分离宠物 B
                    self._separate_pet(pet_b, pet_a, zoom)

    def _pets_overlap(self, pet_a, pet_b, zoom=1.0):
        """检查两只宠物是否重叠

        Args:
            zoom: 相机缩放倍率
        """
        fp_a = pet_a.get_footprint_world(zoom)
        fp_b = pet_b.get_footprint_world(zoom)

        if not fp_a or not fp_b:
            return False

        # 使用宠物的碰撞检测方法
        return pet_a.check_overlap_with(fp_b, zoom)

    def _separate_pet(self, pet_to_move, pet_stay, zoom=1.0):
        """将 pet_to_move 移动到不与 pet_stay 重叠的位置

        注意：宠物的 (x, y) 是精灵图左上角的世界坐标

        Args:
            zoom: 相机缩放倍率
        """
        # 获取当前重叠的宠物位置（需要转换为中心点）
        stay_center_x, stay_center_y = self._get_pet_center(pet_stay, zoom)

        # 尝试在周围寻找安全位置

        # 搜索半径（像素）- 需要足够大以确保分离后不在 footprint 区域内
        search_radius = 150
        # 最小距离（确保偏移足够远）
        min_distance = 80
        # 最大尝试次数
        max_attempts = 30

        for _ in range(max_attempts):
            # 在周围随机选择一个位置（基于中心点）
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(min_distance, search_radius)
            new_center_x = stay_center_x + math.cos(angle) * distance
            new_center_y = stay_center_y + math.sin(angle) * distance

            # 转换为左上角坐标（宠物的 (x, y) 是左上角）
            new_x, new_y = self._center_to_top_left(new_center_x, new_center_y, pet_to_move, zoom)

            # 检查新位置是否有效（不与其他宠物重叠）
            if self._is_position_safe(new_x, new_y, pet_to_move, zoom):
                # 移动宠物
                pet_to_move.x = new_x
                pet_to_move.y = new_y
                pet_to_move.path = []  # 清除路径，让宠物重新寻路
                pet_to_move.target_pos = None
                print(f"分离宠物 {pet_to_move.pet_id} 到 ({new_x:.1f}, {new_y:.1f})")
                return

        # 如果找不到安全位置，使用网格位置
        self._separate_pet_to_grid(pet_to_move, pet_stay, zoom)

    def _get_pet_center(self, pet, zoom=1.0):
        """获取宠物的中心点世界坐标

        Args:
            zoom: 相机缩放倍率
        """
        # 宠物的 (x, y) 是左上角，需要加上缩放后的宽高的一半
        frames = pet._images.get(pet.pet_type, {}).get(pet.state, [])
        if not frames:
            return pet.x, pet.y

        frame_idx = pet.current_frame % len(frames)
        sprite = frames[frame_idx]
        total_scale = pet.get_total_scale(pet.pet_type)

        # 计算缩放后的尺寸（与渲染一致，需要乘 zoom）
        scaled_w = max(1, int(sprite.get_width() * zoom * total_scale))
        scaled_h = max(1, int(sprite.get_height() * zoom * total_scale))

        # 中心点 = 左上角 + 宽高的一半
        center_x = pet.x + scaled_w / 2
        center_y = pet.y + scaled_h / 2
        return center_x, center_y

    def _center_to_top_left(self, center_x, center_y, pet, zoom=1.0):
        """将中心点坐标转换为左上角坐标

        Args:
            zoom: 相机缩放倍率
        """
        # 宠物的 (x, y) 是左上角，需要减去缩放后的宽高的一半
        frames = pet._images.get(pet.pet_type, {}).get(pet.state, [])
        if not frames:
            return center_x, center_y

        frame_idx = pet.current_frame % len(frames)
        sprite = frames[frame_idx]
        total_scale = pet.get_total_scale(pet.pet_type)

        # 计算缩放后的尺寸（与渲染一致，需要乘 zoom）
        scaled_w = max(1, int(sprite.get_width() * zoom * total_scale))
        scaled_h = max(1, int(sprite.get_height() * zoom * total_scale))

        # 左上角 = 中心点 - 宽高的一半
        top_left_x = center_x - scaled_w / 2
        top_left_y = center_y - scaled_h / 2
        return top_left_x, top_left_y

    def _separate_pet_to_grid(self, pet_to_move, pet_stay, zoom=1.0):
        """将宠物移动到附近的网格位置

        注意：宠物的 (x, y) 是精灵图左上角的世界坐标

        Args:
            zoom: 相机缩放倍率
        """

        # 获取当前中心点，然后转换为网格坐标
        center_x, center_y = self._get_pet_center(pet_to_move, zoom)
        current_grid = self.world.world_to_grid(center_x, center_y)
        current_gx, current_gy = math.floor(current_grid[0]), math.floor(current_grid[1])

        # 尝试周围的网格
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx == 0 and dy == 0:
                    continue

                test_gx = current_gx + dx
                test_gy = current_gy + dy

                # 检查网格是否有效
                if (test_gx, test_gy) not in self._valid_patrol_area:
                    continue

                # 转换为世界坐标（这是网格中心的世界坐标）
                world_center_x, world_center_y = self.world.grid_to_world(test_gx + 0.5, test_gy + 0.5)

                # 转换为宠物的左上角坐标
                new_x, new_y = self._center_to_top_left(world_center_x, world_center_y, pet_to_move, zoom)

                # 检查是否安全
                if self._is_position_safe(new_x, new_y, pet_to_move, zoom):
                    pet_to_move.x = new_x
                    pet_to_move.y = new_y
                    pet_to_move.path = []
                    pet_to_move.target_pos = None
                    print(f"分离宠物 {pet_to_move.pet_id} 到网格 ({test_gx}, {test_gy})")
                    return

    def _is_position_safe(self, x, y, exclude_pet, zoom=1.0):
        """检查位置是否安全（不与其他宠物重叠）

        Args:
            x, y: 要检查的位置（宠物左上角坐标）
            exclude_pet: 要排除的宠物
            zoom: 相机缩放倍率
        """
        # 获取该位置的 footprint
        old_x, old_y = exclude_pet.x, exclude_pet.y
        exclude_pet.x, exclude_pet.y = x, y
        pet_fp = exclude_pet.get_footprint_world(zoom)
        exclude_pet.x, exclude_pet.y = old_x, old_y

        if not pet_fp:
            return True

        # 检查是否与其他宠物重叠
        for other_pet in self.scene_pets:
            if other_pet == exclude_pet:
                continue

            other_fp = other_pet.get_footprint_world(zoom)
            if other_fp and exclude_pet.check_overlap_with(other_fp, zoom):
                return False

        return True

    def _find_random_release_point(self):
        """随机选择一个可用的释放位置"""
        if self._valid_patrol_area is None:
            self._update_valid_patrol_area()

        if not self._valid_patrol_area:
            return None, None

        # 随机选择一个有效区块
        grid_x, grid_y = random.choice(self._valid_patrol_area)
        return grid_x, grid_y

    def is_pet_on_screen(self, pet, camera):
        """检查宠物是否在屏幕内"""
        screen_rect = pet.get_screen_rect(camera)
        if not screen_rect:
            return False

        # 留一些边距
        margin = 100
        screen_width = camera.screen.get_width() if hasattr(camera, 'screen') else 800
        screen_height = camera.screen.get_height() if hasattr(camera, 'screen') else 600

        return (screen_rect.right > -margin and
                screen_rect.left < screen_width + margin and
                screen_rect.bottom > -margin and
                screen_rect.top < screen_height + margin)

    def is_object_behind_pet(self, obj, camera):
        """检查对象是否遮挡了宠物（需要半透明化）

        优化：先做 AABB 包围盒检测，只有包围盒重叠时才进行像素级检测

        注意：使用 footprint_bottom_y 进行深度比较，而不是直接比较 y 坐标
        - 家具的 y 是精灵图中心
        - 宠物的 y 是精灵图左上角
        - 两者语义不同，必须使用统一的比较基准
        """
        # 使用 footprint_bottom_y 进行深度比较（与 world.py 渲染排序一致）
        obj_bottom_y = obj.get_footprint_bottom_y() if hasattr(obj, 'get_footprint_bottom_y') else getattr(obj, 'y', 0)

        for pet in self.scene_pets:
            # 使用宠物的 footprint_bottom_y 进行比较
            pet_bottom_y = pet.get_footprint_bottom_y()

            # 条件1：对象在宠物前面（obj_bottom_y > pet_bottom_y，Y越大越靠近镜头）
            if obj_bottom_y > pet_bottom_y:
                # 条件2：快速 AABB 包围盒检测（性能优化）
                if self._check_aabb_overlap(obj, pet, camera):
                    # 条件3：像素级重叠检测（精确检测）
                    if self._check_pixel_overlap(obj, pet, camera):
                        return True

        return False

    def _check_aabb_overlap(self, obj, pet, camera):
        """快速 AABB 包围盒重叠检测

        注意：宠物和家具的坐标系统不同
        - 宠物：(x, y) 是精灵图左上角的世界坐标
        - 家具：(x, y) 是精灵图中心的世界坐标
        """
        # 获取宠物的屏幕包围盒（宠物的 (x, y) 是左上角）
        pet_screen_x, pet_screen_y = camera.world_to_screen((pet.x, pet.y))
        pet_frames = pet._images.get(pet.pet_type, {}).get(pet.state, [])
        if not pet_frames:
            return False

        pet_frame_idx = pet.current_frame % len(pet_frames)
        pet_sprite = pet_frames[pet_frame_idx]
        pet_scale = pet.get_total_scale(pet.pet_type)
        pet_zoom = camera.zoom

        pet_scaled_w = max(1, int(pet_sprite.get_width() * pet_zoom * pet_scale))
        pet_scaled_h = max(1, int(pet_sprite.get_height() * pet_zoom * pet_scale))

        # 宠物包围盒：左上角在 (pet_screen_x, pet_screen_y)
        pet_rect = pygame.Rect(
            int(pet_screen_x), int(pet_screen_y),
            pet_scaled_w, pet_scaled_h
        )

        # 获取对象的屏幕包围盒（家具的 (x, y) 是中心）
        # 需要将中心转换为左上角
        obj_screen_x, obj_screen_y = camera.world_to_screen((obj.x, obj.y))

        # 获取缩放后的图片尺寸
        if hasattr(obj, 'get_scaled_image'):
            zoom = camera.zoom
            scaled_img = obj.get_scaled_image(obj.furniture_id, zoom, obj.is_flipped)
            if scaled_img:
                obj_scaled_w, obj_scaled_h = scaled_img.get_size()
                # 家具包围盒：左上角在 (obj_screen_x - obj_scaled_w//2, obj_screen_y - obj_scaled_h//2)
                obj_rect = pygame.Rect(
                    int(obj_screen_x - obj_scaled_w // 2),
                    int(obj_screen_y - obj_scaled_h // 2),
                    obj_scaled_w,
                    obj_scaled_h
                )
            else:
                return False
        else:
            # 没有 get_scaled_image 方法，使用 footprint
            obj_rect = self._get_object_screen_rect(obj, camera)
            if not obj_rect:
                return False

        # AABB 重叠检测
        return pet_rect.colliderect(obj_rect)

    def _check_pixel_overlap(self, obj, pet, camera):
        """像素级检测对象是否遮挡宠物

        优化：采样步长根据宠物实际大小动态调整，避免小宠物漏检
        注意：宠物和家具的坐标系统不同
        - 宠物：(x, y) 是精灵图左上角的世界坐标
        - 家具：(x, y) 是精灵图中心的世界坐标
        """
        # 获取宠物的屏幕位置和精灵图（宠物的 (x, y) 是左上角）
        pet_screen_x, pet_screen_y = camera.world_to_screen((pet.x, pet.y))
        pet_frames = pet._images.get(pet.pet_type, {}).get(pet.state, [])
        if not pet_frames:
            return False

        pet_frame_idx = pet.current_frame % len(pet_frames)
        pet_sprite = pet_frames[pet_frame_idx]
        pet_scale = pet.get_total_scale(pet.pet_type)
        pet_zoom = camera.zoom

        # 宠物缩放后的尺寸
        pet_scaled_w = max(1, int(pet_sprite.get_width() * pet_zoom * pet_scale))
        pet_scaled_h = max(1, int(pet_sprite.get_height() * pet_zoom * pet_scale))

        # 宠物在屏幕上的包围盒（左上角在 (pet_screen_x, pet_screen_y)）
        pet_rect = pygame.Rect(
            int(pet_screen_x), int(pet_screen_y),
            pet_scaled_w, pet_scaled_h
        )

        # 获取对象的屏幕包围盒（家具的 (x, y) 是中心）
        # 需要将中心转换为左上角
        obj_screen_x, obj_screen_y = camera.world_to_screen((obj.x, obj.y))

        # 获取缩放后的图片尺寸
        if hasattr(obj, 'get_scaled_image'):
            zoom = camera.zoom
            scaled_img = obj.get_scaled_image(obj.furniture_id, zoom, obj.is_flipped)
            if scaled_img:
                obj_scaled_w, obj_scaled_h = scaled_img.get_size()
                # 家具包围盒：左上角在 (obj_screen_x - obj_scaled_w//2, obj_screen_y - obj_scaled_h//2)
                obj_rect = pygame.Rect(
                    int(obj_screen_x - obj_scaled_w // 2),
                    int(obj_screen_y - obj_scaled_h // 2),
                    obj_scaled_w,
                    obj_scaled_h
                )
            else:
                return False
        else:
            # 没有 get_scaled_image 方法，使用 footprint
            obj_rect = self._get_object_screen_rect(obj, camera)
            if not obj_rect:
                return False

        # 先做快速包围盒检测（已被 _check_aabb_overlap 调用，这里保留作为安全检查）
        if not pet_rect.colliderect(obj_rect):
            return False

        # 像素级检测：检查宠物的非透明像素是否在对象区域内

        # 计算重叠区域
        overlap_left = max(pet_rect.left, obj_rect.left)
        overlap_top = max(pet_rect.top, obj_rect.top)
        overlap_right = min(pet_rect.right, obj_rect.right)
        overlap_bottom = min(pet_rect.bottom, obj_rect.bottom)

        if overlap_left >= overlap_right or overlap_top >= overlap_bottom:
            return False

        # 在重叠区域内采样检测
        # 采样步长（像素）：根据宠物大小动态调整
        # 对于小宠物（如仓鼠），使用更小的步长避免漏检
        overlap_w = overlap_right - overlap_left
        overlap_h = overlap_bottom - overlap_top
        min_overlap = min(overlap_w, overlap_h)

        # 动态步长：最小2像素，最大不超过重叠区域的1/5
        sample_step = max(2, min(5, int(min_overlap / 5)))

        # 调试输出（临时启用，用于诊断问题）
        DEBUG_OVERLAP = False  # 设为 True 启用调试
        if DEBUG_OVERLAP:
            print(f"[半透明调试] 宠物: {pet.pet_id}, 对象: {getattr(obj, 'furniture_id', 'unknown')}")
            print(f"[半透明调试] 宠物屏幕位置: ({pet_screen_x:.0f}, {pet_screen_y:.0f}), 尺寸: {pet_scaled_w}x{pet_scaled_h}")
            print(f"[半透明调试] 对象屏幕位置: ({obj_screen_x:.0f}, {obj_screen_y:.0f}), 包围盒: {obj_rect}")
            print(f"[半透明调试] 重叠区域: ({overlap_left:.0f}, {overlap_top:.0f}) - ({overlap_right:.0f}, {overlap_bottom:.0f})")
            print(f"[半透明调试] 采样步长: {sample_step}")

        for sy in range(overlap_top, overlap_bottom, sample_step):
            for sx in range(overlap_left, overlap_right, sample_step):
                # 转换为宠物精灵图的本地坐标
                pet_local_x = int((sx - pet_rect.left) * pet_sprite.get_width() / pet_rect.width)
                pet_local_y = int((sy - pet_rect.top) * pet_sprite.get_height() / pet_rect.height)

                # 检查宠物该像素是否非透明
                if 0 <= pet_local_x < pet_sprite.get_width() and 0 <= pet_local_y < pet_sprite.get_height():
                    alpha = pet_sprite.get_at((pet_local_x, pet_local_y)).a
                    if alpha > 128:  # 非透明像素
                        # 检查对象该像素是否非透明（对象需要是可见的）
                        if self._is_obj_pixel_visible(obj, sx, sy, obj_rect, camera):
                            if DEBUG_OVERLAP:
                                print(f"[半透明调试] 找到重叠像素! 屏幕位置: ({sx:.0f}, {sy:.0f})")
                            return True

        if DEBUG_OVERLAP:
            print(f"[半透明调试] 未找到重叠像素")
        return False

    def _is_obj_pixel_visible(self, obj, screen_x, screen_y, obj_rect, camera):
        """检查对象在指定屏幕位置是否有可见像素"""
        # 获取对象的缩放精灵图
        if hasattr(obj, 'get_scaled_image'):
            zoom = camera.zoom
            scaled_img = obj.get_scaled_image(obj.furniture_id, zoom, obj.is_flipped)
            if scaled_img:
                # 转换为对象本地坐标
                local_x = int((screen_x - obj_rect.left) * scaled_img.get_width() / obj_rect.width)
                local_y = int((screen_y - obj_rect.top) * scaled_img.get_height() / obj_rect.height)

                if 0 <= local_x < scaled_img.get_width() and 0 <= local_y < scaled_img.get_height():
                    alpha = scaled_img.get_at((local_x, local_y)).a
                    return alpha > 128

        # 如果没有精灵图，假设可见
        return True

    def _get_object_screen_rect(self, obj, camera):
        """获取对象的屏幕空间包围盒"""
        # 尝试获取 footprint
        if hasattr(obj, 'get_footprint_world'):
            world_fp = obj.get_footprint_world()
            if world_fp:
                screen_points = [camera.world_to_screen(p) for p in world_fp]
                xs = [p[0] for p in screen_points]
                ys = [p[1] for p in screen_points]
                return pygame.Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

        # 如果没有 footprint，使用位置和尺寸（需要应用缩放）
        if hasattr(obj, 'x') and hasattr(obj, 'y') and hasattr(obj, 'width') and hasattr(obj, 'height'):
            screen_x, screen_y = camera.world_to_screen((obj.x, obj.y))
            # 应用缩放因子
            zoom = camera.zoom
            scaled_width = int(obj.width * zoom)
            scaled_height = int(obj.height * zoom)

            # 区分家具和宠物的坐标系统
            # 家具：(x, y) 是精灵图中心，需要减去宽高的一半得到左上角
            # 宠物：(x, y) 是精灵图左上角，直接使用
            if hasattr(obj, 'furniture_id'):
                # 家具：从中心转换为左上角
                return pygame.Rect(
                    int(screen_x - scaled_width // 2),
                    int(screen_y - scaled_height // 2),
                    scaled_width,
                    scaled_height
                )
            else:
                # 宠物或其他：直接使用
                return pygame.Rect(screen_x, screen_y, scaled_width, scaled_height)

        return None

    def render(self, screen, camera):
        """渲染所有宠物（只渲染屏幕内的）"""
        for pet in self.scene_pets:
            if self.is_pet_on_screen(pet, camera):
                pet.render(screen, camera)

    def get_pet_at_position(self, world_pos, camera):
        """获取指定位置的宠物（像素级检测）"""
        if not self.scene_pets:
            return None

        for pet in self.scene_pets:
            if pet.is_clicked_at(world_pos, camera):
                return pet
        return None

    # ==================== 食物喜好系统 ====================

    # 食物喜好表：{crop_id: {pet_id: "普通"|"喜欢"|"最爱"}}
    FOOD_PREFERENCE = {
        "tomato": {
            "golden_retriever": "喜欢",
            "blue_cat": "普通",
            "rabbit": "普通",
            "hamster": "普通",
            "chick": "普通",
            "penguin": "普通"
        },
        "carrot": {
            "golden_retriever": "普通",
            "blue_cat": "普通",
            "rabbit": "最爱",
            "hamster": "喜欢",
            "chick": "普通",
            "penguin": "普通"
        },
        "pumpkin": {
            "golden_retriever": "喜欢",
            "blue_cat": "普通",
            "rabbit": "喜欢",
            "hamster": "最爱",
            "chick": "普通",
            "penguin": "普通"
        },
        "sunflower": {
            "golden_retriever": "普通",
            "blue_cat": "普通",
            "rabbit": "普通",
            "hamster": "普通",
            "chick": "喜欢",
            "penguin": "普通"
        },
        "strawberry": {
            "golden_retriever": "喜欢",
            "blue_cat": "喜欢",
            "rabbit": "喜欢",
            "hamster": "喜欢",
            "chick": "喜欢",
            "penguin": "喜欢"
        }
    }

    # 不可喂食的作物
    INEDIBLE_CROPS = ["rose"]

    # 喜爱程度对应的效果
    PREFERENCE_EFFECTS = {
        "普通": {"satiety": 20, "happiness": 1},
        "喜欢": {"satiety": 30, "happiness": 2},
        "最爱": {"satiety": 40, "happiness": 5}
    }

    def get_food_preference(self, crop_id, pet_id):
        """获取食物对宠物的喜好程度"""
        if crop_id in self.FOOD_PREFERENCE:
            # pet_id 可能是实例ID（如 golden_retriever_1）或类型ID（如 golden_retriever）
            # 需要获取宠物类型
            pet_type = self._get_pet_type(pet_id)
            return self.FOOD_PREFERENCE[crop_id].get(pet_type, "普通")
        return "普通"

    def get_feed_effects(self, crop_id, pet_id):
        """获取喂食效果"""
        preference = self.get_food_preference(crop_id, pet_id)
        return self.PREFERENCE_EFFECTS.get(preference, self.PREFERENCE_EFFECTS["普通"])

    def can_feed_crop(self, crop_id):
        """检查作物是否可以喂食"""
        return crop_id not in self.INEDIBLE_CROPS

    def get_feedable_crops_from_inventory(self, inventory):
        """从背包中获取可喂食的作物列表"""
        feedable_crops = []
        # inventory 是字典，harvests 存储收获的作物
        harvests = inventory.get("harvests", {})
        for item_id, quantity in harvests.items():
            if quantity > 0 and self.can_feed_crop(item_id):
                feedable_crops.append({"id": item_id, "quantity": quantity})
        return feedable_crops

    def show_feed_crop_selector(self, pet_id):
        """显示喂食作物选择器"""
        # 这个方法会被 UI 调用，显示作物选择界面
        # 实际的 UI 渲染由 UI 类处理
        self._feeding_pet_id = pet_id
        print(f"显示喂食选择器，目标宠物: {pet_id}")

    def feed_pet_with_crop(self, pet_id, crop_id, inventory):
        """用指定作物喂食宠物"""
        # 查找宠物
        pet = None
        for p in self.scene_pets:
            if p.pet_id == pet_id:
                pet = p
                break

        if not pet:
            return False, "宠物不在场景中"

        # 检查饱腹度
        if pet.satiety >= 100:
            return False, "宠物已经吃饱了"

        # 检查作物是否可喂食
        if not self.can_feed_crop(crop_id):
            return False, "该作物不可喂食"

        # 检查背包中是否有该作物
        harvests = inventory.get("harvests", {})
        if harvests.get(crop_id, 0) <= 0:
            return False, "背包中没有该作物"

        # 获取喂食效果
        effects = self.get_feed_effects(crop_id, pet_id)

        # 应用效果
        result, reward_gold = pet.feed(effects["satiety"], effects["happiness"])

        if result:
            # 消耗作物
            harvests[crop_id] = harvests.get(crop_id, 0) - 1
            if harvests[crop_id] <= 0:
                del harvests[crop_id]

            # 获取喜好程度
            preference = self.get_food_preference(crop_id, pet_id)

            # 如果是最爱，播放爱心粒子
            if preference == "最爱":
                pet.spawn_love_particles()

            msg = f"喂食成功！饱腹度+{effects['satiety']}，好感度+{effects['happiness']}"
            if reward_gold > 0:
                msg += f"，升级奖励+{reward_gold}金币"
            return True, msg
        else:
            return False, "喂食失败"
