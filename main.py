"""
2.5D温馨小屋 - 主程序入口
Pygame 实现
"""
import pygame
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from src.ui.loading_screen import LoadingScreen

def main():
    """主函数"""
    pygame.init()

    # 游戏窗口设置（模拟真实手机大小）
    SCREEN_WIDTH = 755
    SCREEN_HEIGHT = 339
    SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

    # 创建窗口（Pygame 2.x，禁用VSync）
    screen = pygame.display.set_mode(SCREEN_SIZE, vsync=0)
    pygame.display.set_caption("2.5D温馨小屋")

    # 显示加载界面
    loading = LoadingScreen(screen)
    clock = pygame.time.Clock()

    def update_loading(progress, status):
        """更新加载界面"""
        loading.update_progress(progress, status)
        # 连续渲染多帧确保平滑过渡
        for _ in range(3):
            loading.render()
            pygame.display.flip()
            clock.tick(60)

    # 开始加载
    update_loading(0.05, "初始化系统")

    from src.core.game import Game

    update_loading(0.1, "加载配置")

    # 创建游戏实例
    game = Game(screen, loading_callback=update_loading)

    # 主循环
    running = True
    while running:
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # 退出时自动保存
                game.save_manager.auto_save_on_exit()
                running = False
            else:
                game.handle_event(event)

        # 更新游戏逻辑
        game.update()

        # 渲染
        game.render()

        # 刷新显示
        pygame.display.flip()

        # 控制帧率（最高120fps）
        game.clock.tick(120)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
