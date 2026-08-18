import sys
from datetime import datetime

from bson import ObjectId

from pymongo import (
    MongoClient,
    ASCENDING,
    DESCENDING
)

from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError
)

from config import Config


class Database:

    _client = None
    _db = None
    _indexes_created = False

    # =========================
    # MongoDB Client
    # =========================

    @classmethod
    def get_client(cls):

        if cls._client is None:

            if not Config.MONGO_URI:
                raise RuntimeError(
                    "MONGO_URI environment variable is not set."
                )

            try:

                print(
                    "[INFO] Creating MongoDB Atlas client...",
                    file=sys.stderr
                )

                cls._client = MongoClient(
                    Config.MONGO_URI,
                    **Config.MONGO_OPTIONS
                )

                print(
                    "[INFO] MongoDB client created.",
                    file=sys.stderr
                )

            except Exception as e:

                cls._client = None

                print(
                    "[ERROR] Could not create MongoDB client.",
                    file=sys.stderr
                )

                print(
                    f"[ERROR] {e}",
                    file=sys.stderr
                )

                raise

        return cls._client

    # =========================
    # Database
    # =========================

    @classmethod
    def get_db(cls):

        if cls._db is None:

            client = cls.get_client()

            cls._db = client[Config.DB_NAME]

            print(
                f"[INFO] Using MongoDB database: {Config.DB_NAME}",
                file=sys.stderr
            )

        # Create indexes only once
        if not cls._indexes_created:

            cls._ensure_indexes(cls._db)

            cls._indexes_created = True

        return cls._db

    # =========================
    # Indexes
    # =========================

    @classmethod
    def _ensure_indexes(cls, db):

        try:

            # =========================
            # Users
            # =========================

            db.users.create_index(
                [("email", ASCENDING)],
                unique=True,
                sparse=True
            )

            db.users.create_index(
                [("phone", ASCENDING)]
            )

            # =========================
            # Admins
            # =========================

            db.admins.create_index(
                [("email", ASCENDING)],
                unique=True
            )

            # =========================
            # Menu Items
            # =========================

            db.menu_items.create_index(
                [("category", ASCENDING)]
            )

            db.menu_items.create_index(
                [("is_available", ASCENDING)]
            )

            # =========================
            # Orders
            # =========================

            db.orders.create_index(
                [("status", ASCENDING)]
            )

            db.orders.create_index(
                [("table_number", ASCENDING)]
            )

            db.orders.create_index(
                [("user_id", ASCENDING)]
            )

            db.orders.create_index(
                [("created_at", DESCENDING)]
            )

            # =========================
            # Tables
            # =========================

            db.tables.create_index(
                [("table_number", ASCENDING)],
                unique=True
            )

            print(
                "[INFO] MongoDB indexes ready.",
                file=sys.stderr
            )

        except Exception as e:

            print(
                f"[WARN] Error ensuring indexes: {e}",
                file=sys.stderr
            )

    # =========================
    # Optional Connection Test
    # =========================

    @classmethod
    def test_connection(cls):

        try:

            client = cls.get_client()

            client.admin.command("ping")

            print(
                "[INFO] MongoDB Atlas connection successful.",
                file=sys.stderr
            )

            return True

        except (
            ConnectionFailure,
            ServerSelectionTimeoutError
        ) as e:

            print(
                "[ERROR] MongoDB Atlas connection failed.",
                file=sys.stderr
            )

            print(
                f"[ERROR] {e}",
                file=sys.stderr
            )

            return False


# =========================
# Convenience Function
# =========================

def get_db():
    return Database.get_db()


# =========================
# Serialize One Document
# =========================

def serialize_doc(doc):

    if not doc:
        return doc

    result = {}

    for key, value in doc.items():

        if key == "_id":

            result["id"] = str(value)
            result["_id"] = str(value)

        elif isinstance(value, ObjectId):

            result[key] = str(value)

        elif isinstance(value, datetime):

            result[key] = value.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        elif isinstance(value, list):

            result[key] = [
                serialize_doc(item)
                if isinstance(item, dict)
                else (
                    str(item)
                    if isinstance(item, ObjectId)
                    else item
                )
                for item in value
            ]

        elif isinstance(value, dict):

            result[key] = serialize_doc(value)

        else:

            result[key] = value

    # Prevent Jinja dict.items collision
    if (
        "items" in result
        and isinstance(result["items"], list)
    ):
        result["ordered_items"] = result["items"]

    return result


# =========================
# Serialize Multiple Docs
# =========================

def serialize_docs(docs):

    return [
        serialize_doc(document)
        for document in docs
    ]
