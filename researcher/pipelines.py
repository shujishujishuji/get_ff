# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import json
import sqlite3
import os
from itemadapter import ItemAdapter


class ResearcherPipeline:
    _db = None

    @classmethod
    def get_database(cls):
        cls._db = sqlite3.connect(os.path.join(os.getcwd(), 'items.sqlite3'))

        cursor = cls._db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS bland(\
                            id INTEGER PRIMARY KEY AUTOINCREMENT, \
                            img TEXT, \
                            img_file TEXT, \
                            title TEXT, \
                            price TEXT, \
                            shopper_status TEXT, \
                            shopper_name TEXT, \
                            shopper_url TEXT, \
                            category TEXT);')
        return cls._db

    def process_item(self, item, spider):
        self.save_bland(item)
        return item

    def save_bland(self, item):
        if self.find_bland(item['img']):
            return

        db = self.get_database()
        db.execute(
            'INSERT INTO bland (img, img_file, title, price, shopper_status, shopper_name, shopper_url, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (item['img'], item['img_file'], item['title'], item['price'], item['shopper_status'], item['shopper_name'], item['shopper_url'], item['category'])
        )
        db.commit()

    def find_bland(self, img):
        db = self.get_database()
        cursor = db.execute('SELECT * FROM bland WHERE img=?', (img,))
        return cursor.fetchone()


class JsonWriterPipeline:

    def open_spider(self, spider):
        self.file = open('items.jl', 'w')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(ItemAdapter(item).asdict()) + "\n"
        self.file.write(line)
        return item