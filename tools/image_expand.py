"""
图片画布扩图工具
为图片四周添加透明边距，可复用
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog
from PIL import Image


def expand_image(input_path, output_path=None, padding_percent=20):
    """扩图：四周添加透明边距

    Args:
        input_path: 输入图片路径
        output_path: 输出路径，None 则覆盖原图
        padding_percent: 四周边距占原图尺寸的百分比，默认 20%
    """
    img = Image.open(input_path).convert('RGBA')
    w, h = img.size

    pad_x = int(w * padding_percent / 100)
    pad_y = int(h * padding_percent / 100)
    new_w = w + pad_x * 2
    new_h = h + pad_y * 2

    new_img = Image.new('RGBA', (new_w, new_h), (0, 0, 0, 0))
    new_img.paste(img, (pad_x, pad_y))

    save_path = output_path or input_path
    new_img.save(save_path)
    print(f"{os.path.basename(input_path)}: {w}x{h} -> {new_w}x{new_h} (+{padding_percent}%)")
    return save_path


def expand_folder(folder_path, padding_percent=20):
    """批量扩图：处理文件夹内所有 png"""
    for fname in os.listdir(folder_path):
        if fname.lower().endswith('.png'):
            expand_image(os.path.join(folder_path, fname), padding_percent=padding_percent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    print("选择方式：")
    print("  1 - 选择单张图片")
    print("  2 - 选择文件夹批量处理")
    choice = input("输入 1 或 2: ").strip()

    if choice == "1":
        path = filedialog.askopenfilename(title="选择图片", filetypes=[("PNG", "*.png")])
        if path:
            pct = input("边距百分比 (默认20): ").strip()
            expand_image(path, padding_percent=int(pct) if pct else 20)
    elif choice == "2":
        path = filedialog.askdirectory(title="选择文件夹")
        if path:
            pct = input("边距百分比 (默认20): ").strip()
            expand_folder(path, padding_percent=int(pct) if pct else 20)

    input("按回车退出...")
