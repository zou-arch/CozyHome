"""
坐标系可视化工具
展示斜坐标系（26°/334°）的网格和坐标转换
"""
import pygame
import math
import sys

# 初始化 pygame
pygame.init()

# 屏幕设置（与游戏 main.py 一致）
SCREEN_WIDTH = 755
SCREEN_HEIGHT = 339
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("坐标系可视化工具 - 26°/334° 斜坐标系")

# 颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
GRAY = (180, 150, 120)  # 地板颜色
LIGHT_GRAY = (220, 220, 220)
DARK_GRAY = (100, 100, 100)

# 坐标系参数（与 world.py 一致）
TILE_SPACING = 120
TILE_WIDTH = 174  # 菱形水平半对角线
TILE_HEIGHT = 85  # 菱形垂直半对角线

# 斜坐标系角度（116°/244°，对应 26°/334° 边方向）
ALPHA = math.radians(116)
BETA = math.radians(244)

# 计算变换矩阵（与 world.py 完全一致）
COS_A, SIN_A = math.cos(ALPHA), math.sin(ALPHA)
COS_B, SIN_B = math.cos(BETA), math.sin(BETA)
DET = COS_A * SIN_B - SIN_A * COS_B
K = TILE_SPACING / abs(DET)

# 正变换矩阵（斜网格坐标 -> 世界坐标）
M_FORWARD = [
    [-SIN_A * K / DET, SIN_B * K / DET],
    [COS_A * K / DET, -COS_B * K / DET]
]

# 逆变换矩阵（世界坐标 -> 斜网格坐标）
DET_M = M_FORWARD[0][0] * M_FORWARD[1][1] - M_FORWARD[0][1] * M_FORWARD[1][0]
M_INVERSE = [
    [M_FORWARD[1][1] / DET_M, -M_FORWARD[0][1] / DET_M],
    [-M_FORWARD[1][0] / DET_M, M_FORWARD[0][0] / DET_M]
]

def grid_to_world(gx, gy):
    """斜网格坐标 -> 世界坐标"""
    wx = M_FORWARD[0][0] * gx + M_FORWARD[0][1] * gy
    wy = M_FORWARD[1][0] * gx + M_FORWARD[1][1] * gy
    return wx, wy

def world_to_grid(wx, wy):
    """世界坐标 -> 斜网格坐标"""
    gx = M_INVERSE[0][0] * wx + M_INVERSE[0][1] * wy
    gy = M_INVERSE[1][0] * wx + M_INVERSE[1][1] * wy
    return gx, gy

def world_to_screen(wx, wy, camera_x, camera_y, zoom):
    """世界坐标 -> 屏幕坐标"""
    sx = (wx - camera_x) * zoom + SCREEN_WIDTH // 2
    sy = (wy - camera_y) * zoom + SCREEN_HEIGHT // 2
    return sx, sy

def screen_to_world(sx, sy, camera_x, camera_y, zoom):
    """屏幕坐标 -> 世界坐标"""
    wx = (sx - SCREEN_WIDTH // 2) / zoom + camera_x
    wy = (sy - SCREEN_HEIGHT // 2) / zoom + camera_y
    return wx, wy

def get_tile_vertices(gx, gy):
    """获取区块的四个顶点（菱形）"""
    x0, y0 = grid_to_world(gx, gy)
    x1, y1 = grid_to_world(gx + 1, gy)
    x2, y2 = grid_to_world(gx + 1, gy + 1)
    x3, y3 = grid_to_world(gx, gy + 1)
    return [(x0, y0), (x1, y1), (x2, y2), (x3, y3)]

class GridRenderer:
    """网格渲染器（带缓存，优化性能）"""
    def __init__(self):
        self.grid_surface = None
        self.grid_size = (0, 0)
        self.grid_camera = (0, 0)
        self.grid_zoom = 1.0

    def render(self, surface, camera_x, camera_y, zoom):
        """渲染网格（带缓存）"""
        # 检查是否需要重绘
        needs_redraw = (
            self.grid_surface is None or
            self.grid_size != (SCREEN_WIDTH, SCREEN_HEIGHT) or
            abs(self.grid_camera[0] - camera_x) > 0.1 or
            abs(self.grid_camera[1] - camera_y) > 0.1 or
            abs(self.grid_zoom - zoom) > 0.01
        )

        if needs_redraw:
            self._redraw(camera_x, camera_y, zoom)

        surface.blit(self.grid_surface, (0, 0))

    def _redraw(self, camera_x, camera_y, zoom):
        """重绘网格"""
        # 创建或重用 Surface
        if self.grid_surface is None or self.grid_size != (SCREEN_WIDTH, SCREEN_HEIGHT):
            self.grid_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.grid_size = (SCREEN_WIDTH, SCREEN_HEIGHT)

        self.grid_surface.fill(WHITE)

        # 计算可见范围（世界坐标）
        left = camera_x - SCREEN_WIDTH / (2 * zoom)
        right = camera_x + SCREEN_WIDTH / (2 * zoom)
        top = camera_y - SCREEN_HEIGHT / (2 * zoom)
        bottom = camera_y + SCREEN_HEIGHT / (2 * zoom)

        # 转换为网格坐标范围
        gx1, gy1 = world_to_grid(left, top)
        gx2, gy2 = world_to_grid(right, top)
        gx3, gy3 = world_to_grid(left, bottom)
        gx4, gy4 = world_to_grid(right, bottom)

        min_gx = int(math.floor(min(gx1, gx2, gx3, gx4))) - 1
        max_gx = int(math.floor(max(gx1, gx2, gx3, gx4))) + 1
        min_gy = int(math.floor(min(gy1, gy2, gy3, gy4))) - 1
        max_gy = int(math.floor(max(gy1, gy2, gy3, gy4))) + 1

        # 绘制菱形网格
        for gy in range(min_gy, max_gy + 1):
            for gx in range(min_gx, max_gx + 1):
                vertices = get_tile_vertices(gx, gy)
                screen_vertices = [world_to_screen(vx, vy, camera_x, camera_y, zoom) for vx, vy in vertices]
                screen_vertices_int = [(int(sx), int(sy)) for sx, sy in screen_vertices]

                # 绘制菱形边框
                pygame.draw.polygon(self.grid_surface, DARK_GRAY, screen_vertices_int, 1)

                # 绘制网格线（A线和B线）
                # A线方向（26°）
                if gx % 5 == 0:
                    wx1, wy1 = grid_to_world(gx, min_gy)
                    wx2, wy2 = grid_to_world(gx, max_gy)
                    sx1, sy1 = world_to_screen(wx1, wy1, camera_x, camera_y, zoom)
                    sx2, sy2 = world_to_screen(wx2, wy2, camera_x, camera_y, zoom)
                    pygame.draw.line(self.grid_surface, BLUE, (int(sx1), int(sy1)), (int(sx2), int(sy2)), 1)

                # B线方向（334°）
                if gy % 5 == 0:
                    wx1, wy1 = grid_to_world(min_gx, gy)
                    wx2, wy2 = grid_to_world(max_gx, gy)
                    sx1, sy1 = world_to_screen(wx1, wy1, camera_x, camera_y, zoom)
                    sx2, sy2 = world_to_screen(wx2, wy2, camera_x, camera_y, zoom)
                    pygame.draw.line(self.grid_surface, GREEN, (int(sx1), int(sy1)), (int(sx2), int(sy2)), 1)

        # 绘制原点
        sx, sy = world_to_screen(0, 0, camera_x, camera_y, zoom)
        pygame.draw.circle(self.grid_surface, RED, (int(sx), int(sy)), 5)
        font = pygame.font.SysFont(None, 24)
        text = font.render("O(0,0)", True, RED)
        self.grid_surface.blit(text, (int(sx) + 10, int(sy) - 10))

        # 更新缓存状态
        self.grid_camera = (camera_x, camera_y)
        self.grid_zoom = zoom

def main():
    clock = pygame.time.Clock()
    camera_x, camera_y = 0, 0
    zoom = 1.0
    font = pygame.font.SysFont(None, 20)

    # 网格渲染器（带缓存）
    grid_renderer = GridRenderer()

    # 显示选项
    show_info = True

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_i:
                    show_info = not show_info
                elif event.key == pygame.K_r:
                    # 重置视图
                    camera_x, camera_y = 0, 0
                    zoom = 1.0
                    grid_renderer.grid_surface = None  # 强制重绘
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键点击
                    sx, sy = event.pos
                    wx, wy = screen_to_world(sx, sy, camera_x, camera_y, zoom)
                    gx, gy = world_to_grid(wx, wy)
                    print("=" * 50)
                    print("点击信息:")
                    print("  屏幕坐标: (%d, %d)" % (sx, sy))
                    print("  世界坐标: (%.2f, %.2f)" % (wx, wy))
                    print("  斜网格坐标: (%.2f, %.2f)" % (gx, gy))
                    print("  斜网格坐标(取整): (%d, %d)" % (int(math.floor(gx)), int(math.floor(gy))))
                    print("=" * 50)
            elif event.type == pygame.MOUSEMOTION:
                if event.buttons[0]:  # 按住左键拖动
                    dx = event.rel[0] / zoom
                    dy = event.rel[1] / zoom
                    camera_x -= dx
                    camera_y -= dy
                    # 拖动时不需要强制重绘，缓存会自动更新
            elif event.type == pygame.MOUSEWHEEL:
                zoom *= 1.1 if event.y > 0 else 0.9
                zoom = max(0.1, min(5.0, zoom))

        # 渲染网格（带缓存）
        grid_renderer.render(screen, camera_x, camera_y, zoom)

        # 绘制信息
        if show_info:
            info_lines = [
                "坐标系可视化工具 - 26/334 斜坐标系",
                "",
                "菱形网格: 26/334 方向",
                "蓝色线: A线方向（26）",
                "绿色线: B线方向（334）",
                "",
                "操作:",
                "  左键点击: 打印坐标信息",
                "  左键拖动: 移动视图",
                "  滚轮: 缩放",
                "  I键: 显示/隐藏信息",
                "  R键: 重置视图",
                "",
                "相机: (%.1f, %.1f)  缩放: %.2f" % (camera_x, camera_y, zoom),
            ]

            # 半透明背景
            info_bg = pygame.Surface((300, len(info_lines) * 20 + 10), pygame.SRCALPHA)
            info_bg.fill((0, 0, 0, 128))
            screen.blit(info_bg, (5, 5))

            y = 10
            for line in info_lines:
                text = font.render(line, True, WHITE)
                screen.blit(text, (10, y))
                y += 20

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()