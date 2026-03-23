from flask import Flask
from models.models import db
import os

app = None

def setup_app():
    global app
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quiz_master.sqlite3"
    app.config["SECRET_KEY"] = os.urandom(24)
    db.init_app(app)
    app.app_context().push()

setup_app()

from controllers.controllers import *

if __name__ == "__main__":
    app.run(debug=True)
