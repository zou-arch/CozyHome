# -*- coding: utf-8 -*-
"""
设置面板 - 美化版设置界面
"""

import pygame
from typing import Optional, Tuple


class SettingsPanel:
    """设置面板"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # 面板尺寸
        self.panel_width = min(280, screen_width - 40)
        self.panel_height = min(320, screen_height - 40)
        self.panel_x = (screen_width - self.panel_width) // 2
        self.panel_y = (screen_height - self.panel_height) // 2

        # 颜色主题
        self.colors = {
            "bg": (45, 45, 55),
            "bg_light": (55, 55, 68),
            "accent": (255, 183, 77),
            "accent_hover": (255, 199, 115),
            "text": (255, 255, 255),
            "text_dim": (180, 180, 190),
            "slider_bg": (70, 70, 85),
            "slider_fill": (255, 183, 77),
            "slider_handle": (255, 255, 255),
            "divider": (70, 70, 85),
        }

        # 字体
        self.font_title = pygame.font.SysFont("microsoftyaheimicrosoftyaheiui,simhei,arial", 16)
        self.font_label = pygame.font.SysFont("microsoftyaheimicrosoftyaheiui,simhei,arial", 12)
        self.font_value = pygame.font.SysFont("microsoftyaheimicrosoftyaheiui,simhei,arial", 11)

        # 音量设置
        self.bgm_volume = 0.5
        self.sfx_volume = 0.7

        # 滑块状态
        self._dragging: Optional[str] = None
        self._slider_rects = {}

        # 按钮
        self._close_rect: Optional[pygame.Rect] = None
        self._btn_rects = {}

        self.visible = False

    def show(self):
        """显示设置面板"""
        self.visible = True

    def hide(self):
        """隐藏设置面板"""
        self.visible = False
        self._dragging = None

    def set_bgm_volume(self, volume: float):
        """设置背景音乐音量"""
        self.bgm_volume = max(0.0, min(1.0, volume))

    def set_sfx_volume(self, volume: float):
        """设置音效音量"""
        self.sfx_volume = max(0.0, min(1.0, volume))

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理事件"""
        if not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._dragging = None
            return False
        elif event.type == pygame.MOUSEMOTION:
            if self._dragging:
                return self._handle_drag(event.pos)

        return True

    def _handle_click(self, pos: tuple) -> bool:
        """处理点击"""
        x, y = pos

        # 检查关闭按钮
        if self._close_rect and self._close_rect.collidepoint(x, y):
            self.hide()
            return True

        # 检查滑块
        for name, rect in self._slider_rects.items():
            if rect.collidepoint(x, y):
                self._dragging = name
                self._update_slider(name, x)
                return True

        # 检查按钮
        for name, rect in self._btn_rects.items():
            if rect.collidepoint(x, y):
                return True

        # 点击面板外部关闭
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        if not panel_rect.collidepoint(x, y):
            self.hide()
            return True

        return True

    def _handle_drag(self, pos: tuple) -> bool:
        """处理拖拽"""
        if self._dragging:
            self._update_slider(self._dragging, pos[0])
            return True
        return False

    def _update_slider(self, name: str, x: int):
        """更新滑块值"""
        if name not in self._slider_rects:
            return

        rect = self._slider_rects[name]
        # 计算滑块位置（留出边距）
        handle_w = 12
        slider_left = rect.x + handle_w // 2
        slider_right = rect.right - handle_w // 2
        slider_width = slider_right - slider_left

        # 计算比例
        ratio = (x - slider_left) / slider_width
        ratio = max(0.0, min(1.0, ratio))

        if name == "bgm":
            self.bgm_volume = ratio
        elif name == "sfx":
            self.sfx_volume = ratio

    def render(self, screen: pygame.Surface):
        """渲染设置面板"""
        if not self.visible:
            return

        # 半透明背景遮罩
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # 面板背景（圆角效果）
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        self._draw_rounded_rect(screen, panel_rect, self.colors["bg"], 12)

        # 标题栏
        title_y = self.panel_y + 20
        title_text = self.font_title.render("设置", True, self.colors["accent"])
        title_x = self.panel_x + (self.panel_width - title_text.get_width()) // 2
        screen.blit(title_text, (title_x, title_y))

        # 分割线
        divider_y = title_y + 30
        pygame.draw.line(screen, self.colors["divider"],
                        (self.panel_x + 20, divider_y),
                        (self.panel_x + self.panel_width - 20, divider_y), 1)

        # 音量设置区域
        section_y = divider_y + 20

        # 背景音乐音量
        bgm_label = self.font_label.render("背景音乐", True, self.colors["text"])
        screen.blit(bgm_label, (self.panel_x + 25, section_y))

        bgm_value = self.font_value.render(f"{int(self.bgm_volume * 100)}%", True, self.colors["text_dim"])
        screen.blit(bgm_value, (self.panel_x + self.panel_width - 55, section_y))

        # 背景音乐滑块
        slider_y = section_y + 22
        slider_rect = pygame.Rect(self.panel_x + 25, slider_y, self.panel_width - 50, 20)
        self._slider_rects["bgm"] = slider_rect
        self._render_slider(screen, slider_rect, self.bgm_volume, "bgm")

        # 音效音量
        sfx_y = slider_y + 35
        sfx_label = self.font_label.render("音效", True, self.colors["text"])
        screen.blit(sfx_label, (self.panel_x + 25, sfx_y))

        sfx_value = self.font_value.render(f"{int(self.sfx_volume * 100)}%", True, self.colors["text_dim"])
        screen.blit(sfx_value, (self.panel_x + self.panel_width - 55, sfx_y))

        # 音效滑块
        sfx_slider_y = sfx_y + 22
        sfx_slider_rect = pygame.Rect(self.panel_x + 25, sfx_slider_y, self.panel_width - 50, 20)
        self._slider_rects["sfx"] = sfx_slider_rect
        self._render_slider(screen, sfx_slider_rect, self.sfx_volume, "sfx")

        # 分割线
        divider2_y = sfx_slider_y + 35
        pygame.draw.line(screen, self.colors["divider"],
                        (self.panel_x + 20, divider2_y),
                        (self.panel_x + self.panel_width - 20, divider2_y), 1)

        # 按钮区域
        btn_y = divider2_y + 15
        btn_w = 80
        btn_h = 30
        btn_gap = 15

        # 保存按钮
        save_x = self.panel_x + (self.panel_width - btn_w * 2 - btn_gap) // 2
        save_rect = pygame.Rect(save_x, btn_y, btn_w, btn_h)
        self._btn_rects["save"] = save_rect
        self._render_button(screen, save_rect, "保存游戏", is_primary=True)

        # 加载按钮
        load_x = save_x + btn_w + btn_gap
        load_rect = pygame.Rect(load_x, btn_y, btn_w, btn_h)
        self._btn_rects["load"] = load_rect
        self._render_button(screen, load_rect, "加载游戏", is_primary=False)

        # 关闭按钮
        close_y = btn_y + btn_h + 15
        close_w = 100
        close_x = self.panel_x + (self.panel_width - close_w) // 2
        close_rect = pygame.Rect(close_x, close_y, close_w, btn_h)
        self._close_rect = close_rect
        self._render_button(screen, close_rect, "关闭", is_primary=False)

    def _render_slider(self, screen: pygame.Surface, rect: pygame.Rect, value: float, name: str):
        """渲染滑块"""
        # 滑块背景
        self._draw_rounded_rect(screen, rect, self.colors["slider_bg"], 4)

        # 填充部分
        handle_w = 12
        fill_width = int((rect.width - handle_w) * value)
        if fill_width > 0:
            fill_rect = pygame.Rect(rect.x, rect.y, fill_width + handle_w // 2, rect.height)
            self._draw_rounded_rect(screen, fill_rect, self.colors["slider_fill"], 4)

        # 滑块手柄
        handle_x = rect.x + fill_width
        handle_rect = pygame.Rect(handle_x, rect.y + 2, handle_w, rect.height - 4)
        self._draw_rounded_rect(screen, handle_rect, self.colors["slider_handle"], 6)

    def _render_button(self, screen: pygame.Surface, rect: pygame.Rect, text: str, is_primary: bool = False):
        """渲染按钮"""
        # 按钮背景
        bg_color = self.colors["accent"] if is_primary else self.colors["bg_light"]
        self._draw_rounded_rect(screen, rect, bg_color, 6)

        # 按钮文字
        text_color = (45, 45, 55) if is_primary else self.colors["text"]
        text_surface = self.font_label.render(text, True, text_color)
        text_x = rect.x + (rect.width - text_surface.get_width()) // 2
        text_y = rect.y + (rect.height - text_surface.get_height()) // 2
        screen.blit(text_surface, (text_x, text_y))

    def _draw_rounded_rect(self, surface: pygame.Surface, rect: pygame.Rect, color: tuple, radius: int):
        """绘制圆角矩形"""
        # 简单实现：用多个矩形和圆组成
        x, y, w, h = rect

        # 四个角的圆
        pygame.draw.circle(surface, color, (x + radius, y + radius), radius)
        pygame.draw.circle(surface, color, (x + w - radius, y + radius), radius)
        pygame.draw.circle(surface, color, (x + radius, y + h - radius), radius)
        pygame.draw.circle(surface, color, (x + w - radius, y + h - radius), radius)

        # 填充矩形
        pygame.draw.rect(surface, color, (x + radius, y, w - radius * 2, h))
        pygame.draw.rect(surface, color, (x, y + radius, w, h - radius * 2))

    def get_click_action(self, pos: tuple) -> Optional[str]:
        """获取点击位置对应的action"""
        if not self.visible:
            return None

        x, y = pos

        if self._close_rect and self._close_rect.collidepoint(x, y):
            return "close"

        for name, rect in self._btn_rects.items():
            if rect.collidepoint(x, y):
                return name

        return None
