#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mongo_db.py — Couche base de données MongoDB pour Kengni Finance
Remplace SQLite sans changer la logique métier de app.py
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
import os
from datetime import datetime

# ── Connexion MongoDB ──────────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGODB_URI", "")

_client = None
_db = None

def get_mongo_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI)
        _db = _client["kengni_finance"]
    return _db

def get_db():
    return get_mongo_db()

# ── Collections ────────────────────────────────────────────────────────────────
def get_col(name):
    return get_mongo_db()[name]

# ── Auto-incrément (remplace INTEGER PRIMARY KEY AUTOINCREMENT) ────────────────
def get_next_id(collection_name: str) -> int:
    """Retourne le prochain ID entier pour une collection."""
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
    """Convertit un document MongoDB en dict compatible SQLite (retire _id, garde id)."""
    if doc is None:
        return None
    d = dict(doc)
    d.pop("_id", None)
    return d

def docs_to_list(cursor):
    """Convertit un curseur MongoDB en liste de dicts."""
    return [doc_to_dict(d) for d in cursor]

# ── Initialisation de la base ──────────────────────────────────────────────────
def init_db():
    """Crée les index nécessaires et l'utilisateur admin par défaut."""
    from werkzeug.security import generate_password_hash

    db = get_mongo_db()

    # Index uniques et de performance
    db.users.create_index("email", unique=True)
    db.users.create_index("id", unique=True)
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
    db.training_leads.create_index("id", unique=True)
    db.reports.create_index("id", unique=True)
    db.trader_scores.create_index("id", unique=True)
    db.psychological_patterns.create_index("id", unique=True)
    db.ai_analysis.create_index("id", unique=True)
    db.agenda_reminders_sent.create_index("id", unique=True)

    # Créer l'utilisateur admin par défaut s'il n'existe pas
    existing = db.users.find_one({"email": "fabrice.kengni@icloud.com"})
    if not existing:
        uid = get_next_id("users")
        db.users.insert_one({
            "id": uid,
            "username": "kengni",
            "email": "fabrice.kengni@icloud.com",
            "password": generate_password_hash("Kengni@fablo12"),
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
    else:
        # S'assurer que l'admin a toujours le bon mot de passe
        db.users.update_one(
            {"email": "fabrice.kengni@icloud.com", "role": "admin"},
            {"$set": {"password": generate_password_hash("Kengni@fablo12")}}
        )

    print("✅ MongoDB initialisée avec succès !")
