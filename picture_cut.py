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
    # cv2で画像表示
    def show_img(self, img):
        cv2.imshow('image', img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # cv2ベタ塗り画像の作成
    def create_blank(self, width, height, rgb_color=(0, 0, 0)):
        image = np.zeros((height, width, 3), np.uint8)
        color = tuple(reversed(rgb_color))
        image[:] = color
        return image

    # 背景を白っぽくして、商品画像を貼り付けたイメージ
    def add_bg_item(self, img_path, bg_path):
        dir_name = os.path.dirname(img_path)
        f_path = os.path.join(dir_name, '0.jpg')

        # 前景になる画像の読み出し
        img_1 = cv2.imread(img_path)
        # 背景になる画像の読み出し
        img_2 = cv2.imread(bg_path)

        white = (255, 255, 255)

        height, width = img_2.shape[:2]

        # 白ベタを読み込み
        image = self.create_blank(width, height, rgb_color=white)

        # 白ベタと背景画像を組み合わせる
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

    def squere(self, img_1):
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
        return new_img

    # pillowのテキスト追加
    def add_title(self, txt, font, f_path):
        img = Image.open(f_path)
        draw = ImageDraw.Draw(img)
        txt_font = ImageFont.truetype(f'~/Library/Fonts/{font}', 60)
        w, h = draw.textsize(txt, font=txt_font)
        draw.text((20, 20), text=txt, font=txt_font, fill=(0, 0, 0))
        img.save(f_path)

    def make_square_add_margin(self, img_path, txt, font):
        # 画像の読み込み
        if not os.path.exists(img_path):
            img_path = os.path.splitext(img_path)[0] + '.png'
        img = Image.open(img_path)

        new_path_lis = img_path.split('/')
        new_path_lis[-1] = '0.jpg'
        new_path = '/'.join(new_path_lis)

        # 背景色の取り込み
        rgb_im = img.convert('RGB')
        r, g, b = rgb_im.getpixel((1, 1))

        w, h = img.size
        if h > w:
            size = h
            limit = h - w
            result = Image.new(img.mode, (size, size), (0, 0, 0))
            result.paste(img, (limit, 0))
            # pngとして保存
            re_path = new_path.replace('.jpg', '.png')
            result.save(re_path)
            self.add_text_png(re_path, h, limit, round(limit/3), txt, font)
        else:
            size = w
            limit = w - h
            result = Image.new(img.mode, (size, size), (0, 0, 0))
            result.paste(img, (0, 0))
            # テキストの挿入
            # draw = ImageDraw.Draw(result)
            # txt_font = ImageFont.truetype(f'~/Library/Fonts/{font}', round(limit/2))
            # t_size = draw.textsize(txt, font=txt_font)
            # draw.text((20, 20), text=txt, font=txt_font, fill=(0, 0, 0))
            # img.save(f_path)

    def add_text_png(self, re_path, w, h, font_size, txt, font):
        # pngを読み込み
        img = Image.open(re_path)
        textImg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        tmpDraw = ImageDraw.Draw(textImg)
        txt_font = ImageFont.truetype(f'~/Library/Fonts/{font}', font_size)
        tmpDraw.text((0, (h - font_size)/2), text=txt, font=txt_font, fill=(255, 255, 255))
        t_size = tmpDraw.textsize(txt, font=txt_font)
        textImg = textImg.rotate(-90, expand=True)
        img.paste(textImg, (0, round((w - t_size[0])/3)))
        img.save(re_path)


@picapp.route('/post_img', methods=['POST'])
def post_url():
    bg_path = os.path.join('bg', request.form.get('backgroundimg'))
    font = request.form.get('font')
    txt = request.form.get('title')
    pattern = request.form.get('pattern')
    ip = ImageProcessing()
    path = '出品'
    files = os.listdir(path)
    files_dir = [f for f in files if os.path.isdir(os.path.join(path, f))]
    for f_dir in files_dir:
        img_path = os.path.join(path, f_dir, '1.jpg')
        if pattern == 'white_bg':
            f_path = ip.add_bg_item(img_path, bg_path)
            ip.add_title(txt, font, f_path)
        elif pattern == 'black_margin':
            ip.make_square_add_margin(img_path, txt, font)
    return 'end'


if __name__ == '__main__':
    ip = ImageProcessing()
    txt = 'RAINS'
    font = 'Oranienbaum.ttf'
    for x in range(1, 33):
        f_path = os.path.join('出品', str(x), '1.jpg')
        ip.make_square_add_margin(f_path, txt, font)
        # img_1 = cv2.imread(f_path)
        # new = ip.squere(img_1)
        # cv2.imwrite(new_path, new)
        # ip.add_title('RAINS', 'Oranienbaum.ttf', new_path)
