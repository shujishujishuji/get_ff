# get_ff
flask+vue.js+sqlite3のスクレイピング ツール

❶gitクローンする
git clone https://github.com/shujishujishuji/get_ff.git

❷requirements.txtをpip installする
pip install -r requirements.txt

❸sqlite3のデータベースを作成する
DB Browser for SQLiteを使用する
データベース名：items.sqlite3
SQL文：
CREATE TABLE IF NOT EXISTS "stock" (
        "id"    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        "url"   TEXT NOT NULL UNIQUE,
        "stock_info"    TEXT NOT NULL,
        "buyma_id"      INTEGER,
        "del_flg"       INTEGER DEFAULT 0,
        "created"       TIMESTAMP DEFAULT (datetime(CURRENT_TIMESTAMP,'localtime')),
        "updated"       TIMESTAMP DEFAULT (datetime(CURRENT_TIMESTAMP,'localtime'))
);

スプレッドシートの行数を超えるリスト登録しようとるすると、エラーになる
onesizeはサイズ表がないので、他のアイテムのサイズ表を取得してしまう。
chromedriverとchromeのバージョンがあってないと、ブラウザが開いて即閉じるエラーがでる