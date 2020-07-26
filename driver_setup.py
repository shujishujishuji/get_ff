import sys
from pathlib import Path

# ライブラリのパス
sys.path.append('/usr/local/lib/python3.7/site-packages')

# 上層階のファイルを読み込むためのパス
sys.path.append(str(Path(__file__).resolve().parent.parent))

import chromedriver_binary
from selenium import webdriver


# seleniumのdriverのセットアップ
def set_driver(url, headless=False):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')          # headlessモードで暫定的に必要なフラグ(そのうち不要になる)
    options.add_argument('--disable-extensions')       # すべての拡張機能を無効にする。ユーザースクリプトも無効にする
    options.add_argument('--proxy-server="direct://"') # Proxy経由ではなく直接接続する
    options.add_argument('--proxy-bypass-list=*')      # すべてのホスト名
    options.add_argument('--start-maximized')          # 起動時にウィンドウを最大化する
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.get(url)
    return driver