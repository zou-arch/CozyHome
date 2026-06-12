"""
天气系统 - 雨天自动浇水，全屏雨滴动画
"""
import random
import time
import pygame


class Weather:
    """天气系统"""

    WEATHER_SUNNY = "晴天"
    WEATHER_RAINY = "雨天"

    # 雨滴长度预设
    RAIN_LENGTHS = [8, 12, 16, 20, 25]
    # 雨滴 Surface 缓存 {(length, alpha): surface}
    _rain_cache = {}

    def __init__(self):
        self.current_weather = self.WEATHER_SUNNY
        self.last_change_time = time.time()
        self.change_interval = 3600 * 4  # 4小时变化一次
        self.rain_duration = 0  # 雨天剩余持续时间（秒）
        self.last_water_tick = 0  # 上次浇水时间戳
        self.rain_water_added = False  # 本次下雨是否已增加水量

        # 雨滴粒子
        self.rain_drops = []
        self.rain_timer = 0  # 生成雨滴的计时器

        # 预创建雨滴 Surface 缓存
        self._init_rain_cache()

    def _init_rain_cache(self):
        """预创建雨滴 Surface 缓存"""
        for length in self.RAIN_LENGTHS:
            for alpha in [80, 120, 160, 200]:
                surface = pygame.Surface((1, length), pygame.SRCALPHA)
                color = (150, 180, 255, alpha)
                pygame.draw.line(surface, color, (0, 0), (0, length - 1), 1)
                self._rain_cache[(length, alpha)] = surface

    def _get_rain_surface(self, length: int, alpha: int):
        """获取缓存的雨滴 Surface"""
        # 找到最接近的长度
        closest_length = min(self.RAIN_LENGTHS, key=lambda x: abs(x - length))
        # 找到最接近的 alpha
        closest_alpha = min([80, 120, 160, 200], key=lambda x: abs(x - alpha))
        return self._rain_cache.get((closest_length, closest_alpha))

    def update(self, world):
        """更新天气状态"""
        now = time.time()

        # 检查是否需要变化天气
        if self.current_weather == self.WEATHER_SUNNY:
            if now - self.last_change_time >= self.change_interval:
                self.change_weather()
                self.last_change_time = now
        else:
            # 雨天：检查是否结束
            self.rain_duration -= (now - self.last_change_time)
            self.last_change_time = now
            if self.rain_duration <= 0:
                self.current_weather = self.WEATHER_SUNNY
                self.rain_water_added = False  # 重置标记

        # 雨天：增加水量（一次下雨只触发一次）
        if self.current_weather == self.WEATHER_RAINY and not self.rain_water_added:
            if hasattr(world, 'game_manager') and world.game_manager:
                world.game_manager.water += 200
                # 填充所有蓄水器（一次下雨只触发一次）
                self.fill_water_storages(world)
                self.rain_water_added = True

        # 雨天：每秒给作物浇水
        if self.current_weather == self.WEATHER_RAINY:
            if now - self.last_water_tick >= 1.0:
                self.auto_water_crops(world)
                self.last_water_tick = now

    def change_weather(self):
        """随机变化天气"""
        if random.random() < 0.3:  # 30%概率下雨
            self.current_weather = self.WEATHER_RAINY
            self.rain_duration = random.uniform(60, 180)  # 1-3分钟
            self.last_water_tick = time.time()
            self.rain_drops = []
            self.rain_water_added = False  # 重置水量增加标记
        else:
            self.current_weather = self.WEATHER_SUNNY

    def auto_water_crops(self, world):
        """雨天每秒给所有作物+1水分"""
        for crop in world.crop_list:
            if crop.current_stage < 3 and crop.type != 1:  # 水生不需要
                crop.water_level = min(100, crop.water_level + 1)

    def fill_water_storages(self, world):
        """填充所有蓄水器（一次下雨只触发一次）"""
        if not hasattr(world, 'furniture_list'):
            return
        from ..entities.furniture import Furniture
        for furniture in world.furniture_list:
            if furniture.furniture_id == "waterstorage" and hasattr(furniture, 'max_water'):
                furniture.water_stored = furniture.max_water
                print(f"蓄水器已填满: {furniture.water_stored}/{furniture.max_water}")
        # 清除缩放缓存，确保下次渲染使用正确的图片
        Furniture._scale_cache.clear()

    def update_rain_drops(self, screen_w, screen_h):
        """更新雨滴粒子（每帧调用）"""
        if self.current_weather != self.WEATHER_RAINY:
            self.rain_drops.clear()
            return

        # 生成新雨滴（不均匀分布）
        self.rain_timer += 1
        if self.rain_timer % 2 == 0:  # 每2帧生成一批
            # 随机生成几条雨滴，集中在某些区域
            cluster_x = random.randint(0, screen_w)
            for _ in range(random.randint(2, 5)):
                x = cluster_x + random.randint(-80, 80)
                y = random.randint(-20, -5)
                length = random.randint(8, 25)  # 随机长度
                speed = random.uniform(4, 10)   # 随机速度
                alpha = random.randint(100, 200)  # 随机透明度
                self.rain_drops.append({
                    "x": x, "y": y,
                    "length": length,
                    "speed": speed,
                    "alpha": alpha
                })

        # 更新雨滴位置
        for drop in self.rain_drops:
            drop["y"] += drop["speed"]

        # 移除超出屏幕的雨滴
        self.rain_drops = [d for d in self.rain_drops if d["y"] < screen_h + 20]

        # 限制雨滴数量
        if len(self.rain_drops) > 150:
            self.rain_drops = self.rain_drops[-150:]

    def render_rain(self, screen):
        """渲染雨滴"""
        if self.current_weather != self.WEATHER_RAINY:
            return

        for drop in self.rain_drops:
            x = int(drop["x"])
            y = int(drop["y"])
            length = drop["length"]
            alpha = drop["alpha"]

            # 使用缓存的雨滴 Surface
            rain_surface = self._get_rain_surface(length, alpha)
            if rain_surface:
                screen.blit(rain_surface, (x, y))

    def get_weather_name(self) -> str:
        return self.current_weather

    def get_save_data(self) -> dict:
        """获取存档数据"""
        return {
            "weather": self.current_weather,
            "last_change_time": self.last_change_time,
            "rain_duration": self.rain_duration,
            "rain_water_added": self.rain_water_added,
        }

    def load_save_data(self, data: dict):
        """加载存档数据"""
        self.current_weather = data.get("weather", self.WEATHER_SUNNY)
        self.last_change_time = data.get("last_change_time", time.time())
        self.rain_duration = data.get("rain_duration", 0)
        self.rain_water_added = data.get("rain_water_added", False)
        self.last_water_tick = time.time()
        self.rain_drops = []
