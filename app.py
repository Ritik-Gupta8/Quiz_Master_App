from flask import Flask, send_from_directory
from flask_compress import Compress
from models.models import db, User
from flask_login import LoginManager
from flask_session import Session
from werkzeug.security import generate_password_hash
from flask_migrate import Migrate
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

    # Performance: Cache static files for 1 year in browser
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000

    # Performance: Enable Gzip/Brotli compression on all responses
    Compress(app)
    db.init_app(app)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # Configure Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "signin"
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Configure Flask-Session — store sessions in database (persistent across Render restarts)
    app.config["SESSION_TYPE"] = "sqlalchemy"
    app.config["SESSION_SQLALCHEMY"] = db
    app.config["SESSION_PERMANENT"] = False

    # Security: Proper session cookie settings (these MUST be in app.config, not just env vars)
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"  # HTTPS only in prod
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access to session cookie
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Prevent CSRF via cross-site requests
    app.config["SESSION_COOKIE_NAME"] = "session"  # Explicit cookie name
    Session(app)
    
    @app.before_request
    def log_session_info():
        # Verification logging for session debugging
        from flask import session, request
        from flask_login import current_user
        user_name = current_user.full_name if current_user.is_authenticated else "Guest"
        sid = getattr(session, 'sid', 'No SID')
        print(f"--- [SESSION LOG] User: {user_name} | SessionSID: {sid} | Request: {request.path} ---")

    @app.after_request
    def add_cache_headers(response):
        # FORCE strict security headers for all dynamic responses to prevent cross-user leakage
        # We removed the 'if' check to ensure these are ALWAYS applied, overriding any defaults.
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Vary'] = 'Cookie'  # Ensure proxies vary content based on session cookie
        return response
    
    app.app_context().push()
    
    # Create an admin user if tables exist
    try:
        create_admin()
    except Exception as e:
        print("⚠️ Skipping admin creation (Database tables might not be migrated yet).")

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
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)