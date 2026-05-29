from extensions import db

class Obra(db.Model):
    __tablename__ = "obras"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    ubicacion = db.Column(db.String(150))
    responsable = db.Column(db.String(100))
    estado = db.Column(db.String(30), default="ACTIVA")