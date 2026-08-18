import sys
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import Config

class Database:
    _instance = None
    _client = None
    _db = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            try:
                cls._client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=3000)
                # Verify connection
                cls._client.server_info()
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                print(f"[ERROR] Could not connect to MongoDB at {Config.MONGO_URI}: {e}", file=sys.stderr)
                # If local connection fails, fallback to mongomock if available
                try:
                    import mongomock
                    print("[INFO] Fallback to in-memory mongomock database...", file=sys.stderr)
                    cls._client = mongomock.MongoClient()
                except ImportError:
                    raise e
        return cls._client

    @classmethod
    def get_db(cls):
        if cls._db is None:
            client = cls.get_client()
            # Extract database name from URI or use Config.DB_NAME
            cls._db = client.get_default_database(default=Config.DB_NAME)
            cls._ensure_indexes(cls._db)
        return cls._db

    @classmethod
    def _ensure_indexes(cls, db):
        try:
            # Users collection indexes
            db.users.create_index([("email", ASCENDING)], unique=True, sparse=True)
            db.users.create_index([("phone", ASCENDING)])
            
            # Admins collection indexes
            db.admins.create_index([("email", ASCENDING)], unique=True)
            
            # Menu items collection indexes
            db.menu_items.create_index([("category", ASCENDING)])
            db.menu_items.create_index([("is_available", ASCENDING)])
            
            # Orders collection indexes
            db.orders.create_index([("status", ASCENDING)])
            db.orders.create_index([("table_number", ASCENDING)])
            db.orders.create_index([("user_id", ASCENDING)])
            db.orders.create_index([("created_at", DESCENDING)])
            
            # Tables collection indexes
            db.tables.create_index([("table_number", ASCENDING)], unique=True)
        except Exception as e:
            print(f"[WARN] Error ensuring indexes: {e}", file=sys.stderr)

def get_db():
    """Convenience function to get the current MongoDB database instance."""
    return Database.get_db()

def serialize_doc(doc):
    """Recursively serializes MongoDB document for JSON/Template consumption."""
    if not doc:
        return doc
    result = {}
    for key, value in doc.items():
        if key == '_id':
            result['id'] = str(value)
            result['_id'] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, list):
            result[key] = [serialize_doc(item) if isinstance(item, dict) else (str(item) if isinstance(item, ObjectId) else item) for item in value]
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        else:
            result[key] = value
            
    # Provide ordered_items alias if items exists so templates avoid dict.items method collision
    if 'items' in result and isinstance(result['items'], list):
        result['ordered_items'] = result['items']
        
    return result

def serialize_docs(docs):
    """Serialize a cursor or list of MongoDB documents."""
    return [serialize_doc(d) for d in docs]
