"""
性能测试脚本3 - 手动测量帧时间
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
    pygame.display.set_caption("性能测试")
    clock = pygame.time.Clock()

    game = Game(screen)
    game.camera.zoom = 0.3  # 最小缩放（最大视角）

    print("=" * 60)
    print("性能测试开始 (5秒)")
    print("=" * 60)

    frame_times = []
    test_duration = 5
    start_time = time.time()
    frame_count = 0

    running = True
    while running:
        current_time = time.time()
        if current_time - start_time >= test_duration:
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        frame_start = time.time()

        game.update()
        screen.fill((135, 206, 235))
        game.world.render(screen, game.camera, game.ui.is_edit_mode)
        game.lighting.render(screen, game.camera, game.world.furniture_list, game.camera.zoom)
        game.ui.render()
        pygame.display.flip()

        frame_end = time.time()
        frame_times.append(frame_end - frame_start)
        frame_count += 1

    # 输出结果
    if frame_times:
        avg_frame_time = sum(frame_times) / len(frame_times)
        avg_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        max_frame_time = max(frame_times)
        min_frame_time = min(frame_times)

        print(f"\n测试结果:")
        print(f"  总帧数: {frame_count}")
        print(f"  平均帧时间: {avg_frame_time*1000:.2f} ms")
        print(f"  平均FPS: {avg_fps:.1f}")
        print(f"  最慢帧: {max_frame_time*1000:.2f} ms ({1.0/max_frame_time:.1f} FPS)")
        print(f"  最快帧: {min_frame_time*1000:.2f} ms ({1.0/min_frame_time:.1f} FPS)")

        # 分析各阶段耗时（估算）
        print(f"\n分析:")
        print(f"  如果平均帧时间 {avg_frame_time*1000:.2f} ms > 16.67 ms (60FPS)，需要优化")

    pygame.quit()

if __name__ == "__main__":
    main()
