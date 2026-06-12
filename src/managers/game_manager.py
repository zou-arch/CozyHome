"""
游戏管理器 - 管理游戏数据和状态
"""
from ..entities.crop import Crop
from ..entities.furniture import Furniture

class GameManager:
    """游戏管理器类"""

    def __init__(self):
        # 玩家数据
        self.coins = 100  # 初始代币

        # 已解锁物品（所有种子和家具从一开始可用）
        self.unlocked_seeds = list(Crop.CROP_DATA.keys())
        # 初始家具：1份蓄水器
        self.unlocked_furniture = ["waterstorage"]

        # UI偏好设置（跨会话持久化）
        self.ui_settings = {
            "fp_category": "all",  # 家具放置菜单上次选的分类
        }

        # 背包
        self.inventory = {
            "seeds": {          # 种子（商店购买）
                "tomato": 20,   # 初始只给20个番茄
            },
            "harvests": {       # 果实（收获获得）
            },
            "pets": [],         # 宠物ID列表
        }

        # 每种种植区类型当前选择的种子 (farm_type -> crop_id)
        self.selected_seeds = {}

        # 水资源
        self.water = 1000  # 新手一桶水=1000单位

        # 已解锁的区块坐标列表 ["x,y", ...]
        self.unlocked_tiles = []

        # 新手引导是否已完成
        self.tutorial_completed = False

        # 世界数据引用（由 game.py 设置）
        self.world = None

        # 宠物管理器引用（由 game.py 设置）
        self.pet_manager = None

    def add_coins(self, amount: int):
        """增加代币"""
        self.coins += amount
        print(f"获得 {amount} 代币，当前: {self.coins}")

    def spend_coins(self, amount: int) -> bool:
        """花费代币"""
        if self.coins >= amount:
            self.coins -= amount
            print(f"花费 {amount} 代币，当前: {self.coins}")
            return True
        else:
            print(f"代币不足，需要 {amount}，当前: {self.coins}")
            return False

    def get_save_data(self) -> dict:
        """获取存档数据"""
        save_data = {
            "coins": self.coins,
            "unlocked_seeds": self.unlocked_seeds,
            "unlocked_furniture": self.unlocked_furniture,
            "inventory": self.inventory,
            "selected_seeds": self.selected_seeds,
            "water": self.water,
            "ui_settings": self.ui_settings,
            "unlocked_tiles": self.unlocked_tiles,
            "tutorial_completed": self.tutorial_completed,
        }

        # 保存世界数据
        if self.world:
            # 将 tuple key 转换为字符串 key 以便 JSON 序列化
            save_data["floor_styles"] = {f"{k[0]},{k[1]}": v for k, v in self.world.floor_styles.items()}
            save_data["farm_styles"] = {f"{k[0]},{k[1]}": v for k, v in self.world.farm_styles.items()}

            # 保存作物列表
            save_data["crops"] = self.world.get_crop_save_data()

            # 保存家具列表
            save_data["furniture"] = self.world.get_furniture_save_data()

            # 保存天气
            save_data["weather"] = self.world.weather.get_save_data()

        # 保存宠物数据
        if self.pet_manager:
            # 不要覆盖 active_pets，让它自己维护（只有在场景中的宠物才会在列表中）
            save_data["pets"] = self.pet_manager.get_save_data()

        return save_data

    def load_save_data(self, data: dict):
        """加载存档数据"""
        self.coins = data.get("coins", 100)
        # 所有种子从一开始可用
        self.unlocked_seeds = list(Crop.CROP_DATA.keys())

        # 加载家具背包数据（如果没有存档，给默认值各两份）
        furniture_data = data.get("unlocked_furniture", None)
        if furniture_data:
            # 从存档加载
            self.unlocked_furniture = furniture_data
        else:
            # 默认值：所有家具各两份
            complete_furniture = []
            for ftype in Furniture.FURNITURE_DATA.keys():
                if ftype != "wall":
                    complete_furniture.extend([ftype, ftype])
            self.unlocked_furniture = complete_furniture

        # 加载背包数据（兼容旧版本）
        inventory_data = data.get("inventory", None)
        if inventory_data and "crops" in inventory_data and "seeds" not in inventory_data:
            # 旧版本：将 crops 拆分为 seeds
            old_crops = inventory_data.get("crops", {})
            self.inventory = {
                "seeds": old_crops.copy(),
                "harvests": {},
                "pets": inventory_data.get("pets", []),
            }
            print("检测到旧版本存档，已转换背包数据格式")
        elif inventory_data:
            # 新版本
            self.inventory = inventory_data
            # 确保 pets 字段存在
            if "pets" not in self.inventory:
                self.inventory["pets"] = []
        else:
            # 默认值
            self.inventory = {
                "seeds": {"tomato": 10, "carrot": 10},
                "harvests": {},
                "pets": [],
            }

        self.selected_seeds = data.get("selected_seeds", {})
        self.water = data.get("water", 1000)
        self.ui_settings = data.get("ui_settings", {"fp_category": "all"})
        self.unlocked_tiles = data.get("unlocked_tiles", [])
        self.tutorial_completed = data.get("tutorial_completed", False)

        # 加载世界数据
        if self.world:
            # 恢复已解锁的区块
            for tile_str in self.unlocked_tiles:
                gx, gy = map(int, tile_str.split(","))
                self.world.unlock_tile(gx, gy)
            print(f"恢复已解锁区块: {len(self.unlocked_tiles)} 个")

            # 将字符串 key 转换回 tuple key
            floor_styles_data = data.get("floor_styles", {})
            self.world.floor_styles = {tuple(map(int, k.split(","))): v for k, v in floor_styles_data.items()}

            farm_styles_data = data.get("farm_styles", {})
            self.world.farm_styles = {tuple(map(int, k.split(","))): v for k, v in farm_styles_data.items()}

            print(f"加载地板样式: {len(self.world.floor_styles)} 个区块")
            print(f"加载种植区样式: {len(self.world.farm_styles)} 个区块")

            # 加载作物列表
            crops_data = data.get("crops", [])
            self.world.load_crop_save_data(crops_data)
            print(f"加载作物: {len(self.world.crop_list)} 株")

            # 加载家具列表
            furniture_data = data.get("furniture", [])
            self.world.load_furniture_save_data(furniture_data)

            # 加载天气
            weather_data = data.get("weather", {})
            self.world.weather.load_save_data(weather_data)
            print(f"加载天气: {self.world.weather.get_weather_name()}")

        # 加载宠物数据
        if self.pet_manager:
            pets_data = data.get("pets", {})
            self.pet_manager.load_pets_from_save(data)  # 传入完整的 save_data
            print(f"加载宠物: {len(self.pet_manager.scene_pets)} 只在场景中")
