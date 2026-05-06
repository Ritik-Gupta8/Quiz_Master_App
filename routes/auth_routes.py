from flask import render_template, request, url_for, redirect, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.models import db, User

def init_auth_routes(app):
    @app.route("/") 
    def home():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.route("/support")
    def support():
        return render_template("support.html")


    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("signin"))

    @app.route("/login", methods=["GET", "POST"])
    def signin():
        if current_user.is_authenticated:
            if current_user.role == 0:
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("user_dashboard"))

        if request.method == "POST":
            uname = request.form.get("user_name")
            pwd = request.form.get("password")

            usr = User.query.filter_by(email=uname).first()
            if not usr:
                flash("User not found. Please check your email or register a new account.", "danger")
                return render_template("login.html")
                
            if check_password_hash(usr.password, pwd):
                # Clear session to prevent cross-user session leakage or fixation
                session.clear()
                login_user(usr)
                print(f"--- [LOGIN SUCCESS] User: {usr.full_name} | Email: {usr.email} | New Session: {session.get('_id', 'Pending')} ---")
                if usr.role == 0:
                    return redirect(url_for("admin_dashboard"))
                elif usr.role == 1:
                    return redirect(url_for("user_dashboard")) 
            else:
                flash("Incorrect password. Please try again.", "danger")
                return render_template("login.html")

        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            uname = request.form.get("user_name")
            pwd = request.form.get("password")
            full_name = request.form.get("full_name")
            qualification = request.form.get("qualification")
         
            usr = User.query.filter_by(email=uname).first()
            if usr:
                return render_template("register.html", msg="This email is already registered. Please log in.")

            hashed_pwd = generate_password_hash(pwd, method='pbkdf2:sha256')
            new_usr = User(email=uname, password=hashed_pwd, full_name=full_name, qualification=qualification)
            db.session.add(new_usr)
            db.session.commit()
            return render_template("login.html", msg1="Thank you for registering! Try logging in now.")

        return render_template("register.html")
