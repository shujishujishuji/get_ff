import sys
from pathlib import Path

# ライブラリのパス
sys.path.append('/usr/local/lib/python3.7/site-packages')

# 上層階のファイルを読み込むためのパス
sys.path.append(str(Path(__file__).resolve().parent.parent))

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

from bs4 import BeautifulSoup as bs
from datetime import datetime as dt
import pandas as pd
import time
import os
import re
import urllib
from pprint import pprint

from flask import request, Blueprint

from sqlalchemy.orm import sessionmaker

from config import config_ini as cf
from logger import logger, log
from driver_setup import set_driver
from set_spsheet import set_ss
from db import Stock, engine
from picture_cut import ImageProcessing

asoapp = Blueprint('asoapp', __name__)

ip = ImageProcessing()


class AsoGetList:
    """
        商品一覧ページのURLを一括取得するクラス
    """
    @log
    def aso_get_page_list(self, url):
        """
            複数ページURLを取得し、スプレッドシートに記載
        """
        ss = set_ss(cf.get('SS_SHEET', 'KEY_FILE'), cf.get('SS_SHEET', 'SHEET_NAME')).worksheet('出品シート')
        url_lis = ss.col_values(9)
        page_list = self.aso_move_page(url)
        page_lis = [[x] for x in page_list]
        ss_data = [{'range': 'I{}:I{}'.format(len(url_lis) + 1,
                                              len(url_lis) + len(page_list)),
                    'values': page_lis}]
        ss.batch_update(ss_data)

    @log
    def aso_move_page(self, url):
        """商品一覧ページから各商品のURLリストを作成する。
        　　リストをforで回して、各ページの情報を取得する。
            ページが複数ある場合は、各ページを実行する必要あり。
            headlessでは動かない
        """
        try:
            driver = set_driver(url)
            class_tag = driver.find_element_by_class_name('_3pQmLlY')
            a_tags = class_tag.find_elements_by_tag_name('a')
            page_src_list = [url.get_attribute('href') for url in a_tags]
            return page_src_list
        finally:
            driver.quit()


def aso_get_pagesource(url):
    """
        htmlを保存する
    """
    driver = set_driver(url)
    html = driver.page_source
    with open('asos_item_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    driver.quit()


@log
def aso_get_src(driver, tag_name, img_suffix, folder_name):
    """
        画像を取得してディレクトリに保存
        img_suffix = .jpg
    """
    # フォルダがなければ作成
    img_path = os.path.join(tag_name, folder_name)
    if not os.path.exists(img_path):
        os.makedirs(img_path)

    # 画像のリスト取得
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, 'fullImageContainer')))
    time.sleep(2)
    img_list = driver.find_elements_by_class_name('fullImageContainer')

    # サムネイルに使用されているURLをリストの先頭に移動
    img_list[0], img_list[1] = img_list[1], img_list[0]

    for i, x in enumerate(img_list):
        img = x.find_element_by_class_name('img').get_attribute('src')
        urllib.request.urlretrieve(img, os.path.join(img_path, '{}{}'.format(i, img_suffix)))


@log
def aso_get_description(driver, stock_check=None):
    """
        商品説明取得関数
    　　 headlessモードはダメ、全て取得できない。
        価格、サイズ、商品説明、サイズガイドの順に取得
        stock_check=Trueの場合は、価格、サイズのみ取得
    """
    price = pure_price = color = size = title = desc = 'nodata'

    # セットの場合は処理を終わる
    time.sleep(1)
    if len(driver.find_elements_by_id('mixmatch-size-select-0')) > 0:
        return price, pure_price, color, size, title, desc

    time.sleep(1)
    if len(driver.find_elements_by_class_name('product-out-of-stock-label')) > 0:
        if 'out' in driver.find_element_by_class_name('product-out-of-stock-label').text.lower():
            return price, pure_price, color, size, title, desc

    # 価格文字列を数字だけ抽出
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, 'product-price')))
    price_el = driver.find_element_by_id('product-price').find_elements_by_class_name('product-prev-price')
    pre_price_lis = [re.sub("^\D*", "", x.text) for x in price_el if bool(re.search(r'\d', x.text))]
    cure_price_el = driver.find_element_by_class_name('current-price-container').text
    if len(pre_price_lis) == 0:
        pure_price = re.sub("^\D*", "", cure_price_el)
        price = pure_price
    else:
        pure_price = pre_price_lis[0]
        price = re.sub("^\D*", "", cure_price_el)

    # 色の取得
    color = driver.find_element_by_class_name('product-colour').text.strip()

    # サイズと価格と在庫を取得
    if len(driver.find_elements_by_id('main-size-select-0')):
        select_id = driver.find_element_by_id('main-size-select-0')
        select = Select(select_id)
        sizes = select.options
        size_list = [x.text for x in sizes if x.text]
        if len(size_list) > 0:
            if 'Please' in size_list[0]:
                size_list.pop(0)
            size = '\n'.join(size_list)
        else:
            size = 'no size'
    else:
        size = 'one size'

    # 在庫管理の場合は以降はスキップ
    if stock_check is None:
        # タイトル取得
        title = ''
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, 'product-hero')))
        title = driver.find_element_by_class_name('product-hero').find_element_by_tag_name('h1').text
        # log出力
        logger.info(f'title: {title}')

        # 商品説明取得
        size_fit = care_info = about_me = ''
        if len(driver.find_elements_by_class_name('product-description')) > 0:
            desc = driver.find_elements_by_class_name('product-description')[1].text
        if len(driver.find_elements_by_class_name('size-and-fit')) > 0:
            size_fit = driver.find_element_by_class_name('size-and-fit').text
        if len(driver.find_elements_by_class_name('care-info')) > 0:
            care_info = driver.find_element_by_class_name('care-info').text
        if len(driver.find_elements_by_class_name('about-me')) > 0:
            about_me_el = driver.find_element_by_class_name('about-me')
            about_me = about_me_el.get_attribute('textContent').replace('            ', '')

        desc = '\n\n'.join([desc, size_fit, care_info, about_me])

        return price, pure_price, color, size, title, desc
    return price, size


# urlを受け取る
@asoapp.route('/aso_post', methods=['POST'])
def aso_post_url():
    url = request.form.get('url')
    getlist = AsoGetList()
    getlist.aso_get_page_list(url)
    return url


@log
@asoapp.route('/aso_post_desc', methods=['POST'])
def aso_get_info():
    """
        情報取得実行関数
        スプレッドシートからURLを読み込み
        各URLに情報取得関数を実行し、
        在庫リストに追加する。
    """
    try:
        # GUIからの入力値
        deadline = request.form.get('deadline')
        ratio = request.form.get('ratio')
        overship = request.form.get('overship')
        exchange = request.form.get('exchange')
        cat = request.form.get('category')
        catchcopy = request.form.get('catchcopy')

        # spred_sheetのセットアップ
        sss = set_ss(cf.get('SS_SHEET', 'KEY_FILE'), cf.get('SS_SHEET', 'SHEET_NAME'))
        ss = sss.worksheet('出品シート')
        bland_dic = sss.worksheet('ブランド').get_all_records()
        category_dic = sss.worksheet(str(cat)).get_all_records()
        color_dic = sss.worksheet('カラーズ').get_all_records()

        # スプレッドシートからURLリスト作成
        url_lis = ss.col_values(9)[1:]

        # データベースから在庫情報を辞書に読み込む
        Session = sessionmaker(bind=engine)
        ses = Session()
        res = ses.query(Stock).all()
        ses.close()
        stock = []
        for item in res:
            stock.append(item.to_dict())

        # 在庫urlリストの作成
        stock_url = []
        for x in stock:
            stock_url.append(x['url'])

        driver = set_driver('https://www.google.com/')
        # URL毎の処理
        for i, url in enumerate(url_lis):
            # log出力
            logger.info(f'URL: {url}')
            if url in stock_url:
                continue

            # driverセットアップ
            driver.get(url)
            # 画像取得
            aso_get_src(driver, '出品', '.jpg', str(i+1))
            # 商品説明取得
            price, pure_price, color, size, title, desc = aso_get_description(driver)

            def is_num(s):
                return s.replace('.', '').isnumeric()

            if is_num(pure_price):
                pure_price = float(pure_price)
            else:
                continue

            # ブランドの取得
            item = desc.split('\n')[1].split(' by ')
            brand = item[1].strip()
            cate = title

            # 画像編集
            if title != 'a':
                img_path = os.path.join('出品', str(i+1), '0.jpg')
                ip.add_txt(img_path, brand)

            # 初期化
            bland_str = category_str = ''

            # ブランド名の取得
            bland_lis = [str(bland['ブランド']) for bland in bland_dic if str(brand).lower() in str(bland['ff_ブランド']).lower()]
            if len(bland_lis) > 0:
                bland_str = bland_lis[0]

            # カテゴリーの取得
            category_lis = [str(_category['カテゴリ']) for _category in category_dic if str(_category['ff_カテゴリ']) in cate]
            if len(category_lis) > 0:
                category_str = category_lis[0]

            # カラーの取得
            color_lis = [str(_color['カラー']) for _color in color_dic if str(_color['colors']).lower() in color.lower()]
            if len(color_lis) > 0:
                color_str = color_lis[0]

            # 発送地の取得
            area_str = '海外:ヨーロッパ:イギリス:選択なし'

            # スプレッドシート への書き込み
            cell_row = i+2
            ss_data = [{'range': 'A{}:H{}'.format(cell_row, cell_row),
                        'values': [[str(i+1),
                                    catchcopy + title.replace('\n', ' '),
                                    bland_str, '',
                                    category_str,
                                    desc,
                                    size,
                                    deadline]]},
                       {'range': 'J{}'.format(cell_row),
                        'values': [[area_str]]},
                       {'range': 'N{}'.format(cell_row),
                        'values': [[color_str]]},
                       {'range': 'Z{}:AA{}'.format(cell_row, cell_row),
                        'values': [[pure_price, int(exchange)]]},
                       {'range': 'AD{}'.format(cell_row),
                        'values': [[overship]]}]
            ss.batch_update(ss_data)

            # 在庫データベースの更新
            stock_info = price + size
            stock_obj = Stock(url=url, stock_info=stock_info)
            Session = sessionmaker(bind=engine)
            ses = Session()
            ses.add(stock_obj)
            ses.commit()
            ses.close()
        result = 'True'
    except Exception as e:
        result = str(e)
        logger.error(e)
    finally:
        driver.quit()
        return result


# # ブランドページのスクレイピング
# def scraping(url):
#     blands_list = []
#     driver = set_driver(url, True)
#     target_ul_list = driver.find_elements_by_css_selector(
#         '#slice-designers-index > div > div._c9b90c > div > ul > li > a')
#     for x in target_ul_list:
#         bland_name = x.text
#         bland_url = x.get_attribute('href')
#         blands_list.append({'bland': bland_name, 'url': bland_url})

#     for z in blands_list:
#         category, num = getter(z['url'])
#         z.update({'category': category, 'num': num})
#     df = pd.DataFrame(blands_list)
#     df.to_csv('ff_women_bland.csv')
#     driver.quit()


# # ブランドのカテゴリーとアイテム数の取得
# def getter(url):
#     t = []
#     num = ''
#     y = []
#     driver = set_driver(url, False)
#     target = driver.find_elements_by_xpath(
#         '//*[@id="slice-container"]/div[3]/div[2]/div[1]/div/div/div/ul/li[1]')
#     if len(target) > 0:
#         for x in target:
#             t.append(x.text)
#         y = t[0].split()

#     css = '#slice-container > div:nth-child(3) > div._d7c730 > div > div > div._185fbf > span'
#     ttt = driver.find_elements_by_css_selector(css)
#     if len(ttt) > 0:
#         for x in ttt:
#             num = re.sub("\\D", "", x.text)
#     driver.quit()
#     return y, num
