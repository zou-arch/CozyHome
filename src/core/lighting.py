"""
灯光效果管理器 - 昼夜循环 + 灯具照明
"""
import pygame
import math
import time


class LightingManager:
    """灯光效果管理器"""

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h

        # 灰层颜色（偏蓝）
        self.tint_color = (10, 10, 40)

        # 灯光参数
        self.light_radius_world = 180  # 1.5个区块对角线距离

        # 缓存 overlay Surface（避免每帧创建）
        self._overlay_cache = None
        self._overlay_size = (0, 0)

    @staticmethod
    def get_game_time():
        """获取游戏时间（小时, 分钟）
        系统分钟 0 → 游戏 00:00
        系统分钟 30 → 游戏 12:00
        系统分钟 60 → 游戏 00:00
        """
        real_minute = int(time.time() % 3600 / 60)
        game_total_minutes = real_minute * 24
        game_hours = (game_total_minutes // 60) % 24
        game_minutes = game_total_minutes % 60
        return game_hours, game_minutes

    def get_daylight_alpha(self, game_hours, game_minutes):
        """
        根据游戏时间计算灰层透明度
        游戏时间映射（1真实分钟=24游戏分钟）:
        00:00-04:00 → 黑夜→白天 (204 → 0)
        04:00-16:00 → 白天 (0)
        16:00-20:00 → 白天→黑夜 (0 → 204)
        20:00-00:00 → 夜晚 (204)
        """
        max_alpha = 204  # 80% × 255
        # 转为游戏分钟数（0-1439）
        t = game_hours * 60 + game_minutes

        if t < 240:       # 00:00-04:00 黑夜→白天
            return int(max_alpha * (1.0 - t / 240.0))
        elif t < 960:     # 04:00-16:00 白天
            return 0
        elif t < 1200:    # 16:00-20:00 白天→黑夜
            return int(max_alpha * ((t - 960) / 240.0))
        else:              # 20:00-00:00 夜晚
            return max_alpha

    def render(self, screen, camera, furniture_list, zoom):
        """渲染灯光效果到屏幕"""
        game_hours, game_minutes = self.get_game_time()
        daylight_alpha = self.get_daylight_alpha(game_hours, game_minutes)

        if daylight_alpha == 0:
            return

        # 收集光源（屏幕坐标）
        lights = []
        for obj in furniture_list:
            if hasattr(obj, 'is_light') and obj.is_light and obj.is_on:
                sx, sy = camera.world_to_screen((obj.x, obj.y))
                light_r = self.light_radius_world * zoom
                lights.append((sx, sy, light_r))

        # 复用 overlay Surface（避免每帧创建）
        if self._overlay_cache is None or self._overlay_size != (self.screen_w, self.screen_h):
            self._overlay_cache = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            self._overlay_size = (self.screen_w, self.screen_h)

        # 清空 overlay
        self._overlay_cache.fill((0, 0, 0, 0))

        if not lights:
            self._overlay_cache.fill((*self.tint_color, daylight_alpha))
        else:
            self._render_with_lights(self._overlay_cache, daylight_alpha, lights)

        screen.blit(self._overlay_cache, (0, 0))

    def _render_with_lights(self, overlay, daylight_alpha, lights):
        """灰层 + 灯光减法：灯光区域灰层变透明"""
        block_size = 10

        # 首先用完整灰层填充整个屏幕
        overlay.fill((*self.tint_color, daylight_alpha))

        # 然后在灯光影响区域减去灰层（使灯光区域变亮）
        for lx, ly, lr in lights:
            # 计算灯光影响的屏幕范围
            min_x = max(0, int(lx - lr))
            max_x = min(self.screen_w, int(lx + lr) + block_size)
            min_y = max(0, int(ly - lr))
            max_y = min(self.screen_h, int(ly + lr) + block_size)

            # 只遍历灯光影响区域内的块
            for by in range(min_y, max_y, block_size):
                for bx in range(min_x, max_x, block_size):
                    # 块中心坐标
                    cx = bx + block_size / 2
                    cy = by + block_size / 2

                    dist = math.hypot(cx - lx, cy - ly)
                    if dist < lr:
                        # 计算亮度
                        brightness = 1.0 - (dist / lr)
                        brightness = brightness * brightness

                        # 该块的最终alpha（灯光越亮，alpha越低）
                        final_alpha = int(daylight_alpha * (1.0 - brightness))

                        if final_alpha < daylight_alpha:
                            # 用更透明的色块覆盖（减去灰层）
                            rect = (bx, by,
                                    min(block_size, self.screen_w - bx),
                                    min(block_size, self.screen_h - by))
                            pygame.draw.rect(overlay, (*self.tint_color, final_alpha), rect)
