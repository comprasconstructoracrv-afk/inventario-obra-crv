from flask import Blueprint, render_template, session, make_response
from flask_login import login_required

from models.destino import Destino
from models.movimiento import Movimiento
from models.obra import Obra

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

consumos_bp = Blueprint("consumos", __name__)


@consumos_bp.route("/consumos/destino")
@login_required
def consumo_por_destino():
    empresa_id = session.get("empresa_id")

    if empresa_id and hasattr(Destino, "empresa_id"):
        destinos = Destino.query.filter_by(
            empresa_id=empresa_id,
            activo=True
        ).order_by(Destino.nombre.asc()).all()
    else:
        destinos = Destino.query.filter_by(activo=True).order_by(Destino.nombre.asc()).all()

    if empresa_id:
        bodegas_empresa = Obra.query.filter_by(empresa_id=empresa_id).all()
        bodega_ids = [b.id for b in bodegas_empresa]
    else:
        bodega_ids = None

    for destino in destinos:
        query_mov = Movimiento.query.filter(
            Movimiento.tipo == "SALIDA",
            Movimiento.destino_id == destino.id
        )

        if bodega_ids is not None:
            if bodega_ids:
                query_mov = query_mov.filter(Movimiento.obra_id.in_(bodega_ids))
            else:
                query_mov = query_mov.filter(Movimiento.id == -1)

        movimientos = query_mov.all()

        productos_usados = set()
        total_cantidad = 0

        for m in movimientos:
            productos_usados.add(m.producto_id)
            total_cantidad += m.cantidad

        destino.total_productos = len(productos_usados)
        destino.total_cantidad = "{:,.2f}".format(total_cantidad).replace(",", "X").replace(".", ",").replace("X", ".")

    return render_template(
        "consumos/destino.html",
        destinos=destinos
    )

@consumos_bp.route("/consumos/destino/<int:destino_id>")
@login_required
def detalle_destino(destino_id):
    empresa_id = session.get("empresa_id")

    if empresa_id and hasattr(Destino, "empresa_id"):
        destino = Destino.query.filter_by(id=destino_id, empresa_id=empresa_id).first_or_404()
    else:
        destino = Destino.query.get_or_404(destino_id)

    query_mov = Movimiento.query.filter(
        Movimiento.tipo == "SALIDA",
        Movimiento.destino_id == destino_id
    )

    if empresa_id:
        bodegas_empresa = Obra.query.filter_by(empresa_id=empresa_id).all()
        bodega_ids = [b.id for b in bodegas_empresa]
        if bodega_ids:
            query_mov = query_mov.filter(Movimiento.obra_id.in_(bodega_ids))
        else:
            query_mov = query_mov.filter(Movimiento.id == -1)

    movimientos = query_mov.order_by(Movimiento.fecha.desc()).all()

    return render_template(
        "consumos/detalle_destino.html",
        destino=destino,
        movimientos=movimientos
    )


@consumos_bp.route("/consumos/destino/<int:destino_id>/pdf")
@login_required
def destino_pdf(destino_id):
    empresa_id = session.get("empresa_id")
    empresa_nombre = session.get("empresa_nombre", "SISTEMA DE INVENTARIO")

    if empresa_id and hasattr(Destino, "empresa_id"):
        destino = Destino.query.filter_by(id=destino_id, empresa_id=empresa_id).first_or_404()
    else:
        destino = Destino.query.get_or_404(destino_id)

    query_mov = Movimiento.query.filter(
        Movimiento.tipo == "SALIDA",
        Movimiento.destino_id == destino_id
    )

    if empresa_id:
        bodegas_empresa = Obra.query.filter_by(empresa_id=empresa_id).all()
        bodega_ids = [b.id for b in bodegas_empresa]
        if bodega_ids:
            query_mov = query_mov.filter(Movimiento.obra_id.in_(bodega_ids))
        else:
            query_mov = query_mov.filter(Movimiento.id == -1)

    movimientos = query_mov.order_by(Movimiento.fecha.asc()).all()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    width, height = letter
    y = height - 50

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(width / 2, y, empresa_nombre.upper())
    y -= 24

    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, y, "Reporte de consumo por destino")
    y -= 35

    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(width / 2, y, f"REPORTE - {destino.nombre}")
    y -= 25

    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, y, f"Sector: {destino.sector or '-'}")
    y -= 35

    pdf.setFillColorRGB(0.06, 0.09, 0.16)
    pdf.roundRect(35, y - 8, 540, 24, 6, fill=True, stroke=False)

    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(43, y, "Fecha")
    pdf.drawString(95, y, "Producto")
    pdf.drawString(190, y, "Codigo")
    pdf.drawString(245, y, "Bodega")
    pdf.drawString(320, y, "Cantidad")
    pdf.drawString(385, y, "Unidad")
    pdf.drawString(445, y, "Observaciones")

    y -= 28
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 7)

    total = 0

    for m in movimientos:

        if y < 70:
            pdf.showPage()
            y = height - 50

            pdf.setFillColorRGB(0.06, 0.09, 0.16)
            pdf.roundRect(35, y - 8, 540, 24, 6, fill=True, stroke=False)

            pdf.setFillColorRGB(1, 1, 1)
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(43, y, "Fecha")
            pdf.drawString(95, y, "Producto")
            pdf.drawString(190, y, "Codigo")
            pdf.drawString(245, y, "Bodega")
            pdf.drawString(320, y, "Cantidad")
            pdf.drawString(385, y, "Unidad")
            pdf.drawString(445, y, "Observaciones")

            y -= 28
            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont("Helvetica", 7)

        total += m.cantidad

        pdf.drawString(43, y, m.fecha.strftime("%d/%m/%Y"))
        pdf.drawString(95, y, m.producto.nombre[:18] if m.producto else "-")
        pdf.drawString(190, y, m.producto.codigo[:8] if m.producto else "-")
        pdf.drawString(245, y, m.obra.nombre[:13] if m.obra else "-")
        pdf.drawRightString(365, y, f"{m.cantidad:,.2f}")
        pdf.drawString(385, y, m.producto.unidad[:10] if m.producto else "-")
        pdf.drawString(445, y, (m.observaciones or "")[:25])

        y -= 16

    y -= 15
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(365, y, f"TOTAL: {total:,.2f}")

    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(width / 2, 35, f"Documento generado por {empresa_nombre}")

    pdf.save()
    buffer.seek(0)

    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=reporte_{destino.nombre}.pdf"

    return response