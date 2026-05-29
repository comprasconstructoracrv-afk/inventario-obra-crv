from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, login_user, logout_user, login_required
from config import Config
from extensions import db
from models.usuario import Usuario
from routes.obras import obras_bp
from routes.traslados import traslados_bp
from routes.existencias import existencias_bp
from routes.kardex import kardex_bp
from routes.reportes import reportes_bp
from routes.consumos import consumos_bp
from models.destino import Destino
from routes.destinos import destinos_bp

login_manager = LoginManager()


def crear_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "login"

    from models.producto import Producto
    from models.movimiento import Movimiento
    from models.obra import Obra
    from routes.productos import productos_bp
    from routes.movimientos import movimientos_bp

    app.register_blueprint(productos_bp)
    app.register_blueprint(movimientos_bp)
    app.register_blueprint(obras_bp)
    app.register_blueprint(traslados_bp)
    app.register_blueprint(existencias_bp)
    app.register_blueprint(kardex_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(consumos_bp)
    app.register_blueprint(destinos_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    @app.route("/")
    def inicio():
        return redirect(url_for("dashboard"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            usuario = request.form.get("usuario") or request.form.get("username")
            password = request.form.get("password")

            if not usuario or not password:
                return render_template("login.html", error="Debe ingresar usuario y contraseña")

            user = Usuario.query.filter_by(usuario=usuario).first()

            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("dashboard"))

            return render_template("login.html", error="Usuario o contraseña incorrectos")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))
    
    @app.route("/dashboard")
    @login_required
    def dashboard():

        productos_total = Producto.query.count()
        movimientos_total = Movimiento.query.count()
        obras_total = Obra.query.count()

        inventario = Producto.query.all()

        stock_bajo = Producto.query.filter(
            Producto.stock <= Producto.stock_minimo
        ).count()

        return render_template(
            "dashboard.html",
            productos_total=productos_total,
            movimientos_total=movimientos_total,
            obras_total=obras_total,
            stock_bajo=stock_bajo,
            inventario=inventario
        )

    with app.app_context():
        db.create_all()

        admin = Usuario.query.filter_by(usuario="admin").first()

        destinos_iniciales = [
            ("Casa 11 Tamarindo", "TAMARINDO"),
            ("Casa 12 Tamarindo", "TAMARINDO"),
            ("Casa 19 Tamarindo", "TAMARINDO"),
            ("Casa 20 Tamarindo", "TAMARINDO"),
            ("Casa 24 Tamarindo", "TAMARINDO"),
            ("Casa 25 Tamarindo", "TAMARINDO"),
            ("Casa 28 Tamarindo", "TAMARINDO"),
            ("Casa 8 Almendros", "ALMENDROS"),
            ("Casa 9 Almendros", "ALMENDROS"),
            ("Casa 14 Ceiba", "CEIBA"),
            ("Casa 16 Ceiba", "CEIBA"),
            ("Urbanismo vía principal", "URBANISMO"),
            ("Portería", "PORTERÍA"),
        ]

        for nombre, sector in destinos_iniciales:
            existe = Destino.query.filter_by(nombre=nombre.upper()).first()
            if not existe:
                destino = Destino(
                    nombre=nombre.upper(),
                    sector=sector.upper(),
                    estado="ACTIVO",
                    activo=True
                )
                db.session.add(destino)

        db.session.commit()

        if not admin:
            admin = Usuario(
                nombre="Administrador",
                usuario="admin",
                rol="ADMIN"
            )

            admin.set_password("1234")

            db.session.add(admin)

        # =========================
        # BODEGAS AUTOMATICAS
        # =========================

        from models.obra import Obra

        bodegas_base = [
            "BODEGA 1",
            "BODEGA 2",
            "BODEGA 3",
            "BODEGA 4",
            "BODEGA 5",
            "BODEGA 6",
            "BODEGA 7",
            "FERRETERIA"
        ]

        for nombre_bodega in bodegas_base:

            existe = Obra.query.filter_by(nombre=nombre_bodega).first()

            if not existe:

                nueva_bodega = Obra(
                    nombre=nombre_bodega,
                    ubicacion="EDEN LUXURY",
                    responsable="POR ASIGNAR",
                    estado="ACTIVA"
                )

                db.session.add(nueva_bodega)

        db.session.commit()

    return app



app = crear_app()

if __name__ == "__main__":
    app.run(debug=True)