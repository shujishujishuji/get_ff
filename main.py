from flask import Blueprint, render_template


mainapp = Blueprint('mainapp', __name__)


# home画面の表示
@mainapp.route('/', methods=['GET'])
def index():
    return render_template(
        'index.html',
        title='Get-ff'
    )