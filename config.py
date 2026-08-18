import os
import certifi
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=20000,
    socketTimeoutMS=20000
)

db = client["breakfast_hotel"]

# Test connection
try:
    client.admin.command("ping")
    print("MongoDB Atlas connected successfully!")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
