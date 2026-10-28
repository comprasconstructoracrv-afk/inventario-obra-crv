from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models.usuario import Usuario
from models.empresa import Empresa
from functools import wraps

usuarios_bp = Blueprint("usuarios", __name__)

def admin_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if getattr(current_user, "rol", "") != "ADMIN":
            flash("Acceso denegado: Se requieren permisos de Administrador.", "danger")
            return redirect(url_for("productos.listar_productos"))
        return f(*args, **kwargs)
    return decorated_function


# PANEL UNIFICADO DE USUARIOS (LISTAR + CREAR + EDITAR)
@usuarios_bp.route("/usuarios", methods=["GET", "POST"])
@login_required
@admin_requerido
def gestion_usuarios():
    # Procesar creación o edición vía POST en la misma pantalla
    if request.method == "POST":
        action = request.form.get("action")
        
        # --- CREAR USUARIO ---
        if action == "crear":
            nombre = request.form.get("nombre", "").strip()
            usuario_str = request.form.get("usuario", "").strip().lower()
            password = request.form.get("password", "").strip()
            rol = request.form.get("rol", "ALMACENISTA")
            empresa_id = request.form.get("empresa_id")

            if Usuario.query.filter_by(usuario=usuario_str).first():
                flash("El nombre de usuario ya existe.", "warning")
                return redirect(url_for("usuarios.gestion_usuarios"))

            nuevo_u = Usuario(
                nombre=nombre,
                usuario=usuario_str,
                rol=rol,
                empresa_id=int(empresa_id) if empresa_id and rol == "ALMACENISTA" else None
            )
            nuevo_u.set_password(password)
            db.session.add(nuevo_u)
            db.session.commit()
            flash(f"Usuario '{nombre}' creado exitosamente.", "success")

        # --- EDITAR USUARIO ---
        elif action == "editar":
            user_id = int(request.form.get("user_id"))
            u = Usuario.query.get_or_404(user_id)
            
            u.nombre = request.form.get("nombre", "").strip()
            u.rol = request.form.get("rol", "ALMACENISTA")
            empresa_id = request.form.get("empresa_id")
            
            u.empresa_id = int(empresa_id) if empresa_id and u.rol == "ALMACENISTA" else None

            password = request.form.get("password", "").strip()
            if password:
                u.set_password(password)

            db.session.commit()
            flash(f"Usuario '{u.nombre}' actualizado correctamente.", "success")

        return redirect(url_for("usuarios.gestion_usuarios"))

    # Cargar datos para la vista
    usuarios = Usuario.query.order_by(Usuario.nombre.asc()).all()
    empresas = Empresa.query.filter_by(activo=True).order_by(Empresa.nombre.asc()).all()

    return render_template("usuarios/gestion.html", usuarios=usuarios, empresas=empresas)


# ELIMINAR USUARIO
@usuarios_bp.route("/usuarios/eliminar/<int:id>", methods=["POST", "GET"])
@login_required
@admin_requerido
def eliminar_usuario(id):
    if current_user.id == id:
        flash("No puedes eliminar tu propio usuario activo.", "danger")
        return redirect(url_for("usuarios.gestion_usuarios"))

    u = Usuario.query.get_or_404(id)
    db.session.delete(u)
    db.session.commit()
    flash("Usuario eliminado correctamente.", "success")
    return redirect(url_for("usuarios.gestion_usuarios"))