import os
import certifi

class Config:
    MONGO_URI = os.getenv("MONGO_URI")

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "sagar-hotel-secret-key"
    )

    MONGO_OPTIONS = {
        "tls": True,
        "tlsCAFile": certifi.where(),
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 20000,
        "socketTimeoutMS": 20000
    }
