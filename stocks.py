from flask import Blueprint, request
from sqlalchemy.orm import sessionmaker
import os
import shutil

from logger import log
from db import Stock, engine

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