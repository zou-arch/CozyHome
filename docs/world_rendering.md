# 世界渲染系统

## 坐标系统

### 坐标转换链路
```
屏幕坐标 (screen_pos)
    ↓ camera.screen_to_world()
世界坐标 (world_pos)
    ↓ world.world_to_grid()
斜网格坐标 (grid_x, grid_y)
```

### 关键公式

**screen_to_world（与 coordinate_viewer 一致）**
```python
world_x = (screen_pos[0] - screen_width // 2) / zoom + camera.x
world_y = (screen_pos[1] - screen_height // 2) / zoom + camera.y
```

**world_to_screen（与 coordinate_viewer 一致）**
```python
screen_x = (world_pos[0] - camera.x) * zoom + screen_width // 2
screen_y = (world_pos[1] - camera.y) * zoom + screen_height // 2
```

**world_to_grid（返回浮点数，不取整）**
```python
# 使用 116°/244° 角度的逆变换矩阵
grid_x = M_inv[0][0] * x + M_inv[0][1] * y
grid_y = M_inv[1][0] * x + M_inv[1][1] * y
```

**grid_to_world**
```python
# 使用 116°/244° 角度的正变换矩阵
world_x = M[0][0] * grid_x + M[0][1] * grid_y
world_y = M[1][0] * grid_x + M[1][1] * grid_y
```

### 常量参数
- TILE_SPACING = 120
- TILE_WIDTH = 174（菱形水平半对角线）
- TILE_HEIGHT = 85（菱形垂直半对角线）
- 角度：ALPHA = 116°，BETA = 244°

### 取整规则
- world_to_grid 返回浮点数
- 需要整数区块坐标时使用 `math.floor()`（不是 `int()`）

## 区块顶点计算

```python
def get_tile_vertices(grid_x, grid_y):
    """获取区块的四个顶点"""
    corners = [
        self.grid_to_world(grid_x, grid_y),      # 左上
        self.grid_to_world(grid_x + 1, grid_y),  # 右上
        self.grid_to_world(grid_x + 1, grid_y + 1),  # 右下
        self.grid_to_world(grid_x, grid_y + 1),  # 左下
    ]
    return corners
```

## 区块类型

```python
TILE_FLOOR = 0   # 地板（已解锁）
TILE_FARM = 1    # 种植区（已解锁）
TILE_UNLOCKED = -1  # 未解锁
```

### 数据存储
- tile_map[y][x]：区块类型（0/1/-1）
- floor_styles[(x, y)]：地板样式索引（0/1/2）
- farm_styles[(x, y)]：种植区样式索引（0/1/2/3）

## 精灵图系统

### 加载流程
1. 加载原始 PNG 图片
2. 用 `_get_tile_pixel_size()` 计算区块实际像素尺寸
3. 根据缩放因子缩放：`smoothscale(img, (tile_w * scale, tile_h * scale))`
4. 用 `_get_diamond_bbox()` 裁剪透明边框 + 边缘羽化抗锯齿

### 精灵图对应关系

**地板（3种）**
| 索引 | 样式 | 文件 |
|------|------|------|
| 0 | 木地板 | F_floor_wood.png |
| 1 | 瓷砖 | F_floor_tile.png |
| 2 | 地毯 | F_floor_carpet.png |

**种植区（4种）**
| 索引 | 样式 | 文件 |
|------|------|------|
| 0 | 土生 | F_farm_soil.png |
| 1 | 水生 | F_farm_water.png |
| 2 | 盆栽 | F_farm_pot.png |
| 3 | 沙生 | F_farm_sand.png |

### 渲染流程
```
1. 获取区块顶点（get_tile_vertices）
2. 转换为屏幕坐标（camera.world_to_screen）
3. 根据 zoom 缩放精灵图（带缓存）
4. 创建临时 Surface
5. 绘制精灵图到临时 Surface
6. 用菱形遮罩裁剪（BLEND_RGBA_MULT）
7. 绘制到屏幕
```

### 菱形遮罩裁剪
```python
# 创建临时 Surface
temp = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
temp.blit(scaled_img, img_rect)

# 创建菱形遮罩
mask = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
pygame.draw.polygon(mask, (255, 255, 255, 255), screen_vertices_int)

# 用遮罩裁剪
temp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

# 绘制到屏幕
screen.blit(temp, (0, 0))
```

## 未解锁区域

- 覆盖颜色：黑色 (30, 30, 30, 200)
- 边框颜色：白色 (255, 255, 255)，线宽 2px
- 问号：白色，位于区块中心

## 渲染顺序

1. 绘制所有区块（已解锁=精灵图，未解锁=黑色覆盖）
2. 统一 blit overlay（未解锁区域）
3. 绘制未解锁区块的白色边框和问号
4. 渲染物体（家具、作物、宠物）
5. 渲染天气效果

## 性能优化

- overlay 缓存：复用同一个 Surface，避免每帧创建
- 精灵图缩放缓存：用 (id(img), zoom_int) 作为 key
- 缓存上限：50 个缩放结果
