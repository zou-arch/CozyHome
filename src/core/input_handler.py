"""
输入处理器 - 处理长按拖拽和点按交互
"""
import pygame
import time
import math

class InputHandler:
    """输入处理器类"""

    # 长按阈值（秒）
    LONG_PRESS_THRESHOLD = 0.05
    # 拖拽最小移动距离（像素），防止误触
    DRAG_DISTANCE_THRESHOLD = 8

    def __init__(self, camera, world, ui, game_manager):
        self.camera = camera
        self.world = world
        self.ui = ui
        self.game_manager = game_manager

        # 鼠标状态
        self.mouse_pos = (0, 0)
        self.mouse_down = False
        self.mouse_down_time = 0.0
        self.is_long_press = False
        self.is_dragging = False
        self.click_handled = False

        # 选中的物体
        self.selected_object = None

        # 拖拽状态：记录最后一个合法位置（用于不合法时停在原位）
        self._last_valid_pos = None

        # 编辑模式
        self.is_edit_mode = False
        self.edit_tool = "select"  # 编辑工具: select/move/remove/place/flip

    def handle_event(self, event: pygame.event.Event):
        """处理事件"""
        # 新手引导优先处理
        if hasattr(self.ui, 'tutorial') and self.ui.tutorial.active:
            if self.ui.tutorial.handle_event(event):
                return

        if event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.handle_mouse_up(event)
        elif event.type == pygame.MOUSEWHEEL:
            self.handle_mouse_wheel(event)
        elif event.type == pygame.KEYDOWN:
            self.handle_key_down(event)
        # 触摸事件支持（移动端）
        elif event.type == pygame.FINGERDOWN:
            # 将触摸转换为鼠标按下
            fake_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                button=1, pos=(event.x * self.camera.screen_width, event.y * self.camera.screen_height))
            self.handle_mouse_down(fake_event)
        elif event.type == pygame.FINGERMOTION:
            # 将触摸移动转换为鼠标移动
            fake_event = pygame.event.Event(pygame.MOUSEMOTION,
                pos=(event.x * self.camera.screen_width, event.y * self.camera.screen_height))
            self.handle_mouse_motion(fake_event)
        elif event.type == pygame.FINGERUP:
            # 将触摸释放转换为鼠标释放
            fake_event = pygame.event.Event(pygame.MOUSEBUTTONUP,
                button=1, pos=(event.x * self.camera.screen_width, event.y * self.camera.screen_height))
            self.handle_mouse_up(fake_event)

    def handle_mouse_motion(self, event: pygame.event.Event):
        """处理鼠标移动"""
        self.mouse_pos = event.pos

        # 如果有菜单打开，传递给UI处理（用于滑动条拖动）
        if self.ui.current_menu:
            if self.ui.current_menu == "inventory":
                self.ui.handle_inventory_drag(event.pos)
            elif self.ui.current_menu == "settings":
                # 传递给设置面板处理滑块拖拽
                self.ui.settings_panel.handle_event(event)
                # 同步音量
                from ..core.audio_manager import audio_manager
                audio_manager.set_bgm_volume(self.ui.settings_panel.bgm_volume)
                audio_manager.set_sfx_volume(self.ui.settings_panel.sfx_volume)
            return

        # 放置模式：更新预览位置
        if hasattr(self.ui, '_placing_furniture') and self.ui._placing_furniture:
            self.ui._placing_pos = self.camera.screen_to_world(event.pos)
            return

        # 如果正在拖拽，更新摄像头或物体位置
        if self.is_dragging:
            if self.is_long_press:
                # 长按拖拽 - 移动摄像头
                self.camera.update_drag(event.pos)
            elif self.selected_object and self.is_edit_mode:
                # 【编辑模式拖拽】拖拽家具时实时检测位置合法性
                # 体验优化：
                # 1. 家具停在最后一个合法位置，可以向合法位置移动
                # 2. 显示所有槽位点（绿色=空闲，红色=占用）
                # 3. 显示家具 footprint（绿色=可放置，红色=不可放置）
                world_pos = self.camera.screen_to_world(event.pos)
                if hasattr(self.selected_object, 'update_drag'):
                    # 1. 计算新位置（考虑点击偏移，保持鼠标相对家具的位置不变）
                    new_x = world_pos[0] + self.selected_object.drag_offset[0]
                    new_y = world_pos[1] + self.selected_object.drag_offset[1]
                    # 2. 获取所有物体列表，用于碰撞检测
                    all_objects = self.world.furniture_list + self.world.crop_list
                    # 3. 从检测列表中移除自身，避免自身碰撞
                    if self.selected_object in all_objects:
                        all_objects.remove(self.selected_object)
                    # 4. 调用统一放置检测入口（与放置、end_drag 使用相同逻辑）
                    #    检测：水种植区 → 槽位重叠 → 物体碰撞
                    can_place = self.world.can_place_furniture(self.selected_object, new_x, new_y, all_objects)
                    # 缓存结果供渲染复用，避免重复检测
                    self.world._drag_can_place = can_place
                    self.world._drag_furniture = self.selected_object
                    if can_place:
                        # 5. 位置合法，更新家具位置并记录为合法位置
                        self.selected_object.update_drag(world_pos)
                        self._last_valid_pos = (new_x, new_y)
                    elif self._last_valid_pos:
                        # 6. 位置不合法，家具停在最后一个合法位置（不跟随鼠标）
                        self.selected_object.x = self._last_valid_pos[0]
                        self.selected_object.y = self._last_valid_pos[1]
                        self.selected_object.rect.x = self.selected_object.x - self.selected_object.width // 2
                        self.selected_object.rect.y = self.selected_object.y - self.selected_object.height // 2

    def handle_mouse_down(self, event: pygame.event.Event):
        """处理鼠标按下"""
        if event.button == 1:  # 左键
            # 检查是否在UI区域内（顶部状态栏或底部按钮栏）
            if self.ui.is_ui_area(event.pos):
                # 在UI区域内，只处理按钮点击，不启动拖拽
                self.ui.handle_click(event.pos)
                self.click_handled = True  # 标记已处理
                return

            # 检查重命名对话框
            if hasattr(self.ui, '_rename_active') and self.ui._rename_active:
                self.ui.handle_click(event.pos)
                self.click_handled = True
                return

            # 检查是否点击了菜单
            if self.ui.current_menu:
                self.ui.handle_click(event.pos)
                self.click_handled = True
                return

            # 检查是否点击了种子选择器
            if self.ui.seed_selector_active:
                self.ui.handle_click(event.pos)
                self.click_handled = True
                return

            # 检查是否点击了地板样式选择器
            if self.ui.floor_selector_active:
                self.ui.handle_click(event.pos)
                self.click_handled = True
                return

            self.click_handled = False
            self.mouse_down = True
            self.mouse_down_time = time.time()
            self.mouse_pos = event.pos
            self.is_long_press = False
            self.is_dragging = False

            # 记录拖拽起点（不立即启动摄像头拖拽）
            self.drag_start_pos = event.pos
            self.drag_start_camera_pos = (self.camera.x, self.camera.y)

    def handle_mouse_up(self, event: pygame.event.Event):
        """处理鼠标释放"""
        if event.button == 1:  # 左键
            # 停止滑动条拖动
            if hasattr(self.ui, '_inv_dragging_slider'):
                self.ui._inv_dragging_slider = False

            # 停止设置面板滑块拖拽
            if self.ui.current_menu == "settings":
                self.ui.settings_panel.handle_event(event)

            # 如果已经处理过点击，不再处理
            if self.click_handled:
                self.mouse_down = False
                self.is_long_press = False
                self.is_dragging = False
                self.click_handled = False
                return

            # 如果有菜单打开，不处理其他交互
            if self.ui.current_menu:
                self.mouse_down = False
                self.is_long_press = False
                self.is_dragging = False
                return

            if not self.is_dragging:
                # 点按交互（记录按压时长）
                press_duration = time.time() - self.mouse_down_time
                self.handle_click(event.pos, press_duration)
            else:
                # 【结束拖拽】检测最终位置合法性，不合法则跳回原位
                self.camera.end_drag()
                if self.selected_object and hasattr(self.selected_object, 'end_drag'):
                    # 获取所有物体列表，用于碰撞检测
                    all_objects = self.world.furniture_list + self.world.crop_list
                    # 调用 end_drag：使用 can_place_furniture 检测，失败时跳回 drag_start_pos
                    self.selected_object.end_drag(self.world.collision, all_objects, self.world)

            self.mouse_down = False
            self.is_long_press = False
            self.is_dragging = False
            self._last_valid_pos = None  # 清除拖拽状态
            self.world.stop_drag_visualization()  # 停止拖拽可视化

    def handle_click(self, screen_pos: tuple, press_duration: float = 0):
        """处理点按交互（仅从 handle_mouse_up 调用，UI/菜单检查已在上游完成）"""
        # 转换为世界坐标
        world_pos = self.camera.screen_to_world(screen_pos)

        # 【最优先】放置模式：点击确认放置
        if hasattr(self.ui, '_placing_furniture') and self.ui._placing_furniture:
            self._confirm_place_furniture(screen_pos)
            return

        # 取消当前选中
        self.world.deselect_all()
        self.selected_object = None

        # 【优先】检查是否点击了作物（成熟→收获，未成熟→操作选择器）
        # 【编辑模式】禁用作物交互（不能浇水、收获、查看信息）
        clicked_object = self.world.get_object_at_pos(world_pos, self.camera)
        if clicked_object and hasattr(clicked_object, 'current_stage'):
            # 是作物
            if not self.is_edit_mode:
                # 非编辑模式：正常作物交互
                if clicked_object.current_stage == 3:
                    result = self.world.harvest_crop(clicked_object)
                    if result:
                        # 收获后存入果实背包
                        crop_id = result["crop_id"]
                        harvests = self.game_manager.inventory.get("harvests", {})
                        harvests[crop_id] = harvests.get(crop_id, 0) + 1
                        self.game_manager.inventory["harvests"] = harvests
                        print(f"收获 {result['crop_name']}！已存入果实背包")
                        if hasattr(self.game_manager, 'save_manager'):
                            self.game_manager.save_manager.auto_save_on_action("收获")
                    return
                else:
                    # 选中作物（显示信息面板）
                    self.selected_object = clicked_object
                    self.world.select_object(clicked_object)
                    # 显示操作菜单
                    self.ui.show_crop_action_menu(clicked_object)
                    return
            # 编辑模式下：跳过作物交互，继续检测家具和区块

        # 【优先】检查是否点击了家具（家具检测优先于地板检测）
        if clicked_object and hasattr(clicked_object, 'furniture_id'):
            # 是家具
            self.selected_object = clicked_object
            self.world.select_object(clicked_object)

            if self.is_edit_mode:
                # 编辑模式下，根据当前工具执行不同操作
                tool = getattr(self, 'edit_tool', 'select')
                print(f"编辑模式工具: {tool}")
                if tool == "remove":
                    # 收回工具：放回仓库
                    print(f"尝试收回家具: {clicked_object.name}")
                    self.world.remove_furniture(clicked_object)
                    self.selected_object = None
                    print(f"已收回: {clicked_object.name}")
                    # 保存
                    if hasattr(self.game_manager, 'save_manager'):
                        self.game_manager.save_manager.auto_save_on_action("收回家具")
                elif tool == "flip":
                    # 翻转工具：镜像翻转
                    clicked_object.flip()
                # select和move工具：只选中，拖拽由update处理
                # 编辑模式下不触发交互（如开关灯）
            else:
                # 非编辑模式下触发交互
                if hasattr(clicked_object, 'handle_click'):
                    clicked_object.handle_click(world_pos, self.game_manager)
            return

        # 【优先】检查是否点击了宠物
        if hasattr(self.world, 'pet_manager'):
            # 调试：显示场景中的宠物数量
            if not hasattr(self, '_debug_pet_count_printed'):
                self._debug_pet_count_printed = True
                print(f"场景宠物数量: {len(self.world.pet_manager.scene_pets)}")
                for p in self.world.pet_manager.scene_pets:
                    print(f"  - {p.pet_id}: ({p.x:.1f}, {p.y:.1f})")

            clicked_pet = self.world.pet_manager.get_pet_at_position(world_pos, self.camera)
            if clicked_pet:
                self.selected_object = clicked_pet
                self.world.selected_object = clicked_pet  # 同步到 world
                # 调试信息
                print("=" * 50)
                print("点击宠物:")
                print(f"  ID: {clicked_pet.pet_id}")
                print(f"  位置: ({clicked_pet.x:.2f}, {clicked_pet.y:.2f})")
                print(f"  状态: {clicked_pet.state}")
                print(f"  等级: {clicked_pet.level}")
                print(f"  好感度: {clicked_pet.happiness}")
                print(f"  饱腹度: {clicked_pet.satiety}")
                print(f"  可用状态: {clicked_pet.available_states}")
                print("=" * 50)
                # 显示宠物交互菜单
                self.ui.show_pet_interaction_menu(clicked_pet)
                return

        # 检查是否点击了区块（地板或种植区）
        grid_x_raw, grid_y_raw = self.world.world_to_grid(world_pos[0], world_pos[1])
        grid_x, grid_y = math.floor(grid_x_raw), math.floor(grid_y_raw)
        tile_type = self.world.get_tile_type(grid_x, grid_y)

        # 调试信息：点击检测详情（与 coordinate_viewer 格式一致）
        if getattr(self, '_debug_click', False):
            print("=" * 50)
            print("点击信息:")
            print("  屏幕坐标: (%d, %d)" % (screen_pos[0], screen_pos[1]))
            print("  世界坐标: (%.2f, %.2f)" % (world_pos[0], world_pos[1]))
            print("  斜网格坐标: (%.2f, %.2f)" % (grid_x_raw, grid_y_raw))
            print("  斜网格坐标(取整): (%d, %d)" % (grid_x, grid_y))
            print("=" * 50)

        if tile_type in [self.world.TILE_FLOOR, self.world.TILE_FARM]:
            # 仅当编辑模式且选择工具时，才允许切换样式
            if self.is_edit_mode and self.edit_tool == "select":
                result = self.world.click_tile(grid_x, grid_y, True, world_pos)
                if result and result.get("type") == "floor_menu":
                    print(f"[点击检测] 触发地板菜单 → 区块({grid_x},{grid_y})")
                    self.ui.show_floor_style_menu(result["grid_x"], result["grid_y"])
                elif result and result.get("type") == "farm_menu":
                    print(f"[点击检测] 触发种植区菜单 → 区块({grid_x},{grid_y})")
                    self.ui.show_farm_style_menu(result["grid_x"], result["grid_y"])
                return
            elif not self.is_edit_mode:
                # 非编辑模式：种植区点击用于种植
                result = self.world.click_tile(grid_x, grid_y, False, world_pos)
                if result and result.get("type") == "plant_slot":
                    farm_type = self.world.farm_styles.get((grid_x, grid_y), 0)
                    print(f"[点击检测] 触发种植槽位 → 区块({grid_x},{grid_y}) farm_type={farm_type}")
                    if press_duration >= 1.0:
                        self.ui.show_seed_select_menu(farm_type, grid_x, grid_y, result["slot_idx"])
                    else:
                        selected_seed = self.game_manager.selected_seeds.get(str(farm_type))
                        if selected_seed:
                            self.plant_at_slot(result["grid_x"], result["grid_y"], result["slot_idx"], selected_seed)
                        else:
                            self.ui.show_seed_select_menu(farm_type, grid_x, grid_y, result["slot_idx"])
                return
        elif tile_type == -1 and self.is_edit_mode and self.edit_tool == "select":
            # 未解锁区块 → 显示解锁菜单
            print(f"[点击检测] 未解锁区块 → 区块({grid_x},{grid_y})")
            self.ui.show_unlock_menu(grid_x, grid_y)
            return

        # 编辑模式下，先检查是否点击了编辑工具栏
        if self.is_edit_mode:
            if self.ui.handle_edit_tool_click(screen_pos):
                return

    def handle_key_down(self, event: pygame.event.Event):
        """处理键盘按下（手机端不依赖按键，保留用于调试）"""
        # 如果重命名对话框激活，传递给UI处理
        if hasattr(self.ui, '_rename_active') and self.ui._rename_active:
            self.ui._handle_rename_input(event)
            return

        if event.key == pygame.K_c:
            # C键切换点击检测调试信息
            self._debug_click = not getattr(self, '_debug_click', False)
            print(f"点击检测调试: {'开启' if self._debug_click else '关闭'}")

    def handle_mouse_wheel(self, event: pygame.event.Event):
        """处理鼠标滚轮（缩放或菜单滚动）"""
        # 喂食菜单优先处理
        if self.ui.feed_menu_active:
            self.ui.scroll_feed_menu(event.y)
            return

        # 如果有菜单打开
        if self.ui.current_menu:
            if self.ui.current_menu in ("inventory", "furniture_place"):
                self.ui.scroll_inventory_detail(event.y * 15, self.mouse_pos)
            else:
                self.ui.scroll_menu(event.y * 20)
        else:
            # 否则缩放
            if event.y > 0:
                self.camera.zoom_in()
            elif event.y < 0:
                self.camera.zoom_out()

    def plant_at_slot(self, grid_x: int, grid_y: int, slot_idx: int, crop_id: str):
        """在指定槽位种植作物（从种子背包扣除）"""
        seeds = self.game_manager.inventory.get("seeds", {})
        seed_count = seeds.get(crop_id, 0)

        if seed_count <= 0:
            return

        success = self.world.plant_crop(crop_id, grid_x, grid_y, slot_idx)
        if success:
            seeds[crop_id] -= 1
            self.game_manager.inventory["seeds"] = seeds
            if hasattr(self.game_manager, 'save_manager'):
                self.game_manager.save_manager.auto_save_on_action("种植")

    def _confirm_place_furniture(self, screen_pos: tuple):
        """确认放置家具"""
        world_pos = self.camera.screen_to_world(screen_pos)
        furniture_id = self.ui._placing_furniture_id

        placed = self.world.place_furniture_from_backpack(furniture_id, world_pos[0], world_pos[1])
        if placed:
            print(f"放置成功: {furniture_id}")
            placed._show_edit_footprint = False
            self.ui._placing_furniture = False
            self.ui._placing_furniture_id = None
            self.edit_tool = "select"
            # 保存
            if hasattr(self.game_manager, 'save_manager'):
                self.game_manager.save_manager.auto_save_on_action("放置家具")
        else:
            print(f"放置失败: 位置被占用")

    def update_placing_furniture(self):
        """更新放置中的家具位置（跟随手指）"""
        if hasattr(self.ui, '_placing_furniture') and self.ui._placing_furniture:
            self.ui._placing_pos = self.camera.screen_to_world(self.mouse_pos)

    def toggle_edit_mode(self):
        """切换编辑模式"""
        self.is_edit_mode = not self.is_edit_mode
        self.edit_tool = "select"

        # 【修复】退出编辑模式时，如果正在放置家具，取消放置模式
        if not self.is_edit_mode:
            if hasattr(self.ui, '_placing_furniture') and self.ui._placing_furniture:
                # 家具还没有从仓库移除，只需取消放置模式
                self.ui._placing_furniture = False
                self.ui._placing_furniture_id = None
                print(f"退出编辑模式，取消放置模式")

            # 取消选中
            self.selected_object = None
            if hasattr(self.world, 'deselect_all'):
                self.world.deselect_all()

        for furniture in self.world.furniture_list:
            furniture.set_edit_mode(self.is_edit_mode)

        print(f"编辑模式: {'开启' if self.is_edit_mode else '关闭'}")

    def set_edit_tool(self, tool: str):
        """设置编辑工具"""
        if tool in ("select", "move", "remove", "place", "flip"):
            # 【修复】切换工具时，如果正在放置家具，取消放置模式
            if hasattr(self.ui, '_placing_furniture') and self.ui._placing_furniture:
                # 家具还没有从仓库移除，只需取消放置模式
                self.ui._placing_furniture = False
                self.ui._placing_furniture_id = None
                print(f"切换工具，取消放置模式")

            # 切换工具时取消选中
            if tool != self.edit_tool:
                self.selected_object = None
                if hasattr(self.world, 'deselect_all'):
                    self.world.deselect_all()
            self.edit_tool = tool
            print(f"编辑工具: {tool}")

    def update(self):
        """更新输入状态"""
        # 如果有菜单打开，不允许拖拽
        if self.ui.current_menu:
            return

        if self.mouse_down and not self.is_dragging:
            # 检查移动距离是否足够启动拖拽
            dx = self.mouse_pos[0] - self.drag_start_pos[0]
            dy = self.mouse_pos[1] - self.drag_start_pos[1]
            distance = (dx * dx + dy * dy) ** 0.5

            if distance >= self.DRAG_DISTANCE_THRESHOLD:
                self.is_dragging = True

                # 移动工具：选中了家具 → 拖拽移动家具（在任何位置都可拖）
                if self.is_edit_mode and self.edit_tool == "move" and self.selected_object:
                    self.is_long_press = False
                    world_pos = self.camera.screen_to_world(self.drag_start_pos)
                    if hasattr(self.selected_object, 'start_drag'):
                        self.selected_object.start_drag(world_pos, self.world.collision,
                                                        self.world.furniture_list + self.world.crop_list)
                        # 记录起始位置为最后一个合法位置
                        self._last_valid_pos = (self.selected_object.x, self.selected_object.y)
                        # 开始拖拽可视化（显示槽位点和 footprint）
                        self.world.start_drag_visualization(self.selected_object)

                # 其他情况：长按拖拽 → 移动摄像头
                else:
                    self.is_long_press = True
                    self.camera.start_drag(self.drag_start_pos)
