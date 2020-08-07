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
from researcher.spiders.bym_spider import BlandSpider

from flask import request, Blueprint, jsonify, url_for, redirect
from db import engine, Bland

researchapp = Blueprint('researchapp', __name__)

output_data = []
crawl_runner = CrawlerRunner()

new_date = dt.now().strftime('%Y%m%d')


def get_all_items(self):
    Session = sessionmaker(bind=engine)
    ses = Session()
    res = ses.query(Bland).all()
    ses.close()
    bland = [item.to_dict() for item in res]
    return bland


def get_all_img(self):
    Session = sessionmaker(bind=engine)
    ses = Session()
    res = ses.query(Bland).all()
    ses.close()
    bland = [item.to_dict() for item in res]
    if not os.path.exists('items'):
        os.makedirs('items')
    for bl in bland:
        img_file = bl['img'].split('/')[-2] + '.jpg'
        urllib.request.urlretrieve(bl['img'], os.path.join('items', img_file))
    return bland


def find_items_by_category(self, category):
    Session = sessionmaker(bind=engine)
    ses = Session()
    res = ses.query(Bland).filter_by(category=category)
    ses.close()
    item_lis = [item.to_dict() for item in res]
    return item_lis


def average_price(self, category):
    items_lis = self.find_items_by_category(category)
    price_lis = [int(re.sub("\\D", "", price['price'])) for price in items_lis]
    return round(sum(price_lis) / len(price_lis))


@researchapp.route('/bland_research', methods=['POST'])
def bland_research():
    if request.method == 'POST':
        s = request.form['research_url']
        global baseURL
        baseURL = s

        result = scrape()

        return jsonify(result)


def scrape():
    global baseURL
    global output_data
    table_name = baseURL.split("/")[-2] + new_date
    conn = sqlite3.connect('bland.sqlite3')
    # テーブルがあるかどうか確認
    c = conn.cursor()
    c.execute('''SELECT count(name) FROM sqlite_master WHERE name='%s' AND type='table' '''%table_name)

    if(c.fetchone()[0] == 0):
        # テーブルがなかった場合は作成
        scrape_with_crochet(baseURL=baseURL)
        time.sleep(100)

        conn.execute('''CREATE TABLE '%s' (\
                            id INTEGER PRIMARY KEY AUTOINCREMENT, \
                            img TEXT, \
                            img_file TEXT, \
                            title TEXT, \
                            price TEXT, \
                            shopper_status TEXT, \
                            shopper_name TEXT, \
                            shopper_url TEXT, \
                            category TEXT);''' % table_name)

        for item in output_data:
            c.execute(
                '''INSERT INTO '%s' (img, img_file, title, price, shopper_status, shopper_name, shopper_url, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''' % table_name,
                (item['img'], item['img_file'], item['title'], item['price'], item['shopper_status'], item['shopper_name'], item['shopper_url'], item['category']))
        conn.commit()
        conn.close()

    else:
        # テーブルがあればそのデータを取得
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(''' SELECT * from '%s' ''' % table_name)
        rows = cur.fetchall()
        output_data = ([dict(i) for i in rows])
        conn.close()

    return output_data


@crochet.run_in_reactor
def scrape_with_crochet(baseURL):
    dispatcher.connect(_crawler_result, signal=signals.item_scraped)
    eventual = crawl_runner.crawl(BlandSpider, category=baseURL)
    return eventual


def _crawler_result(item, response, spider):
    output_data.append(dict(item))
