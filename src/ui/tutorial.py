"""
新手引导系统 - 书本翻页风格
"""
import pygame
import math


class Tutorial:
    """新手引导类"""

    PAGES = [
        {
            "left_title": "欢迎",
            "left_lines": [
                "这是一款",
                "温馨的模拟经营游戏",
                "",
                "在这里你可以:",
            ],
            "right_title": "温馨小屋",
            "right_lines": [
                "种植作物",
                "收获果实",
                "",
                "摆放家具",
                "装饰小屋",
                "",
                "收集宠物",
                "经营庭院",
            ],
        },
        {
            "left_title": "基础",
            "left_lines": [
                "点击物体",
                "即可交互",
                "",
                "长按拖动",
                "移动视角",
            ],
            "right_title": "操作",
            "right_lines": [
                "点击作物",
                " -> 浇水/收获",
                "",
                "点击家具",
                " -> 查看/互动",
                "",
                "点击宠物",
                " -> 喂食/抚摸",
            ],
        },
        {
            "left_title": "种植",
            "left_lines": [
                "种菜是",
                "赚钱的主要方式",
                "",
                "1.点击种植区",
                "  选择种子",
            ],
            "right_title": "系统",
            "right_lines": [
                "2.等待作物",
                "  生长",
                "",
                "3.成熟后",
                "  点击收获",
                "",
                "4.果实可以",
                "  出售换金币",
            ],
        },
        {
            "left_title": "编辑",
            "left_lines": [
                "点击底部",
                "[编辑]按钮进入",
                "",
                "选择工具:",
                "  点击选择物体",
            ],
            "right_title": "模式",
            "right_lines": [
                "移动工具:",
                "  拖拽移动家具",
                "",
                "收回工具:",
                "  将家具放回仓库",
                "",
                "翻转工具:",
                "  镜像翻转家具",
            ],
        },
        {
            "left_title": "开始",
            "left_lines": [
                "更多内容",
                "等你探索",
                "",
                "商店购买",
                "种子和家具",
            ],
            "right_title": "冒险吧!",
            "right_lines": [
                "宠物会",
                "陪伴你冒险",
                "",
                "解锁更多区域",
                "扩建家园",
                "",
                "祝你游戏愉快!",
            ],
        },
    ]

    def __init__(self, screen: pygame.Surface, game_manager=None):
        self.screen = screen
        self.sw = screen.get_width()
        self.sh = screen.get_height()
        self.game_manager = game_manager

        # 字体
        pygame.font.init()
        base = max(11, min(14, self.sw // 50))
        self.fonts = {
            "page_title": self._font(int(base * 1.4)),
            "content": self._font(int(base * 0.95)),
            "btn": self._font(int(base * 0.85)),
            "hint": self._font(int(base * 0.7)),
        }

        # 状态
        self.page = 0
        self.active = False
        self.flip_progress = 1.0  # 翻页动画 0-1

        # 按钮
        self.rect_next = None
        self.rect_skip = None

    def _font(self, size):
        for p in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
            try:
                return pygame.font.Font(p, size)
            except:
                pass
        return pygame.font.Font(None, size)

    def show(self):
        self.active = True
        self.page = 0
        self.flip_progress = 1.0

    def hide(self):
        self.active = False
        if self.game_manager:
            self.game_manager.tutorial_completed = True

    def handle_event(self, event):
        if not self.active:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if self.rect_next and self.rect_next.collidepoint(mx, my):
                self._next()
                return True
            if self.rect_skip and self.rect_skip.collidepoint(mx, my):
                self.hide()
                return True
            # 点击书本左半部分 = 上一页，右半部分 = 下一页
            book_left = self.sw // 2 - self._book_w() // 2
            book_right = self.sw // 2 + self._book_w() // 2
            if book_left < mx < self.sw // 2:
                self._prev()
                return True
            elif self.sw // 2 < mx < book_right:
                self._next()
                return True
        return False

    def _next(self):
        if self.page < len(self.PAGES) - 1:
            self.page += 1
            self.flip_progress = 0.0
        else:
            self.hide()

    def _prev(self):
        if self.page > 0:
            self.page -= 1
            self.flip_progress = 0.0

    def update(self):
        if self.active and self.flip_progress < 1.0:
            self.flip_progress = min(1.0, self.flip_progress + 0.1)

    def render(self):
        if not self.active:
            return

        # 遮罩
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # 书本参数
        bw = self._book_w()
        bh = self._book_h()
        bx = (self.sw - bw) // 2
        by = (self.sh - bh) // 2

        # 绘制书本
        self._draw_book(bx, by, bw, bh)

        # 绘制内容
        page = self.PAGES[self.page]
        self._draw_page_content(bx, by, bw, bh, page)

        # 绘制按钮
        self._draw_next_btn(bx, by + bh)

        # 绘制跳过
        self._draw_skip()

        # 绘制翻页提示
        self._draw_nav_hints(bx, by, bw, bh)

    def _book_w(self):
        return min(380, self.sw - 40)

    def _book_h(self):
        return min(250, self.sh - 70)

    def _draw_book(self, x, y, w, h):
        """绘制书本"""
        # 书本阴影
        shadow = pygame.Surface((w + 10, h + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 80), (5, 5, w, h), border_radius=6)
        self.screen.blit(shadow, (x - 5, y - 5))

        # 左页背景
        left_page = pygame.Surface((w // 2 - 1, h), pygame.SRCALPHA)
        for i in range(h):
            ratio = i / h
            r = int(35 + ratio * 8)
            g = int(32 + ratio * 6)
            b = int(45 + ratio * 10)
            pygame.draw.line(left_page, (r, g, b, 240), (0, i), (w // 2 - 1, i))
        self.screen.blit(left_page, (x, y))

        # 右页背景
        right_page = pygame.Surface((w // 2 - 1, h), pygame.SRCALPHA)
        for i in range(h):
            ratio = i / h
            r = int(32 + ratio * 8)
            g = int(30 + ratio * 6)
            b = int(42 + ratio * 10)
            pygame.draw.line(right_page, (r, g, b, 240), (0, i), (w // 2 - 1, i))
        self.screen.blit(right_page, (x + w // 2 + 1, y))

        # 书本边框
        pygame.draw.rect(self.screen, (80, 75, 95), (x, y, w, h), 2, border_radius=4)

        # 中间装订线
        mid_x = x + w // 2
        pygame.draw.line(self.screen, (60, 55, 75), (mid_x, y + 5), (mid_x, y + h - 5), 2)

        # 装订线装饰点
        for dy in range(15, h - 10, 25):
            pygame.draw.circle(self.screen, (70, 65, 85), (mid_x, y + dy), 2)

    def _draw_page_content(self, x, y, w, h, page):
        """绘制页面内容"""
        half_w = w // 2 - 10
        margin_top = 30
        line_h = 18

        # 左页
        left_x = x + 15
        left_cx = x + w // 4

        # 左页标题
        title_surf = self.fonts["page_title"].render(page["left_title"], True, (255, 230, 180))
        self.screen.blit(title_surf, title_surf.get_rect(center=(left_cx, y + margin_top)))

        # 左页横线
        line_y = y + margin_top + 18
        pygame.draw.line(self.screen, (100, 90, 110), (left_x + 10, line_y), (left_x + half_w - 10, line_y), 1)

        # 左页内容
        content_y = line_y + 12
        for line in page["left_lines"]:
            if not line:
                content_y += 8
                continue
            surf = self.fonts["content"].render(line, True, (200, 200, 210))
            self.screen.blit(surf, surf.get_rect(center=(left_cx, content_y)))
            content_y += line_h

        # 右页
        right_x = x + w // 2 + 10
        right_cx = x + w * 3 // 4

        # 右页标题
        title_surf = self.fonts["page_title"].render(page["right_title"], True, (180, 220, 255))
        self.screen.blit(title_surf, title_surf.get_rect(center=(right_cx, y + margin_top)))

        # 右页横线
        pygame.draw.line(self.screen, (100, 90, 110), (right_x + 10, line_y), (right_x + half_w - 10, line_y), 1)

        # 右页内容
        content_y = line_y + 12
        for line in page["right_lines"]:
            if not line:
                content_y += 8
                continue
            surf = self.fonts["content"].render(line, True, (200, 200, 210))
            self.screen.blit(surf, surf.get_rect(center=(right_cx, content_y)))
            content_y += line_h

    def _draw_next_btn(self, x, y):
        """绘制下一页按钮"""
        bw = 80
        bh = 26
        bx = x + (self._book_w() - bw) // 2

        is_last = self.page == len(self.PAGES) - 1
        text = "开始游戏" if is_last else "下一页"
        color = (80, 160, 110) if is_last else (80, 130, 200)

        self.rect_next = pygame.Rect(bx, y + 6, bw, bh)
        pygame.draw.rect(self.screen, color, self.rect_next, border_radius=13)
        ts = self.fonts["btn"].render(text, True, (255, 255, 255))
        self.screen.blit(ts, ts.get_rect(center=self.rect_next.center))

    def _draw_skip(self):
        """绘制跳过按钮"""
        ts = self.fonts["hint"].render("跳过 >", True, (90, 95, 110))
        tr = ts.get_rect(topright=(self.sw - 10, 6))
        self.rect_skip = pygame.Rect(tr.x - 4, tr.y - 2, tr.width + 8, tr.height + 4)
        self.screen.blit(ts, tr)

    def _draw_nav_hints(self, x, y, w, h):
        """绘制翻页提示"""
        cy = y + h // 2
        # 左箭头
        if self.page > 0:
            pts = [(x + 5, cy), (x + 14, cy - 6), (x + 14, cy + 6)]
            pygame.draw.polygon(self.screen, (70, 75, 90), pts)
        # 右箭头
        if self.page < len(self.PAGES) - 1:
            rx = x + w - 5
            pts = [(rx, cy), (rx - 9, cy - 6), (rx - 9, cy + 6)]
            pygame.draw.polygon(self.screen, (70, 75, 90), pts)
