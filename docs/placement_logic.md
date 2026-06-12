# 放置逻辑与鼠标输入规范

## 一、物体类型定义

| 类型 | 说明 | 碰撞数据 | 家具 |
|------|------|----------|------|
| ground | 纯地面家具 | footprint | lamp, tv, piano, floor_lamp, storage_basket, table, table_lamp |
| surface | 可放置平面 | footprint + placeable_areas | bed, chair, coffee_table, desk, flower_stand, sofa |
| surface_wall | 可放置+可挂 | footprint + placeable_areas + wall_surfaces | bookshelf, wardrobe |
| wall_surface | 墙面（系统预设） | wall_surfaces | wall |
| wall_mount | 挂饰类 | footprint + wall_surfaces | painting, wall_shelf, wall_lamp, clock |
| rug | 纯装饰地板 | 无（任意放置） | rug |

### 类型行为规则

| 类型 | 可放在地面 | 可挂在墙上 | 可承载其他物品 |
|------|:----------:|:----------:|:--------------:|
| ground | ✅ | ❌ | ❌ |
| surface | ✅ | ❌ | ✅（placeable_areas） |
| surface_wall | ✅ | ✅（自身作为 wall_surface） | ✅（placeable_areas） |
| wall_surface | — | — | ✅（wall_surfaces） |
| wall_mount | ❌ | ✅ | ❌ |

---

## 二、碰撞检测方法

### 2.1 地面放置检测

**方法：** `check_ground_placement(obj, new_x, new_y, other_objects)`

**逻辑：**
1. 计算 obj 在 (new_x, new_y) 处的 footprint 多边形
2. 遍历 all_objects，跳过以下对象：
   - obj 自身
   - 无 furniture_id 的对象（Crop、Pet 等）
   - obj_type 为 wall_mount 的对象（墙挂不参与地面碰撞）
3. 计算 obj footprint 与每个 other 的 footprint 交集面积
4. 重叠比例 = 交集面积 / min(obj面积, other面积)
5. 重叠比例 > 15%（OVERLAP_THRESHOLD）→ 返回 True（有碰撞，禁止放置）

**返回值：** True = 有碰撞，False = 无碰撞

### 2.2 墙面放置检测

**方法：** `check_wall_mount_placement(obj, new_x, new_y, other_objects)`

**逻辑：**
1. 计算 obj 在 (new_x, new_y) 处的 footprint 多边形
2. 计算 footprint 中心点
3. 遍历 all_objects，找到 obj_type 为 wall_surface 的对象
4. 对每个 wall_surface，检查：
   a. 墙挂中心点是否在 wall_surface 的 wall_surfaces 多边形内
   b. 墙挂 footprint 与 wall_surface 区域的重叠比例 >= 70%
5. 两项都满足 → 返回 True（合法放置）
6. 所有 wall_surface 都不满足 → 返回 False（禁止放置）

**注意：** 此方法不检测与其他 wall_mount 的重叠，需额外调用 check_ground_placement 检测。

### 2.3 表面放置检测

**方法：** `check_item_on_surface(item, surface_obj, area_name=None)`

**逻辑：**
1. 获取 surface_obj 的 placeable_areas
2. 计算 item 的 footprint 中心点
3. 遍历每个 area：
   a. 检查 item 中心点是否在 area 的 points 多边形内
   b. 计算 item footprint 与 area 的重叠比例
   c. 重叠比例 >= 90% → 返回 True（合法放置）
4. 所有 area 都不满足 → 返回 False

**方法：** `check_item_collision_on_surface(item, surface_obj, area_name, other_items)`

**逻辑：**
1. 遍历 other_items（同表面上的其他物品）
2. 计算 item 与每个 other 的 footprint 重叠
3. 重叠比例 > 15% → 返回 True（有碰撞）

### 2.4 辅助方法

| 方法 | 说明 |
|------|------|
| `get_surface_under_point(point, all_objects)` | 检测指定位置下方是否有 surface/surface_wall 类型家具 |
| `point_in_wall_surface(obj, point)` | 检测点是否在 obj 的 wall_surfaces 区域内 |
| `point_in_placeable_area(obj, point)` | 检测点是否在 obj 的 placeable_areas 区域内 |
| `check_surface_items_collision(item, surface_obj, area_name, all_objects)` | 检测物品在表面上与其他物品的碰撞 |

---

## 三、放置流程

### 3.1 统一入口

**方法：** `can_place(obj, new_x, new_y, all_objects, surface_obj=None, area_name=None, items_on_surface=None)`

**流程：**
```
can_place(obj, new_x, new_y, all_objects, surface_obj, area_name, items_on_surface)
    ↓
判断 obj_type：
    ├── wall_surface → 返回 False（不可由玩家放置）
    │
    ├── wall_mount → 调用 check_wall_mount_placement
    │
    ├── surface_wall
    │   ├── 指定了 surface_obj → 按表面放置检测
    │   └── 未指定 → 按地面放置检测
    │
    ├── surface（指定了 surface_obj）
    │   ├── check_item_on_surface → 不通过则禁止
    │   ├── check_item_collision_on_surface → 不通过则禁止
    │   └── 通过 → 返回 True
    │
    └── ground / surface（未指定 surface_obj）
        └── check_ground_placement → 有碰撞则禁止
```

### 3.2 拖拽放置（end_drag）

**方法：** `furniture.end_drag(collision_system, all_objects)`

**流程：**
```
end_drag(obj, collision_system, all_objects)
    ↓
    is_dragging = False
    ↓
    计算 obj 中心点 center = (x + width/2, y + height/2)
    ↓
    判断 obj_type：
    │
    ├── wall_mount
    │   └── check_wall_mount_placement(obj, x, y, all_objects)
    │       ├── 不合法 → 恢复 drag_start_pos
    │       └── 合法 → 保持新位置
    │
    ├── surface / surface_wall
    │   ├── get_surface_under_point(center, all_objects)
    │   │   ├── 返回 surface_obj（落在表面上）
    │   │   │   ├── check_item_on_surface → 不通过则恢复
    │   │   │   ├── check_surface_items_collision → 不通过则恢复
    │   │   │   └── 都通过 → 保持新位置
    │   │   │
    │   │   └── 返回 None（落在地面上）
    │   │       └── check_ground_placement → 有碰撞则恢复
    │   │
    │   └── （不区分 surface_wall 的挂墙场景，拖拽放置仅处理地面和表面）
    │
    └── ground
        └── check_ground_placement(obj, x, y, all_objects)
            ├── 有碰撞 → 恢复 drag_start_pos
            └── 无碰撞 → 保持新位置
```

**恢复逻辑：** 任何碰撞检测失败时，将 x/y 恢复为 drag_start_pos（拖拽开始时记录的原始位置）。

---

## 四、鼠标输入逻辑

### 4.1 事件分层

```
鼠标事件
    ↓
InputHandler.handle_event(event)
    ├── 检查 UI 区域（is_ui_area）
    │   ├── 在 UI 区域 → ui.handle_click → 返回
    │   └── 不在 UI 区域 → 继续
    ├── 鼠标按下 → 记录状态
    ├── 鼠标移动 → 处理拖拽
    └── 鼠标释放 → 判断点击或结束拖拽
```

### 4.2 UI 区域判定

**方法：** `ui.is_ui_area(screen_pos)`

```
screen_pos (x, y)
    ├── y < 30  → 顶部状态栏（UI区域）
    ├── y > 240 → 底部按钮栏（UI区域）
    └── 其他    → 非UI区域
```

### 4.3 鼠标按下

```
左键按下
    ├── 在 UI 区域内 → 处理按钮点击，不启动拖拽
    ├── 有菜单打开 → 处理菜单点击
    └── 其他 → 记录按下时间，准备拖拽
```

### 4.4 鼠标移动（触发拖拽）

```
移动距离 > 10 像素
    ↓
设置 is_dragging = True
    ↓
判断拖拽类型：
    ├── 长按（>0.5秒）→ 摄像头拖拽
    └── 短按 + 编辑模式 + 有选中物体 → 物体拖拽
        ├── 不满足条件 → 取消拖拽（is_dragging = False）
```

### 4.5 鼠标移动（执行拖拽）

```
if is_dragging:
    ├── is_long_press = True → 更新摄像头位置
    └── is_long_press = False + 编辑模式 + 有选中物体
        ├── 计算新位置 = 鼠标位置 + drag_offset
        ├── 根据 obj_type 检测碰撞：
        │   ├── wall_mount → check_wall_mount_placement
        │   ├── surface/surface_wall → get_surface_under_point 判断场景
        │   │   ├── 在表面上 → check_item_on_surface + check_surface_items_collision
        │   │   └── 在地面上 → check_ground_placement
        │   └── ground → check_ground_placement
        ├── 无碰撞 → 更新物体位置
        └── 有碰撞 → 不更新（保持原位，继续跟随鼠标）
```

### 4.6 鼠标释放

```
左键释放
    ├── click_handled = True → 已处理过，忽略
    ├── 有菜单打开 → 忽略
    ├── is_dragging = True → 结束拖拽
    │   ├── is_long_press → 结束摄像头拖拽（camera.end_drag）
    │   └── 非长按 → 结束物体拖拽（furniture.end_drag）
    │       └── 最终碰撞检测，不合法则恢复原位
    └── is_dragging = False → 点按交互
        ├── 计算按压时长
        └── 调用 handle_click
```

### 4.7 点击交互（handle_click）

```
handle_click(screen_pos, press_duration)
    ↓
    world_pos = camera.screen_to_world(screen_pos)
    ↓
    取消当前选中（deselect_all）
    ↓
    按优先级检测点击目标：
    │
    ├── 1. 作物（get_object_at_pos）
    │   ├── 成熟（stage=3）→ 收获
    │   └── 未成熟 → 选中 + 显示操作菜单
    │
    ├── 2. 地块（world_to_grid + get_tile_type）
    │   ├── 编辑模式 + select 工具 → 切换地板/种植区样式
    │   ├── 普通模式 + 种植区 → 种植/操作
    │   └── 其他 → 不处理
    │
    ├── 3. 家具（get_object_at_pos）
    │   ├── 编辑模式 → 选中（可拖拽）
    │   │   ├── remove 工具 → 收回到仓库
    │   │   ├── flip 工具 → 镜像翻转
    │   │   └── select/move 工具 → 仅选中，拖拽由 update 处理
    │   └── 普通模式 → 触发交互（开灯/弹琴等）
    │
    └── 4. 空地 → 取消选中
```

---

## 五、编辑模式工具

### 5.1 工具列表

| 工具 | 功能 | 点击行为 |
|------|------|----------|
| select | 选中家具 | 选中后可拖拽 |
| move | 移动家具 | 选中后可拖拽 |
| place | 放置家具 | 打开家具选择菜单 |
| remove | 收回家具 | 点击家具收回到仓库 |
| flip | 翻转家具 | 点击家具镜像翻转 |

### 5.2 UI 布局

- **底部栏替换：** 进入编辑模式后，底部栏的7个常规按钮替换为5个编辑工具按钮（居中排列）
- **顶部提示：** 状态栏下方显示当前工具的操作提示文字
- **工具栏按钮：** 48x25 像素，居中排列，间距 6 像素

---

## 六、碰撞检测方法对照表

| 场景 | 方法 | 返回值 | 说明 |
|------|------|--------|------|
| 地面放置 | `check_ground_placement(obj, x, y, others)` | True=有碰撞 | 检测 footprint 重叠，跳过 wall_mount |
| 墙面放置 | `check_wall_mount_placement(obj, x, y, others)` | True=合法 | 中心点在 wall_surface 内 + 70%重叠 |
| 表面放置 | `check_item_on_surface(item, surface, area)` | True=合法 | 中心点在 area 内 + 90%重叠 |
| 表面碰撞 | `check_item_collision_on_surface(item, surface, area, others)` | True=有碰撞 | 检测同区域物品 footprint 重叠 |
| 统一入口 | `can_place(obj, x, y, all, surface, area, items)` | True=合法 | 根据 obj_type 自动选择检测方法 |
| 表面定位 | `get_surface_under_point(point, all)` | surface/None | 检测位置下方的 surface 类型家具 |
| 墙面区域 | `point_in_wall_surface(obj, point)` | True/False | 点是否在 wall_surfaces 内 |
| 表面区域 | `point_in_placeable_area(obj, point)` | True/False | 点是否在 placeable_areas 内 |
| 表面碰撞 | `check_surface_items_collision(item, surface, area, all)` | True=有碰撞 | 检测表面物品碰撞，排除宿主 |
| 底部Y | `get_footprint_bottom_y(obj)` | float | 获取 footprint 最底部 Y 坐标（渲染排序用） |

---

## 七、渲染排序

```
第零层：地毯（rug）— 纯装饰，无碰撞，始终在最底层
    └── 按 footprint 底部 Y 排序
第一层：墙面物体（wall_surface + wall_mount）
    └── 按 Y 坐标排序
第二层：地面物体（ground + surface + surface_wall + crop + pet）
    └── 按 footprint 底部 Y 坐标排序（get_footprint_bottom_y）
```

---

## 八、数据文件格式

### footprints.json
```json
{
  "bed": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
  "chair": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
}
```

### wall_surfaces.json
```json
{
  "wall": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
  "bookshelf": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
}
```

### placeable_areas.json
```json
{
  "bed": [
    {"name": "area_0", "points": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]}
  ],
  "flower_stand": [
    {"name": "area_0", "points": [...]},
    {"name": "area_1", "points": [...]},
    {"name": "area_2", "points": [...]}
  ]
}
```

---

## 九、关键阈值

| 参数 | 值 | 说明 |
|------|-----|------|
| OVERLAP_THRESHOLD | 15% | 地面/表面物品碰撞判定阈值 |
| 墙挂区域重叠 | 70% | wall_mount 必须有 70% 在 wall_surface 内 |
| 表面放置重叠 | 90% | 物品必须有 90% 在 placeable_area 内 |
| 拖拽触发距离 | 10px | 移动超过 10 像素才触发拖拽 |
| 长按判定时间 | 0.5s | 按住超过 0.5 秒判定为长按（镜头拖拽） |

---

## 十、重要注意事项

### 10.1 精灵图缩放

- `Furniture.SCALE = 0.05`，所有精灵图加载时缩放到原始尺寸的 5%
- `load_all_images()` 加载后同步更新 `FURNITURE_DATA` 中的 width/height
- **修改 SCALE 后无需改 JSON 数据**，碰撞系统和渲染会自动读取 SCALE

### 10.2 Footprint 坐标空间

- **编辑器保存的是原始精灵图像素坐标**（相对精灵图左上角 0,0）
- 碰撞系统和渲染中使用时需乘以 `SCALE` 转换到游戏世界坐标
- rug 没有 footprint（可放在任意位置）

### 10.3 编辑模式行为

- 选中家具：只显示像素级高光（黄色半透明覆盖），不显示矩形边框
- 放置预览：用 footprint 多边形画绿色边框，不是矩形
- 放置后的新家具 `_show_edit_footprint = False`，不显示 footprint
- 点击检测：像素级 alpha 检查（`is_clicked_at`），不是矩形碰撞

### 10.4 点击检测 vs 碰撞检测

- **点击选择**：用精灵图 alpha 通道做像素级检测（`is_clicked_at`）
- **放置/碰撞**：用 footprint、wall_surfaces、placeable_areas 做多边形重叠检测
- 两套系统独立，footprint 数据只用于碰撞，不用于点击判定

### 10.5 已修复的已知问题

- end_drag 现在按物体类型分别检测（wall_mount/surface/ground）
- surface/surface_wall 拖拽结束时会判断是否落在表面上
- 新放置的家具不会触发 edit mode footprint 高光
