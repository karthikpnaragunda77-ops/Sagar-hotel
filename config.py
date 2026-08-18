import os
import certifi


class Config:
    MONGO_URI = os.getenv("MONGO_URI")

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "sagar-hotel-secret-key"
    )

    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "static",
        "uploads"
    )

    MONGO_OPTIONS = {
        "tls": True,
        "tlsCAFile": certifi.where(),
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 20000,
        "socketTimeoutMS": 20000
    }
