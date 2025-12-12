# Starting of the application
from flask import Flask
from models.models import db
import os

app = None

def setup_app():
    global app  # This makes sure you're modifying the global `app` variable
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quiz_master.sqlite3"  # Having db file
    db.init_app(app)  # Flask app connected to db 
    app.app_context().push()  # Direct access to other modules
    print("Quiz master app is started..")

# Call the function
setup_app()

# app.config["SECRET_KEY"] = os.urandom(24)  # Generates a random secret key


from controllers.controllers import *

if __name__ == "__main__":
    app.run(debug = True)
