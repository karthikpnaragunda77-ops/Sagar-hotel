import os
import certifi


class Config:
    # =========================
    # MongoDB
    # =========================

    MONGO_URI = os.getenv("MONGO_URI")

    # Database name
    DB_NAME = os.getenv("DB_NAME", "sagar_hotel")

    # =========================
    # Flask
    # =========================

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "sagar-hotel-secret-key"
    )

    # =========================
    # Upload Folder
    # =========================

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    UPLOAD_FOLDER = os.path.join(
        BASE_DIR,
        "static",
        "uploads"
    )

    # =========================
    # QR Code Folder
    # =========================

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
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 20000,
        "socketTimeoutMS": 20000,
        "retryWrites": True,
        "retryReads": True
    }
