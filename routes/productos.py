from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from datetime import datetime

from models.producto import Producto
from models.obra import Obra
from models.existencia import Existencia
from models.movimiento import Movimiento
from extensions import db
from flask import redirect, url_for
from utils.permisos import solo_admin

productos_bp = Blueprint("productos", __name__)


def generar_codigo_producto():
    ultimo = Producto.query.order_by(Producto.id.desc()).first()
    if not ultimo:
        return "001"
    return str(ultimo.id + 1).zfill(3)


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


@productos_bp.route("/productos")
@login_required
def listar_productos():
    buscar = request.args.get("buscar", "")

    productos = Producto.query

    if buscar:
        productos = productos.filter(
            (Producto.nombre.contains(buscar.upper())) |
            (Producto.codigo.contains(buscar))
        )

    productos = productos.order_by(Producto.nombre.asc()).all()

    producto_bodegas = {}

    for p in productos:
        existencias = Existencia.query.filter_by(producto_id=p.id).all()
        bodegas = []

        for e in existencias:
            if e.cantidad > 0:
                cantidad = "{:,.2f}".format(e.cantidad).replace(",", "X").replace(".", ",").replace("X", ".")
                bodegas.append(f"{e.obra.nombre}: {cantidad} {p.unidad}")

        producto_bodegas[p.id] = bodegas

    return render_template(
        "productos/lista.html",
        productos=productos,
        producto_bodegas=producto_bodegas
    )


@productos_bp.route("/productos/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_producto():
    bodegas = Obra.query.order_by(Obra.nombre.asc()).all()
    codigo = generar_codigo_producto()

    if request.method == "POST":
        nombre = request.form["nombre"].upper()

        producto_existente = Producto.query.filter(
            Producto.nombre.ilike(nombre)
        ).first()

        if producto_existente:
            return render_template(
                "productos/nuevo.html",
                bodegas=bodegas,
                codigo=codigo,
                error_producto=f"El producto {nombre} ya existe. Debe usar la opción Ingresar para aumentar inventario."
            )

        codigo_existente = Producto.query.filter_by(
            codigo=request.form["codigo"]
        ).first()

        if codigo_existente:
            return """
            <h2 style='font-family:Arial'>
                El código ya existe.<br><br>
                <a href='/productos'>Volver a productos</a>
            </h2>
            """

        obra_id = int(request.form["obra_id"])
        cantidad = float(request.form["cantidad"])

        unidad = request.form["unidad"].upper()

        if unidad == "OTRO":
            unidad = request.form["unidad_personalizada"].upper()

        producto = Producto(
            codigo=request.form["codigo"],
            nombre=nombre,
            categoria=request.form["categoria"].upper(),
            unidad=unidad,
            stock=cantidad,
            stock_minimo=0,
            activo=True
        )

        db.session.add(producto)
        db.session.flush()

        existencia = obtener_existencia(producto.id, obra_id)
        existencia.cantidad += cantidad

        movimiento = Movimiento(
            producto_id=producto.id,
            obra_id=obra_id,
            tipo="INGRESO",
            cantidad=cantidad,
            observaciones="Registro inicial del producto"
        )

        db.session.add(movimiento)
        db.session.commit()

        return redirect(url_for("productos.listar_productos"))

    return render_template(
        "productos/nuevo.html",
        bodegas=bodegas,
        codigo=codigo
    )

@productos_bp.route("/productos/ingresar/<int:id>", methods=["GET", "POST"])
@login_required
def ingresar_producto(id):
    producto = Producto.query.get_or_404(id)
    bodegas = Obra.query.order_by(Obra.nombre.asc()).all()

    if request.method == "POST":
        obra_id = int(request.form["obra_id"])
        cantidad = float(request.form["cantidad"])
        responsable = request.form.get("responsable", "").upper()
        observaciones = request.form.get("observaciones", "").upper()

        producto.stock += cantidad

        existencia = obtener_existencia(producto.id, obra_id)
        existencia.cantidad += cantidad

        movimiento = Movimiento(
            producto_id=producto.id,
            obra_id=obra_id,
            tipo="INGRESO",
            cantidad=cantidad,
            observaciones=f"INGRESO DE PRODUCTO. RESPONSABLE: {responsable}. {observaciones}"
        )

        db.session.add(movimiento)
        db.session.commit()

        return redirect(url_for("productos.recibo_ingreso", movimiento_id=movimiento.id))

    return render_template(
        "productos/ingresar.html",
        producto=producto,
        bodegas=bodegas
    )

@productos_bp.route("/productos/recibo-ingreso/<int:movimiento_id>")
@login_required
def recibo_ingreso(movimiento_id):

    movimiento = Movimiento.query.get_or_404(movimiento_id)

    return render_template(
        "productos/recibo_ingreso.html",
        producto=movimiento.producto,
        bodega=movimiento.obra,
        cantidad=movimiento.cantidad,
        observaciones=movimiento.observaciones,
        fecha_ingreso=movimiento.fecha.strftime("%d/%m/%Y %H:%M"),
        responsable=""
    )

@productos_bp.route("/productos/editar/<int:id>", methods=["GET", "POST"])
@login_required
@solo_admin
def editar_producto(id):
    producto = Producto.query.get_or_404(id)

    if request.method == "POST":
        producto.nombre = request.form["nombre"].upper()
        producto.categoria = request.form["categoria"].upper()
        producto.unidad = request.form["unidad"].upper()
        producto.activo = True

        db.session.commit()
        return redirect(url_for("productos.listar_productos"))

    return render_template("productos/editar.html", producto=producto)


@productos_bp.route("/productos/eliminar/<int:id>")
@login_required
@solo_admin
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)

    # borrar movimientos del producto
    Movimiento.query.filter_by(producto_id=producto.id).delete()

    # borrar existencias del producto
    Existencia.query.filter_by(producto_id=producto.id).delete()

    # borrar producto
    db.session.delete(producto)
    db.session.commit()

    return redirect(url_for("productos.listar_productos"))