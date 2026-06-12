"""
存档管理器 - 保存和加载游戏
支持自动保存（定时+关键操作点）
"""
import json
import os
import time


def _get_save_dir():
    """获取跨平台的可写存档目录"""
    # Android: 使用应用私有目录
    android_private = os.environ.get('ANDROID_PRIVATE', '')
    if android_private:
        save_dir = os.path.join(android_private, 'saves')
    else:
        # 桌面端：项目根目录下的 saves 文件夹
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'saves')
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


class SaveManager:
    """存档管理器类"""

    AUTO_SAVE_INTERVAL = 60  # 自动保存间隔（秒）

    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.last_save_time = 0
        self.auto_save_enabled = True
        self.save_path = os.path.join(_get_save_dir(), "savegame.json")

    def save_game(self):
        """保存游戏"""
        try:
            save_data = self.game_manager.get_save_data()
            save_data["save_time"] = time.time()
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            self.last_save_time = time.time()
            print("游戏已保存")
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False

    def load_game(self) -> bool:
        """加载游戏"""
        if not os.path.exists(self.save_path):
            print("没有找到存档文件")
            return False

        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            self.game_manager.load_save_data(save_data)
            print("游戏已加载")
            return True
        except Exception as e:
            print(f"加载失败: {e}")
            return False

    def has_save(self) -> bool:
        """检查是否有存档"""
        return os.path.exists(self.save_path)

    def check_auto_save(self):
        """检查是否需要自动保存（定时）"""
        if not self.auto_save_enabled:
            return

        current_time = time.time()
        if current_time - self.last_save_time >= self.AUTO_SAVE_INTERVAL:
            self.save_game()

    def auto_save_on_action(self, action_name: str = ""):
        """关键操作点自动保存"""
        if not self.auto_save_enabled:
            return

        print(f"自动保存（触发点: {action_name}）")
        self.save_game()

    def auto_save_on_exit(self):
        """退出游戏时自动保存"""
        print("退出游戏，自动保存...")
        self.save_game()
