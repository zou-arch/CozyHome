"""
存档管理器 - 保存和加载游戏
支持自动保存（定时+关键操作点）
"""
import json
import os
import time

class SaveManager:
    """存档管理器类"""

    SAVE_PATH = "savegame.json"
    AUTO_SAVE_INTERVAL = 60  # 自动保存间隔（秒）

    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.last_save_time = 0
        self.auto_save_enabled = True

    def save_game(self):
        """保存游戏"""
        try:
            save_data = self.game_manager.get_save_data()
            save_data["save_time"] = time.time()
            with open(self.SAVE_PATH, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            self.last_save_time = time.time()
            print("游戏已保存")
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False

    def load_game(self) -> bool:
        """加载游戏"""
        if not os.path.exists(self.SAVE_PATH):
            print("没有找到存档文件")
            return False

        try:
            with open(self.SAVE_PATH, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            self.game_manager.load_save_data(save_data)
            print("游戏已加载")
            return True
        except Exception as e:
            print(f"加载失败: {e}")
            return False

    def has_save(self) -> bool:
        """检查是否有存档"""
        return os.path.exists(self.SAVE_PATH)

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
