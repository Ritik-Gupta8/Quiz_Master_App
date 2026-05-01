from flask import Flask, send_from_directory, request, session
from flask_compress import Compress
from models.models import db, User
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
import uuid
from datetime import timedelta

load_dotenv()

app = None

def setup_app():
    global app
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

    # 🔐 SECRET KEY (must be set)
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY must be set in environment variables")
    app.config["SECRET_KEY"] = secret

    # 🔥 COOKIE CONFIG (fixed)
    app.config.update(
        SESSION_COOKIE_SECURE=False,   # ⚠️ IMPORTANT FIX
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_DOMAIN=None,
    )

    # 🔥 SESSION CONTROL
    app.config["SESSION_REFRESH_EACH_REQUEST"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=3)

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ⚡ Performance
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000
    Compress(app)

    db.init_app(app)
    migrate = Migrate(app, db)

    # 🔐 Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "signin"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 🔥 CRITICAL FIX — UNIQUE SESSION PER DEVICE
    @app.before_request
    def ensure_unique_session():
        if 'session_uuid' not in session:
            session['session_uuid'] = str(uuid.uuid4())

    # 🔥 NO-CACHE FOR DYNAMIC ROUTES
    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith('/static') or request.path in ['/sw.js', '/manifest.json']:
            return response

        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Vary'] = 'Cookie'  # 🔥 VERY IMPORTANT
        return response

    app.app_context().push()

    # Create admin if not exists
    try:
        create_admin()
    except Exception:
        print("⚠️ Skipping admin creation (DB not ready)")

def create_admin():
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if admin_email and admin_password:
        if not User.query.filter_by(email=admin_email).first():
            hashed_pw = generate_password_hash(admin_password, method='pbkdf2:sha256')
            admin = User(
                email=admin_email,
                password=hashed_pw,
                role=0,
                full_name="Administrator"
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created")

setup_app()

# Routes
from routes.auth_routes import init_auth_routes
from routes.admin_routes import init_admin_routes
from routes.user_routes import init_user_routes
from routes.quiz_routes import init_quiz_routes
from routes.analytics_routes import init_analytics_routes
from routes.api_routes import init_api_routes

init_auth_routes(app)
init_admin_routes(app)
init_user_routes(app)
init_quiz_routes(app)
init_analytics_routes(app)
init_api_routes(app)

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)