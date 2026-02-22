# ════════════════════════════════════════════════════════════════
# PATCH RAILWAY / POSTGRESQL
# Remplace les lignes suivantes dans ton app.py :
#
#   DB_FILE = 'kengni_finance.db'
#
#   def get_db_connection():
#       connection = sqlite3.connect(DB_FILE)
#       connection.row_factory = sqlite3.Row
#       return connection
#
# Par ce bloc :
# ════════════════════════════════════════════════════════════════

import os
DATABASE_URL = os.environ.get('DATABASE_URL')  # Railway injecte cette variable

if DATABASE_URL:
    # ── Mode PostgreSQL (Railway) ──────────────────────────────
    import psycopg2
    import psycopg2.extras

    def get_db_connection():
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            conn.autocommit = False
            return conn
        except Exception as e:
            print(f"PostgreSQL connection error: {e}")
            return None

else:
    # ── Mode SQLite (local) ────────────────────────────────────
    import sqlite3
    DB_FILE = 'kengni_finance.db'

    def get_db_connection():
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"SQLite connection error: {e}")
            return None

# ════════════════════════════════════════════════════════════════
# IMPORTANT : dans toutes tes requêtes SQL, remplace aussi
#   %s  →  ?   en SQLite  (déjà bon)
#   ?   →  %s  en PostgreSQL
#
# La façon la plus simple : utilise un helper comme ceci :
#
#   PLACEHOLDER = '%s' if DATABASE_URL else '?'
#
# Exemple :
#   cursor.execute(f"SELECT * FROM users WHERE email={PLACEHOLDER}", (email,))
# ════════════════════════════════════════════════════════════════
PLACEHOLDER = '%s' if DATABASE_URL else '?'

# ════════════════════════════════════════════════════════════════
# AUSSI : remplace dans __main__ la ligne :
#   app.run(debug=True, host='0.0.0.0', port=5001)
# Par :
#   port = int(os.environ.get('PORT', 5001))
#   app.run(debug=False, host='0.0.0.0', port=port)
# ════════════════════════════════════════════════════════════════
