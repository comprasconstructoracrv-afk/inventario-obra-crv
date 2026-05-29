from extensions import db

class Existencia(db.Model):
    __tablename__ = "existencias"

    id = db.Column(db.Integer, primary_key=True)

    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    obra_id = db.Column(db.Integer, db.ForeignKey("obras.id"), nullable=False)

    cantidad = db.Column(db.Float, default=0)

    producto = db.relationship("Producto")
    obra = db.relationship("Obra")