import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-breakfast-hotel-secret-key-default-2026')
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/breakfast_hotel')
    DB_NAME = os.environ.get('DB_NAME', 'breakfast_hotel')
    
    # Uploads & Media
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    QRCODE_FOLDER = os.path.join(BASE_DIR, 'static', 'qrcodes')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    
    # Server settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1'
