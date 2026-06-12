# 渲染性能分析报告

## 发现的严重性能问题

### 1. crop.py - 每帧执行 smoothscale（严重）

**问题位置**：`src/entities/crop.py` render 方法（第317行）

```python
# 每帧都在执行，没有缓存！
scaled_sprite = pygame.transform.smoothscale(sprite, (sprite_w, sprite_h))
```

**影响**：
- `smoothscale` 是 CPU 密集型操作
- 每个作物每帧都执行一次
- 如果有 50 个作物，每帧执行 50 次 smoothscale

**修复建议**：
```python
# 在 Crop 类中添加缩放缓存
_sprite_scale_cache = {}  # {(crop_id, stage, zoom_int): scaled_surface}

@classmethod
def get_scaled_sprite(cls, crop_id, stage, zoom, scale):
    """获取缩放后的精灵图（带缓存）"""
    zoom_int = int(zoom * 100)
    cache_key = (crop_id, stage, zoom_int, int(scale * 100))
    
    if cache_key not in cls._sprite_scale_cache:
        sprites = cls._sprite_cache.get(crop_id, [])
        if stage < len(sprites) and sprites[stage] is not None:
            sprite = sprites[stage]
            target_w = int(40 * zoom * scale)
            sprite_ratio = sprite.get_height() / sprite.get_width()
            sprite_w = max(1, target_w)
            sprite_h = max(1, int(sprite_w * sprite_ratio))
            cls._sprite_scale_cache[cache_key] = pygame.transform.smoothscale(sprite, (sprite_w, sprite_h))
    
    return cls._sprite_scale_cache.get(cache_key)
```

---

### 2. furniture.py - 每帧执行 transform.scale（严重）

**问题位置**：`src/entities/furniture.py` _render_wall_surface、_render_wall_mount、_render_ground 方法

```python
# 每帧都在执行，没有缓存！
render_img = pygame.transform.scale(render_img, (scaled_w, scaled_h))
```

**影响**：
- 每个家具每帧都执行一次 scale
- 如果有 30 个家具，每帧执行 30 次 scale

**修复建议**：
```python
# 在 Furniture 类中添加缩放缓存
_scale_cache = {}  # {(furniture_id, zoom_int, is_flipped): scaled_surface}

@classmethod
def get_scaled_image(cls, furniture_id, zoom, is_flipped):
    """获取缩放后的图片（带缓存）"""
    zoom_int = int(zoom * 100)
    cache_key = (furniture_id, zoom_int, is_flipped)
    
    if cache_key not in cls._scale_cache:
        img = cls._images.get(furniture_id)
        if img:
            render_img = img if not is_flipped else pygame.transform.flip(img, True, False)
            img_w, img_h = img.get_size()
            extra_scale = cls.get_extra_scale(furniture_id)
            total_scale = cls.SCALE * extra_scale
            scaled_w = int(img_w * zoom * total_scale)
            scaled_h = int(img_h * zoom * total_scale)
            cls._scale_cache[cache_key] = pygame.transform.scale(render_img, (scaled_w, scaled_h))
    
    return cls._scale_cache.get(cache_key)
```

---

### 3. world.py - 每帧创建临时 Surface（中等）

**问题位置**：`src/core/world.py` render 方法（第945-952行）

```python
# 每个区块每帧都创建两个 Surface！
temp = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
mask = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
```

**影响**：
- 创建 `SRCALPHA` Surface 非常耗时
- 每帧创建 2 × 可见区块数 个 Surface
- 如果可见 20 个区块，每帧创建 40 个 Surface

**修复建议**：
```python
# 在 __init__ 中预创建
self._temp_surface = None
self._mask_surface = None

# 在 render 中复用
if self._temp_surface is None or self._temp_surface.get_size() != (screen_w, screen_h):
    self._temp_surface = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    self._mask_surface = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)

# 渲染时清空复用
self._temp_surface.fill((0, 0, 0, 0))
self._mask_surface.fill((0, 0, 0, 0))
```

---

### 4. ui.py - 多处 smoothscale 无缓存（中等）

**问题位置**：多处

```python
# 第154行
self.seed_previews[crop_id] = pygame.transform.smoothscale(img, (preview_size, preview_size))

# 第164行
self.harvest_previews[crop_id] = pygame.transform.smoothscale(img, (preview_size, preview_size))

# 第406行
preview = pygame.transform.smoothscale(img, (preview_size, preview_size))

# 第1821行
small_icon = pygame.transform.smoothscale(crop_icon, (small_icon_size, small_icon_size))

# 第1930行
mini_coin = pygame.transform.smoothscale(self.ui_icons["coin"], (mini_size, mini_size))

# 第2084行
preview = pygame.transform.scale(img, (scaled_w, scaled_h))

# 第2197行
scaled_bg = pygame.transform.smoothscale(self.bag_background, (panel_w, panel_h))

# 第2208行
close_icon = pygame.transform.smoothscale(close_icon, (close_size, close_size))

# 第2297行
scaled = pygame.transform.smoothscale(preview, (icon_size, icon_size))

# 第2357行
big_icon = pygame.transform.smoothscale(preview, (icon_size, icon_size))

# 第2482行
scaled_bg = pygame.transform.smoothscale(self.fsm_background, (new_w, new_h))

# 第2485行
scaled_bg = pygame.transform.smoothscale(self.bag_background, (panel_w, panel_h))

# 第2496行
close_icon = pygame.transform.smoothscale(close_icon, (close_size, close_size))

# 第2584行
scaled = pygame.transform.smoothscale(preview, (icon_size, icon_size))

# 第2797行
scaled_preview = pygame.transform.smoothscale(preview_img, (preview_size, preview_size))

# 第2865行
scaled = pygame.transform.smoothscale(preview, (preview_size, preview_size))

# 第2885行
icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
```

**影响**：
- UI 渲染时多次执行 smoothscale
- 虽然不是每帧都执行（只在打开菜单时），但仍然影响性能

**修复建议**：
```python
# 在 UI 类中添加预览缓存
_preview_cache = {}  # {(crop_id, size): scaled_surface}

def get_crop_preview(self, crop_id, size):
    """获取作物预览图（带缓存）"""
    cache_key = (crop_id, size)
    if cache_key not in self._preview_cache:
        seed_path = os.path.join(sprites_dir, f"{crop_id}_stage0.png")
        if os.path.exists(seed_path):
            img = pygame.image.load(seed_path).convert_alpha()
            self._preview_cache[cache_key] = pygame.transform.smoothscale(img, (size, size))
    return self._preview_cache.get(cache_key)
```

---

## 性能影响排序

| 问题 | 严重程度 | 每帧调用次数 | 修复难度 |
|------|----------|--------------|----------|
| crop.py smoothscale | 严重 | 作物数量 × 1 | 简单 |
| furniture.py scale | 严重 | 家具数量 × 1 | 简单 |
| world.py 临时 Surface | 中等 | 可见区块数 × 2 | 简单 |
| ui.py smoothscale | 中等 | 打开菜单时多次 | 中等 |

---

## 预期性能提升

如果修复所有问题：
- **crop.py**：减少 50-80% 的 smoothscale 调用
- **furniture.py**：减少 50-80% 的 scale 调用
- **world.py**：减少 90% 的 Surface 创建
- **ui.py**：减少 70% 的 smoothscale 调用

**总体预期**：FPS 提升 30-50%

---

## 实施优先级

1. **高优先级**：修复 crop.py 和 furniture.py 的缩放缓存
2. **中优先级**：修复 world.py 的临时 Surface 复用
3. **低优先级**：修复 ui.py 的预览缓存

---

## 已完成的修复

### 1. crop.py 缩放缓存（已完成）

**修复内容**：
- 添加 `_sprite_scale_cache` 字典缓存缩放后的精灵图
- 添加 `get_scaled_sprite()` 类方法获取缩放后的精灵图（带缓存）
- 修改 `render()` 方法使用缓存
- 修改枯萎覆盖使用缓存
- 修改高亮覆盖使用缓存

**缓存键**：`(crop_id, stage, zoom_int, scale_int)`

### 2. furniture.py 缩放缓存（已完成）

**修复内容**：
- 添加 `_scale_cache` 字典缓存缩放后的图片
- 添加 `get_scaled_image()` 类方法获取缩放后的图片（带缓存）
- 修改 `_render_wall_surface()` 方法使用缓存
- 修改 `_render_wall_mount()` 方法使用缓存
- 修改 `_render_ground()` 方法使用缓存（支持开灯状态）

**缓存键**：`(furniture_id, zoom_int, is_flipped, is_light_on)`

### 3. world.py 临时 Surface 复用（已完成）

**修复内容**：
- 添加 `_temp_surface`、`_mask_surface`、`_temp_surface_size` 变量
- 修改 `render()` 方法复用临时 Surface
- 清空并复用 Surface，而不是每帧创建新的

### 4. ui.py 预览缓存（已完成）

**修复内容**：
- 添加 `_crop_info_cache` 字典缓存作物信息预览
- 添加 `_placing_preview_cache` 字典缓存家具放置预览
- 修改 `render_crop_info_top_bar()` 方法使用缓存
- 修改 `render_placing_furniture_preview()` 方法使用缓存

---

## 验证方法

修复后，可以通过以下方式验证：
1. 在渲染循环中添加计时器，统计 smoothscale/scale 调用次数
2. 使用 `pygame.time.Clock()` 监控 FPS
3. 检查内存使用是否降低（Surface 创建减少）
