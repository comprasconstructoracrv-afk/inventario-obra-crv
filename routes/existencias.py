from io import BytesIO
from flask import Blueprint, render_template, request, send_file, session
from flask_login import login_required
from sqlalchemy import func
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas

from models.existencia import Existencia
from models.movimiento import Movimiento
from models.obra import Obra
from models.producto import Producto

existencias_bp = Blueprint("existencias", __name__)


def obtener_resumen_existencias(obra_id=None):
    empresa_id = session.get("empresa_id")
    query = Existencia.query

    if obra_id:
        query = query.filter_by(obra_id=obra_id)
    elif empresa_id:
        bodegas = Obra.query.filter_by(empresa_id=empresa_id).all()
        bodega_ids = [b.id for b in bodegas]
        if bodega_ids:
            query = query.filter(Existencia.obra_id.in_(bodega_ids))
        else:
            return [], {}

    existencias = query.all()
    resumen = {}
    existencias_validas = []

    for e in existencias:
        if not e.producto:
            continue

        ingresos = Movimiento.query.with_entities(
            func.coalesce(func.sum(Movimiento.cantidad), 0)
        ).filter_by(
            producto_id=e.producto_id,
            obra_id=e.obra_id,
            tipo="INGRESO"
        ).scalar()

        salidas = Movimiento.query.with_entities(
            func.coalesce(func.sum(Movimiento.cantidad), 0)
        ).filter_by(
            producto_id=e.producto_id,
            obra_id=e.obra_id,
            tipo="SALIDA"
        ).scalar()

        resumen[e.id] = {
            "ingresos": ingresos,
            "salidas": salidas,
            "disponible": e.cantidad
        }

        existencias_validas.append(e)

    return existencias_validas, resumen


@existencias_bp.route("/existencias")
@login_required
def listar_bodegas_inventario():
    empresa_id = session.get("empresa_id")

    if empresa_id:
        bodegas = Obra.query.filter_by(empresa_id=empresa_id).order_by(Obra.nombre.asc()).all()
    else:
        bodegas = Obra.query.order_by(Obra.nombre.asc()).all()

    bodegas_data = []

    for bodega in bodegas:
        existencias = Existencia.query.filter_by(obra_id=bodega.id).all()

        total_productos = 0
        total_cantidad = 0

        for e in existencias:
            if e.cantidad > 0:
                total_productos += 1
                total_cantidad += e.cantidad

        bodegas_data.append({
            "bodega": bodega,
            "total_productos": total_productos,
            "total_cantidad": total_cantidad
        })

    return render_template(
        "existencias/bodegas.html",
        bodegas_data=bodegas_data
    )


@existencias_bp.route("/existencias/bodega/<int:obra_id>")
@login_required
def inventario_por_bodega(obra_id):
    bodega = Obra.query.get_or_404(obra_id)
    tipo_filtro = request.args.get("tipo", "TODOS").upper()
    existencias_todas, resumen = obtener_resumen_existencias(obra_id)

    # 2. Conteo total
    conteo_todos = len(existencias_todas)
    tipos_conteo = {}

    for e in existencias_todas:
        if e.producto:
            tipo = (getattr(e.producto, "tipo_producto", "OBRA") or "OBRA").upper()
            tipos_conteo[tipo] = tipos_conteo.get(tipo, 0) + 1

    iconos_map = {
        "OBRA": "🏗️",
        "BICICLETA": "🚲",
        "REPUESTO": "⚙️"
    }

    categorias_cards = []
    for tipo_nombre, cantidad in tipos_conteo.items():
        icono = iconos_map.get(tipo_nombre, "📦")
        categorias_cards.append({
            "codigo": tipo_nombre,
            "nombre": tipo_nombre.capitalize(),
            "icono": icono,
            "cantidad": cantidad
        })

    # 4. Filtrar lista según el tipo_producto seleccionado
    if tipo_filtro != "TODOS":
        existencias = [
            e for e in existencias_todas
            if e.producto and (getattr(e.producto, "tipo_producto", "OBRA") or "OBRA").upper() == tipo_filtro
        ]
    else:
        existencias = existencias_todas

    return render_template(
        "existencias/lista.html",
        bodega=bodega,
        existencias=existencias,
        resumen=resumen,
        tipo_filtro=tipo_filtro,
        conteo_todos=conteo_todos,
        categorias_cards=categorias_cards
    )


@existencias_bp.route("/existencias/excel")
@login_required
def exportar_existencias_excel():
    existencias, resumen = obtener_resumen_existencias()

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario"

    ws.append(["VER INVENTARIO"])
    ws.append([])
    ws.append(["Producto", "Unidad", "Bodega", "Ingresos", "Salidas", "Disponible", "Estado"])

    for e in existencias:
        disponible = resumen[e.id]["disponible"]

        if disponible <= 0:
            estado = "AGOTADO"
        elif disponible <= e.producto.stock_minimo:
            estado = "STOCK BAJO"
        else:
            estado = "DISPONIBLE"

        ws.append([
            e.producto.nombre,
            e.producto.unidad,
            e.obra.nombre,
            resumen[e.id]["ingresos"],
            resumen[e.id]["salidas"],
            disponible,
            estado
        ])

    archivo = BytesIO()
    wb.save(archivo)
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name="inventario_general.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@existencias_bp.route("/existencias/pdf")
@login_required
def exportar_existencias_pdf():
    existencias, resumen = obtener_resumen_existencias()

    archivo = BytesIO()
    pdf = canvas.Canvas(archivo, pagesize=landscape(letter))

    width, height = landscape(letter)
    y = height - 45

    def encabezado():
        nonlocal y
        y = height - 45
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(30, y, "REPORTE GENERAL DE INVENTARIO")
        y -= 25

        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(30, y, "Producto")
        pdf.drawString(270, y, "Unidad")
        pdf.drawString(350, y, "Bodega")
        pdf.drawString(450, y, "Ingresos")
        pdf.drawString(530, y, "Salidas")
        pdf.drawString(610, y, "Disponible")
        pdf.drawString(710, y, "Estado")
        y -= 12

        pdf.line(30, y, 770, y)
        y -= 12

    encabezado()
    pdf.setFont("Helvetica", 7)

    for e in existencias:
        if y < 45:
            pdf.showPage()
            encabezado()
            pdf.setFont("Helvetica", 7)

        disponible = resumen[e.id]["disponible"]

        if disponible <= 0:
            estado = "AGOTADO"
        elif disponible <= e.producto.stock_minimo:
            estado = "STOCK BAJO"
        else:
            estado = "DISPONIBLE"

        pdf.drawString(30, y, str(e.producto.nombre)[:42])
        pdf.drawString(270, y, str(e.producto.unidad)[:12])
        pdf.drawString(350, y, str(e.obra.nombre)[:16])
        pdf.drawString(450, y, str(resumen[e.id]["ingresos"]))
        pdf.drawString(530, y, str(resumen[e.id]["salidas"]))
        pdf.drawString(610, y, str(disponible))
        pdf.drawString(710, y, estado)
        y -= 12

    pdf.save()
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name="inventario_general.pdf",
        mimetype="application/pdf"
    )


@existencias_bp.route("/existencias/bodega/<int:obra_id>/excel")
@login_required
def exportar_bodega_excel(obra_id):
    bodega = Obra.query.get_or_404(obra_id)
    existencias, resumen = obtener_resumen_existencias(obra_id)

    wb = Workbook()
    ws = wb.active
    ws.title = bodega.nombre

    ws.append([f"INVENTARIO - {bodega.nombre}"])
    ws.append([])
    ws.append(["Producto", "Unidad", "Ingresos", "Salidas", "Disponible", "Estado"])

    for e in existencias:
        disponible = resumen[e.id]["disponible"]

        if disponible <= 0:
            estado = "AGOTADO"
        elif disponible <= e.producto.stock_minimo:
            estado = "STOCK BAJO"
        else:
            estado = "DISPONIBLE"

        ws.append([
            e.producto.nombre,
            e.producto.unidad,
            resumen[e.id]["ingresos"],
            resumen[e.id]["salidas"],
            disponible,
            estado
        ])

    archivo = BytesIO()
    wb.save(archivo)
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name=f"inventario_{bodega.nombre}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@existencias_bp.route("/existencias/bodega/<int:obra_id>/pdf")
@login_required
def exportar_bodega_pdf(obra_id):
    bodega = Obra.query.get_or_404(obra_id)
    existencias, resumen = obtener_resumen_existencias(obra_id)

    archivo = BytesIO()
    pdf = canvas.Canvas(archivo, pagesize=landscape(letter))

    width, height = landscape(letter)
    y = height - 45

    def encabezado():
        nonlocal y
        y = height - 45
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(30, y, f"INVENTARIO - {bodega.nombre}")
        y -= 25

        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(30, y, "Producto")
        pdf.drawString(300, y, "Unidad")
        pdf.drawString(400, y, "Ingresos")
        pdf.drawString(500, y, "Salidas")
        pdf.drawString(600, y, "Disponible")
        pdf.drawString(710, y, "Estado")
        y -= 12

        pdf.line(30, y, 770, y)
        y -= 12

    encabezado()
    pdf.setFont("Helvetica", 7)

    for e in existencias:
        if y < 45:
            pdf.showPage()
            encabezado()
            pdf.setFont("Helvetica", 7)

        disponible = resumen[e.id]["disponible"]

        if disponible <= 0:
            estado = "AGOTADO"
        elif disponible <= e.producto.stock_minimo:
            estado = "STOCK BAJO"
        else:
            estado = "DISPONIBLE"

        pdf.drawString(30, y, str(e.producto.nombre)[:48])
        pdf.drawString(300, y, str(e.producto.unidad)[:14])
        pdf.drawString(400, y, str(resumen[e.id]["ingresos"]))
        pdf.drawString(500, y, str(resumen[e.id]["salidas"]))
        pdf.drawString(600, y, str(disponible))
        pdf.drawString(710, y, estado)
        y -= 12

    pdf.save()
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name=f"inventario_{bodega.nombre}.pdf",
        mimetype="application/pdf"
    )