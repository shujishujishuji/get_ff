import sys
from pathlib import Path

# ライブラリのパス
sys.path.append('/usr/local/lib/python3.7/site-packages')


from datetime import datetime as dt
import pandas as pd
import time
import re
from pprint import pprint

from flask import Blueprint, jsonify
from sqlalchemy.orm import sessionmaker

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

from config import config_ini as cf
from logger import logger, log
from driver_setup import set_driver
from set_spsheet import set_ss
from db import Stock, engine, Sales

bymapp = Blueprint('bymapp', __name__)


def login_bym(driver):
    """BUYMAへのログイン
    """
    login_mail = driver.find_element_by_id('txtLoginId')
    login_mail.send_keys(cf.get('BUYMA', 'BUYMA_MAIL'))
    login_pass = driver.find_element_by_id('txtLoginPass')
    login_pass.send_keys(cf.get('BUYMA', 'BUYMA_PASSWORD'))
    login_btn = driver.find_element_by_id('login_do')
    login_btn.click()


# BUYMAのブランドリストを取得
def scp_b():
    b_lis = []
    alist = [chr(i) for i in range(97, 97+26)]
    alist.append('other')
    driver = set_driver('https://www.buyma.com/list/fashion.html', True)
    for i in alist:
        target_ul_list = driver.find_elements_by_css_selector(
            f'#brindex_{i} > ul > li')
        for x in target_ul_list:
            bland = x.text.translate(str.maketrans({'(': '/', ')': '', ' ': ''})).split('/')
            if len(x.find_elements_by_css_selector('a')) > 0:
                bland.append(x.find_element_by_css_selector('a').get_attribute('href'))
            b_lis.append(bland)
    df = pd.DataFrame(b_lis)
    df.to_csv('buyma_mens_bland.csv')
    driver.quit()


@bymapp.route('/get_bym', methods=['GET'])
def get_bym():
    """BUYMAのIDをbuyermanagerから取得して、DBに追加する。
    """
    # データベースから在庫情報を辞書に読み込む
    Session = sessionmaker(bind=engine)
    ses = Session()
    res = ses.query(Stock).all()
    ses.close()
    stock = [item.to_dict() for item in res]
    stock_list = [item for item in stock if item['del_flg'] == 0 and item['buyma_id'] == 'None']

    buyma = 'https://teraplot.net/app/buyma/'
    # バイヤーマネージャーログイン
    driver = set_driver(buyma)
    inp_mail = driver.find_element_by_name('mail')
    inp_mail.send_keys('shuji00881199@gmail.com')
    inp_pass = driver.find_element_by_name('password')
    inp_pass.send_keys('bHbaDYhO')
    login_btn = driver.find_element_by_name('action')
    login_btn.click()


    # 最初の商品検索
    for stock in stock_list:
        logger.info(stock['id'])
        inp_url = driver.find_element_by_name('buyingUrl')
        inp_url.send_keys(stock['url'])
        if stock == stock_list[0]:
            url_btn = driver.find_element_by_css_selector('#content > form:nth-child(5) > input[type=submit]:nth-child(2)')
        else:
            url_btn = driver.find_element_by_css_selector('#header > form > input[type=submit]:nth-child(2)')
        url_btn.click()

        # DBセクション作成
        Session = sessionmaker(bind=engine)
        ses = Session()
        query = ses.query(Stock)

        # buyma_id,urlの取得
        if len(driver.find_elements_by_css_selector('#header > p:nth-child(4) > a:nth-child(1)')) > 0:
            b_id = driver.find_element_by_css_selector('#header > p:nth-child(4) > a:nth-child(1)').text
            b_url = driver.find_element_by_css_selector('#header > p:nth-child(4) > a:nth-child(2)').get_attribute('href')
            query.filter(Stock.id == stock['id']).update(
                {Stock.buyma_id: b_id, Stock.buyma_url: b_url, Stock.updated: dt.now()})
        else:
            query.filter(Stock.id == stock['id']).update({Stock.del_flg: 1})
        ses.commit()
        ses.close()
    driver.close()
    return 'owata'


def change_bym_status(driver, url, status):
    """BUYMAの出品停止と出品中を切り替える
        url: 商品編集ページURL
        status: 出品中か出品停止中のうち、変更後のステータス
    """
    driver.get(url)
    class_name = 'bmm-c-switch'
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, class_name)))
    item_txt = driver.find_element_by_class_name(class_name).text
    if item_txt != status:
        driver.execute_script("document.getElementsByClassName('" + class_name + "')[0].click();")
        time.sleep(1)
        btn = 'bmm-c-btn'
        driver.execute_script("document.getElementsByClassName('" + btn + "')[0].click();")
        time.sleep(5)


def change_man(driver, man):
    switch_class_name = 'my-page-menu__switch'
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, switch_class_name)))
    switch = driver.find_element_by_class_name(switch_class_name)
    if man in switch.text:
        switch.click()


@bymapp.route('/stop_bym', methods=['GET'])
def change_bym_item_status():
    """BUYMAの出品ステータスを出品停止に変更する。
    """
    # 削除URLの取得
    ss = set_ss(cf.get('SS_SHEET', 'KEY_FILE'), cf.get('SS_SHEET', 'SHEET_NAME')).worksheet('在庫削除')
    url_lis = ss.col_values(6)
    id_lis = ss.col_values(1)

    # ドライバーの設定
    driver = set_driver('https://www.buyma.com/login/')

    # ログイン
    login_bym(driver)

    # 購入者ページに入ったら切り替える
    change_man(driver, '出品者')

    # 出品ステータスの変更
    for url in url_lis:
        change_bym_status(driver, url, '出品停止中')
    driver.quit()

    # DB削除
    Session = sessionmaker(bind=engine)
    ses = Session()
    query = ses.query(Stock)
    for x in id_lis:
        if not isinstance(x, int):
            x = int(x)
        query.filter(Stock.id == x).update({Stock.del_flg: 1})
    ses.commit()
    ses.close()
    return 'end of 出品停止処理'


@bymapp.route('/data_bym', methods=['GET'])
def get_sale():
    """データをDBに追加する定期的に実行すること
    """
    driver = set_driver('https://www.buyma.com/login/')
    login_bym(driver)
    css = '#wrapper > div.bmm-l-wrap.my-page > div.bmm-l-main.my-page__main > div > div.my-page-status > table > tbody > tr > td'
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, css)))
    time.sleep(2)
    data = driver.find_elements_by_css_selector(css)
    data_lis = [re.sub("\\D", "", x.text) for x in data]
    driver.quit()
    data_lis = list(map(int, data_lis))

    # DB保存
    sales_obj = Sales(sales=data_lis[0],
                      close=data_lis[1],
                      follower=data_lis[2],
                      like=data_lis[3],
                      access=data_lis[4])
    Session = sessionmaker(bind=engine)
    ses = Session()
    ses.add(sales_obj)
    ses.commit()
    ses.close()
    return '取れたデーた'


def get_all():
    """全データを取得する
    """
    Session = sessionmaker(bind=engine)
    ses = Session()
    res = ses.query(Sales).all()
    ses.close()
    resp = [x.to_dic() for x in res]
    return resp


@bymapp.route('/all_bym_data', methods=['GET'])
def all_bym_data():
    """全データを返す
    """
    res = get_all()
    return jsonify(res)


def syopper_data(url):
    driver = set_driver(url, True)
    css = '#profile_wrap > dl > dd:nth-child(2)'
    profile = driver.find_element_by_css_selector(css).text
    print(profile)


if __name__ == '__main__':
    scp_b()