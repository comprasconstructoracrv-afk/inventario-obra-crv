from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_login import login_required
from datetime import datetime

from models.producto import Producto
from models.obra import Obra
from models.existencia import Existencia
from models.movimiento import Movimiento
from extensions import db
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


from sqlalchemy import func

@productos_bp.route("/productos")
@login_required
def listar_productos():
    buscar = request.args.get("buscar", "").strip()
    tipo_filtro = request.args.get("tipo", "TODOS").upper()
    empresa_id = session.get("empresa_id")

    # 🔍 Filtrar productos base por la empresa activa
    if empresa_id:
        base_query = Producto.query.filter_by(empresa_id=empresa_id)
    else:
        base_query = Producto.query

    # 1. Obtener conteo total
    conteo_todos = base_query.count()

    # 2. Consultar TODOS los tipos de productos existentes dinámicamente en la base de datos
    # Devuelve una lista de tuplas: [('OBRA', 10), ('BICICLETA', 5), ('REPUESTO', 8), ('HERRAMIENTAS', 2)]
    tipos_dinamicos_query = (
        db.session.query(
            Producto.tipo_producto, 
            func.count(Producto.id)
        )
        .filter(Producto.empresa_id == empresa_id if empresa_id else True)
        .group_by(Producto.tipo_producto)
        .all()
    )

    # Definir iconos por defecto para los tipos más comunes
    iconos_map = {
        "OBRA": "🏗️",
        "BICICLETA": "🚲",
        "REPUESTO": "⚙️"
    }

    # Estructurar la lista de categorías para la plantilla
    categorias_cards = []
    for tipo_nombre, cantidad in tipos_dinamicos_query:
        if not tipo_nombre:
            tipo_nombre = "OBRA"
            
        nombre_upper = tipo_nombre.upper()
        icono = iconos_map.get(nombre_upper, "📦") # Si es un tipo nuevo personalizado, asigna el icono 📦
        
        categorias_cards.append({
            "codigo": nombre_upper,
            "nombre": nombre_upper.capitalize(),
            "icono": icono,
            "cantidad": cantidad
        })

    # 3. Aplicar filtro por tipo de producto en la consulta principal
    productos_query = base_query
    if tipo_filtro != "TODOS":
        productos_query = productos_query.filter(Producto.tipo_producto == tipo_filtro)

    # 4. Aplicar búsqueda por nombre o código
    if buscar:
        productos_query = productos_query.filter(
            (Producto.nombre.ilike(f"%{buscar}%")) |
            (Producto.codigo.ilike(f"%{buscar}%"))
        )

    productos = productos_query.order_by(Producto.nombre.asc()).all()

    # 5. Cargar información de bodegas para cada producto
    producto_bodegas = {}
    for p in productos:
        existencias = Existencia.query.filter_by(producto_id=p.id).all()
        bodegas = []
        for e in existencias:
            if e.cantidad > 0:
                cant_fmt = "{:,.2f}".format(e.cantidad).replace(",", "X").replace(".", ",").replace("X", ".")
                ubicacion = e.obra.ubicacion if e.obra.ubicacion else "Sin ubicación"
                bodegas.append(f"{e.obra.nombre}- {ubicacion}: {cant_fmt} {p.unidad}")
        producto_bodegas[p.id] = bodegas

    return render_template(
        "productos/lista.html",
        productos=productos,
        producto_bodegas=producto_bodegas,
        tipo_filtro=tipo_filtro,
        buscar=buscar,
        conteo_todos=conteo_todos,
        categorias_cards=categorias_cards
    )


@productos_bp.route("/productos/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_producto():
    empresa_id = session.get("empresa_id")

    # Filtrar bodegas solo de la empresa seleccionada
    if empresa_id:
        bodegas = Obra.query.filter_by(empresa_id=empresa_id).order_by(Obra.nombre.asc()).all()
    else:
        bodegas = Obra.query.order_by(Obra.nombre.asc()).all()

    codigo = generar_codigo_producto()

    if request.method == "POST":
        nombre = request.form["nombre"].upper()

        # Validar si el producto ya existe en ESTA empresa
        if empresa_id:
            producto_existente = Producto.query.filter(
                Producto.nombre.ilike(nombre),
                Producto.empresa_id == empresa_id
            ).first()
        else:
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

        # Validar si el código ya existe en ESTA empresa
        if empresa_id:
            codigo_existente = Producto.query.filter_by(
                codigo=request.form["codigo"],
                empresa_id=empresa_id
            ).first()
        else:
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
        cantidad_input = request.form["cantidad"]
        cantidad = round(float(cantidad_input),2)
        unidad = request.form["unidad"].upper()

        if unidad == "OTRO":
            unidad = request.form["unidad_personalizada"].upper()

        # CAPTURAR TIPO DE PRODUCTO (OBRA, BICICLETA, REPUESTO U OTRO PERSONALIZADO)
        tipo_producto = request.form.get("tipo_producto", "OBRA").upper()
        if tipo_producto == "OTRO":
            tipo_producto = request.form.get("tipo_producto_personalizado", "OBRA").upper()

        # Guardar asignando empresa_id y tipo_producto
        producto = Producto(
            codigo=request.form["codigo"],
            nombre=nombre,
            categoria=request.form["categoria"].upper(),
            tipo_producto=tipo_producto, # Nuevo campo guardado
            unidad=unidad,
            stock=cantidad,
            stock_minimo=0,
            activo=True,
            empresa_id=empresa_id
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
    empresa_id = session.get("empresa_id")

    # 🔍 Filtrar bodegas de la empresa activa
    if empresa_id:
        bodegas = Obra.query.filter_by(empresa_id=empresa_id).order_by(Obra.nombre.asc()).all()
    else:
        bodegas = Obra.query.order_by(Obra.nombre.asc()).all()

    if request.method == "POST":
        obra_id = int(request.form["obra_id"])
        cantidad = float(request.form["cantidad"])
        responsable = request.form.get("responsable", "").upper()
        observaciones = request.form.get("observaciones", "").upper()
        responsable = request.form.get("responsable", "").upper()

        producto.stock += cantidad

        existencia = obtener_existencia(producto.id, obra_id)
        existencia.cantidad += cantidad

        movimiento = Movimiento(
            producto_id=producto.id,
            obra_id=obra_id,
            tipo="INGRESO",
            cantidad=cantidad,
            observaciones=f"INGRESO DE PRODUCTO. RESPONSABLE: {responsable}. {observaciones}",
            responsable=responsable
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
        responsable=movimiento.responsable,
        fecha_ingreso=movimiento.fecha.strftime("%d/%m/%Y %H:%M")
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