# -*- coding: utf-8 -*-
"""
音频管理器 - 管理背景音乐和音效
"""

import pygame
import os
from typing import Optional


# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")


class AudioManager:
    """音频管理器单例"""

    _instance: Optional["AudioManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.mixer_initialized = False
        self.current_bgm: Optional[str] = None
        self.bgm_volume = 0.5
        self.sfx_volume = 0.7

        self._init_mixer()

    def _init_mixer(self):
        """初始化混音器"""
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            self.mixer_initialized = True
            pygame.mixer.music.set_volume(self.bgm_volume)
        except pygame.error as e:
            self.mixer_initialized = False

    def play_bgm(self, filename: str, loops: int = -1):
        """
        播放背景音乐

        Args:
            filename: 音乐文件名（相对于assets/audio/bgm/）
            loops: 循环次数，-1为无限循环
        """
        if not self.mixer_initialized:
            return

        if self.current_bgm == filename:
            return

        filepath = os.path.join(ASSETS_DIR, "audio", "bgm", filename)

        if not os.path.exists(filepath):
            return

        try:
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play(loops)
            self.current_bgm = filename
        except pygame.error as e:
            pass

    def stop_bgm(self):
        """停止背景音乐"""
        if not self.mixer_initialized:
            return
        pygame.mixer.music.stop()
        self.current_bgm = None

    def pause_bgm(self):
        """暂停背景音乐"""
        if not self.mixer_initialized:
            return
        pygame.mixer.music.pause()

    def resume_bgm(self):
        """恢复背景音乐"""
        if not self.mixer_initialized:
            return
        pygame.mixer.music.unpause()

    def set_bgm_volume(self, volume: float):
        """设置背景音乐音量 (0.0 - 1.0)"""
        self.bgm_volume = max(0.0, min(1.0, volume))
        if self.mixer_initialized:
            pygame.mixer.music.set_volume(self.bgm_volume)

    def set_sfx_volume(self, volume: float):
        """设置音效音量 (0.0 - 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, volume))

    def get_bgm_list(self) -> list:
        """获取所有可用的背景音乐列表"""
        bgm_dir = os.path.join(ASSETS_DIR, "audio", "bgm")
        if not os.path.exists(bgm_dir):
            return []

        files = []
        for f in os.listdir(bgm_dir):
            if f.lower().endswith(('.mp3', '.ogg', '.wav')):
                files.append(f)
        return files

    def play_next_bgm(self):
        """播放下一首背景音乐"""
        bgm_list = self.get_bgm_list()
        if not bgm_list:
            return

        if self.current_bgm in bgm_list:
            current_index = bgm_list.index(self.current_bgm)
            next_index = (current_index + 1) % len(bgm_list)
            self.play_bgm(bgm_list[next_index])
        else:
            self.play_bgm(bgm_list[0])

    def play_random_bgm(self):
        """随机播放一首背景音乐"""
        import random
        bgm_list = self.get_bgm_list()
        if not bgm_list:
            return
        random_bgm = random.choice(bgm_list)
        self.play_bgm(random_bgm)


# 全局音频管理器实例
audio_manager = AudioManager()
