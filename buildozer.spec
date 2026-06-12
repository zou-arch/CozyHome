[app]

# App基本信息
title = 2.5D温馨小屋
package.name = cozyhome
package.domain = org.cozyhome

# 源代码目录
source.dir = .
# 需要打包到apk里的文件扩展名类型
source.include_exts = py,png,jpg,kv,atlas,json,mp3,ogg,ttf
# 需要打包到apk里的资源目录及子目录（关键！遗漏会导致资源缺失）
source.include_patterns = assets/*,data/*,fonts/*

# 版本
version = 0.1.0

# 依赖
requirements = python3,pygame

# Android配置
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE
android.api = 31
android.minapi = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

# 应用配置
fullscreen = 0
orientation = landscape
# icon 和 presplash 暂时禁用（文件不存在会导致构建失败）
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png

# 构建配置
android.ndk = 25b
android.gradle_dependencies =

# 日志级别
log_level = 2
