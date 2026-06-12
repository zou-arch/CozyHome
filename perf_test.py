"""
性能测试脚本 - 通过添加/剔除绘制来找出影响FPS最大的因素
"""
import pygame
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.game import Game

def main():
    pygame.init()
    screen = pygame.display.set_mode((755, 339))
    pygame.display.set_caption("性能测试")
    clock = pygame.time.Clock()

    game = Game(screen)

    # 设置最小缩放（最大视角）
    game.camera.zoom = 0.3  # 最小缩放，看到最多内容

    # 测试模式
    test_modes = {
        "all": "全部渲染",
        "no_pets": "隐藏宠物",
        "no_furniture": "隐藏家具",
        "no_crops": "隐藏作物",
        "no_weather": "隐藏天气",
        "no_lighting": "隐藏灯光",
        "no_ui": "隐藏UI",
        "minimal": "最小渲染（只渲染地板）",
    }
    current_mode = "all"
    mode_keys = list(test_modes.keys())
    mode_index = 0

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # 切换测试模式
                    mode_index = (mode_index + 1) % len(mode_keys)
                    current_mode = mode_keys[mode_index]
                    print(f"\n切换到模式: {test_modes[current_mode]}")
                elif event.key == pygame.K_UP:
                    game.camera.zoom = max(0.3, game.camera.zoom - 0.1)
                    print(f"缩放: {game.camera.zoom:.1f} (视角更大)")
                elif event.key == pygame.K_DOWN:
                    game.camera.zoom = min(2.0, game.camera.zoom + 0.1)
                    print(f"缩放: {game.camera.zoom:.1f} (视角更小)")

        # 更新
        game.update()

        # 清屏
        screen.fill((135, 206, 235))

        # 根据模式渲染
        if current_mode == "all":
            game.world.render(screen, game.camera, game.ui.is_edit_mode)
            game.lighting.render(screen, game.camera, game.world.furniture_list, game.camera.zoom)
            game.ui.render()
        elif current_mode == "no_pets":
            # 临时隐藏宠物
            pets = game.world.pet_manager.scene_pets[:]
            game.world.pet_manager.scene_pets = []
            game.world.render(screen, game.camera, game.ui.is_edit_mode)
            game.lighting.render(screen, game.camera, game.world.furniture_list, game.camera.zoom)
            game.ui.render()
            game.world.pet_manager.scene_pets = pets
        elif current_mode == "no_furniture":
            # 临时隐藏家具
            furniture = game.world.furniture_list[:]
            game.world.furniture_list = []
            game.world.render(screen, game.camera, game.ui.is_edit_mode)
            game.lighting.render(screen, game.camera, [], game.camera.zoom)
            game.ui.render()
            game.world.furniture_list = furniture
        elif current_mode == "no_crops":
            # 临时隐藏作物
            crops = game.world.crop_list[:]
            game.world.crop_list = []
            game.world.render(screen, game.camera, game.ui.is_edit_mode)
            game.lighting.render(screen, game.camera, game.world.furniture_list, game.camera.zoom)
            game.ui.render()
            game.world.crop_list = crops
        elif current_mode == "no_weather":
            # 跳过天气渲染
            game.world.render(screen, game.camera, game.ui.is_edit_mode)
            game.lighting.render(screen, game.camera, game.world.furniture_list, game.camera.zoom)
            game.ui.render()
        elif current_mode == "no_lighting":
            # 跳过灯光渲染
            game.world.render(screen, game.camera, game.ui.is_edit_mode)
            game.ui.render()
        elif current_mode == "no_ui":
            # 跳过UI渲染
            game.world.render(screen, game.camera, game.ui.is_edit_mode)
            game.lighting.render(screen, game.camera, game.world.furniture_list, game.camera.zoom)
        elif current_mode == "minimal":
            # 只渲染地板
            game.world.render(screen, game.camera, game.ui.is_edit_mode)

        # 显示FPS和当前模式
        fps = clock.get_fps()
        fps_text = pygame.font.SysFont(None, 24).render(f"FPS: {fps:.0f} | {test_modes[current_mode]}", True, (255, 255, 255))
        screen.blit(fps_text, (10, 10))

        # 显示操作提示
        help_text = pygame.font.SysFont(None, 20).render("SPACE: 切换模式 | UP/DOWN: 缩放 | ESC: 退出", True, (200, 200, 200))
        screen.blit(help_text, (10, 310))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
