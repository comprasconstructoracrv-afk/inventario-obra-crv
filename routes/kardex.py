from flask import Blueprint, render_template, request, make_response
from flask_login import login_required
from models.producto import Producto
from models.movimiento import Movimiento
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO


kardex_bp = Blueprint("kardex", __name__)


@kardex_bp.route("/historial-producto", methods=["GET"])
@login_required
def kardex():
    productos = Producto.query.order_by(Producto.nombre.asc()).all()

    producto_id = request.args.get("producto_id")
    movimientos = []
    producto_seleccionado = None

    if producto_id:
        producto_seleccionado = Producto.query.get(int(producto_id))

        movimientos = Movimiento.query.filter_by(
            producto_id=int(producto_id)
        ).order_by(Movimiento.fecha.desc()).all()

    return render_template(
        "kardex/index.html",
        productos=productos,
        movimientos=movimientos,
        producto_seleccionado=producto_seleccionado
    )

@kardex_bp.route("/historial-producto/pdf/<int:producto_id>")
@login_required
def historial_producto_pdf(producto_id):
    producto = Producto.query.get_or_404(producto_id)

    movimientos = Movimiento.query.filter_by(
        producto_id=producto_id
    ).order_by(Movimiento.fecha.asc()).all()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    width, height = letter
    y = height - 50

    # ENCABEZADO
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, y, "INVENTARIO DE OBRA CRV")
    y -= 22

    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, y, "Historial detallado por producto")
    y -= 35

    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(width / 2, y, "HISTORIAL POR PRODUCTO")
    y -= 35

    # DATOS DEL PRODUCTO
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Producto:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(120, y, producto.nombre)
    y -= 18

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Codigo:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(120, y, producto.codigo)
    y -= 18

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Unidad:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(120, y, producto.unidad)
    y -= 18

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Stock actual:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(120, y, f"{producto.stock:,.2f}")
    y -= 30

    # CABECERA TABLA
    pdf.setFillColorRGB(0.06, 0.09, 0.16)
    pdf.roundRect(40, y - 8, 520, 24, 6, fill=True, stroke=False)

    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(48, y, "Fecha")
    pdf.drawString(100, y, "Tipo")
    pdf.drawString(165, y, "Bodega")
    pdf.drawString(245, y, "Destino")
    pdf.drawString(355, y, "Cantidad")
    pdf.drawString(420, y, "Observaciones")

    y -= 28
    pdf.setFillColorRGB(0, 0, 0)

    # FILAS
    pdf.setFont("Helvetica", 7)

    for m in movimientos:
        if y < 70:
            pdf.showPage()
            y = height - 50

            pdf.setFillColorRGB(0.06, 0.09, 0.16)
            pdf.roundRect(40, y - 8, 520, 24, 6, fill=True, stroke=False)

            pdf.setFillColorRGB(1, 1, 1)
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(48, y, "Fecha")
            pdf.drawString(100, y, "Tipo")
            pdf.drawString(165, y, "Bodega")
            pdf.drawString(245, y, "Destino")
            pdf.drawString(355, y, "Cantidad")
            pdf.drawString(420, y, "Observaciones")

            y -= 28
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont("Helvetica", 7)

        fecha = m.fecha.strftime("%d/%m/%Y")
        tipo = m.tipo
        bodega = m.obra.nombre if m.obra else "-"
        destino = m.destino.nombre if m.destino else "-"
        cantidad = f"{m.cantidad:,.2f}"
        observaciones = m.observaciones or ""

        pdf.drawString(48, y, fecha)
        pdf.drawString(100, y, tipo[:10])
        pdf.drawString(165, y, bodega[:14])
        pdf.drawString(245, y, destino[:20])
        pdf.drawRightString(395, y, cantidad)
        pdf.drawString(420, y, observaciones[:30])

        y -= 18

    # PIE
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(width / 2, 35, "Documento generado por Inventario de Obra CRV")

    pdf.save()
    buffer.seek(0)

    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=historial_{producto.codigo}.pdf"

    return response