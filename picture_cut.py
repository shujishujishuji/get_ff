import sys
from pathlib import Path

# ライブラリのパス
sys.path.append('/usr/local/lib/python3.7/site-packages')

import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class ImageProcessing():
    """画像加工のクラス
    """
    # 画像から輪郭画像を作成
    def find_edge(self, img_path: str):
        img = cv2.imread(img_path, 0)
        blur = cv2.blur(img, (5, 5))
        edges = cv2.Canny(blur, 100, 200)
        return edges

    # 対象の切り取り範囲を取得
    def find_target(self, edges):
        results = np.where(edges == 255)
        top = np.min(results[0])
        bottom = np.max(results[0]) - 1
        left = np.min(results[1])
        right = np.max(results[1]) - 1
        return (left, top, right, bottom)

    # RGB画像に変換
    def to_RGB(self, image: Image):
        if image.mode == 'RGB':
            return image
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
        background.format = image.format
        return background

    # 対象物を背景からトリミング
    def get_crop_img(self, img_path: str):
        edges = self.find_edge(img_path)
        left, top, right, bottom = self.find_target(edges)
        rgb_img = self.to_RGB(Image.open(img_path))
        trim_img = rgb_img.crop((left, top, right, bottom))
        return trim_img

    # cv2で画像表示
    def show_img(self, img):
        cv2.imshow('image', img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # 画像のサイズを取得
    def pic_size(self, img):
        pic_size = img.size[0] * img.size[1]
        return pic_size

    # 画像にテキストを挿入
    def add_txt(self, img_path, txt):
        # 画像の読み込み
        img = Image.open(img_path)

        # 外枠の追加
        top, left, right, bottom = 10, 10, 10, 80
        width, height = img.size
        new_w = width + right + left
        new_h = height + top + bottom
        result = Image.new(img.mode, (new_w, new_h), (0, 0, 0))
        result.paste(img, (left, top))

        # テキストの追加
        draw = ImageDraw.Draw(result)
        font = ImageFont.truetype('~/Library/Fonts/Oranienbaum.ttf', 68)
        w, h = draw.textsize(txt, font=font)
        draw.text(((new_w - w) / 2, (height + top)), text=txt, font=font, fill=(255, 255, 255))
        result.save(img_path)


def main():
    ip = ImageProcessing()
    txt = 'bname'
    dir_lis = [f for f in os.listdir('出品') if os.path.isdir(os.path.join('出品', f))]
    for x in dir_lis:
        ip.add_txt(os.path.join('出品', x, '0.jpg'), txt).save(os.path.join('出品', x, '0.jpg'))
