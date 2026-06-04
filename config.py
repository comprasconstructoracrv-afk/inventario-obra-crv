import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "clave-secreta-inventario-obra"

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+pg8000://"
        )
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "inventario_obra.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False