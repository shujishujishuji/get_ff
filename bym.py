from datetime import datetime as dt
import pandas as pd
import time

from flask import Blueprint
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
from db import Stock, engine

bymapp = Blueprint('bymapp', __name__)


def login_bym(driver):
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
    driver = set_driver('https://www.buyma.com/list/mens.html', True)
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


@bymapp.route('/stop_bym', methods=['GET'])
def change_bym_item_status():
    # 削除URLの取得
    ss = set_ss(cf.get('SS_SHEET', 'KEY_FILE'), cf.get('SS_SHEET', 'SHEET_NAME')).worksheet('在庫削除')
    url_lis = ss.col_values(6)
    id_lis = ss.col_values(1)

    # ドライバーの設定
    driver = set_driver('https://www.buyma.com/login/')

    # ログイン
    login_bym(driver)

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