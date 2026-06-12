# -*- coding: utf-8 -*-
"""
加载界面 - 游戏启动时显示
"""

import pygame
import os
import math
import time


class LoadingScreen:
    """加载界面"""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

        # 颜色
        self.bg_color = (25, 28, 35)
        self.accent_color = (255, 183, 77)
        self.text_color = (220, 220, 230)

        # 字体
        self.font_title = self._load_font(28)
        self.font_text = self._load_font(13)

        # 进度
        self.progress = 0.0
        self.progress_target = 0.0
        self.status_text = "正在加载..."

        # 动画时间
        self.start_time = time.time()
        self.pulse_phase = 0

        # 装饰元素
        self.dots_count = 0
        self.dot_timer = 0

    def _load_font(self, size: int):
        """加载字体"""
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return pygame.font.Font(font_path, size)
                except:
                    continue
        return pygame.font.Font(None, size)

    def update_progress(self, progress: float, status: str = None):
        """更新进度"""
        self.progress_target = min(1.0, progress)
        if status:
            self.status_text = status

    def render(self):
        """渲染加载界面"""
        # 背景渐变
        self._render_gradient_bg()

        # 脉冲动画
        elapsed = time.time() - self.start_time
        pulse = math.sin(elapsed * 3) * 0.5 + 0.5

        # 标题
        title = self.font_title.render("2.5D温馨小屋", True, self.accent_color)
        title_x = (self.screen_width - title.get_width()) // 2
        title_y = int(self.screen_height * 0.3)
        self.screen.blit(title, (title_x, title_y))

        # 进度条
        self._render_progress_bar(pulse)

        # 状态文字
        self._render_status(pulse)

    def _render_gradient_bg(self):
        """渲染渐变背景"""
        for y in range(self.screen_height):
            ratio = y / self.screen_height
            r = int(25 + 10 * (1 - ratio))
            g = int(28 + 8 * (1 - ratio))
            b = int(35 + 5 * (1 - ratio))
            pygame.draw.line(self.screen, (r, g, b), (0, y), (self.screen_width, y))

    def _render_progress_bar(self, pulse: float):
        """渲染进度条"""
        # 平滑进度过渡
        diff = self.progress_target - self.progress
        if abs(diff) < 0.001:
            self.progress = self.progress_target
        else:
            self.progress += diff * 0.15

        # 进度条尺寸
        bar_width = min(240, self.screen_width - 100)
        bar_height = 10
        bar_x = (self.screen_width - bar_width) // 2
        bar_y = int(self.screen_height * 0.55)

        # 进度条背景（带圆角）
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(self.screen, (50, 53, 65), bg_rect, border_radius=5)

        # 进度条填充
        fill_width = int(bar_width * self.progress)
        if fill_width > 4:
            fill_rect = pygame.Rect(bar_x, bar_y, fill_width, bar_height)
            # 主色
            pygame.draw.rect(self.screen, self.accent_color, fill_rect, border_radius=5)
            # 高光
            highlight_rect = pygame.Rect(bar_x, bar_y, fill_width, bar_height // 2)
            highlight_color = (255, 200, 120)
            pygame.draw.rect(self.screen, highlight_color, highlight_rect, border_radius=5)

        # 进度百分比
        percent = int(self.progress * 100)
        percent_text = self.font_text.render(f"{percent}%", True, self.text_color)
        percent_x = (self.screen_width - percent_text.get_width()) // 2
        percent_y = bar_y + bar_height + 10
        self.screen.blit(percent_text, (percent_x, percent_y))

    def _render_status(self, pulse: float):
        """渲染状态文字"""
        # 闪烁点动画
        self.dot_timer += 1
        if self.dot_timer >= 20:
            self.dot_timer = 0
            self.dots_count = (self.dots_count + 1) % 4

        dots = "." * self.dots_count
        status = f"{self.status_text}{dots}"
        status_text = self.font_text.render(status, True, (150, 155, 170))
        status_x = (self.screen_width - status_text.get_width()) // 2
        status_y = int(self.screen_height * 0.7)
        self.screen.blit(status_text, (status_x, status_y))
