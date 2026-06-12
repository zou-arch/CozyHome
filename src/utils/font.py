"""
跨平台字体加载工具
支持 Windows / Android / Linux
"""
import os
import sys
import pygame


def _get_assets_dir():
    """获取 assets 目录路径"""
    # Android: 使用 ANDROID_PRIVATE
    android_private = os.environ.get('ANDROID_PRIVATE', '')
    if android_private:
        return os.path.join(android_private, 'assets')
    # 桌面端：从当前文件向上三级到项目根目录
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets')


def load_chinese_font(size: int):
    """加载中文字体（跨平台）

    优先级：
    1. 项目自带的 fonts/ 目录（Android 和桌面通用）
    2. Windows 系统字体
    3. pygame 默认字体（兜底）
    """
    assets_dir = _get_assets_dir()

    # 项目自带字体（优先）
    bundled_fonts = [
        os.path.join(assets_dir, "fonts", "NotoSansSC-Regular.ttf"),
        os.path.join(assets_dir, "fonts", "NotoSansSC-Bold.ttf"),
    ]

    for font_path in bundled_fonts:
        if os.path.exists(font_path):
            try:
                return pygame.font.Font(font_path, size)
            except Exception:
                continue

    # Windows 系统字体（开发环境）
    if sys.platform == 'win32':
        win_fonts = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/msyhbd.ttc",
        ]
        for font_path in win_fonts:
            if os.path.exists(font_path):
                try:
                    return pygame.font.Font(font_path, size)
                except Exception:
                    continue

    # 兜底：pygame 默认字体（中文可能显示方块）
    print("警告：未找到中文字体，使用默认字体")
    return pygame.font.Font(None, size)
