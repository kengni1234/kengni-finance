#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_and_fix.py — Migration SQLite → MongoDB Atlas + fix mot de passe
Kengni Finance — Script tout-en-un
Lance : python3 migrate_and_fix.py
"""

import sqlite3, os, sys
from datetime import datetime

# ══════════════════════════════════════════════════════════════
# TA CONFIGURATION — déjà remplie !
# ══════════════════════════════════════════════════════════════

MONGODB_URI = "mongodb+srv://Vercel-Admin-fabricekengni12_db_user:MWoiKRSDZO3eVBVL@fabricekengni12-db-user.v193src.mongodb.net/kengni_finance?retryWrites=true&w=majority&appName=fabricekengni12-db-user"
SQLITE_PATH = "kengni_finance.db"
DB_NAME     = "kengni_finance"

# Mot de passe admin à corriger
ADMIN_EMAIL    = "fabrice.kengni@icloud.com"
ADMIN_PASSWORD = "Kengni@fablo12"

# ══════════════════════════════════════════════════════════════
# VÉRIFICATION DÉPENDANCES
# ══════════════════════════════════════════════════════════════

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
except ImportError:
    print("❌ pymongo manquant. Lancez d'abord :")
    print("   pip install pymongo dnspython")
    sys.exit(1)

try:
    from werkzeug.security import generate_password_hash
except ImportError:
    print("❌ werkzeug manquant. Lancez d'abord :")
    print("   pip install werkzeug")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════
# CONNEXIONS
# ══════════════════════════════════════════════════════════════

def connect_sqlite():
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ Fichier SQLite introuvable : {SQLITE_PATH}")
        print("   Assurez-vous de lancer ce script depuis le dossier du projet.")
        sys.exit(1)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    print(f"✅ SQLite connecté : {SQLITE_PATH}")
    return conn

def connect_mongo():
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")
        db = client[DB_NAME]
        print(f"✅ MongoDB Atlas connecté ! (base : {DB_NAME})")
        return db
    except Exception as e:
        print(f"❌ Connexion MongoDB échouée : {e}")
        sys.exit(1)

# ══════════════════════════════════════════════════════════════
# MIGRATION
# ══════════════════════════════════════════════════════════════

TABLES = [
    "users",
    "positions",
    "transactions",
    "trading_journal",
    "ai_analysis",
    "trader_scores",
    "psychological_patterns",
    "reports",
    "notifications",
    "financial_transactions",
    "training_courses",
    "training_leads",
    "agenda_events",
    "agenda_reminders_sent",
]

def migrate_all(sqlite_conn, mongo_db):
    total = 0
    for table in TABLES:
        try:
            cursor = sqlite_conn.cursor()
            cursor.execute(f'SELECT * FROM "{table}"')
            rows = [dict(r) for r in cursor.fetchall()]

            col = mongo_db[table]
            col.delete_many({})  # nettoyage avant import

            if rows:
                col.insert_many(rows)
                print(f"   ✅ {table:<30} {len(rows)} documents")
                total += len(rows)
            else:
                print(f"   ⏭️  {table:<30} vide")
        except Exception as e:
            print(f"   ❌ {table:<30} erreur : {e}")
    return total

def migrate_counters(sqlite_conn, mongo_db):
    """Synchronise les compteurs auto-incrément."""
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT name, seq FROM sqlite_sequence")
        sequences = cursor.fetchall()
        mongo_db.counters.delete_many({})
        for name, seq in sequences:
            mongo_db.counters.replace_one(
                {"_id": name},
                {"_id": name, "seq": seq},
                upsert=True
            )
        print(f"   ✅ {'counters':<30} {len(sequences)} séquences")
    except Exception as e:
        print(f"   ❌ counters : {e}")

def create_indexes(mongo_db):
    """Crée tous les index de performance."""
    try:
        mongo_db.users.create_index("email", unique=True)
        mongo_db.users.create_index("id",    unique=True)
        mongo_db.financial_transactions.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
        mongo_db.financial_transactions.create_index("id", unique=True)
        mongo_db.transactions.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        mongo_db.transactions.create_index("id", unique=True)
        mongo_db.positions.create_index([("user_id", ASCENDING), ("symbol", ASCENDING)])
        mongo_db.positions.create_index("id", unique=True)
        mongo_db.trading_journal.create_index("id", unique=True)
        mongo_db.notifications.create_index("id", unique=True)
        mongo_db.agenda_events.create_index("id", unique=True)
        mongo_db.training_courses.create_index("id", unique=True)
        print("   ✅ Index créés")
    except Exception as e:
        print(f"   ⚠️  Index (non bloquant) : {e}")

def fix_admin_password(mongo_db):
    """Corrige le mot de passe admin — résout le bug de connexion."""
    new_hash = generate_password_hash(ADMIN_PASSWORD)
    result = mongo_db.users.update_one(
        {"email": ADMIN_EMAIL},
        {"$set": {
            "password": new_hash,
            "role": "admin",
            "status": "active",
            "updated_at": datetime.now().isoformat()
        }}
    )
    if result.matched_count > 0:
        print(f"   ✅ Mot de passe admin corrigé pour : {ADMIN_EMAIL}")
    else:
        # L'utilisateur n'existe pas encore → on le crée
        from pymongo import MongoClient
        next_id = mongo_db.counters.find_one_and_update(
            {"_id": "users"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )["seq"]
        mongo_db.users.insert_one({
            "id": next_id,
            "username": "kengni",
            "email": ADMIN_EMAIL,
            "password": new_hash,
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
        print(f"   ✅ Admin créé : {ADMIN_EMAIL}")

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print()
    print("=" * 60)
    print("  🚀 Kengni Finance — Migration SQLite → MongoDB Atlas")
    print(f"  📅 {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    print("=" * 60)

    sqlite_conn = connect_sqlite()
    mongo_db    = connect_mongo()

    print()
    print("📦 Étape 1 — Migration des données...")
    total = migrate_all(sqlite_conn, mongo_db)

    print()
    print("🔢 Étape 2 — Synchronisation des compteurs...")
    migrate_counters(sqlite_conn, mongo_db)

    print()
    print("⚡ Étape 3 — Création des index...")
    create_indexes(mongo_db)

    print()
    print("🔐 Étape 4 — Correction du mot de passe admin...")
    fix_admin_password(mongo_db)

    sqlite_conn.close()

    print()
    print("=" * 60)
    print(f"  🎉 TERMINÉ ! {total} documents migrés vers MongoDB Atlas")
    print("=" * 60)
    print()
    print("  Connexion à l'app :")
    print(f"  📧 Email    : {ADMIN_EMAIL}")
    print(f"  🔑 Password : {ADMIN_PASSWORD}")
    print()
    print("  Prochaine étape — déployez sur Vercel :")
    print("  1. Ajoutez MONGODB_URI dans Vercel → Settings → Env Vars")
    print("  2. git add . && git commit -m 'mongo ok' && git push")
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()
