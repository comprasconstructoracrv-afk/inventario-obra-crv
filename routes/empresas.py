from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from extensions import db
from models.empresa import Empresa
from models.obra import Obra
from models.existencia import Existencia
from utils.permisos import solo_admin

empresas_bp = Blueprint("empresas", __name__)

@empresas_bp.route("/empresas")
@login_required
def listar_empresas():
    empresas = Empresa.query.order_by(Empresa.nombre.asc()).all()
    empresas_data = []

    for emp in empresas:
        # Consultar bodegas vinculadas a la empresa
        bodegas = Obra.query.filter_by(empresa_id=emp.id).all()
        bodega_ids = [b.id for b in bodegas]

        total_bodegas = len(bodegas)
        total_productos = 0
        total_cantidad = 0

        if bodega_ids:
            existencias = Existencia.query.filter(Existencia.obra_id.in_(bodega_ids)).all()
            productos_unicos = set()
            for e in existencias:
                if e.cantidad > 0:
                    productos_unicos.add(e.producto_id)
                    total_cantidad += e.cantidad
            total_productos = len(productos_unicos)

        empresas_data.append({
            "empresa": emp,
            "total_bodegas": total_bodegas,
            "total_productos": total_productos,
            "total_cantidad": total_cantidad
        })

    return render_template("empresas/lista.html", empresas_data=empresas_data)


@empresas_bp.route("/empresas/seleccionar/<int:id>")
@login_required
def seleccionar_empresa(id):
    empresa = Empresa.query.get_or_404(id)

    # Guardar la empresa seleccionada en la sesión activa
    session["empresa_id"] = empresa.id
    session["empresa_nombre"] = empresa.nombre

    flash(f"Sede seleccionada: {empresa.nombre}", "success")

    # Redirigir al dashboard interno / secundario
    return redirect(url_for("dashboard"))


@empresas_bp.route("/empresas/nueva", methods=["GET", "POST"])
@login_required
@solo_admin
def nueva_empresa():
    if request.method == "POST":
        nombre = request.form["nombre"].strip().upper()

        if Empresa.query.filter_by(nombre=nombre).first():
            flash("La empresa ya existe.", "danger")
            return redirect(url_for("empresas.nueva_empresa"))

        nueva = Empresa(nombre=nombre, estado="ACTIVO", activo=True)
        db.session.add(nueva)
        db.session.commit()
        return redirect(url_for("dashboard_principal"))

    return render_template("empresas/nueva.html")


@empresas_bp.route("/empresas/editar/<int:id>", methods=["GET", "POST"])
@login_required
@solo_admin
def editar_empresa(id):
    empresa = Empresa.query.get_or_404(id)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip().upper()
        estado = request.form.get("estado", "ACTIVO")

        if nombre and nombre != empresa.nombre:
            existe = Empresa.query.filter_by(nombre=nombre).first()
            if existe:
                flash("Ya existe otra empresa con ese nombre.", "danger")
                return redirect(url_for("empresas.editar_empresa", id=id))
            empresa.nombre = nombre

        empresa.estado = estado
        empresa.activo = True if estado == "ACTIVO" else False

        db.session.commit()
        flash(f"Empresa '{empresa.nombre}' actualizada correctamente.", "success")
        return redirect(url_for("dashboard_principal"))

    return render_template("empresas/editar.html", empresa=empresa)

@empresas_bp.route("/empresas/eliminar/<int:id>")
@login_required
@solo_admin
def eliminar_empresa(id):
    empresa = Empresa.query.get_or_404(id)
    nombre_empresa = empresa.nombre

    try:
        # Eliminar permanentemente la empresa de la base de datos
        db.session.delete(empresa)
        db.session.commit()
        flash(f"La empresa '{nombre_empresa}' ha sido eliminada permanentemente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"No se pudo eliminar la empresa '{nombre_empresa}' porque tiene registros asociados (bodegas, productos o movimientos).", "danger")

    return redirect(url_for("dashboard_principal"))