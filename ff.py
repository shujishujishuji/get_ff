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
# from picture_cut import ImageProcessing

ffapp = Blueprint('ffapp', __name__)

# ip = ImageProcessing()


class GetList:
    """
        商品一覧ページのURLを一括取得するクラス
    """
    @log
    def get_page_list(self, url):
        """
            複数ページURLを取得し、スプレッドシートに記載
        """
        ss = set_ss(cf.get('SS_SHEET', 'KEY_FILE'), cf.get('SS_SHEET', 'SHEET_NAME')).worksheet('出品シート')
        url_lis = ss.col_values(9)
        page_list = self.move_page(url)
        page_lis = [[x] for x in page_list]
        ss_data = [{'range': 'I{}:I{}'.format(len(url_lis) + 1,
                                              len(url_lis) + len(page_list)),
                    'values': page_lis}]
        ss.batch_update(ss_data)

    def get_tag(self, tag, attr_name, attr_val):
        """
            tagの中から指定の要素をもつタグのtextを返す。
        """
        if attr_val == tag.get_attribute(attr_name):
            return tag

    @log
    def move_page(self, url):
        """商品一覧ページから各商品のURLリストを作成する。
        　　リストをforで回して、各ページの情報を取得する。
        """
        try:
            driver = set_driver(url, True)
            ul_tags = driver.find_elements_by_tag_name('ul')
            ul_list = []
            page_src_list = []
            for x in ul_tags:
                if self.get_tag(x,
                                'data-test',
                                'product-card-list') is not None:
                    ul_list.append(self.get_tag(x, 'data-test',
                                                'product-card-list'))
            for y in ul_list:
                a_tags = y.find_elements_by_tag_name('a')
                for z in a_tags:
                    page_src = z.get_attribute('href')

                    # log出力
                    logger.info(f'URL: {page_src}')
                    page_src_list.append(page_src)
            return page_src_list
        finally:
            driver.quit()


def get_pagesource(url):
    """
        htmlを保存する
    """
    driver = set_driver(url, True)
    html = driver.page_source
    with open('farfetch_item_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    driver.quit()


@log
def get_src(driver, tag_name, img_suffix, folder_name):
    """
        画像を取得してディレクトリに保存
        img_suffix = .jpg
    """
    # サムネイルに使用されてる画像のURLを取得
    img_div = driver.find_element_by_class_name('_42f8cf')
    img_src = img_div.find_elements_by_tag_name('source')
    t_img = img_src[0].get_attribute('srcset')
    t_url = re.findall(r'(.*)_', t_img)[0]

    # ページソースをテキスト取得
    soup = bs(driver.page_source, 'html.parser')
    # ソース文字列から600.jpgを含むリストを作成し、リスト化
    soup_list = [x.strip() for x in str(soup).split(',') if '600.jpg' in x]
    # url以外の文字列を削除
    url_lis = list(set([re.findall(r'https.*jpg', x)[0] for x in soup_list if len(x) < 100]))

    # サムネイルに使用されているURLをリストの先頭に移動
    t_index = [i for i, x in enumerate(url_lis) if t_url in x]
    if t_index != [0]:
        url_lis[0], url_lis[t_index[0]] = url_lis[t_index[0]], url_lis[0]

    # フォルダがなければ作成
    img_path = os.path.join(tag_name, folder_name)
    if not os.path.exists(img_path):
        os.makedirs(img_path)

    # 画像ファイルのダウンロード
    for i, s in enumerate(url_lis):
        logger.info(f'src_url: {s}')
        urllib.request.urlretrieve(
            s, os.path.join(img_path, '{}{}'.format(i+1, img_suffix)))


@log
def get_description(driver, stock_check=None):
    """
        商品説明取得関数
    　　 headlessモードはダメ、全て取得できない。
        価格、サイズ、商品説明、サイズガイドの順に取得
        stock_check=Trueの場合は、価格、サイズのみ取得
    """
    # タイトルdivの取得
    WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, '_c40757')))
    soup = bs(driver.page_source, 'html.parser')

    cl = soup.find('div', {'class': '_c40757'})
    soup_span = cl.find('span', {'data-tstid': "oneSizeLabel"})

    # 価格文字列を数字だけ抽出 headlessじゃないとダメ
    price_el = soup.find('div', {'class': '_81fc25'})
    price = price_el.get_text()
    p_price = price_el.find('span', {'data-tstid': 'priceInfo-original'}).get_text()
    pure_price = re.sub("\\D", "", p_price)

    # サイズと価格と在庫を取得、通信状況によって取得できないことがある
    if soup_span != None:
        size = 'one size'
    else:
        select_id = driver.find_element_by_id('dropdown')
        select = Select(select_id)
        sizes = select.options
        size_list = [sizes[i].text for i, _ in enumerate(sizes)]
        size = '\n'.join(size_list[1:])


    # 在庫管理の場合は以降はスキップ
    if stock_check is None:
        # タイトル取得
        title = ''
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '#bannerComponents-Container > h1')))
        title = driver.find_element_by_css_selector(
            '#bannerComponents-Container > h1').text
        logger.info(f'title: {title}')

        # 商品説明,フィッティングガイド取得
        element_list = ['商品説明', 'フィッティングガイド', '配送＆返品無料引き取りサービス']
        text_list = []
        for x in element_list:
            if len(driver.find_elements_by_id(x)):
                panel_button = driver.find_element_by_id(x)
                d = panel_button.get_attribute('aria-controls')
                panel_button.click()
                time.sleep(1)
                if x == '配送＆返品無料引き取りサービス':
                    # 発送国名
                    country = driver.find_element_by_xpath(
                        '//*[@id="panelInner-{}"]/div/div[2]/p/span[2]'.format(
                            d[-1])).text
                    text_list.append(country)
                else:
                    texts = driver.find_element_by_id(d).text
                    text_list.append(texts)
        desc = '\n\n'.join(text_list)

        # サイズガイド取得
        if soup_span is None:
            div_el = driver.find_element_by_class_name('_c40757')
            size_guide_div = div_el.find_element_by_class_name('_05fa91')
            size_guide_button = size_guide_div.find_element_by_tag_name('button')
            size_guide_button.click()
            if len(driver.find_elements_by_id('SizeGuideEmptypage')) > 0:
                size_guide = 'サイズガイドエラー'
            else:
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, '#panelInner-0 > div > div > table')))
                size_guide = driver.find_elements_by_css_selector(
                    '#panelInner-0 > div > div > table')
                if len(size_guide) > 0:
                    size_guide = size_guide[0].text
                else:
                    size_guide = 'サイズガイドエラー'
        else:
            size_guide = ''
        return price, size, desc, size_guide, title, pure_price
    return price, size


# urlを受け取る
@ffapp.route('/post', methods=['POST'])
def post_url():
    url = request.form.get('url')
    getlist = GetList()
    getlist.get_page_list(url)
    return url


@log
@ffapp.route('/post_desc', methods=['POST'])
def get_info():
    """
        情報取得実行関数
        スプレッドシートからURLを読み込み
        各URLに情報取得関数を実行し、
        在庫リストに追加する。
    """
    try:
        # GUIからの入力値
        deadline = request.form.get('deadline')
        overship = request.form.get('overship')
        domship = request.form.get('domship')
        cat = request.form.get('category')
        catchcopy = request.form.get('catchcopy')
        # bg_img = request.form.get('backgroundimg')

        # spred_sheetのセットアップ
        sss = set_ss(cf.get('SS_SHEET', 'KEY_FILE'), cf.get('SS_SHEET', 'SHEET_NAME'))
        ss = sss.worksheet('出品シート')
        bland_dic = sss.worksheet('ブランド').get_all_records()
        category_dic = sss.worksheet(str(cat)).get_all_records()
        area_dic = sss.worksheet('地域').get_all_records()

        # スプレッドシートからURLリスト作成
        url_lis = ss.col_values(9)[1:]
        logger.info(f'URLリスト: {len(url_lis)}')

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
        logger.info(f'在庫URLリスト: {len(stock_url)}')

        # driver = set_driver('https://www.google.com/')
        # URL毎の処理

        for i, url in enumerate(url_lis):
            #　初期値設定
            price = size = desc = size_guide = title = pure_price = 'a'
            # log出力
            logger.info(f'targetURL: {i}: {url}')
            if url in stock_url:
                continue

            # driverセットアップ
            # driver.get(url)
            driver = set_driver(url)
            for _ in range(3):
                try:
                    # 画像取得
                    get_src(driver, '出品', '.jpg', str(i+1))
                except Exception as e:
                    logger.error(f'retry: {e}')
                    continue
                else:
                    break

            for _ in range(3):
                try:
                    # 商品説明取得
                    price, size, desc, size_guide, title, pure_price = get_description(driver)
                except Exception as e:
                    driver.get(url)
                    logger.error(f'retry: {e}')
                    time.sleep(1)
                    continue
                else:
                    break

            logger.info(f'タイトル: {title}')
            logger.info(f'サイズ: {size}')

            # ブランドの取得
            t = re.search(r"^.*", title).group(0)

            # 画像編集
            # if title != 'a':
            #     img_path = os.path.join('出品', str(i+1), '1.jpg')
            #     bg_path = os.path.join('bg', bg_img)
            #     ip.add_title(t, img_path, bg_path)

            # 初期化
            bland_str = category_str = area_str = ''

            # ブランド名の取得
            bland_lis = [str(bland['ブランド']) for bland in bland_dic if str(t).lower() in str(bland['ff_ブランド']).lower()]
            if len(bland_lis) > 0:
                bland_str = bland_lis[0]

            # カテゴリーの取得
            category_lis = [str(_category['カテゴリ']) for _category in category_dic if str(_category['ff_カテゴリ']) in title]
            if len(category_lis) > 0:
                category_str = category_lis[0]

            # 商品説明からいらない部分を削除
            desc_list = desc.split('\n')
            # スタイルIDのインデックスを検索
            _index = [i for i, x in enumerate(desc_list) if 'ID:' in x]

            # 発送地の取得
            c = re.search(
                r"^.*のショップ", desc_list[-1]).group(0).replace('のショップ', '')
            area_lis = [str(area['地域']) for area in area_dic if c in str(area['ff_地域'])]
            if len(area_lis) > 0:
                area_str = area_lis[0]

            # ブランド名、商品名、発送地を削除
            # del desc_list[_index[0]]
            del desc_list[0:3], desc_list[-1]
            desc = '\n'.join(desc_list)

            # driver破棄
            driver.quit()

            # スプレッドシート への書き込み
            now = dt.now()
            today = '在庫状況:{0}月{1}日現在'.format(now.month, now.day)
            cell_row = i+2
            ss_data = [{'range': 'A{}:H{}'.format(cell_row, cell_row),
                        'values': [[str(i+1),
                                    catchcopy + title.replace('\n', ' '),
                                    bland_str, '',
                                    category_str,
                                    desc,
                                    today + '\n\n' + size + '\n\n' + size_guide,
                                    deadline]]},
                       {'range': 'J{}'.format(cell_row),
                        'values': [[area_str]]},
                       {'range': 'Z{}'.format(cell_row),
                        'values': [[pure_price]]},
                       {'range': 'AE{}:AF{}'.format(cell_row, cell_row),
                        'values': [[overship, domship]]}]
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


# ブランドページのスクレイピング
def scraping(url):
    blands_list = []
    driver = set_driver(url, True)
    target_ul_list = driver.find_elements_by_css_selector(
        '#slice-designers-index > div > div._c9b90c > div > ul > li > a')
    for x in target_ul_list:
        bland_name = x.text
        bland_url = x.get_attribute('href')
        blands_list.append({'bland': bland_name, 'url': bland_url})

    for z in blands_list:
        category, num = getter(z['url'])
        z.update({'category': category, 'num': num})
    df = pd.DataFrame(blands_list)
    df.to_csv('ff_women_bland.csv')
    driver.quit()


# ブランドのカテゴリーとアイテム数の取得
def getter(url):
    t = []
    num = ''
    y = []
    driver = set_driver(url, False)
    target = driver.find_elements_by_xpath(
        '//*[@id="slice-container"]/div[3]/div[2]/div[1]/div/div/div/ul/li[1]')
    if len(target) > 0:
        for x in target:
            t.append(x.text)
        y = t[0].split()

    css = '#slice-container > div:nth-child(3) > div._d7c730 > div > div > div._185fbf > span'
    ttt = driver.find_elements_by_css_selector(css)
    if len(ttt) > 0:
        for x in ttt:
            num = re.sub("\\D", "", x.text)
    driver.quit()
    return y, num
