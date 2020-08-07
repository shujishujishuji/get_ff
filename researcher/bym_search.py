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


# create database model
engine = create_engine('sqlite:///buyma.sqlite3')
Base = declarative_base()


class Bland(Base):
    __tablename__ = 'bland'

    id = Column(Integer, primary_key=True)
    img = Column(Text)
    img_file = Column(Text)
    title = Column(Text)
    price = Column(Text)
    shopper_status = Column(Text)
    shopper_name = Column(Text)
    shopper_url = Column(Text)
    category = Column(Text)

    def to_dict(self):
        return {
            'id': int(self.id),
            'img': self.img,
            'img_file': self.img_file,
            'title': self.title,
            'price': self.price,
            'shopper_status': self.shopper_status,
            'shopper_name': self.shopper_name,
            'shopper_url': self.shopper_url,
            'category': self.category
        }

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


if __name__ == '__main__':
    bl = Bland()
    pprint(bl.average_price('JAMES PERSE / メンズファッション'))