from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from models.obra import Obra
from models.existencia import Existencia
from io import BytesIO
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

reportes_bp = Blueprint("reportes", __name__)


@reportes_bp.route("/reportes/bodega", methods=["GET"])
@login_required
def reporte_bodega():
    bodegas = Obra.query.order_by(Obra.nombre.asc()).all()

    bodega_id = request.args.get("bodega_id")
    existencias = []
    bodega_seleccionada = None

    if bodega_id:
        bodega_seleccionada = Obra.query.get(int(bodega_id))
        existencias = Existencia.query.filter_by(obra_id=int(bodega_id)).all()

    return render_template(
        "reportes/bodega.html",
        bodegas=bodegas,
        existencias=existencias,
        bodega_seleccionada=bodega_seleccionada
    )


@reportes_bp.route("/reportes/bodega/excel/<int:bodega_id>")
@login_required
def exportar_bodega_excel(bodega_id):
    bodega = Obra.query.get_or_404(bodega_id)
    existencias = Existencia.query.filter_by(obra_id=bodega_id).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte Bodega"

    ws.append(["REPORTE DE INVENTARIO POR BODEGA"])
    ws.append(["Bodega", bodega.nombre])
    ws.append(["Ubicación", bodega.ubicacion])
    ws.append(["Responsable", bodega.responsable])
    ws.append([])

    ws.append(["Producto", "Unidad", "Cantidad", "Precio Unitario", "Valor Estimado"])

    total = 0

    for e in existencias:
        valor = e.cantidad * e.producto.precio
        total += valor

        ws.append([
            e.producto.nombre,
            e.producto.unidad,
            e.cantidad,
            e.producto.precio,
            valor
        ])

    ws.append([])
    ws.append(["TOTAL", "", "", "", total])

    archivo = BytesIO()
    wb.save(archivo)
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name=f"reporte_bodega_{bodega.nombre}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@reportes_bp.route("/reportes/bodega/pdf/<int:bodega_id>")
@login_required
def exportar_bodega_pdf(bodega_id):
    bodega = Obra.query.get_or_404(bodega_id)
    existencias = Existencia.query.filter_by(obra_id=bodega_id).all()

    archivo = BytesIO()
    pdf = canvas.Canvas(archivo, pagesize=letter)

    width, height = letter
    y = height - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "REPORTE DE INVENTARIO POR BODEGA")
    y -= 30

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, y, f"Bodega: {bodega.nombre}")
    y -= 18
    pdf.drawString(50, y, f"Ubicacion: {bodega.ubicacion or ''}")
    y -= 18
    pdf.drawString(50, y, f"Responsable: {bodega.responsable or ''}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(50, y, "Producto")
    pdf.drawString(230, y, "Unidad")
    pdf.drawString(320, y, "Cantidad")
    pdf.drawString(390, y, "Precio")
    pdf.drawString(470, y, "Valor")
    y -= 15

    pdf.setFont("Helvetica", 8)

    total = 0

    for e in existencias:
        if y < 60:
            pdf.showPage()
            y = height - 50

        valor = e.cantidad * e.producto.precio
        total += valor

        pdf.drawString(50, y, str(e.producto.nombre)[:28])
        pdf.drawString(230, y, str(e.producto.unidad)[:12])
        pdf.drawString(320, y, str(e.cantidad))
        pdf.drawString(390, y, f"$ {e.producto.precio:,.0f}".replace(",", "."))
        pdf.drawString(470, y, f"$ {valor:,.0f}".replace(",", "."))
        y -= 15

    y -= 20
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(390, y, "TOTAL:")
    pdf.drawString(470, y, f"$ {total:,.0f}".replace(",", "."))

    pdf.save()
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name=f"reporte_bodega_{bodega.nombre}.pdf",
        mimetype="application/pdf"
    )