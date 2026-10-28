from extensions import db

class Empresa(db.Model):
    __tablename__ = "empresa"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False, unique=True)
    estado = db.Column(db.String(20), default="ACTIVO")
    activo = db.Column(db.Boolean, default=True)

    # Relación con las bodegas (obras)
    obras = db.relationship("Obra", backref="empresa", lazy=True)