from driver_setup import set_driver
from config import config_ini as cf
import pandas as pd
import time


# リサーチ関係
def research_bym():
    """buyer_lifeのランキングを取得する。
    """
    driver = set_driver('https://buyer-life.com/')
    login_btn = driver.find_element_by_id('header_login')
    login_btn.click()
    login_mail = driver.find_element_by_name('mail')
    login_mail.send_keys(cf.get('BUYMA', 'BUYMA_MAIL'))
    login_pass = driver.find_element_by_name('pw')
    login_pass.send_keys(cf.get('BUYMA', 'BUYMA_PASSWORD'))
    login_btn = driver.find_element_by_css_selector('#login_form > form > div.center > input')
    login_btn.click()
    time.sleep(1)
    driver.get("https://buyer-life.com/choice/brand/")
    time.sleep(5)
    b_lis = driver.find_element_by_id('brand_list')
    brand_list = b_lis.find_elements_by_class_name('list_item')
    brands = [x.text for x in brand_list]
    driver.quit()
    df = pd.DataFrame(brands)
    df.columns = ['name']
    df_s = pd.concat([df, df['name'].str.split('\n', expand=True)], axis=1).drop('name', axis=1)
    df_s.columns = ['name', 'ladies', 'mens', 'kids', 'a', 'b', 'c', 'd']
    df_s.to_csv('bym_bland_rank.csv')
