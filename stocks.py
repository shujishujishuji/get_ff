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
import shutil

from flask import request, Blueprint

from sqlalchemy.orm import sessionmaker

from config import config_ini as cf
from logger import logger, log
from driver_setup import set_driver
from set_spsheet import set_ss
from db import Stock, engine
from ff import get_description
from aso import aso_get_description


stockapp = Blueprint('stockapp', __name__)


@log
@stockapp.route('/del_img', methods=['GET'])
def del_img():
    """出品フォルダのファイルを全削除する
    """
    try:
        shutil.rmtree('出品')
        os.mkdir('出品')
        result = 'True'
    except Exception as e:
        result = str(e)
    finally:
        return result


@log
@stockapp.route('/del_stock', methods=['POST'])
def del_stock():
    """在庫削除関数
    """
    if '-' in request.form.get('id'):
        id_list = request.form.get('id').split('-')
        s = int(id_list[0])
        e = int(id_list[1]) + 1
        id_list = list(range(s, e))
    else:
        id_list = request.form.get('id').split(',')
    Session = sessionmaker(bind=engine)
    ses = Session()
    query = ses.query(Stock)
    for x in id_list:
        if not isinstance(x, int):
            x = int(x)
        query.filter(Stock.id == x).update({Stock.del_flg: 1})

    ses.commit()
    ses.close()
    return 'True'


@stockapp.route('/get_stock', methods=['POST'])
@log
def check_stock():
    """
        在庫管理実行関数
        比較ファイルと在庫ファイルを読み込み、
        現在情報を取得、在庫ファイルと差分があるものは
        比較ファイルに追加する。
    """
    # スライスを取得
    s = request.form.get('sid').split(':')
    slices = slice(int(s[0]), int(s[1]))
    try:
        # データベースから在庫情報を辞書に読み込む
        Session = sessionmaker(bind=engine)
        ses = Session()
        res = ses.query(Stock).all()
        ses.close()
        stock = []
        diff_list = []
        for item in res:
            stock.append(item.to_dict())

        # 差分比較
        for item in stock[slices]:
            logger.info(item['id'])
            logger.info(item['url'])
            if item['del_flg'] == 0:
                time.sleep(1)
                driver = set_driver(item['url'])
                try:
                    if 'www.farfetch.com' in item['url']:
                        price, size = get_description(driver, True)
                    elif 'www.asos.com' in item['url']:
                        price, size = aso_get_description(driver, True)
                except Exception as e:
                    # 例外発生は在庫ないためなので、エラーを挿入
                    driver.close()
                    val = 'Error' + str(e)
                    Session = sessionmaker(bind=engine)
                    ses = Session()
                    query = ses.query(Stock)
                    query.filter(
                        Stock.id == item['id']).update(
                            {Stock.stock_info: val, Stock.updated: dt.now()})
                    ses.commit()
                    ses.close()
                    diff_data = {'id': item['id'],
                                 'URL': item['url'],
                                 'stock_info': item['stock_info'],
                                 'diff_info': val,
                                 'buyma_id': item['buyma_id'],
                                 'buyma_url': item['buyma_url']}
                    diff_list.append(diff_data)
                    continue
                driver.close()

                # 差分があったらdatabase更新
                val = price + size
                if item['stock_info'] != val:
                    Session = sessionmaker(bind=engine)
                    ses = Session()
                    query = ses.query(Stock)
                    query.filter(
                        Stock.id == item['id']).update(
                            {Stock.stock_info: val, Stock.updated: dt.now()})
                    ses.commit()
                    ses.close()

                    # 在庫情報と更新情報をリストに追加する
                    diff_data = {'id': item['id'],
                                 'URL': item['url'],
                                 'stock_info': item['stock_info'],
                                 'diff_info': val,
                                 'buyma_id': item['buyma_id'],
                                 'buyma_url': item['buyma_url']}
                    diff_list.append(diff_data)
        result = '終わったよ(笑)'
    except Exception as e:
        result = str(e)
        logger.error(e)
    finally:
        ss = set_ss(cf.get('SS_SHEET', 'KEY_FILE'), cf.get('SS_SHEET', 'SHEET_NAME')).worksheet('在庫')
        diff_lis = [[x['id'], x['URL'], x['stock_info'], x['diff_info'], x['buyma_id'], x['buyma_url']] for x in diff_list]
        ss_data = [{'range': 'A{}:F{}'.format(2, len(diff_list) + 1),
                    'values': diff_lis}]
        ss.batch_update(ss_data)
        return result
