from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from models.producto import Producto
from models.obra import Obra
from models.movimiento import Movimiento
from models.existencia import Existencia
from extensions import db

traslados_bp = Blueprint("traslados", __name__)


def obtener_existencia(producto_id, obra_id):
    existencia = Existencia.query.filter_by(
        producto_id=producto_id,
        obra_id=obra_id
    ).first()

    if not existencia:
        existencia = Existencia(
            producto_id=producto_id,
            obra_id=obra_id,
            cantidad=0
        )
        db.session.add(existencia)
        db.session.flush()

    return existencia


@traslados_bp.route("/traslados/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_traslado():
    productos = Producto.query.order_by(Producto.nombre.asc()).all()
    bodegas = Obra.query.order_by(Obra.nombre.asc()).all()
    existencias = Existencia.query.all()

    if request.method == "POST":
        producto_id = int(request.form["producto_id"])
        bodega_origen_id = int(request.form["bodega_origen_id"])
        bodega_destino_id = int(request.form["bodega_destino_id"])
        cantidad = float(request.form["cantidad"])
        observacion = request.form.get("observacion", "")

        if bodega_origen_id == bodega_destino_id:
            return "Error: La bodega origen y destino no pueden ser iguales."

        existencia_origen = obtener_existencia(producto_id, bodega_origen_id)
        existencia_destino = obtener_existencia(producto_id, bodega_destino_id)

        if existencia_origen.cantidad < cantidad:
            return "Error: No hay stock suficiente en la bodega origen."

        existencia_origen.cantidad -= cantidad
        existencia_destino.cantidad += cantidad

        salida = Movimiento(
            producto_id=producto_id,
            obra_id=bodega_origen_id,
            tipo="SALIDA",
            cantidad=cantidad,
            observaciones=f"TRASLADO A BODEGA DESTINO. {observacion}"
        )

        ingreso = Movimiento(
            producto_id=producto_id,
            obra_id=bodega_destino_id,
            tipo="INGRESO",
            cantidad=cantidad,
            observaciones=f"TRASLADO DESDE BODEGA ORIGEN. {observacion}"
        )

        db.session.add(salida)
        db.session.add(ingreso)
        db.session.commit()

        return redirect(url_for("movimientos.listar_movimientos"))

    return render_template(
        "traslados/nuevo.html",
        productos=productos,
        bodegas=bodegas,
        existencias=existencias
    )