"""
碰撞系统 - 管理物体的放置检测和渲染排序
支持类型：ground(地面), surface(可放置面), wall_surface(墙面), wall_mount(墙挂)
"""
import json
import os
from ..entities.furniture import Furniture


class CollisionSystem:
    """碰撞检测系统"""

    OVERLAP_THRESHOLD = 0.15  # 允许最大重叠比例 15%

    def __init__(self):
        self.footprints = {}      # {obj_id: [[x,y], ...]} 地面碰撞区域
        self.wall_surfaces = {}   # {obj_id: [[x,y], ...]} 墙面可挂区域
        self.placeable_areas = {} # {obj_id: [{"name":str, "points":[[x,y]...]}]} 可放置平面

        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        self.load()

    def load(self):
        """加载所有数据"""
        self.footprints = self._load_json("footprints")
        self.wall_surfaces = self._load_json("wall_surfaces")
        self.placeable_areas = self._load_json("placeable_areas")

    def _load_json(self, name):
        """加载JSON文件"""
        path = os.path.join(self.data_dir, f"{name}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载 {name} 失败: {e}")
        return {}

    def get_footprint(self, obj_id):
        """获取物体的地面碰撞区域"""
        return self.footprints.get(obj_id, [])

    def get_wall_surface(self, obj_id):
        """获取物体的墙面区域"""
        return self.wall_surfaces.get(obj_id, [])

    def get_placeable_areas(self, obj_id):
        """获取物体的可放置平面"""
        return self.placeable_areas.get(obj_id, [])

    def get_world_footprint(self, obj):
        """
        获取物体在世界坐标下的footprint（地面碰撞区域）

        【坐标说明】
        - footprints.json 中的坐标是相对于精灵图左上角的原始像素坐标
        - 在 tools/furniture_editor.py 中编辑保存
        - 转换逻辑同 get_world_placeable_area：
          1. obj.x, obj.y 是精灵图中心，减去 img_w * scale / 2 得到左上角
          2. 原始像素坐标 * scale + 左上角偏移 = 世界坐标
        - footprint 用于地面碰撞检测（两个地面物体重叠检测）
        - 如果 is_flipped=True，需要对坐标进行水平翻转
        """
        # 使用总缩放倍率（基础缩放 × 额外缩放），渲染和碰撞统一
        furniture_id = getattr(obj, 'furniture_id', None)
        scale = Furniture.get_total_scale(furniture_id) if furniture_id else Furniture.SCALE
        extra_scale = Furniture.get_extra_scale(furniture_id) if furniture_id else 1.0
        is_flipped = getattr(obj, 'is_flipped', False)
        local_points = self.get_footprint(obj.furniture_id)
        if not local_points:
            # 默认矩形（obj.x, obj.y 是精灵图中心）
            img = Furniture._images.get(obj.furniture_id)
            if img:
                img_w, img_h = img.get_size()
                # img_w 是原始尺寸，渲染尺寸 = img_w * total_scale
                rendered_w = img_w * scale
                rendered_h = img_h * scale
                offset_x = obj.x - rendered_w / 2
                offset_y = obj.y - rendered_h / 2
            else:
                offset_x = obj.x
                offset_y = obj.y
            return [
                (offset_x, offset_y),
                (offset_x + obj.width, offset_y),
                (offset_x + obj.width, offset_y + obj.height),
                (offset_x, offset_y + obj.height)
            ]
        # obj.x, obj.y 是精灵图中心，需要减去偏移
        img = Furniture._images.get(obj.furniture_id)
        if img:
            img_w, img_h = img.get_size()
            # img_w 是原始尺寸，渲染尺寸 = img_w * total_scale
            rendered_w = img_w * scale
            rendered_h = img_h * scale
            offset_x = obj.x - rendered_w / 2
            offset_y = obj.y - rendered_h / 2
            # 如果翻转，需要对原始像素坐标进行水平翻转
            if is_flipped:
                return [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in local_points]
        else:
            offset_x = obj.x
            offset_y = obj.y
        return [(offset_x + px * scale, offset_y + py * scale) for px, py in local_points]

    def get_world_wall_surface(self, obj):
        """
        获取墙面物体在世界坐标下的墙面区域

        【坐标说明】
        - wall_surfaces.json 中的坐标是相对于精灵图左上角的原始像素坐标
        - 在 tools/furniture_editor.py 中编辑保存
        - 转换逻辑同 get_world_placeable_area：
          1. obj.x, obj.y 是精灵图中心，减去 img_w/2 得到左上角
          2. 原始像素坐标 * SCALE * EXTRA_SCALE + 左上角偏移 = 世界坐标
        - wall_surface 用于墙挂检测（装饰画等挂在墙面上）
        - 如果 is_flipped=True，需要对坐标进行水平翻转
        """
        # 使用总缩放倍率（基础缩放 × 额外缩放），渲染和碰撞统一
        furniture_id = getattr(obj, 'furniture_id', None)
        scale = Furniture.get_total_scale(furniture_id) if furniture_id else Furniture.SCALE
        extra_scale = Furniture.get_extra_scale(furniture_id) if furniture_id else 1.0
        is_flipped = getattr(obj, 'is_flipped', False)
        local_points = self.get_wall_surface(obj.furniture_id)
        if not local_points:
            return []
        # obj.x, obj.y 是精灵图中心，需要减去偏移
        img = Furniture._images.get(obj.furniture_id)
        if img:
            img_w, img_h = img.get_size()
            # offset 需要乘 total_scale，与渲染保持一致
            rendered_w = img_w * scale
            rendered_h = img_h * scale
            offset_x = obj.x - rendered_w / 2
            offset_y = obj.y - rendered_h / 2
            # 如果翻转，需要对原始像素坐标进行水平翻转
            if is_flipped:
                return [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in local_points]
        else:
            offset_x = obj.x
            offset_y = obj.y
        return [(offset_x + px * scale, offset_y + py * scale) for px, py in local_points]

    def get_world_placeable_area(self, obj, area_name=None):
        """
        获取可放置平面在世界坐标下的区域（自动应用缩放比例）

        【重要坐标说明 - 不要再问了】
        placeable_areas.json 中的坐标来源：
        - 在 tools/furniture_editor.py 中编辑保存
        - 坐标是相对于精灵图左上角的原始像素坐标（编辑器中点击位置）

        坐标转换流程（三步）：
        1. obj.x, obj.y 是精灵图中心（游戏坐标），不是左上角
        2. 减去 img_w/2 * EXTRA_SCALE 得到精灵图左上角的游戏坐标：offset_x, offset_y
           （img_w 已经是缩放后的尺寸 = 原始 * SCALE，需要再乘 EXTRA_SCALE）
        3. 原始像素坐标 * SCALE * EXTRA_SCALE + offset = 世界坐标
           world_x = offset_x + px * SCALE * EXTRA_SCALE

        举例：假设桌子原始精灵图 720px，SCALE=0.05, EXTRA_SCALE=1.5
        - 缩放后精灵图: img_w = 720 * 0.05 = 36
        - 桌子中心 obj.x = 100（游戏坐标）
        - 精灵图左上角 offset_x = 100 - 36*1.5/2 = 73
        - placeable_area 点 px = 30（原始像素）
        - 世界坐标 = 73 + 30 * 0.05 * 1.5 = 75.25
        """
        # 使用总缩放倍率（基础缩放 × 额外缩放），渲染和碰撞统一
        furniture_id = getattr(obj, 'furniture_id', None)
        scale = Furniture.get_total_scale(furniture_id) if furniture_id else Furniture.SCALE
        extra_scale = Furniture.get_extra_scale(furniture_id) if furniture_id else 1.0

        areas = self.get_placeable_areas(obj.furniture_id)
        if not areas:
            return []

        # 【关键】obj.x, obj.y 是精灵图中心，需要减去 rendered_w/2 得到左上角
        # rendered_w = img_w * total_scale（与渲染保持一致）
        img = Furniture._images.get(obj.furniture_id)
        if img:
            img_w, img_h = img.get_size()  # 原始精灵图尺寸
            rendered_w = img_w * scale  # 渲染时的实际宽度
            rendered_h = img_h * scale
            offset_x = obj.x - rendered_w / 2  # 精灵图左上角的游戏坐标
            offset_y = obj.y - rendered_h / 2
        else:
            offset_x = obj.x
            offset_y = obj.y

        # 获取翻转状态
        is_flipped = getattr(obj, 'is_flipped', False)

        result = []
        for area in areas:
            if area_name and area.get("name") != area_name:
                continue
            points = area.get("points", [])
            # 转换：原始像素坐标 * scale + 精灵图左上角偏移 = 世界坐标
            if is_flipped:
                # 翻转时对 x 坐标进行水平镜像
                world_points = [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in points]
            else:
                world_points = [(offset_x + px * scale, offset_y + py * scale) for px, py in points]
            result.append({
                "name": area.get("name", ""),
                "points": world_points
            })

        return result

    def check_overlap(self, obj, new_x, new_y, other_objects):
        """检测物体在新位置是否与其他物体重叠（根据类型选择检测方式）
        返回 True 表示有重叠（不能放置），False 表示无重叠（可以放置）
        """
        obj_type = getattr(obj, 'obj_type', 'ground')
        if obj_type == "wall_mount":
            # _check_wall_mount_placement 返回 True 表示可以放置，需要取反
            return not self._check_wall_mount_placement(obj, new_x, new_y, other_objects)
        return self._check_ground_placement(obj, new_x, new_y, other_objects)

    def check_ground_placement(self, obj, new_x, new_y, other_objects):
        """公开接口：检测地面放置是否合法"""
        return self._check_ground_placement(obj, new_x, new_y, other_objects)

    def check_placement(self, obj, new_x, new_y, obj_type, other_objects):
        """
        检查物体放置是否合法
        obj_type: "ground", "surface", "wall_mount"
        """
        if obj_type == "ground":
            return self._check_ground_placement(obj, new_x, new_y, other_objects)
        elif obj_type == "wall_mount":
            return self._check_wall_mount_placement(obj, new_x, new_y, other_objects)
        elif obj_type == "surface":
            # surface类型物体（如桌子）放在地面上，检查地面碰撞
            return self._check_ground_placement(obj, new_x, new_y, other_objects)
        return False

    def _check_ground_placement(self, obj, new_x, new_y, other_objects):
        """检查地面放置（footprint碰撞）"""
        # 使用总缩放倍率（基础缩放 × 额外缩放），渲染和碰撞统一
        furniture_id = getattr(obj, 'furniture_id', None)
        scale = Furniture.get_total_scale(furniture_id) if furniture_id else Furniture.SCALE
        extra_scale = Furniture.get_extra_scale(furniture_id) if furniture_id else 1.0
        is_flipped = getattr(obj, 'is_flipped', False)

        # 计算新位置的footprint（new_x, new_y 是精灵图中心）
        local_points = self.get_footprint(obj.furniture_id)
        # 计算偏移（精灵图中心 → 左上角，需要乘 total_scale 与渲染保持一致）
        img = Furniture._images.get(obj.furniture_id)
        if img:
            img_w, img_h = img.get_size()
            rendered_w = img_w * scale
            rendered_h = img_h * scale
            offset_x = new_x - rendered_w / 2
            offset_y = new_y - rendered_h / 2
        else:
            offset_x = new_x
            offset_y = new_y

        if not local_points:
            new_fp = [
                (offset_x, offset_y),
                (offset_x + obj.width, offset_y),
                (offset_x + obj.width, offset_y + obj.height),
                (offset_x, offset_y + obj.height)
            ]
        else:
            # 如果翻转，需要对原始像素坐标进行水平翻转
            if is_flipped:
                new_fp = [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in local_points]
            else:
                new_fp = [(offset_x + px * scale, offset_y + py * scale) for px, py in local_points]

        new_area = self._polygon_area(new_fp)
        if new_area <= 0:
            return False

        for other in other_objects:
            if other is obj:
                continue

            # 跳过没有furniture_id的对象（如Crop、Pet）
            if not hasattr(other, 'furniture_id'):
                continue

            # 跳过 no_collision 的物体（如地毯）
            other_no_collision = getattr(other, 'no_collision', False)
            if not other_no_collision:
                other_no_collision = Furniture.FURNITURE_DATA.get(other.furniture_id, {}).get('no_collision', False)
            if other_no_collision:
                continue

            # 只与地面类物体检测碰撞
            other_type = getattr(other, 'obj_type', 'ground')
            if other_type == "wall_mount":
                continue  # 墙挂不影响地面碰撞

            # 快速距离预筛选：距离太远直接跳过，避免昂贵的 footprint 计算
            if abs(other.x - new_x) > 300 and abs(other.y - new_y) > 300:
                continue

            other_fp = self.get_world_footprint(other)
            if not other_fp:
                other_fp = [
                    (other.x, other.y),
                    (other.x + other.width, other.y),
                    (other.x + other.width, other.y + other.height),
                    (other.x, other.y + other.height)
                ]

            other_area = self._polygon_area(other_fp)
            if other_area <= 0:
                continue

            # 计算交集面积
            intersection = self._polygon_intersection_area(new_fp, other_fp)
            if intersection > 0:
                # 关键修复：使用新物体面积作为分母，确保小物体无法"钻空子"
                # 这样即使落地灯很小，只要与桌子有交集就会被检测到
                overlap_ratio = intersection / new_area
                if overlap_ratio > self.OVERLAP_THRESHOLD:
                    return True

        return False

    def _check_wall_mount_placement(self, obj, new_x, new_y, other_objects):
        """
        检查墙挂放置（必须在wall_surface上）

        逻辑：
        1. 墙挂物品（如 painting）使用 wall_surfaces 数据做碰撞检测
        2. 必须依附在拥有 wall_surfaces 的物体（如 wardrobe、bookshelf）
        3. 墙挂的 wall_surfaces 区域必须有 80% 被包含在依附体的 wall_surfaces 区域内
        4. 不能与其他墙挂重叠
        """
        # 使用总缩放倍率（基础缩放 × 额外缩放），渲染和碰撞统一
        furniture_id = getattr(obj, 'furniture_id', None)
        scale = Furniture.get_total_scale(furniture_id) if furniture_id else Furniture.SCALE
        extra_scale = Furniture.get_extra_scale(furniture_id) if furniture_id else 1.0
        is_flipped = getattr(obj, 'is_flipped', False)

        # 计算偏移（精灵图中心 → 左上角，需要乘 total_scale 与渲染保持一致）
        img = Furniture._images.get(obj.furniture_id)
        if img:
            img_w, img_h = img.get_size()
            rendered_w = img_w * scale
            rendered_h = img_h * scale
            offset_x = new_x - rendered_w / 2
            offset_y = new_y - rendered_h / 2
        else:
            offset_x = new_x
            offset_y = new_y

        # 获取墙挂物体的 wall_surfaces 数据（不是 footprint）
        mount_ws = self.get_wall_surface(obj.furniture_id)
        if not mount_ws or len(mount_ws) < 3:
            # 墙挂物品必须有 wall_surfaces 数据
            return False

        # 转换为世界坐标
        if is_flipped:
            # 翻转时对 x 坐标进行水平镜像
            mount_ws_world = [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in mount_ws]
        else:
            mount_ws_world = [(offset_x + px * scale, offset_y + py * scale) for px, py in mount_ws]
        mount_ws_area = self._polygon_area(mount_ws_world)

        # 检查是否在任何 wall_surface 上（依附体）
        for other in other_objects:
            if other is obj:
                continue

            other_type = getattr(other, 'obj_type', 'ground')
            # surface_wall 类型（如 wardrobe、bookshelf）有 wall_surfaces 数据，可作为依附体
            if other_type not in ("wall_surface", "surface_wall"):
                continue

            # 获取依附体的 wall_surfaces 区域
            wall_area = self.get_world_wall_surface(other)
            if not wall_area or len(wall_area) < 3:
                continue

            # 计算墙挂的 wall_surfaces 与依附体的 wall_surfaces 重叠面积
            intersection = self._polygon_intersection_area(mount_ws_world, wall_area)
            if mount_ws_area > 0:
                overlap_ratio = intersection / mount_ws_area

                # 墙挂需要至少 40% 在依附体的 wall_surfaces 区域内
                if overlap_ratio >= 0.4:
                    # 检查是否与其他墙挂重叠
                    if not self._check_wall_mount_collision(obj, mount_ws_world, other_objects):
                        return True

        return False

    def _check_wall_mount_collision(self, obj, mount_ws_world, other_objects):
        """
        检查墙挂是否与其他墙挂重叠

        参数：
        - obj: 当前墙挂物体
        - mount_ws_world: 当前墙挂的世界坐标 wall_surfaces
        - other_objects: 所有物体列表

        返回：
        - True: 有重叠（不能放置）
        - False: 无重叠（可以放置）
        """
        for other in other_objects:
            if other is obj:
                continue

            other_type = getattr(other, 'obj_type', 'ground')
            if other_type != "wall_mount":
                continue

            # 获取其他墙挂的 wall_surfaces 数据
            other_ws = self.get_wall_surface(other.furniture_id)
            if not other_ws or len(other_ws) < 3:
                continue

            # 转换为世界坐标
            other_ws_world = self.get_world_wall_surface(other)
            if not other_ws_world or len(other_ws_world) < 3:
                continue

            # 检查是否重叠
            intersection = self._polygon_intersection_area(mount_ws_world, other_ws_world)
            if intersection > 0:
                return True  # 有重叠

        return False  # 无重叠

    def check_item_on_surface(self, item, surface_obj, area_name=None):
        """
        检查物品是否可以放在可放置平面上
        item: 要放置的物品
        surface_obj: 可放置平面物体（如桌子）
        area_name: 指定的放置区域名称
        """
        # 获取放置区域
        areas = self.get_world_placeable_area(surface_obj, area_name)
        if not areas:
            return False

        # 获取物品的footprint（item.x, item.y 是精灵图中心）
        # 使用总缩放倍率（基础缩放 × 额外缩放），渲染和碰撞统一
        item_furniture_id = getattr(item, 'furniture_id', None)
        scale = Furniture.get_total_scale(item_furniture_id) if item_furniture_id else Furniture.SCALE
        is_flipped = getattr(item, 'is_flipped', False)
        img = Furniture._images.get(item.furniture_id)
        if img:
            img_w, img_h = img.get_size()
            rendered_w = img_w * scale
            rendered_h = img_h * scale
            offset_x = item.x - rendered_w / 2
            offset_y = item.y - rendered_h / 2
        else:
            offset_x = item.x
            offset_y = item.y

        item_local = self.get_footprint(item.furniture_id)
        if not item_local:
            item_fp = [
                (offset_x, offset_y),
                (offset_x + item.width, offset_y),
                (offset_x + item.width, offset_y + item.height),
                (offset_x, offset_y + item.height)
            ]
        else:
            # 如果翻转，需要对原始像素坐标进行水平翻转
            if is_flipped:
                item_fp = [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in item_local]
            else:
                item_fp = [(offset_x + px * scale, offset_y + py * scale) for px, py in item_local]

        item_center = self._polygon_center(item_fp)

        for area in areas:
            area_points = area["points"]
            if len(area_points) < 3:
                continue

            # 检查物品中心是否在放置区域内
            if self._point_in_polygon(item_center, area_points):
                # 检查物品footprint是否完全在放置区域内
                area_size = self._polygon_area(area_points)
                item_size = self._polygon_area(item_fp)

                if area_size > 0 and item_size > 0:
                    intersection = self._polygon_intersection_area(item_fp, area_points)
                    overlap_ratio = intersection / item_size

                    # 物品需要至少90%在放置区域内
                    if overlap_ratio >= 0.9:
                        return True

        return False

    def check_item_collision_on_surface(self, item, surface_obj, area_name, other_items):
        """
        检查物品在放置平面上是否与其他物品重叠
        item: 要放置的物品
        surface_obj: 可放置平面物体
        area_name: 放置区域名称
        other_items: 该区域上已有的其他物品列表
        """
        # 获取物品的footprint（item.x, item.y 是精灵图中心）
        # 使用总缩放倍率（基础缩放 × 额外缩放），渲染和碰撞统一
        item_furniture_id = getattr(item, 'furniture_id', None)
        scale = Furniture.get_total_scale(item_furniture_id) if item_furniture_id else Furniture.SCALE
        is_flipped = getattr(item, 'is_flipped', False)
        img = Furniture._images.get(item.furniture_id)
        if img:
            img_w, img_h = img.get_size()
            rendered_w = img_w * scale
            rendered_h = img_h * scale
            offset_x = item.x - rendered_w / 2
            offset_y = item.y - rendered_h / 2
        else:
            offset_x = item.x
            offset_y = item.y

        item_local = self.get_footprint(item.furniture_id)
        if not item_local:
            item_fp = [
                (offset_x, offset_y),
                (offset_x + item.width, offset_y),
                (offset_x + item.width, offset_y + item.height),
                (offset_x, offset_y + item.height)
            ]
        else:
            # 如果翻转，需要对原始像素坐标进行水平翻转
            if is_flipped:
                item_fp = [(offset_x + (img_w - px) * scale, offset_y + py * scale) for px, py in item_local]
            else:
                item_fp = [(offset_x + px * scale, offset_y + py * scale) for px, py in item_local]

        item_area = self._polygon_area(item_fp)
        if item_area <= 0:
            return False

        for other in other_items:
            if other is item or other is surface_obj:
                # 跳过自身和宿主物体（宿主物体的footprint重叠是允许的）
                continue

            # other.x, other.y 是精灵图中心
            other_furniture_id = getattr(other, 'furniture_id', None)
            other_scale = Furniture.get_total_scale(other_furniture_id) if other_furniture_id else Furniture.SCALE
            other_img = Furniture._images.get(other.furniture_id)
            if other_img:
                other_img_w, other_img_h = other_img.get_size()
                other_rendered_w = other_img_w * other_scale
                other_rendered_h = other_img_h * other_scale
                other_offset_x = other.x - other_rendered_w / 2
                other_offset_y = other.y - other_rendered_h / 2
            else:
                other_offset_x = other.x
                other_offset_y = other.y

            other_local = self.get_footprint(other.furniture_id)
            if not other_local:
                other_fp = [
                    (other_offset_x, other_offset_y),
                    (other_offset_x + other.width, other_offset_y),
                    (other_offset_x + other.width, other_offset_y + other.height),
                    (other_offset_x, other_offset_y + other.height)
                ]
            else:
                other_fp = [(other_offset_x + px * scale, other_offset_y + py * scale) for px, py in other_local]

            other_area = self._polygon_area(other_fp)
            if other_area <= 0:
                continue

            intersection = self._polygon_intersection_area(item_fp, other_fp)
            if intersection > 0:
                # 关键修复：使用要放置物品的面积作为分母
                # 确保小物体无法"钻空子"
                overlap_ratio = intersection / item_area
                if overlap_ratio > self.OVERLAP_THRESHOLD:
                    return True

        return False

    def _polygon_area(self, polygon):
        """计算多边形面积（Shoelace公式）"""
        n = len(polygon)
        if n < 3:
            return 0
        area = 0
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        return abs(area) / 2

    def _polygon_center(self, polygon):
        """计算多边形中心点"""
        if not polygon:
            return (0, 0)
        n = len(polygon)
        cx = sum(p[0] for p in polygon) / n
        cy = sum(p[1] for p in polygon) / n
        return (cx, cy)

    def _polygon_intersection_area(self, poly1, poly2):
        """计算两个凸多边形的交集面积（采样近似）"""
        bbox1 = self._get_bbox(poly1)
        bbox2 = self._get_bbox(poly2)

        # AABB不相交则无交集
        if (bbox1[0] > bbox2[2] or bbox2[0] > bbox1[2] or
            bbox1[1] > bbox2[3] or bbox2[1] > bbox1[3]):
            return 0

        # 在交集AABB内采样
        x_min = max(bbox1[0], bbox2[0])
        x_max = min(bbox1[2], bbox2[2])
        y_min = max(bbox1[1], bbox2[1])
        y_max = min(bbox1[3], bbox2[3])

        if x_max <= x_min or y_max <= y_min:
            return 0

        # 采样步长
        step = max(1, min((x_max - x_min), (y_max - y_min)) / 10)
        inside_count = 0
        total_count = 0

        x = x_min
        while x <= x_max:
            y = y_min
            while y <= y_max:
                total_count += 1
                if self._point_in_polygon((x, y), poly1) and self._point_in_polygon((x, y), poly2):
                    inside_count += 1
                y += step
            x += step

        if total_count == 0:
            return 0

        # 估算交集面积
        bbox_area = (x_max - x_min) * (y_max - y_min)
        return bbox_area * (inside_count / total_count)

    def _get_bbox(self, polygon):
        """获取多边形AABB (min_x, min_y, max_x, max_y)"""
        if not polygon:
            return (0, 0, 0, 0)
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        return (min(xs), min(ys), max(xs), max(ys))

    def _point_in_polygon(self, point, polygon):
        """射线法判断点是否在多边形内"""
        if len(polygon) < 3:
            return False
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

    def get_footprint_bottom_y(self, obj):
        """获取footprint底部Y坐标（用于渲染排序）"""
        world_fp = self.get_world_footprint(obj)
        if world_fp:
            return max(py for _, py in world_fp)
        return obj.y + obj.height

    def point_in_wall_surface(self, obj, point):
        """检测点是否在物体的wall_surfaces区域内"""
        wall_area = self.get_world_wall_surface(obj)
        if not wall_area or len(wall_area) < 3:
            return False
        return self._point_in_polygon(point, wall_area)

    def point_in_placeable_area(self, obj, point):
        """检测点是否在物体的placeable_areas区域内"""
        areas = self.get_world_placeable_area(obj)
        for area in areas:
            if self._point_in_polygon(point, area["points"]):
                return True
        return False

    def check_wall_mount_placement(self, obj, new_x, new_y, other_objects):
        """公开接口：检测墙挂放置是否合法（在墙面上且不与其他墙挂重叠）"""
        return self._check_wall_mount_placement(obj, new_x, new_y, other_objects)

    def get_surface_under_point(self, point, all_objects, item_obj=None):
        """
        获取指定位置下方的 surface/surface_wall 类型家具

        参数：
        - point: 要检测的点（通常是物体中心）
        - all_objects: 所有物体列表
        - item_obj: 可选，要检测的物体（用于 footprint 重叠检测）

        检测逻辑：
        1. 如果提供了 item_obj，检测其 footprint 是否与 placeable_area 重叠
        2. 否则，只检测 point 是否在 placeable_area 内
        """
        for obj in all_objects:
            obj_type = getattr(obj, 'obj_type', 'ground')
            if obj_type in ('surface', 'surface_wall'):
                # 如果提供了物体，检测 footprint 与 placeable_area 的重叠
                if item_obj:
                    if self._check_footprint_overlap_placeable_area(item_obj, obj):
                        return obj
                else:
                    # 只检测点是否在区域内
                    if self.point_in_placeable_area(obj, point):
                        return obj
        return None

    def _check_footprint_overlap_placeable_area(self, item, surface):
        """
        检测物体的 footprint 是否与 surface 的 placeable_area 重叠

        用于：检测台灯等物体是否"放在"桌子上（不需要中心点在区域内，只要 footprint 有重叠）
        """
        # 获取 surface 的 placeable_area
        areas = self.get_world_placeable_area(surface)
        if not areas:
            return False

        # 获取 item 的 footprint
        item_fp = self.get_world_footprint(item)
        if not item_fp:
            return False

        # 检测 item footprint 的中心是否在任意 placeable_area 内
        item_center = self._polygon_center(item_fp)
        for area in areas:
            area_points = area["points"]
            if len(area_points) < 3:
                continue
            if self._point_in_polygon(item_center, area_points):
                return True

        # 或者检测 item footprint 与 placeable_area 是否有足够重叠
        for area in areas:
            area_points = area["points"]
            if len(area_points) < 3:
                continue

            area_size = self._polygon_area(area_points)
            item_size = self._polygon_area(item_fp)

            if area_size > 0 and item_size > 0:
                intersection = self._polygon_intersection_area(item_fp, area_points)
                overlap_ratio = intersection / item_size

                # 物品需要至少 30% 在放置区域内（放宽条件，允许部分重叠）
                if overlap_ratio >= 0.3:
                    return True

        return False

    def check_surface_items_collision(self, item, surface_obj, area_name, all_objects):
        """检测物品在表面上是否与其他物品重叠（排除宿主本身）"""
        other_items = []
        for obj in all_objects:
            if obj is item or obj is surface_obj:
                continue
            # 检查其他物品是否在同一表面上
            obj_type = getattr(obj, 'obj_type', 'ground')
            if obj_type in ('ground', 'wall_mount', 'wall_surface'):
                continue
            item_center = (obj.x + obj.width / 2, obj.y + obj.height / 2)
            if self.point_in_placeable_area(surface_obj, item_center):
                other_items.append(obj)
        return self.check_item_collision_on_surface(item, surface_obj, area_name, other_items)

    def can_place(self, obj, new_x, new_y, all_objects, surface_obj=None, area_name=None, items_on_surface=None):
        """
        统一放置检测入口
        obj: 要放置的物体
        new_x, new_y: 新位置
        all_objects: 所有物体列表（用于地面碰撞检测）
        surface_obj: 宿主物体（如果放在表面上）
        area_name: 放置区域名称
        items_on_surface: 该区域上已有的物品列表
        """
        obj_type = getattr(obj, 'obj_type', 'ground')

        if obj_type == "wall_surface":
            # 墙面不可由玩家放置
            return False

        if obj_type == "wall_mount":
            # 挂饰类：检测是否在墙面上
            return self.check_wall_mount_placement(obj, new_x, new_y, all_objects)

        if obj_type == "surface_wall":
            # 可放置+可挂类：如果指定了墙面，检测挂墙；否则检测地面放置
            if surface_obj is not None:
                # 放在表面上
                test_obj = type(obj)(obj.furniture_id, new_x, new_y)
                if not self.check_item_on_surface(test_obj, surface_obj, area_name):
                    return False
                if items_on_surface:
                    if self.check_item_collision_on_surface(test_obj, surface_obj, area_name, items_on_surface):
                        return False
                return True
            else:
                # 地面放置
                return not self.check_ground_placement(obj, new_x, new_y, all_objects)

        if surface_obj is not None:
            # 放置在某个表面上（如桌子、床）
            # 1. 检测物品是否在 placeable_area 内
            test_obj = type(obj)(obj.furniture_id, new_x, new_y)
            if not self.check_item_on_surface(test_obj, surface_obj, area_name):
                return False
            # 2. 检测与其他物品的重叠（排除宿主物体）
            if items_on_surface:
                if self.check_item_collision_on_surface(test_obj, surface_obj, area_name, items_on_surface):
                    return False
            return True

        # 地面放置：检测 footprint 重叠
        return not self.check_ground_placement(obj, new_x, new_y, all_objects)
