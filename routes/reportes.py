from flask import Blueprint, render_template, request, send_file, session
from flask_login import login_required
from sqlalchemy import func
from models.movimiento import Movimiento
from models.obra import Obra
from models.existencia import Existencia
from io import BytesIO
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from flask import Blueprint, render_template, session, request, redirect, url_for
from flask_login import login_required, current_user
from models.obra import Obra
from models.producto import Producto
from models.existencia import Existencia
from models.movimiento import Movimiento
from extensions import db
from sqlalchemy import func

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

from flask import Blueprint, render_template, request, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from models.obra import Obra
from models.producto import Producto
from models.existencia import Existencia
from models.movimiento import Movimiento
from extensions import db

@reportes_bp.route("/reportes/inventario-bodegas")
@login_required
def reporte_inventario_bodegas():
    empresa_id = session.get("empresa_id")

    bodega_id = request.args.get("bodega_id", "TODAS")
    periodo = request.args.get("periodo", "HISTORICO")

    ahora = datetime.now()
    fecha_desde = None

    if periodo == "HOY":
        fecha_desde = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "SEMANA":
        fecha_desde = ahora - timedelta(days=7)
    elif periodo == "MES":
        fecha_desde = ahora - timedelta(days=30)

    if getattr(current_user, "rol", "") == "ADMIN" and not empresa_id:
        bodegas_query = Obra.query
    else:
        bodegas_query = Obra.query.filter_by(empresa_id=empresa_id)

    if bodega_id != "TODAS":
        bodegas_query = bodegas_query.filter(Obra.id == int(bodega_id))

    bodegas = bodegas_query.order_by(Obra.nombre.asc()).all()

    reporte_bodegas = []
    kpi_global_ingresos = 0
    kpi_global_salidas = 0
    kpi_global_stock = 0

    for b in bodegas:
        existencias = Existencia.query.filter_by(obra_id=b.id).all()
        productos_desglose = []

        for ext in existencias:
            p = ext.producto
            if not p:
                continue

            ing_q = db.session.query(func.coalesce(func.sum(Movimiento.cantidad), 0)).filter(
                Movimiento.obra_id == b.id,
                Movimiento.producto_id == p.id,
                Movimiento.tipo == "INGRESO"
            )
            if fecha_desde:
                ing_q = ing_q.filter(Movimiento.fecha >= fecha_desde)
            ingresos = ing_q.scalar()

            sal_q = db.session.query(func.coalesce(func.sum(Movimiento.cantidad), 0)).filter(
                Movimiento.obra_id == b.id,
                Movimiento.producto_id == p.id,
                Movimiento.tipo == "SALIDA"
            )
            if fecha_desde:
                sal_q = sal_q.filter(Movimiento.fecha >= fecha_desde)
            salidas = sal_q.scalar()

            stock_actual = ext.cantidad

            if ingresos > 0 or salidas > 0 or stock_actual > 0:
                productos_desglose.append({
                    "codigo": p.codigo,
                    "nombre": p.nombre,
                    "unidad": p.unidad,
                    "tipo": p.tipo_producto,
                    "ingresos": ingresos,
                    "salidas": salidas,
                    "stock_actual": stock_actual
                })

                kpi_global_ingresos += ingresos
                kpi_global_salidas += salidas
                kpi_global_stock += stock_actual

        reporte_bodegas.append({
            "bodega": b,
            "productos_lista": productos_desglose
        })

    bodegas_todas = Obra.query.filter_by(empresa_id=empresa_id).all() if empresa_id else Obra.query.all()

    return render_template(
        "reportes/inventario_bodegas.html",
        reporte_bodegas=reporte_bodegas,
        bodegas_todas=bodegas_todas,
        bodega_id_sel=bodega_id,
        periodo_sel=periodo,
        kpi_ingresos=kpi_global_ingresos,
        kpi_salidas=kpi_global_salidas,
        kpi_stock=kpi_global_stock
    )