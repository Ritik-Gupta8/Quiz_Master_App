from flask import Flask
from models.models import db, User
from flask_login import LoginManager
from flask_session import Session
from werkzeug.security import generate_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

app = None

def setup_app():
    global app
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "quiz-master-dev-secret-key-change-in-prod")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    
    # Configure Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "signin"
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Configure Flask-Session
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = False
    Session(app)
    
    app.app_context().push()
    
    # Create tables if they don't exist and create an admin user
    db.create_all()
    create_admin()

def create_admin():
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_email and admin_password:
        if not User.query.filter_by(email=admin_email).first():
            # Using the same hashing method as in controllers.py
            hashed_pw = generate_password_hash(admin_password, method='pbkdf2:sha256')
            admin = User(
                email=admin_email,
                password=hashed_pw,
                role=0,
                full_name="Administrator"
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created successfully.")

setup_app()

from routes.auth_routes import init_auth_routes
from routes.admin_routes import init_admin_routes
from routes.user_routes import init_user_routes
from routes.quiz_routes import init_quiz_routes
from routes.analytics_routes import init_analytics_routes
from routes.api_routes import init_api_routes

# Initialize all route modules cleanly
init_auth_routes(app)
init_admin_routes(app)
init_user_routes(app)
init_quiz_routes(app)
init_analytics_routes(app)
init_api_routes(app)

# AI Generation system is now configured and ready for local use
if __name__ == "__main__":
    app.run(debug=True)
