from flask import Blueprint

from oauth2client.service_account import ServiceAccountCredentials
import gspread

from config import config_ini as cf

ssapp = Blueprint('ssapp', __name__)


def set_ss(key_file, sheet_name):
    """
        スプレッドシートのセッティング
    """
    # 2つのAPIを記述しないとリフレッシュトークンを3600秒毎に発行し続けなければならない
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file,
                                                                   scope)
    gc = gspread.authorize(credentials)
    wks = gc.open(sheet_name)
    return wks


@ssapp.route('/del_ss', methods=['GET'])
def del_cells():
    ss = set_ss(cf.get('SS_SHEET', 'KEY_FILE'), cf.get('SS_SHEET', 'SHEET_NAME')).worksheet('出品シート')
    del_lis = [['', '', '', '', '', '', '', '', '', ''] for _ in range(499)]
    del_z = [[''] for _ in range(499)]
    del_a = [['', ''] for _ in range(499)]
    ss_data = [{'range': 'A2:J500',
                'values': del_lis},
               {'range': 'Z2:Z500',
                'values': del_z},
               {'range': 'AD2:AE500',
                'values': del_a}]
    ss.batch_update(ss_data)
    return 'おわた、おわたwww'