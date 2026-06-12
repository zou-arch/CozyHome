"""
性能测试脚本4 - 逐个测试各模块影响
"""
import pygame
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.game import Game

def measure_fps(game, screen, test_func, name, duration=3):
    """测量指定渲染模式的FPS"""
    frame_times = []
    start_time = time.time()

    running = True
    while running:
        if time.time() - start_time >= duration:
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                return 0

        frame_start = time.time()

        game.update()
        screen.fill((135, 206, 235))
        test_func(game, screen)
        pygame.display.flip()

        frame_end = time.time()
        frame_times.append(frame_end - frame_start)

    if frame_times:
        avg_frame_time = sum(frame_times) / len(frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0
    return 0

def main():
    pygame.init()
    screen = pygame.display.set_mode((755, 339))
    pygame.display.set_caption("性能对比测试")
    clock = pygame.time.Clock()

    game = Game(screen)
    game.camera.zoom = 0.3  # 最小缩放（最大视角）

    print("=" * 70)
    print("性能对比测试 (每项测试3秒)")
    print("=" * 70)

    # 定义测试项目
    tests = [
        ("1. 完整渲染", lambda g, s: (
            g.world.render(s, g.camera, g.ui.is_edit_mode),
            g.lighting.render(s, g.camera, g.world.furniture_list, g.camera.zoom),
            g.ui.render()
        )),
        ("2. 无宠物", lambda g, s: (
            setattr(g.world.pet_manager, 'scene_pets', []),
            g.world.render(s, g.camera, g.ui.is_edit_mode),
            g.lighting.render(s, g.camera, g.world.furniture_list, g.camera.zoom),
            g.ui.render(),
            setattr(g.world.pet_manager, 'scene_pets', g.world.pet_manager._saved_pets if hasattr(g.world.pet_manager, '_saved_pets') else [])
        )),
        ("3. 无家具", lambda g, s: (
            setattr(g.world, '_saved_furniture', g.world.furniture_list[:]),
            setattr(g.world, 'furniture_list', []),
            g.world.render(s, g.camera, g.ui.is_edit_mode),
            g.lighting.render(s, g.camera, [], g.camera.zoom),
            g.ui.render(),
            setattr(g.world, 'furniture_list', getattr(g.world, '_saved_furniture', []))
        )),
        ("4. 无作物", lambda g, s: (
            setattr(g.world, '_saved_crops', g.world.crop_list[:]),
            setattr(g.world, 'crop_list', []),
            g.world.render(s, g.camera, g.ui.is_edit_mode),
            g.lighting.render(s, g.camera, g.world.furniture_list, g.camera.zoom),
            g.ui.render(),
            setattr(g.world, 'crop_list', getattr(g.world, '_saved_crops', []))
        )),
        ("5. 无灯光", lambda g, s: (
            g.world.render(s, g.camera, g.ui.is_edit_mode),
            g.ui.render()
        )),
        ("6. 无UI", lambda g, s: (
            g.world.render(s, g.camera, g.ui.is_edit_mode),
            g.lighting.render(s, g.camera, g.world.furniture_list, g.camera.zoom)
        )),
        ("7. 只渲染地板", lambda g, s: (
            g.world.render(s, g.camera, g.ui.is_edit_mode)
        )),
    ]

    # 保存原始数据
    original_pets = game.world.pet_manager.scene_pets[:]
    original_furniture = game.world.furniture_list[:]
    original_crops = game.world.crop_list[:]

    results = []
    for name, test_func in tests:
        print(f"\n测试: {name}...")

        # 恢复原始数据
        game.world.pet_manager.scene_pets = original_pets[:]
        game.world.furniture_list = original_furniture[:]
        game.world.crop_list = original_crops[:]

        fps = measure_fps(game, screen, test_func, name)
        results.append((name, fps))
        print(f"  结果: {fps:.1f} FPS")

    # 输出对比结果
    print("\n" + "=" * 70)
    print("性能对比结果")
    print("=" * 70)

    base_fps = results[0][1] if results[0][1] > 0 else 1
    for name, fps in results:
        impact = ((base_fps - fps) / base_fps) * 100 if base_fps > 0 else 0
        bar = "█" * int(fps / 2)
        print(f"{name:20s}: {fps:6.1f} FPS {bar}")
        if impact > 5:
            print(f"{'':20s}  影响: -{impact:.1f}%")

    pygame.quit()

if __name__ == "__main__":
    main()
