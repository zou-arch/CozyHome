"""
游戏主类 - 管理所有子系统
"""
import pygame
from .camera import Camera
from .world import World
from ..ui.ui import UI
from .input_handler import InputHandler
from .lighting import LightingManager
from ..managers.game_manager import GameManager
from ..managers.save_manager import SaveManager

class Game:
    """游戏主类"""

    def __init__(self, screen: pygame.Surface, loading_callback=None):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

        def update_loading(progress, status):
            if loading_callback:
                loading_callback(progress, status)

        # 初始化子系统
        update_loading(0.2, "加载管理器")
        self.game_manager = GameManager()
        self.save_manager = SaveManager(self.game_manager)

        update_loading(0.35, "初始化摄像头")
        self.camera = Camera(self.screen_width, self.screen_height)

        update_loading(0.5, "加载世界")
        self.world = World(self.game_manager)

        # 设置 world 引用到 game_manager（用于保存/加载）
        self.game_manager.world = self.world

        # 设置 pet_manager 引用到 game_manager（用于保存/加载）
        self.game_manager.pet_manager = self.world.pet_manager

        # 设置 camera 引用到 world（用于宠物更新）
        self.world.camera = self.camera

        update_loading(0.65, "加载UI")
        self.ui = UI(self.screen, self.game_manager, self.world, self.camera)

        update_loading(0.75, "加载输入")
        self.input_handler = InputHandler(self.camera, self.world, self.ui, self.game_manager)

        update_loading(0.85, "加载灯光")
        self.lighting = LightingManager(self.screen_width, self.screen_height)

        # 将clock和input_handler传递给UI
        self.ui.clock = self.clock
        self.ui.input_handler = self.input_handler

        update_loading(0.9, "加载存档")
        # 加载存档
        self.save_manager.load_game()

        update_loading(0.95, "完成初始化")
        # 新手引导：首次进入游戏时显示
        if not self.game_manager.tutorial_completed:
            self.ui.tutorial.show()

        # 开始播放背景音乐
        self._start_bgm()

    def handle_event(self, event: pygame.event.Event):
        """处理事件"""
        self.input_handler.handle_event(event)

    def update(self):
        """更新游戏逻辑"""
        # 更新输入处理（长按检测）
        self.input_handler.update()

        # 更新世界（作物生长、宠物移动等）
        self.world.update(self.screen_width, self.screen_height)

        # 更新UI
        self.ui.update()

        # 检查自动保存（定时）
        self.save_manager.check_auto_save()

    def render(self):
        """渲染画面"""
        # 清屏
        self.screen.fill((135, 206, 235))  # 天蓝色背景

        # 渲染世界（应用摄像头偏移）
        self.world.render(self.screen, self.camera, self.ui.is_edit_mode)

        # 渲染灯光效果（昼夜循环 + 灯具照明）
        self.lighting.render(self.screen, self.camera, self.world.furniture_list, self.camera.zoom)

        # 渲染UI（不受摄像头影响）
        self.ui.render()

    def _start_bgm(self):
        """开始播放背景音乐"""
        from ..core.audio_manager import audio_manager
        bgm_list = audio_manager.get_bgm_list()
        if bgm_list:
            audio_manager.play_bgm(bgm_list[0])
