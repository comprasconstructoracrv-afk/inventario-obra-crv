from extensions import db

class Producto(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(100))
    unidad = db.Column(db.String(50))
    stock = db.Column(db.Float, default=0)
    stock_minimo = db.Column(db.Float, default=0)
    precio = db.Column(db.Float, default=0)
    activo = db.Column(db.Boolean, default=True)