"""
摄像头系统 - 控制视口移动
长按拖拽移动摄像头，查看平面的不同区域
"""
import pygame

class Camera:
    """摄像头类"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # 摄像头位置（左上角坐标）
        self.x = 0.0
        self.y = 0.0

        # 拖拽状态
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_start_camera_pos = (0.0, 0.0)

        # 缩放（zoom越大=放大，zoom越小=缩小）
        self.zoom = 0.8
        self.zoom_min = 0.3    # 最小zoom = 缩到最小 = 看到6x6个区块
        self.zoom_max = 2.0    # 最大zoom = 放到最大 = 看到1个区块
        self.zoom_speed = 0.1

    def start_drag(self, pos: tuple):
        """开始拖拽"""
        self.is_dragging = True
        self.drag_start_pos = pos
        self.drag_start_camera_pos = (self.x, self.y)

    def update_drag(self, pos: tuple):
        """更新拖拽（适配缩放）"""
        if not self.is_dragging:
            return

        # 计算拖拽偏移（需要除以缩放比例）
        dx = (self.drag_start_pos[0] - pos[0]) / self.zoom
        dy = (self.drag_start_pos[1] - pos[1]) / self.zoom

        # 更新摄像头位置
        self.x = self.drag_start_camera_pos[0] + dx
        self.y = self.drag_start_camera_pos[1] + dy

    def end_drag(self):
        """结束拖拽"""
        self.is_dragging = False

    def zoom_in(self):
        """放大（滚轮向上）"""
        self.zoom = min(self.zoom + self.zoom_speed, self.zoom_max)

    def zoom_out(self):
        """缩小（滚轮向下）"""
        self.zoom = max(self.zoom - self.zoom_speed, self.zoom_min)

    def world_to_screen(self, world_pos: tuple) -> tuple:
        """世界坐标转屏幕坐标（与 coordinate_viewer 一致）"""
        screen_x = (world_pos[0] - self.x) * self.zoom + self.screen_width // 2
        screen_y = (world_pos[1] - self.y) * self.zoom + self.screen_height // 2
        return (screen_x, screen_y)

    def screen_to_world(self, screen_pos: tuple) -> tuple:
        """屏幕坐标转世界坐标（与 coordinate_viewer 一致）"""
        world_x = (screen_pos[0] - self.screen_width // 2) / self.zoom + self.x
        world_y = (screen_pos[1] - self.screen_height // 2) / self.zoom + self.y
        return (world_x, world_y)
