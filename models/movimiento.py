from extensions import db
from datetime import datetime

class Movimiento(db.Model):
    __tablename__ = "movimientos"

    id = db.Column(db.Integer, primary_key=True)

    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    obra_id = db.Column(db.Integer, db.ForeignKey('obras.id'), nullable=False)

    tipo = db.Column(db.String(20), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)

    destino_id = db.Column(db.Integer, db.ForeignKey("destinos.id"))
    observaciones = db.Column(db.String(255))

    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    producto = db.relationship("Producto")
    obra = db.relationship("Obra")
    destino = db.relationship("Destino")