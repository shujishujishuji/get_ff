from sqlalchemy import create_engine, Column, Integer, String, \
    Text, DateTime, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.functions import current_timestamp
from sqlalchemy.dialects.mysql import TIMESTAMP as Timestamp
import sqlite3
import urllib.request
import os
import re
from pprint import pprint
import sys
from pathlib import Path
import time
from datetime import datetime as dt

# ライブラリのパス
sys.path.append('/usr/local/lib/python3.7/site-packages')

# 上層階のファイルを読み込むためのパス
sys.path.append(str(Path(__file__).resolve().parent.parent))

import crochet
crochet.setup()

from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.signalmanager import dispatcher
from researcher.spiders.saled import SaledSpider
from logger import logger, log

from flask import request, Blueprint, jsonify, url_for, redirect
from db import engine

saledapp = Blueprint('saledapp', __name__)

output_data = []
crawl_runner = CrawlerRunner()

new_date = dt.now().strftime('%Y%m%d')


@saledapp.route('/saled_research', methods=['POST'])
@log
def saled_research():
    """ショッパーデータから販売実績のある商品を抽出する。
    """
    if request.method == 'POST':
        s = request.form['saled_url']
        b = request.form['saled_bland']

        logger.info(f'URL: {s}')
        logger.info(f'ブランド: {b}')

        global baseURL
        baseURL = s

        result = scrape(b.replace(' ', '').lower())

        return jsonify(result)

@log
def scrape(bland):
    global baseURL
    global output_data
    table_name = baseURL + new_date

    logger.info(f'テーブル名: {table_name}')

    conn1 = sqlite3.connect('saled.sqlite3')
    conn2 = sqlite3.connect('bland.sqlite3')
    # bland_DBにテーブルがあるかどうか確認
    c2 = conn2.cursor()
    c2.execute('''SELECT count(name) FROM sqlite_master WHERE name='%s' AND type='table' ''' % table_name)

    if(c2.fetchone()[0] == 0):
        # テーブルがなかった場合はNoneを返す
        conn2.close()
        logger.warning('テーブルがありません')
        return None
    else:
        # テーブルがあれば、データを取得
        conn2.row_factory = sqlite3.Row
        cur2 = conn2.cursor()
        cur2.execute(''' SELECT * from '%s' ''' % table_name)
        rows = cur2.fetchall()
        bland_data = ([dict(i) for i in rows])
        conn2.close()
        logger.info(f'ブランド商品数: {len(bland_data)}')

        # ショッパーのURLを重複削除して抽出
        shopper_urls = set([x['shopper_url'] for x in bland_data])

        logger.info(f'ショッパー数: {len(shopper_urls)}')

        s_lis = [[url, (url + new_date)] for url in shopper_urls]

        # shopper_urlに対しての繰り返し処理
        for i, url in enumerate(s_lis):
            c1 = conn1.cursor()
            s_table_name = url[0]
            s_url = url[0]

            # saled_DBにデータがあるかどうか確認
            c1.execute('''SELECT count(name) FROM sqlite_master WHERE name='%s' AND type='table' ''' % s_table_name)

            # テーブルがなかった場合はデータ取得
            if(c1.fetchone()[0] == 0):
                # ショッパーの販売実績URL作成
                t_url = create_shopper_url(s_url)
                logger.info(f'{i}:取得対象ショッパーURL: {t_url}')
                pre_output_data = output_data

                # スクレイピングの開始
                output_data = []
                scrape_with_crochet(baseURL=t_url)
                time.sleep(30)

                result = [x for x in output_data if x not in pre_output_data]
                logger.info(f'受注実績商品数: {len(result)}')

                # テーブルの作成
                conn1.execute('''CREATE TABLE '%s' (\
                                    id INTEGER PRIMARY KEY AUTOINCREMENT, \
                                    img TEXT, \
                                    img_file TEXT, \
                                    title TEXT, \
                                    item_url TEXT, \
                                    dates TEXT);''' % s_table_name)

                # DBに抽出したデータを保存
                if len(result) > 0:
                    for item in result:
                        c1.execute(
                            '''INSERT INTO '%s' (img, img_file, title, item_url, dates) VALUES (?, ?, ?, ?, ?)''' % s_table_name,
                            (item['img'], item['img_file'], item['title'], item['item_url'], item['dates']))
                c1.close()
            else:
                c1.close()
        conn1.commit()
        conn1.close()

        # DBデータから条件のデータを抽出
        sel_datas = []
        for table in s_lis:
            sel_data = select_data(bland, table[0])
            sel_datas.extend(sel_data)
        sel_datas.sort(key=lambda x: x['dates'], reverse=True)

    return sel_datas


def create_shopper_url(shopper_url):
    x = shopper_url.split('.')
    x[-2] = x[-2] + '/sales_1'
    x2 = 'https://www.' + '.'.join(x)
    return x2


@log
def select_data(bland, table_name):
    logger.info(f'ショッパーURL: {table_name}')
    new_conn1 = sqlite3.connect('saled.sqlite3')

    # データをDBから抽出
    new_conn1.row_factory = sqlite3.Row
    new_c1 = new_conn1.cursor()
    new_c1.execute(''' SELECT * from '%s' ''' % table_name)
    rows = new_c1.fetchall()
    saled_data = ([dict(i) for i in rows])
    logger.info(f'ショッパー受注商品数: {len(saled_data)}')
    new_conn1.close()

    # データからブランド名が入っているものを抽出
    select_data = []
    for x in saled_data:
        if x['title']:
            if bland in x['title'].replace(' ', '').lower():
                select_data.append(x)
    logger.info(f'ブランド受注商品数: {len(select_data)}')
    return select_data


@crochet.run_in_reactor
def scrape_with_crochet(baseURL):
    dispatcher.connect(_crawler_result, signal=signals.item_scraped)
    eventual = crawl_runner.crawl(SaledSpider, category=baseURL)
    return eventual


def _crawler_result(item, response, spider):
    output_data.append(dict(item))
