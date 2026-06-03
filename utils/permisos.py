from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user


def solo_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if current_user.rol != "ADMIN":
            flash("No tiene permisos para realizar esta acción.", "permiso")
            return redirect(request.referrer or url_for("dashboard"))

        return f(*args, **kwargs)

    return decorated_function