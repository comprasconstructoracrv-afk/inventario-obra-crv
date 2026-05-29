from flask import Blueprint, render_template, send_file
from flask_login import login_required
from sqlalchemy import func
from models.existencia import Existencia
from models.movimiento import Movimiento
from models.obra import Obra
from io import BytesIO
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

existencias_bp = Blueprint("existencias", __name__)

def obtener_resumen_existencias(obra_id=None):
    query = Existencia.query

    if obra_id:
        query = query.filter_by(obra_id=obra_id)

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
    existencias, resumen = obtener_resumen_existencias(obra_id)

    return render_template(
        "existencias/lista.html",
        bodega=bodega,
        existencias=existencias,
        resumen=resumen
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
    pdf = canvas.Canvas(archivo, pagesize=letter)

    width, height = letter
    y = height - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "REPORTE GENERAL DE INVENTARIO")
    y -= 30

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(40, y, "Producto")
    pdf.drawString(160, y, "Unidad")
    pdf.drawString(230, y, "Bodega")
    pdf.drawString(320, y, "Ingresos")
    pdf.drawString(380, y, "Salidas")
    pdf.drawString(440, y, "Disponible")
    pdf.drawString(520, y, "Estado")
    y -= 15

    pdf.setFont("Helvetica", 8)

    for e in existencias:
        if y < 60:
            pdf.showPage()
            y = height - 50

        disponible = resumen[e.id]["disponible"]

        if disponible <= 0:
            estado = "AGOTADO"
        elif disponible <= e.producto.stock_minimo:
            estado = "STOCK BAJO"
        else:
            estado = "DISPONIBLE"

        pdf.drawString(40, y, str(e.producto.nombre)[:18])
        pdf.drawString(160, y, str(e.producto.unidad)[:10])
        pdf.drawString(230, y, str(e.obra.nombre)[:15])
        pdf.drawString(320, y, str(resumen[e.id]["ingresos"]))
        pdf.drawString(380, y, str(resumen[e.id]["salidas"]))
        pdf.drawString(440, y, str(disponible))
        pdf.drawString(520, y, estado)
        y -= 15

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
    pdf = canvas.Canvas(archivo, pagesize=letter)

    width, height = letter
    y = height - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, f"INVENTARIO - {bodega.nombre}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(40, y, "Producto")
    pdf.drawString(170, y, "Unidad")
    pdf.drawString(240, y, "Ingresos")
    pdf.drawString(320, y, "Salidas")
    pdf.drawString(400, y, "Disponible")
    pdf.drawString(500, y, "Estado")
    y -= 15

    pdf.setFont("Helvetica", 8)

    for e in existencias:
        if y < 60:
            pdf.showPage()
            y = height - 50

        disponible = resumen[e.id]["disponible"]

        if disponible <= 0:
            estado = "AGOTADO"
        elif disponible <= e.producto.stock_minimo:
            estado = "STOCK BAJO"
        else:
            estado = "DISPONIBLE"

        pdf.drawString(40, y, str(e.producto.nombre)[:20])
        pdf.drawString(170, y, str(e.producto.unidad)[:12])
        pdf.drawString(240, y, str(resumen[e.id]["ingresos"]))
        pdf.drawString(320, y, str(resumen[e.id]["salidas"]))
        pdf.drawString(400, y, str(disponible))
        pdf.drawString(500, y, estado)
        y -= 15

    pdf.save()
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name=f"inventario_{bodega.nombre}.pdf",
        mimetype="application/pdf"
    )