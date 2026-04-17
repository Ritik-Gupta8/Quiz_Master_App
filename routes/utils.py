from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.signin"))
            
            # 0 for Admin, 1 for User
            role_map = {"admin": 0, "user": 1}
            required_role = role_map.get(role_name)
            
            if current_user.role != required_role:
                flash("Access Denied: You do not have permission to view this page.", "danger")
                return redirect(url_for("user.home") if current_user.role == 1 else redirect(url_for("admin.admin_dashboard")))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
