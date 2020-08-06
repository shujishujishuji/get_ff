import sys
from pathlib import Path

# ライブラリのパス
sys.path.append('/usr/local/lib/python3.7/site-packages')

# 上層階のファイルを読み込むためのパス
sys.path.append(str(Path(__file__).resolve().parent.parent))

import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from matplotlib import pyplot as plt

from flask import request, Blueprint

picapp = Blueprint('picapp', __name__)


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
    def add_txt(self, img_path, txt, bg_path):
        # 画像の読み込み
        img = Image.open(img_path)

        # 正方形に変形
        width, height = img.size
        img = img.resize((width, width))

        # 背景色の取り込み
        rgb_im = img.convert('RGB')
        r, g, b = rgb_im.getpixel((1, width-1))

        # 背景画像読み込み
        bg_img = Image.open(bg_path)

        # テキスト記載部分の作成
        T, L, R, B = 60, 60, 60, 60
        result = Image.new(img.mode, (width + L + R, width + T + B), (r, g, b))
        result.paste(img, (L, T))

        # 外枠の追加
        r_w, r_h = result.size
        top, left, right, bottom = 30, 30, 30, 30
        new_w = r_w + right + left
        new_h = r_h + top + bottom
        r_img = bg_img.resize((new_w, new_h))
        r_img.paste(result, (left, top))

        # テキストの追加
        draw = ImageDraw.Draw(r_img)
        font = ImageFont.truetype('~/Library/Fonts/Oranienbaum.ttf', 48)
        w, h = draw.textsize(txt, font=font)
        draw.text(((new_w - w) / 2, new_h - 90), text=txt, font=font, fill=(0, 0, 0))
        r_img.save(img_path)

    # cv2ベタ塗り画像の作成
    def create_blank(self, width, height, rgb_color=(0, 0, 0)):
        image = np.zeros((height, width, 3), np.uint8)
        color = tuple(reversed(rgb_color))
        image[:] = color
        return image

    # 背景と商品を合成する
    def add_bg_item(self, img_path, bg_path):
        dir_name = os.path.dirname(img_path)
        f_path = os.path.join(dir_name, '0.jpg')

        # 前景になる画像の読み出し
        img_1 = cv2.imread(img_path)
        # 背景になる画像の読み出し
        img_2 = cv2.imread(bg_path)

        white = (255, 255, 255)

        height, width = img_2.shape[:2]

        image = self.create_blank(width, height, rgb_color=white)

        img_2 = cv2.addWeighted(img_2, 0.9, image, 0.1, 120)

        # 正方形に変形
        tmp = img_1[:, :]
        height, width = img_1.shape[:2]
        if height > width:
            size = height
            limit = width
        else:
            size = width
            limit = height
        start = int((size - limit)/2)
        fin = int((size + limit)/2)
        new_img = cv2.resize(np.full((1, 1, 3), 255, np.uint8), (size, size))

        if size == height:
            new_img[:, start:fin] = tmp
        else:
            new_img[start:fin, :] = tmp

        # 背景と商品画像の大きさを合わせる
        img_2 = cv2.resize(img_2, (int(new_img.shape[1]), int(new_img.shape[0])))

        # マスク作成時の二値化閾値
        threshold = 250

        # 前景画像をグレースケール変換
        img_1_gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)

        # 閾値で二値化しマスク画像を作成(人物を黒に)
        ret, img_1_binary = cv2.threshold(img_1_gray, threshold, 255, cv2.THRESH_BINARY)

        # ndarrayの型合わせのためGRAY→BGRに変換
        mask_bgr = cv2.cvtColor(img_1_binary, cv2.COLOR_GRAY2BGR)

        # マスクの白(255)を1に、それ以外を0に変換(01マスクを生成)
        mask_bgr_bin = np.where(mask_bgr == 255, 1, 0)

        # マスクの白(255)を0に、それ以外を1に変換(反転01マスクを生成)
        mask_bgr_bin_inv = np.where(mask_bgr == 255, 0, 1)

        # 前景画像に反転01マスクを掛け人物だけ抜き出す(それ以外は黒)
        img_3 = new_img * mask_bgr_bin_inv

        # 背景画像に1マスクを掛け人物以外の部分を抜き出す(それ以外は黒)
        img_4 = img_2 * mask_bgr_bin

        # 前景、背景を併せる
        img_marged = img_3 + img_4

        # ファイル保存
        cv2.imwrite(f_path, img_marged)

        return f_path

    # pillowのテキスト追加
    def add_title(self, txt, img_path, bg_path):
        f_path = self.add_bg_item(img_path, bg_path)
        img = Image.open(f_path)
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype('~/Library/Fonts/Oranienbaum.ttf', 48)
        w, h = draw.textsize(txt, font=font)
        draw.text((20, 20), text=txt, font=font, fill=(0, 0, 0))
        img.save(f_path)

    # cv2のテキスト追加
    def add_title2(self, txt, img_path, bg_path):
        self.add_bg_item(img_path, bg_path)
        im = cv2.imread('a.jpg')

        # フォントの指定
        # font = cv2.FONT_HERSHEY_COMPLEX_SMALL
        # font = cv2.FONT_HERSHEY_SIMPLEX
        # font = cv2.FONT_HERSHEY_PLAIN
        # font = cv2.FONT_HERSHEY_TRIPLEX | cv2.FONT_ITALIC
        font = cv2.FONT_HERSHEY_COMPLEX | cv2.FONT_ITALIC
        # font = cv2.FONT_HERSHEY_SCRIPT_SIMPLEX | cv2.FONT_ITALIC
        # font = cv2.FONT_HERSHEY_SCRIPT_COMPLEX | cv2.FONT_ITALIC

        # 設定
        w, h = 50, 70
        font_size = 2
        color = (0, 0, 0)
        font_bold = 2

        # 文字の書き込み
        cv2.putText(im, txt, (w, h), font, font_size, color, font_bold, cv2.LINE_AA)
        cv2.imwrite('aaa.jpg', im)


def main():
    ip = ImageProcessing()
    txt = 'bname'
    dir_lis = [f for f in os.listdir('出品') if os.path.isdir(os.path.join('出品', f))]
    for x in dir_lis:
        ip.add_txt(os.path.join('出品', x, '0.jpg'), txt).save(os.path.join('出品', x, '0.jpg'))


def change_pic(pic_path, txt):
    bottom = 80
    img = Image.open(pic_path)
    width, height = img.size
    im = Image.new(img.mode, (width, 80), (0, 0, 0))
    img.paste(im, (0, height - 80))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype('~/Library/Fonts/Oranienbaum.ttf', 48)
    w, h = draw.textsize(txt, font=font)
    draw.text(((width - w) / 2, height - bottom + ((bottom - h) / 2)), text=txt, font=font, fill=(255, 255, 255))
    img.save(pic_path)


def c_pic(pic_path):
    img = Image.open(pic_path)
    w, h = img.size
    t, l, r, b = 15, 15, 15, 75
    im_crop = img.crop((l, t, (w - l), (h - b)))
    im_crop.save(pic_path)


@picapp.route('/post_img', methods=['POST'])
def post_url():
    bg_path = os.path.join('bg', request.form.get('backgroundimg'))
    txt = request.form.get('title')
    ip = ImageProcessing()
    path = '出品'
    files = os.listdir(path)
    files_dir = [f for f in files if os.path.isdir(os.path.join(path, f))]
    for f_dir in files_dir:
        img_path = os.path.join(path, f_dir, '1.jpg')
        ip.add_title(txt, img_path, bg_path)
    return 'end'


if __name__ == '__main__':
    # ip = ImageProcessing()
    # img_marged = ip.add_title('smythson', '出品/1/3.jpg', 'bg/smythson.jpg')
    # for x in range(1, 24):
    #     f_path = os.path.join('出品', str(x), '0.jpg')
    #     ip.add_txt(f_path, 'Smythson', 'bg/smythson.jpg')
    post_url()
