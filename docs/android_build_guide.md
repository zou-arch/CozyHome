# Android APK 打包指南

## 前置条件

### 1. 安装 WSL（Windows Subsystem for Linux）

```powershell
# 在PowerShell中执行（管理员模式）
wsl --install
# 安装Ubuntu 22.04
```

### 2. 在WSL中安装依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y python3-pip python3-dev git zip unzip openjdk-17-jdk

# 安装buildozer
pip3 install buildozer

# 安装cython
pip3 install cython
```

## 打包步骤

### 1. 复制项目到WSL

```bash
# 将项目复制到WSL目录
cp -r /mnt/e/CozyHome ~/CozyHome
cd ~/CozyHome
```

### 2. 初始化buildozer（首次）

```bash
buildozer init
# 按照提示填写配置
```

### 3. 构建APK

```bash
# 调试版本（推荐先测试）
buildozer android debug

# 发布版本
buildozer android release
```

### 4. APK位置

构建完成后，APK文件在：
```
bin/cozyhome-0.1-debug.apk
```

## 触摸事件适配

项目已添加触摸事件支持：
- `FINGERDOWN` → 鼠标按下
- `FINGERMOTION` → 鼠标移动
- `FINGERUP` → 鼠标释放

## 注意事项

1. **首次构建较慢**：需要下载Android SDK/NDK，约2-3GB
2. **签名问题**：发布版本需要配置签名密钥
3. **性能优化**：移动端建议降低分辨率和帧率

## 常见问题

### 构建失败
```bash
# 清理构建缓存
buildozer android clean

# 检查依赖
sudo apt install -y build-essential
```

### 触摸不灵敏
调整 `input_handler.py` 中的触摸灵敏度参数。

### 内存不足
在buildozer.spec中降低分辨率：
```ini
android.arch = armeabi-v7a
```
