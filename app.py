"""
＊＊＊＊＊＊＊＊＊＊＊＊取扱説明書＊＊＊＊＊＊＊＊＊
出品スケジュール
1.商品を探してURLをSPシート(出品シート[I]列)に貼り付け
2.自動で商品情報を取得
3.SPシートの編集
4.自動で出品
5.自動で一日一回在庫管理
6.在庫状況に変化のあったものを削除
"""
from set_app import create_app

app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='localhost')