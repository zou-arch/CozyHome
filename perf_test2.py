"""
性能测试脚本2 - 简单FPS测试
"""
import pygame
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.game import Game

def main():
    pygame.init()
    screen = pygame.display.set_mode((755, 339))
    pygame.display.set_caption("FPS测试 - 关闭此窗口结束")
    clock = pygame.time.Clock()

    game = Game(screen)
    game.camera.zoom = 0.3  # 最小缩放（最大视角）

    print("=" * 60)
    print("性能测试开始")
    print("=" * 60)

    # 记录FPS
    fps_values = []
    test_duration = 5  # 测试5秒
    start_time = time.time()

    running = True
    while running and (time.time() - start_time) < test_duration:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        game.update()
        screen.fill((135, 206, 235))
        game.world.render(screen, game.camera, game.ui.is_edit_mode)
        game.lighting.render(screen, game.camera, game.world.furniture_list, game.camera.zoom)
        game.ui.render()
        pygame.display.flip()

        fps = clock.get_fps()
        fps_values.append(fps)

    # 输出结果
    if fps_values:
        avg_fps = sum(fps_values) / len(fps_values)
        min_fps = min(fps_values)
        max_fps = max(fps_values)
        print(f"\n测试结果 ({test_duration}秒):")
        print(f"  平均FPS: {avg_fps:.1f}")
        print(f"  最低FPS: {min_fps:.1f}")
        print(f"  最高FPS: {max_fps:.1f}")
        print(f"  样本数: {len(fps_values)}")

    pygame.quit()

if __name__ == "__main__":
    main()
