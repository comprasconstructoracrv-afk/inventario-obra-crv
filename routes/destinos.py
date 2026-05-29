from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required

from extensions import db
from models.destino import Destino


destinos_bp = Blueprint("destinos", __name__)


@destinos_bp.route("/destinos")
@login_required
def listar_destinos():
    destinos = Destino.query.order_by(Destino.sector.asc(), Destino.nombre.asc()).all()
    return render_template("destinos/lista.html", destinos=destinos)


@destinos_bp.route("/destinos/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_destino():
    if request.method == "POST":
        nombre = request.form["nombre"].upper()
        sector = request.form["sector"].upper()
        estado = request.form["estado"].upper()

        existe = Destino.query.filter_by(nombre=nombre).first()
        if existe:
            return """
            <h2 style='font-family:Arial'>
                Este destino ya existe.<br><br>
                <a href='/destinos'>Volver a destinos</a>
            </h2>
            """

        destino = Destino(
            nombre=nombre,
            sector=sector,
            estado=estado,
            activo=True if estado == "ACTIVO" else False
        )

        db.session.add(destino)
        db.session.commit()

        return redirect(url_for("destinos.listar_destinos"))

    return render_template("destinos/nuevo.html")


@destinos_bp.route("/destinos/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_destino(id):
    destino = Destino.query.get_or_404(id)

    if request.method == "POST":
        destino.nombre = request.form["nombre"].upper()
        destino.sector = request.form["sector"].upper()
        destino.estado = request.form["estado"].upper()
        destino.activo = True if destino.estado == "ACTIVO" else False

        db.session.commit()

        return redirect(url_for("destinos.listar_destinos"))

    return render_template("destinos/editar.html", destino=destino)


@destinos_bp.route("/destinos/eliminar/<int:id>")
@login_required
def eliminar_destino(id):
    destino = Destino.query.get_or_404(id)
    destino.estado = "INACTIVO"
    destino.activo = False

    db.session.commit()

    return redirect(url_for("destinos.listar_destinos"))