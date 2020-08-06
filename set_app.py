from flask import Flask

from set_spsheet import ssapp
from ff import ffapp
from stocks import stockapp
from bym import bymapp
from main import mainapp
from aso import asoapp
from picture_cut import picapp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(mainapp)
    app.register_blueprint(ssapp)
    app.register_blueprint(ffapp)
    app.register_blueprint(stockapp)
    app.register_blueprint(bymapp)
    app.register_blueprint(asoapp)
    app.register_blueprint(picapp)

    return app