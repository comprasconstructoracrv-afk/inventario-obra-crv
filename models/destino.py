from extensions import db

class Destino(db.Model):
    __tablename__ = "destinos"

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(150), nullable=False, unique=True)
    sector = db.Column(db.String(100))
    estado = db.Column(db.String(20), default="ACTIVO")

    activo = db.Column(db.Boolean, default=True)