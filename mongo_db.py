#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mongo_db.py — Couche base de données MongoDB pour Kengni Finance
Version corrigée pour Vercel (serverless) + MongoDB Atlas
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
import os
from datetime import datetime

# ── Connection string ──────────────────────────────────────────────────────────
MONGO_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb+srv://Vercel-Admin-fabricekengni12_db_user:aoo4baxbOeTkr5qz@fabricekengni12-db-user.v193src.mongodb.net/kengni_finance?retryWrites=true&w=majority&appName=fabricekengni12-db-user"
)

# ── Cache de connexion (crucial pour Vercel serverless) ───────────────────────
_client = None
_db     = None

def get_mongo_db():
    global _client, _db
    if _db is not None:
        try:
            _client.admin.command("ping")
            return _db
        except Exception:
            _client = None
            _db = None

    _client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=8000,
        connectTimeoutMS=8000,
        socketTimeoutMS=30000,
        maxPoolSize=1,
        retryWrites=True,
    )
    _db = _client["kengni_finance"]
    return _db

def get_db():
    return get_mongo_db()

# ── Collections ────────────────────────────────────────────────────────────────
def get_col(name):
    return get_mongo_db()[name]

# ── Auto-incrément ─────────────────────────────────────────────────────────────
def get_next_id(collection_name: str) -> int:
    db = get_mongo_db()
    result = db.counters.find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result["seq"]

# ── Helpers ────────────────────────────────────────────────────────────────────
def doc_to_dict(doc):
    if doc is None:
        return None
    d = dict(doc)
    d.pop("_id", None)
    return d

def docs_to_list(cursor):
    return [doc_to_dict(d) for d in cursor]

# ── Initialisation de la base ──────────────────────────────────────────────────
def init_db():
    from werkzeug.security import generate_password_hash

    db = get_mongo_db()

    # Index de performance
    db.users.create_index("email", unique=True)
    db.users.create_index("id",    unique=True)
    db.financial_transactions.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
    db.financial_transactions.create_index("id", unique=True)
    db.transactions.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.transactions.create_index("id", unique=True)
    db.positions.create_index([("user_id", ASCENDING), ("symbol", ASCENDING)])
    db.positions.create_index("id", unique=True)
    db.trading_journal.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
    db.trading_journal.create_index("id", unique=True)
    db.notifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.notifications.create_index("id", unique=True)
    db.agenda_events.create_index([("user_id", ASCENDING), ("start_datetime", ASCENDING)])
    db.agenda_events.create_index("id", unique=True)
    db.training_courses.create_index([("user_id", ASCENDING)])
    db.training_courses.create_index("id", unique=True)
    db.training_leads.create_index("id",         unique=True)
    db.reports.create_index("id",                unique=True)
    db.trader_scores.create_index("id",          unique=True)
    db.psychological_patterns.create_index("id", unique=True)
    db.ai_analysis.create_index("id",            unique=True)
    db.agenda_reminders_sent.create_index("id",  unique=True)

    # Admin par défaut depuis les variables d'environnement
    admin_email    = os.environ.get("ADMIN_EMAIL",    "fabrice.kengni@icloud.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Kengni@fablo12")

    existing = db.users.find_one({"email": admin_email})
    if not existing:
        uid = get_next_id("users")
        db.users.insert_one({
            "id": uid,
            "username": "kengni",
            "email": admin_email,
            "password": generate_password_hash(admin_password),
            "role": "admin",
            "status": "active",
            "preferred_currency": "EUR",
            "timezone": "Europe/Paris",
            "theme": "dark",
            "notifications_email": 1,
            "notifications_app": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_login": None
        })
        print(f"✅ Admin créé : {admin_email}")
    else:
        # FIX MOT DE PASSE — toujours resynchroniser avec la variable d'env
        db.users.update_one(
            {"email": admin_email},
            {"$set": {
                "password":   generate_password_hash(admin_password),
                "role":       "admin",
                "status":     "active",
                "updated_at": datetime.now().isoformat()
            }}
        )
        print(f"✅ Admin synchronisé : {admin_email}")

    print("✅ MongoDB Atlas prête !")