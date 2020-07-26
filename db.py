from sqlalchemy import create_engine, Column, Integer, String, \
    Text, DateTime, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.functions import current_timestamp
from sqlalchemy.dialects.mysql import TIMESTAMP as Timestamp
import sqlite3


# create database model
engine = create_engine('sqlite:///items.sqlite3')
Base = declarative_base()


class Stock(Base):
    __tablename__ = 'stock'

    id = Column(Integer, primary_key=True)
    url = Column(String(255), unique=True)
    stock_info = Column(Text)
    buyma_id = Column(Integer)
    del_flg = Column(Integer, server_default=text("0"))
    created = Column(Timestamp, server_default=current_timestamp())
    updated = Column(Timestamp, server_default=current_timestamp())
    buyma_url = Column(String(255))

    def to_dict(self):
        return {
            'id': int(self.id),
            'url': str(self.url),
            'stock_info': str(self.stock_info),
            'buyma_id': str(self.buyma_id),
            'del_flg': int(self.del_flg),
            'created': str(self.created),
            'updated': str(self.updated),
            'buyma_url': str(self.buyma_url)
        }