"""
批量去除图片右边细线
"""
import pygame
import os

pygame.init()
pygame.display.set_mode((1, 1))

folder = r"E:\CozyHome\temp\dog\roll"
remove_cols = 2  # 去除右边几列像素

files = sorted([f for f in os.listdir(folder) if f.endswith(".png")])
print(f"处理 {len(files)} 张图片，去除右边 {remove_cols} 列像素")

for fname in files:
    path = os.path.join(folder, fname)
    img = pygame.image.load(path).convert_alpha()
    w, h = img.get_size()

    # 把右边几列设为透明
    for x in range(w - remove_cols, w):
        for y in range(h):
            img.set_at((x, y), (0, 0, 0, 0))

    pygame.image.save(img, path)
    print(f"  {fname}")

print("完成!")
