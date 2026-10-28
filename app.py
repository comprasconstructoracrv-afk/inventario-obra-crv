import os
from flask import Flask, app, render_template, redirect, session, url_for, request
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from config import Config
from extensions import db
from sqlalchemy import text 
from models.usuario import Usuario
from models.destino import Destino
from models.empresa import Empresa
from models.obra import Obra
from models.producto import Producto
from models.movimiento import Movimiento
from models.existencia import Existencia
from models.empresa import Empresa

from routes.obras import obras_bp
from routes.traslados import traslados_bp
from routes.existencias import existencias_bp
from routes.kardex import kardex_bp
from routes.reportes import reportes_bp
from routes.consumos import consumos_bp
from routes.destinos import destinos_bp
from routes.productos import productos_bp
from routes.movimientos import movimientos_bp
from routes.empresas import empresas_bp
from routes.usuarios import usuarios_bp

login_manager = LoginManager()


def crear_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "login"

    # Registro de Blueprints
    app.register_blueprint(productos_bp)
    app.register_blueprint(movimientos_bp)
    app.register_blueprint(obras_bp)
    app.register_blueprint(traslados_bp)
    app.register_blueprint(existencias_bp)
    app.register_blueprint(kardex_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(consumos_bp)
    app.register_blueprint(destinos_bp)
    app.register_blueprint(empresas_bp)
    app.register_blueprint(usuarios_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    @app.route("/")
    def inicio():
        return redirect(url_for("dashboard_principal"))

    from flask import session, request, render_template, redirect, url_for
    from flask_login import login_user
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

                session.pop("empresa_id", None)
                session.pop("empresa_nombre", None)
                return redirect(url_for("dashboard_principal"))

            return render_template("login.html", error="Usuario o contraseña incorrectos")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/dashboard_principal")
    @login_required
    def dashboard_principal():
        if getattr(current_user, "rol", "") == "ADMIN":
            empresas = Empresa.query.order_by(Empresa.nombre.asc()).all()
        else:
            empresa_id = getattr(current_user, "empresa_id", None) or session.get("empresa_id")
            if empresa_id:
                empresas = Empresa.query.filter_by(id=empresa_id).all()
            else:
                empresas = []

        empresas_data = []
        for emp in empresas:
            bodegas = Obra.query.filter_by(empresa_id=emp.id).all()
            bodega_ids = [b.id for b in bodegas]

            total_bodegas = len(bodegas)
            total_productos = 0
            total_cantidad = 0

            if bodega_ids:
                existencias = Existencia.query.filter(Existencia.obra_id.in_(bodega_ids)).all()
                productos_unicos = set()

                for e in existencias:
                    if e.cantidad > 0:
                        productos_unicos.add(e.producto_id)
                        total_cantidad += e.cantidad

                total_productos = len(productos_unicos)

            empresas_data.append({
                "empresa": emp,
                "total_bodegas": total_bodegas,
                "total_productos": total_productos,
                "total_cantidad": total_cantidad
            })

        return render_template("dashboard_principal.html", empresas_data=empresas_data)

    # DASHBOARD DE EMPRESAS (DETALLE DE BODEGAS/SEDES Y PRODUCTOS)
    @app.route("/dashboard")
    @login_required
    def dashboard():
        productos_total = Producto.query.count()
        movimientos_total = Movimiento.query.count()
        obras_total = Obra.query.count()
        empresa_id = session.get("empresa_id")
        empresa=None

        inventario = Producto.query.all()

        stock_bajo = Producto.query.filter(
            Producto.stock <= Producto.stock_minimo
        ).count()

        if empresa_id: 
            empresa_id = Empresa.query.get(empresa_id)

        return render_template(
            "dashboard.html",
            empresa_id=empresa,
            productos_total=productos_total,
            movimientos_total=movimientos_total,
            obras_total=obras_total,
            stock_bajo=stock_bajo,
            inventario=inventario
        )

    with app.app_context():
        db.create_all()

        columnas_a_agregar = [
            ("movimientos", "responsable", "VARCHAR(120)"),
            ("productos", "tipo_producto", "VARCHAR(50) DEFAULT 'OBRA'"),
            ("obras", "empresa_id", "INTEGER REFERENCES empresa(id)"),
            ("productos", "empresa_id", "INTEGER REFERENCES empresa(id)"),
            ("destinos", "empresa_id", "INTEGER REFERENCES empresa(id)"),
            ("usuarios", "empresa_id", "INTEGER REFERENCES empresa(id)"),
        ]

        for tabla, columna, tipo in columnas_a_agregar:
            try:
                db.session.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo};"))
                db.session.commit()
            except Exception:
                db.session.rollback()  

        empresa_principal = Empresa.query.filter_by(nombre="INVENTARIO DE OBRA CRV").first()
        if not empresa_principal:
            empresa_principal = Empresa(
                nombre="INVENTARIO DE OBRA CRV",
                estado="ACTIVO",
                activo=True
            )
            db.session.add(empresa_principal)
            db.session.commit()

        otras_empresas = ["ECOBIKE", "COMERCIALIZADORA"]
        for nombre_emp in otras_empresas:
            if not Empresa.query.filter_by(nombre=nombre_emp).first():
                db.session.add(Empresa(nombre=nombre_emp, estado="ACTIVO", activo=True))
        db.session.commit()

        admin = Usuario.query.filter_by(usuario="admin").first()
        almacenista = Usuario.query.filter_by(usuario="almacen").first()

        if not almacenista:
            almacenista = Usuario(
                nombre="ALMACENISTA",
                usuario="almacen",
                rol="ALMACENISTA",
                empresa_id=empresa_principal.id
            )
            almacenista.set_password("1234")
            db.session.add(almacenista)
            db.session.commit()

        if not admin:
            admin = Usuario(
                nombre="Administrador",
                usuario="admin",
                rol="ADMIN"
            )
            admin.set_password("2314")
            db.session.add(admin)
            db.session.commit()

        try:
            db.session.execute(text(f"UPDATE obras SET empresa_id = {empresa_principal.id} WHERE empresa_id IS NULL OR empresa_id = 0;"))
            db.session.execute(text(f"UPDATE productos SET empresa_id = {empresa_principal.id} WHERE empresa_id IS NULL OR empresa_id = 0;"))
            db.session.execute(text(f"UPDATE destinos SET empresa_id = {empresa_principal.id} WHERE empresa_id IS NULL OR empresa_id = 0;"))
            db.session.execute(text(f"UPDATE usuarios SET empresa_id = {empresa_principal.id} WHERE empresa_id IS NULL OR empresa_id = 0;"))
            db.session.execute(text("UPDATE productos SET tipo_producto = 'OBRA' WHERE tipo_producto IS NULL;"))
            db.session.commit()
        except Exception:
            db.session.rollback()

    return app


app = crear_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )