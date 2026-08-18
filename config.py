import os
import certifi


class Config:

    # =========================
    # MongoDB
    # =========================

    MONGO_URI = os.getenv("MONGO_URI")

    DB_NAME = os.getenv(
        "DB_NAME",
        "sagar_hotel"
    )

    # =========================
    # Flask
    # =========================

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "sagar-hotel-secret-key"
    )

    # =========================
    # Server
    # =========================

    HOST = os.getenv(
        "HOST",
        "0.0.0.0"
    )

    PORT = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    DEBUG = os.getenv(
        "DEBUG",
        "False"
    ).lower() == "true"

    # =========================
    # Paths
    # =========================

    BASE_DIR = os.path.dirname(
        os.path.abspath(__file__)
    )

    UPLOAD_FOLDER = os.path.join(
        BASE_DIR,
        "static",
        "uploads"
    )

    QRCODE_FOLDER = os.path.join(
        BASE_DIR,
        "static",
        "qrcodes"
    )

    # =========================
    # MongoDB Options
    # =========================

    MONGO_OPTIONS = {
        "tls": True,
        "tlsCAFile": certifi.where(),

        # Serverless-friendly timeouts
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 20000,
        "socketTimeoutMS": 20000,

        "retryWrites": True,
        "retryReads": True
    }
