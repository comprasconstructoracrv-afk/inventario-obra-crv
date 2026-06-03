from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from models.movimiento import Movimiento
from models.producto import Producto
from models.obra import Obra
from models.existencia import Existencia
from extensions import db
from models.destino import Destino
from models.existencia import Existencia
import json
from flask import render_template, request, redirect, url_for
from utils.permisos import solo_admin

movimientos_bp = Blueprint("movimientos", __name__)


def obtener_existencia(producto_id, obra_id):
    existencia = Existencia.query.filter_by(
        producto_id=producto_id,
        obra_id=obra_id
    ).first()

    if not existencia:
        existencia = Existencia(producto_id=producto_id, obra_id=obra_id, cantidad=0)
        db.session.add(existencia)
        db.session.flush()

    return existencia


def revertir_movimiento(movimiento):
    producto = Producto.query.get_or_404(movimiento.producto_id)
    existencia = obtener_existencia(movimiento.producto_id, movimiento.obra_id)

    if movimiento.tipo == "INGRESO":
        existencia.cantidad -= movimiento.cantidad
        producto.stock -= movimiento.cantidad
    elif movimiento.tipo == "SALIDA":
        existencia.cantidad += movimiento.cantidad
        producto.stock += movimiento.cantidad


def aplicar_movimiento(producto_id, obra_id, tipo, cantidad):
    producto = Producto.query.get_or_404(producto_id)
    existencia = obtener_existencia(producto_id, obra_id)

    if tipo == "INGRESO":
        existencia.cantidad += cantidad
        producto.stock += cantidad
        return True, ""

    if tipo == "SALIDA":
        if existencia.cantidad < cantidad:
            return False, "Error: No hay stock suficiente en esta bodega."

        existencia.cantidad -= cantidad
        producto.stock -= cantidad
        return True, ""

    return False, "Tipo de movimiento inválido."


@movimientos_bp.route("/movimientos")
@login_required
def listar_movimientos():
    buscar = request.args.get("buscar", "").strip()

    query = Movimiento.query.filter_by(tipo="SALIDA")

    if buscar:
        query = (
            query
            .join(Producto, Movimiento.producto_id == Producto.id)
            .join(Obra, Movimiento.obra_id == Obra.id)
            .outerjoin(Destino, Movimiento.destino_id == Destino.id)
            .filter(
                db.or_(
                    Producto.nombre.ilike(f"%{buscar}%"),
                    Obra.nombre.ilike(f"%{buscar}%"),
                    Destino.nombre.ilike(f"%{buscar}%"),
                    Movimiento.observaciones.ilike(f"%{buscar}%")
                )
            )
        )

    movimientos = query.order_by(Movimiento.fecha.desc()).all()

    return render_template(
        "movimientos/lista.html",
        movimientos=movimientos
    )


@movimientos_bp.route("/movimientos/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_movimiento():

    productos = Producto.query.order_by(
        Producto.nombre.asc()
    ).all()

    bodegas = Obra.query.order_by(
        Obra.nombre.asc()
    ).all()

    destinos = Destino.query.filter_by(
        activo=True
    ).order_by(
        Destino.nombre.asc()
    ).all()

    existencias = Existencia.query.filter(
        Existencia.cantidad > 0
    ).all()

    existencias_json = {}

    for e in existencias:
        existencias_json[str(e.producto_id)] = e.obra_id

    if request.method == "POST":

        producto_id = int(request.form["producto_id"])
        obra_id = int(request.form["obra_id"])
        destino_id = int(request.form["destino_id"])

        cantidad = float(request.form["cantidad"])

        observaciones = request.form.get(
            "observaciones",
            ""
        ).upper()

        ok, mensaje = aplicar_movimiento(
            producto_id,
            obra_id,
            "SALIDA",
            cantidad
        )

        if not ok:
            return mensaje

        movimiento = Movimiento(
            producto_id=producto_id,
            obra_id=obra_id,
            tipo="SALIDA",
            cantidad=cantidad,
            destino_id=destino_id,
            observaciones=observaciones
        )

        db.session.add(movimiento)
        db.session.commit()

        return redirect(
            url_for("movimientos.recibo_salida", id=movimiento.id)
        )

    return render_template(
        "movimientos/nuevo.html",
        productos=productos,
        bodegas=bodegas,
        destinos=destinos,
        existencias=existencias,
        existencias_json=json.dumps(existencias_json)
    )

@movimientos_bp.route("/movimientos/editar/<int:id>", methods=["GET", "POST"])
@login_required
@solo_admin
def editar_movimiento(id):
    movimiento = Movimiento.query.get_or_404(id)
    productos = Producto.query.order_by(Producto.nombre.asc()).all()
    bodegas = Obra.query.order_by(Obra.nombre.asc()).all()

    if request.method == "POST":
        revertir_movimiento(movimiento)

        producto_id = int(request.form["producto_id"])
        obra_id = int(request.form["obra_id"])
        tipo = request.form["tipo"]
        cantidad = float(request.form["cantidad"])
        destino = request.form.get("destino", "").upper()
        observaciones = request.form.get("observaciones", "").upper()

        ok, mensaje = aplicar_movimiento(producto_id, obra_id, tipo, cantidad)

        if not ok:
            db.session.rollback()
            return mensaje

        movimiento.producto_id = producto_id
        movimiento.obra_id = obra_id
        movimiento.tipo = tipo
        movimiento.cantidad = cantidad
        movimiento.destino = destino
        movimiento.observaciones = observaciones

        db.session.commit()

        return redirect(url_for("movimientos.listar_movimientos"))

    return render_template(
        "movimientos/editar.html",
        movimiento=movimiento,
        productos=productos,
        bodegas=bodegas
    )


@movimientos_bp.route("/movimientos/eliminar/<int:id>")
@login_required
@solo_admin
def eliminar_movimiento(id):
    movimiento = Movimiento.query.get_or_404(id)

    revertir_movimiento(movimiento)

    db.session.delete(movimiento)
    db.session.commit()

    return redirect(url_for("movimientos.listar_movimientos"))

@movimientos_bp.route("/movimientos/recibo-salida/<int:id>")
@login_required
def recibo_salida(id):
    movimiento = Movimiento.query.get_or_404(id)

    return render_template(
        "movimientos/recibo_salida.html",
        movimiento=movimiento
    )

@movimientos_bp.route(
    "/movimientos/recibo-salida-multiple"
)
@login_required
def recibo_salida_multiple():

    ids = request.args.get(
        "ids",
        ""
    )

    lista_ids = [
        int(x)
        for x in ids.split(",")
        if x
    ]

    movimientos = Movimiento.query.filter(
        Movimiento.id.in_(lista_ids)
    ).all()

    return render_template(
        "movimientos/recibo_salida_multiple.html",
        movimientos=movimientos
    )

@movimientos_bp.route(
    "/movimientos/nuevo-multiple",
    methods=["GET", "POST"]
)
@login_required
def nuevo_movimiento_multiple():

    productos = Producto.query.order_by(
        Producto.nombre.asc()
    ).all()

    destinos = Destino.query.filter_by(
        activo=True
    ).order_by(
        Destino.nombre.asc()
    ).all()

    if request.method == "POST":

        destino_id = int(
            request.form["destino_id"]
        )

        observaciones = request.form.get(
            "observaciones",
            ""
        ).upper()

        productos_ids = request.form.getlist(
            "producto_id[]"
        )

        cantidades = request.form.getlist(
            "cantidad[]"
        )

        movimientos_creados = []

        for producto_id, cantidad in zip(
            productos_ids,
            cantidades
        ):

            if not cantidad:
                continue

            producto_id = int(producto_id)
            cantidad = float(cantidad)

            existencia = Existencia.query.filter(
                Existencia.producto_id == producto_id,
                Existencia.cantidad > 0
            ).first()

            if not existencia:
                return f"No existe inventario para el producto ID {producto_id}"

            ok, mensaje = aplicar_movimiento(
                producto_id,
                existencia.obra_id,
                "SALIDA",
                cantidad
            )

            if not ok:
                return mensaje

            movimiento = Movimiento(
                producto_id=producto_id,
                obra_id=existencia.obra_id,
                tipo="SALIDA",
                cantidad=cantidad,
                destino_id=destino_id,
                observaciones=observaciones
            )

            db.session.add(movimiento)

            movimientos_creados.append(
                movimiento
            )

        db.session.commit()

        ids = [
            str(m.id)
            for m in movimientos_creados
        ]

        return redirect(
            url_for(
                "movimientos.recibo_salida_multiple",
                ids=",".join(ids)
            )
        )

    return render_template(
        "movimientos/nuevo_multiple.html",
        productos=productos,
        destinos=destinos
    )