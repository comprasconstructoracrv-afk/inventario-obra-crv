from flask import Blueprint, render_template, request, redirect, url_for, send_file
from flask_login import login_required
from models.obra import Obra
from models.existencia import Existencia
from extensions import db
from io import BytesIO
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from utils.permisos import solo_admin

obras_bp = Blueprint("obras", __name__)


@obras_bp.route("/obras")
@login_required
def listar_obras():
    obras = Obra.query.order_by(Obra.nombre.asc()).all()

    bodegas_data = []

    for obra in obras:
        existencias = Existencia.query.filter_by(obra_id=obra.id).all()

        categorias = {}
        total_productos = 0
        total_cantidad = 0

        for e in existencias:
            if e.cantidad <= 0:
                continue

            if not e.producto:
                continue

            categoria = e.producto.categoria or "SIN CATEGORÍA"

            if categoria not in categorias:
                categorias[categoria] = []

            categorias[categoria].append(e)
            total_productos += 1
            total_cantidad += e.cantidad

        bodegas_data.append({
            "obra": obra,
            "categorias": categorias,
            "total_productos": total_productos,
            "total_cantidad": total_cantidad
        })

    return render_template("obras/lista.html", bodegas_data=bodegas_data)


@obras_bp.route("/obras/nueva", methods=["GET", "POST"])
@login_required
def nueva_obra():
    if request.method == "POST":
        obra = Obra(
            nombre=request.form["nombre"].upper(),
            ubicacion=request.form["ubicacion"].upper(),
            responsable=request.form["responsable"].upper(),
            estado=request.form["estado"]
        )
        db.session.add(obra)
        db.session.commit()
        return redirect(url_for("obras.listar_obras"))

    return render_template("obras/nueva.html")


@obras_bp.route("/obras/editar/<int:id>", methods=["GET", "POST"])
@login_required
@solo_admin
def editar_obra(id):
    obra = Obra.query.get_or_404(id)

    if request.method == "POST":
        obra.nombre = request.form["nombre"].upper()
        obra.ubicacion = request.form["ubicacion"].upper()
        obra.responsable = request.form["responsable"].upper()
        obra.estado = request.form["estado"]
        db.session.commit()
        return redirect(url_for("obras.listar_obras"))

    return render_template("obras/editar.html", obra=obra)


@obras_bp.route("/obras/eliminar/<int:id>")
@login_required
@solo_admin
def eliminar_obra(id):
    obra = Obra.query.get_or_404(id)
    db.session.delete(obra)
    db.session.commit()
    return redirect(url_for("obras.listar_obras"))


@obras_bp.route("/obras/excel")
@login_required
def exportar_obras_excel():
    obras = Obra.query.order_by(Obra.nombre.asc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Bodegas"

    ws.append(["REPORTE DE BODEGAS"])
    ws.append([])
    ws.append(["Nombre", "Ubicación", "Responsable", "Estado"])

    for obra in obras:
        ws.append([obra.nombre, obra.ubicacion, obra.responsable, obra.estado])

    archivo = BytesIO()
    wb.save(archivo)
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name="bodegas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@obras_bp.route("/obras/pdf")
@login_required
def exportar_obras_pdf():
    obras = Obra.query.order_by(Obra.nombre.asc()).all()

    archivo = BytesIO()
    pdf = canvas.Canvas(archivo, pagesize=letter)

    width, height = letter
    y = height - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "REPORTE DE BODEGAS")
    y -= 30

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(50, y, "Nombre")
    pdf.drawString(180, y, "Ubicacion")
    pdf.drawString(320, y, "Responsable")
    pdf.drawString(470, y, "Estado")
    y -= 15

    pdf.setFont("Helvetica", 8)

    for obra in obras:
        if y < 60:
            pdf.showPage()
            y = height - 50

        pdf.drawString(50, y, str(obra.nombre)[:22])
        pdf.drawString(180, y, str(obra.ubicacion)[:22])
        pdf.drawString(320, y, str(obra.responsable)[:22])
        pdf.drawString(470, y, str(obra.estado))
        y -= 15

    pdf.save()
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name="bodegas.pdf",
        mimetype="application/pdf"
    )