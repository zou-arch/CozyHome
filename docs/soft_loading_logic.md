# 软化加载逻辑文档

## 概述

软化加载逻辑允许游戏动态发现和加载资源，无需在代码中硬编码。只需将图片放入对应目录，游戏启动时会自动识别并加载。

---

## 植物 (Crop) 加载逻辑

### 目录结构

```
assets/sprites/crops/
├── tomato_stage0.png
├── tomato_stage1.png
├── tomato_stage2.png
├── tomato_stage3.png
├── carrot_stage0.png
└── ...
```

### 识别规则

1. **扫描目录**: 扫描 `assets/sprites/crops/` 中所有 `.png` 文件
2. **识别模式**: 查找 `xxx_stage0.png` 文件
3. **完整性检查**: 必须同时存在 `stage0`, `stage1`, `stage2`, `stage3` 四个文件
4. **自动注册**: 4个状态都完整时，自动添加到植物列表

### 元数据来源

从 `data/furniture_configs.json` 读取：

```json
{
  "putap": {
    "file_type": "crop",
    "name_cn": "葡萄",
    "crop_type": "soil",
    "growth_time": 2.0,
    "sell_price": 15,
    "seed_price": 8,
    "water_rate": 8
  }
}
```

### 字段说明

| 字段 | 说明 | 可选值 |
|------|------|--------|
| `crop_type` | 种植类型 | `soil`(土生), `water`(水生), `pot`(盆栽), `sand`(沙生) |
| `growth_time` | 生长时间(小时) | 数字 |
| `sell_price` | 售价 | 数字 |
| `seed_price` | 种子价格 | 数字 |
| `water_rate` | 水分消耗/小时 | 数字，0=永久湿润 |

### 降级处理

如果 `furniture_configs.json` 中没有配置，使用默认值：
- `crop_type`: 0 (土生)
- `growth_time`: 1.5 小时
- `sell_price`: 10
- `seed_price`: 5
- `water_rate`: 8

---

## 家具 (Furniture) 加载逻辑

### 目录结构

```
assets/sprites/furniture/
├── bed.png
├── bed_turn_on.png  (可选，开灯状态)
├── floor_lamp.png
├── floor_lamp_turn_on.png
├── sofa.png
└── ...
```

### 识别规则

1. **扫描目录**: 扫描 `assets/sprites/furniture/` 中所有 `.png` 文件
2. **排除规则**: 跳过 `_turn_on.png` 和 `F_floor_` 前缀的文件
3. **自动注册**: 发现新图片时，自动添加到家具列表

### 元数据来源

从 `data/furniture_configs.json` 读取：

```json
{
  "my_furniture": {
    "file_type": "furniture",
    "name_cn": "我的家具",
    "category": "ground",
    "scale": 0.1,
    "extra_scale": 1.0,
    "height": 0,
    "is_wall": false,
    "no_collision": false,
    "is_light": false
  }
}
```

### 字段说明

| 字段 | 说明 | 可选值 |
|------|------|--------|
| `category` | 家具类型 | `ground`(地面), `surface`(可放置), `surface_wall`(面+墙), `wall_surface`(墙面), `wall_mount`(墙挂) |
| `scale` | 基础缩放 | 数字，默认 0.1 |
| `extra_scale` | 额外缩放 | 数字，默认 1.0 |
| `height` | 高度(Z轴) | 数字 |
| `is_wall` | 是否墙壁 | true/false |
| `no_collision` | 无碰撞 | true/false |
| `is_light` | 是光源 | true/false |

### 降级处理

如果 `furniture_configs.json` 中没有配置，使用默认值：
- `category`: ground
- `scale`: 0.1
- `extra_scale`: 1.0
- `is_light`: false

---

## 宠物 (Pet) 加载逻辑

### 目录结构

**新格式（推荐）：**
```
assets/sprites/pets/
├── golden_retriever/
│   ├── idle/
│   │   ├── screenshot_001.png
│   │   └── ...
│   ├── walk/
│   │   └── ...
│   └── hungry/
│       └── ...
└── ...
```

**旧格式（兼容）：**
```
assets/sprites/pets/
├── blue_cat_idle_0.png
├── blue_cat_idle_1.png
└── ...
```

### 识别规则

1. **扫描目录**: 扫描 `assets/sprites/pets/` 中的所有项目
2. **子目录识别**: 发现子目录 → 识别为宠物
3. **文件识别**: 发现 `_idle_0.png` 文件 → 识别为宠物
4. **配置检查**: 必须在 `pet_config.json` 中有完整配置

### 元数据来源

从 `data/pet_config.json` 读取（**必须包含 level_unlocks**）：

```json
{
  "my_pet": {
    "states": ["idle", "walk", "hungry"],
    "level_unlocks": {
      0: ["idle", "walk"],
      2: ["hungry"]
    },
    "state_config": {
      "idle": {"fps": 6, "loop": true, "offset_x": 0, "offset_y": 0, "scale": 1.0},
      "walk": {"fps": 8, "loop": true, "offset_x": 0, "offset_y": 0, "scale": 1.0},
      "hungry": {"fps": 6, "loop": false, "offset_x": 0, "offset_y": 0, "scale": 1.0}
    }
  }
}
```

### 必要字段

| 字段 | 说明 | 是否必须 |
|------|------|----------|
| `states` | 可用状态列表 | **必须** |
| `level_unlocks` | 等级解锁配置 | **必须** |
| `state_config` | 各状态配置 | 可选（有默认值） |

### state_config 字段说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `fps` | 帧率 | 8 |
| `loop` | 是否循环 | true |
| `loop_start` | 循环起始帧 | 0 |
| `offset_x` | X偏移 | 0 |
| `offset_y` | Y偏移 | 0 |
| `scale` | 缩放 | 1.0 |

### 降级处理

**不支持降级**：如果缺少 `states` 或 `level_unlocks`，该宠物不会被加载。

---

## 编辑器使用流程

### 1. 导入图片

将图片放入 `temp/` 目录，运行 `furniture_editor.py`：

```bash
python tools/furniture_editor.py
```

编辑器会自动检测文件类型并分类。

### 2. 编辑配置

在右侧配置面板：

1. **选择文件类型**: 点击「文件类型」字段切换
2. **填写元数据**: 根据类型填写对应字段
3. **保存配置**: 点击「保存配置」按钮

### 3. 不同类型的配置面板

**家具类型：**
- 家具类型 (ground/surface/wall_mount...)
- 缩放因子
- 额外缩放
- 高度(Z)
- 是墙壁/无碰撞/是光源

**植物类型：**
- 种植类型 (soil/water/pot/sand)
- 生长时间
- 售价/种子价格
- 水分消耗

**宠物类型：**
- 可用状态 (逗号分隔)
- 等级解锁 (格式: `0:idle,walk;2:hungry`)

### 4. 保存到游戏

配置保存在 `data/furniture_configs.json`，游戏启动时会自动读取。

---

## 数据流

```
图片文件 → 编辑器检测 → 填写配置 → 保存 JSON
                                        ↓
                              furniture_configs.json
                                        ↓
游戏启动 → 扫描目录 → 读取配置 → 动态注册 → 加载图片
```

---

## 注意事项

1. **植物必须4阶段完整**: 只有 stage0-3 都存在的植物才会被加载
2. **宠物必须配置完整**: 缺少 `level_unlocks` 的宠物不会被加载
3. **家具自动识别**: 只要图片存在就会被加载，配置可选
4. **配置优先级**: JSON 配置 > 默认值 > 硬编码值
5. **缓存机制**: 图片和配置都有缓存，修改后需要重启游戏
