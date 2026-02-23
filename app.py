#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kengni Finance - Complete Financial Management & Trading Application
Version 2.0 - Enhanced with AI Analysis and Advanced Features
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import sqlite3
import os
from datetime import datetime, timedelta
import secrets
import random
import json
import pandas as pd
from io import BytesIO
import yfinance as yf
import numpy as np
import base64
from PIL import Image
import io
import urllib.request
import re
import smtplib
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# ── Configuration Gmail pour les rappels d'agenda ──────────────────────────────
GMAIL_CONFIG = {
    'sender_email':    'fabrice.kengni12@gmail.com',
    'sender_name':     'Kengni Finance — Agenda',
    'receiver_email':  'fabrice.kengni@icloud.com',
    'smtp_host':       'smtp.gmail.com',
    'smtp_port':       587,
    'smtp_password':   os.environ.get('GMAIL_PASSWORD', 'hmoz eelj nckb npqi'),
}

# ── Types et couleurs des événements d'agenda ─────────────────────────────────
AGENDA_EVENT_COLORS = {
    'trading':   {'bg': '#00d4aa', 'border': '#00b894', 'icon': '📈', 'label': 'Trading'},
    'finance':   {'bg': '#4a9eff', 'border': '#2980b9', 'icon': '💰', 'label': 'Finance'},
    'formation': {'bg': '#a29bfe', 'border': '#6c5ce7', 'icon': '📚', 'label': 'Formation'},
    'personnel': {'bg': '#fd79a8', 'border': '#e84393', 'icon': '👤', 'label': 'Personnel'},
    'reunion':   {'bg': '#ffd700', 'border': '#f39c12', 'icon': '🤝', 'label': 'Réunion'},
    'revue':     {'bg': '#ff7675', 'border': '#d63031', 'icon': '🔍', 'label': 'Revue'},
}

# ── Informations de paiement Kengni Trading Academy ─────────────────────────
PAYMENT_INFO = {
    'orange_money': {'numero': '695 072 659', 'nom': 'Fabrice Kengni', 'label': 'Orange Money'},
    'mtn_money':    {'numero': '670 695 946', 'nom': 'Fabrice Kengni', 'label': 'MTN MoMo'},
    'paypal':       {'adresse': 'fabrice.kengni@icloud.com', 'label': 'PayPal'},
    'crypto':       {'adresse': 'fabrice.kengni@icloud.com', 'label': 'Crypto (via email)'},
}

FORMATION_PRICES = {
    'Débutant':       {'xaf': 25000,  'eur': 38},
    'Intermédiaire':  {'xaf': 50000,  'eur': 76},
    'Avancé':         {'xaf': 100000, 'eur': 152},
    'Pro / Mentoring':{'xaf': 200000, 'eur': 305},
}

# Add Python built-in functions to Jinja2 environment
app.jinja_env.globals.update({
    'abs': abs,
    'min': min,
    'max': max,
    'round': round,
    'int': int,
    'float': float,
    'len': len,
    'sum': sum
})

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Configuration — PostgreSQL sur Railway, SQLite en local
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # ── Mode PostgreSQL (Railway) ──────────────────────────────────────────────
    import psycopg2
    import psycopg2.extras

    DB_FILE = None  # Non utilisé en mode PostgreSQL

    def get_db_connection():
        """Create and return PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            conn.autocommit = False
            return conn
        except Exception as e:
            print(f"PostgreSQL connection error: {e}")
            return None
else:
    # ── Mode SQLite (local) ────────────────────────────────────────────────────
    DB_FILE = 'kengni_finance.db'

    def get_db_connection():
        """Create and return SQLite database connection"""
        try:
            connection = sqlite3.connect(DB_FILE)
            connection.row_factory = sqlite3.Row
            return connection
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

# Allowed extensions for image uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database with enhanced tables
def init_db():
    """Initialize database with all tables"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        # Détecter le mode : PostgreSQL ou SQLite
        PG = DATABASE_URL is not None
        PH = '%s' if PG else '?'  # placeholder
        AI = 'SERIAL' if PG else 'INTEGER'  # auto-increment
        
        # Users table with preferences
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {AI} PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'active',
            preferred_currency TEXT DEFAULT 'EUR',
            timezone TEXT DEFAULT 'Europe/Paris',
            theme TEXT DEFAULT 'light',
            notifications_email INTEGER DEFAULT 1,
            notifications_app INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
        ''')
        
        # Financial transactions with enhanced categories
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS financial_transactions (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            reason TEXT NOT NULL,
            usage TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'EUR',
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            payment_method TEXT,
            reference TEXT,
            status TEXT DEFAULT 'completed',
            notes TEXT,
            tags TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Trading positions
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS positions (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            quantity REAL NOT NULL,
            avg_price REAL NOT NULL,
            current_price REAL NOT NULL,
            status TEXT DEFAULT 'open',
            stop_loss REAL,
            take_profit REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            closed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Trading transactions
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS transactions (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            amount REAL NOT NULL,
            fees REAL DEFAULT 0,
            status TEXT DEFAULT 'completed',
            strategy TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Trading journal with images
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS trading_journal (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            transaction_id INTEGER,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity REAL NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            profit_loss REAL,
            strategy TEXT,
            setup_description TEXT,
            emotions TEXT,
            mistakes TEXT,
            lessons_learned TEXT,
            notes TEXT,
            image_path TEXT,
            chart_analysis TEXT,
            market_conditions TEXT,
            risk_reward_ratio REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
        ''')
        
        # AI Analysis results
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS ai_analysis (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            analysis_type TEXT NOT NULL,
            subject TEXT,
            insights TEXT NOT NULL,
            recommendations TEXT,
            warnings TEXT,
            confidence_score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Trader performance scores
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS trader_scores (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            overall_score REAL NOT NULL,
            discipline_score REAL,
            risk_management_score REAL,
            strategy_consistency_score REAL,
            emotional_control_score REAL,
            profitability_score REAL,
            monthly_trades INTEGER,
            win_rate REAL,
            profit_factor REAL,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Psychological patterns detection
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS psychological_patterns (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            pattern_type TEXT NOT NULL,
            severity TEXT,
            detected_date TEXT NOT NULL,
            description TEXT,
            evidence TEXT,
            recommendations TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Reports table
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS reports (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            report_type TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            revenue REAL DEFAULT 0,
            expenses REAL DEFAULT 0,
            profit REAL DEFAULT 0,
            profit_margin REAL DEFAULT 0,
            data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Notifications
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS notifications (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            action_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')

        # ── TABLE : Événements d'agenda ────────────────────────────────────────
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS agenda_events (
            id               {AI} PRIMARY KEY,
            user_id          INTEGER NOT NULL,
            title            TEXT NOT NULL,
            description      TEXT,
            event_type       TEXT NOT NULL DEFAULT 'personnel',
            start_datetime   TEXT NOT NULL,
            end_datetime     TEXT NOT NULL,
            all_day          INTEGER DEFAULT 0,
            recurrence       TEXT DEFAULT 'none',
            reminder_minutes INTEGER DEFAULT 30,
            email_reminder   INTEGER DEFAULT 1,
            app_reminder     INTEGER DEFAULT 1,
            location         TEXT,
            notes            TEXT,
            linked_course_id INTEGER,
            status           TEXT DEFAULT 'active',
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at       TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')

        # ── TABLE : Rappels envoyés (anti-doublon) ─────────────────────────────
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS agenda_reminders_sent (
            id        {AI} PRIMARY KEY,
            event_id  INTEGER NOT NULL,
            sent_at   TEXT NOT NULL,
            method    TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES agenda_events(id)
        )
        ''')
        
        # Training courses
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS training_courses (
            id {AI} PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'Sans titre',
            description TEXT,
            course_url TEXT,
            thumbnail_url TEXT,
            category TEXT DEFAULT 'Général',
            level TEXT DEFAULT 'debutant',
            day_of_week TEXT DEFAULT 'Non défini',
            scheduled_date TEXT,
            duration_minutes INTEGER DEFAULT 0,
            tags TEXT,
            is_published INTEGER DEFAULT 1,
            view_count INTEGER DEFAULT 0,
            participant_names TEXT DEFAULT '',
            analyses TEXT DEFAULT '',
            strategies TEXT DEFAULT '',
            position_images TEXT DEFAULT '[]',
            time_start TEXT DEFAULT '',
            time_end TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        # Migration: add columns if not exist
        if not PG:
            for col, defn in [
                ('participant_names', 'TEXT DEFAULT ""'),
                ('analyses', 'TEXT DEFAULT ""'),
                ('strategies', 'TEXT DEFAULT ""'),
                ('position_images', 'TEXT DEFAULT "[]"'),
                ('time_start', 'TEXT DEFAULT ""'),
                ('time_end', 'TEXT DEFAULT ""'),
            ]:
                try:
                    cursor.execute(f'ALTER TABLE training_courses ADD COLUMN {col} {defn}')
                except Exception:
                    pass

        # ── TABLE : Inscriptions Kengni Trading Academy ──
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS training_leads (
            id              {AI} PRIMARY KEY,
            full_name       TEXT NOT NULL,
            email           TEXT NOT NULL,
            whatsapp        TEXT NOT NULL,
            level_selected  TEXT NOT NULL,
            capital         TEXT,
            objective       TEXT,
            source          TEXT DEFAULT 'Non renseigné',
            status          TEXT NOT NULL DEFAULT 'Nouveau',
            notes           TEXT,
            user_id         INTEGER,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        if not PG:
            for col, defn in [('notes', 'TEXT'), ('user_id', 'INTEGER'), ('capital', 'TEXT'), ('objective', 'TEXT'),
                              ('payment_method', 'TEXT'), ('payment_ref', 'TEXT'), ('payment_status', "TEXT DEFAULT 'En attente'"),
                              ('amount_paid', 'REAL DEFAULT 0'), ('sincire_sent_at', 'TEXT')]:
                try:
                    cursor.execute(f'ALTER TABLE training_leads ADD COLUMN {col} {defn}')
                except Exception:
                    pass

        # Check if default user exists
        cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE email = {PH}", ('fabrice.kengni@icloud.com',))
        result = cursor.fetchone()
        count = result[0] if PG else result['count']
        if count == 0:
            hashed_password = generate_password_hash('Kengni@fablo12')
            cursor.execute(f'''
                INSERT INTO users (username, email, password, role, created_at)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH})
            ''', ('kengni', 'fabrice.kengni@icloud.com', hashed_password, 'admin', datetime.now().isoformat()))
        else:
            # Ensure admin always has the correct password (double sécurité)
            hashed_password = generate_password_hash('Kengni@fablo12')
            cursor.execute(
                f"UPDATE users SET password={PH} WHERE email={PH} AND role='admin'",
                (hashed_password, 'fabrice.kengni@icloud.com')
            )
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully!")

# ── URL secrète admin ──
ADMIN_SECRET_TOKEN = 'kengni-control-7749'
ADMIN_SECONDARY_PASSWORD = 'Kengni@fablo12'

# ── Initialisation automatique (gunicorn / Railway ne passe pas par __main__) ──
with app.app_context():
    try:
        init_db()
        start_agenda_scheduler()
        start_report_scheduler()
    except Exception as _e:
        print(f"[Init] Erreur au démarrage : {_e}")


@app.context_processor
def inject_global_context():
    """Injecte des variables globales disponibles dans tous les templates"""
    ctx = {'training_total_nav': 0}
    if 'user_id' in session:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM training_courses WHERE user_id = ?",
                    (session['user_id'],)
                )
                ctx['training_total_nav'] = cursor.fetchone()['cnt']
            except Exception:
                pass
            finally:
                conn.close()
    return ctx

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin-only decorator — 404 pour tout le monde, l'admin reste invisible
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') not in ('admin', 'superadmin'):
            from flask import abort; abort(404)
        return f(*args, **kwargs)
    return decorated_function

# AI Analysis Functions

def analyze_trading_psychology(user_id):
    """Analyze psychological trading patterns"""
    conn = get_db_connection()
    patterns = []
    
    if conn:
        cursor = conn.cursor()
        
        # Get recent transactions
        cursor.execute("""
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,))
        transactions = [dict(row) for row in cursor.fetchall()]
        
        # Get journal entries
        cursor.execute("""
            SELECT * FROM trading_journal
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (user_id,))
        journal_entries = [dict(row) for row in cursor.fetchall()]
        
        # Analyze patterns
        
        # 1. Overtrading detection
        recent_24h = sum(1 for t in transactions if datetime.fromisoformat(t['created_at']) > datetime.now() - timedelta(hours=24))
        if recent_24h > 10:
            patterns.append({
                'type': 'overtrading',
                'severity': 'high' if recent_24h > 20 else 'medium',
                'description': f'Vous avez effectué {recent_24h} transactions en 24h',
                'recommendation': 'Prenez du recul. Le overtrading augmente les frais et diminue la qualité des décisions.'
            })
        
        # 2. FOMO detection (buying after big moves)
        buy_after_loss = 0
        for i in range(1, min(len(transactions), 10)):
            if transactions[i]['type'] == 'buy' and i > 0:
                prev = transactions[i-1]
                if prev['type'] == 'sell' and prev['amount'] < 0:  # Previous was a loss
                    buy_after_loss += 1
        
        if buy_after_loss >= 3:
            patterns.append({
                'type': 'FOMO',
                'severity': 'high',
                'description': 'Tendance à acheter immédiatement après des pertes',
                'recommendation': 'Attendez 30 minutes avant toute nouvelle transaction après une perte.'
            })
        
        # 3. Revenge trading
        consecutive_losses = 0
        max_consecutive = 0
        for t in transactions:
            if t['type'] == 'sell' and t['amount'] < 0:
                consecutive_losses += 1
                max_consecutive = max(max_consecutive, consecutive_losses)
            else:
                consecutive_losses = 0
        
        if max_consecutive >= 3:
            patterns.append({
                'type': 'revenge_trading',
                'severity': 'critical',
                'description': f'{max_consecutive} pertes consécutives détectées',
                'recommendation': 'Arrêtez de trader après 2 pertes consécutives. Analysez vos erreurs.'
            })
        
        # 4. Emotional patterns from journal
        emotional_keywords = {
            'fear': ['peur', 'anxieux', 'stressé', 'inquiet', 'nerveux'],
            'greed': ['avidité', 'cupide', 'trop confiant', 'sûr de moi'],
            'overconfidence': ['facile', 'certain', 'évident', 'garanti']
        }
        
        for entry in journal_entries:
            if entry.get('emotions'):
                emotions_text = entry['emotions'].lower()
                for emotion, keywords in emotional_keywords.items():
                    if any(kw in emotions_text for kw in keywords):
                        patterns.append({
                            'type': emotion,
                            'severity': 'medium',
                            'description': f'Émotion détectée: {emotion}',
                            'recommendation': 'Identifiée dans votre journal. Restez objectif.'
                        })
        
        # Save patterns to database
        for pattern in patterns:
            cursor.execute("""
                INSERT INTO psychological_patterns 
                (user_id, pattern_type, severity, detected_date, description, recommendations)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                pattern['type'],
                pattern['severity'],
                datetime.now().isoformat(),
                pattern['description'],
                pattern['recommendation']
            ))
        
        conn.commit()
        conn.close()
    
    return patterns

def calculate_trader_score(user_id):
    """Calculate comprehensive trader score (0-100)"""
    conn = get_db_connection()
    score_data = {
        'overall_score': 50,
        'discipline_score': 50,
        'risk_management_score': 50,
        'strategy_consistency_score': 50,
        'emotional_control_score': 50,
        'profitability_score': 50,
        'details': {}
    }
    
    if conn:
        cursor = conn.cursor()
        
        # Get transactions
        cursor.execute("""
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 100
        """, (user_id,))
        transactions = [dict(row) for row in cursor.fetchall()]
        
        if not transactions:
            conn.close()
            return score_data
        
        # 1. Profitability Score (30% weight)
        total_profit = sum(t['amount'] for t in transactions if t['type'] == 'sell')
        total_invested = sum(abs(t['amount']) for t in transactions if t['type'] == 'buy')
        
        if total_invested > 0:
            roi = (total_profit / total_invested) * 100
            score_data['profitability_score'] = min(100, max(0, 50 + roi))
        
        wins = sum(1 for t in transactions if t['type'] == 'sell' and t['amount'] > 0)
        total_sells = sum(1 for t in transactions if t['type'] == 'sell')
        win_rate = (wins / total_sells * 100) if total_sells > 0 else 0
        score_data['details']['win_rate'] = round(win_rate, 2)
        
        # 2. Risk Management Score (25% weight)
        risk_score = 50
        
        # Check for stop losses
        cursor.execute("""
            SELECT COUNT(*) as with_sl FROM positions
            WHERE user_id = ? AND stop_loss IS NOT NULL
        """, (user_id,))
        positions_with_sl = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) as total FROM positions
            WHERE user_id = ?
        """, (user_id,))
        total_positions = cursor.fetchone()[0]
        
        if total_positions > 0:
            sl_percentage = (positions_with_sl / total_positions) * 100
            risk_score += (sl_percentage - 50) * 0.5
        
        # Check for position sizing consistency
        amounts = [abs(t['amount']) for t in transactions if t['type'] == 'buy']
        if len(amounts) > 5:
            avg_amount = np.mean(amounts)
            std_amount = np.std(amounts)
            cv = (std_amount / avg_amount) if avg_amount > 0 else 0
            if cv < 0.3:  # Good consistency
                risk_score += 20
            elif cv > 0.8:  # Poor consistency
                risk_score -= 20
        
        score_data['risk_management_score'] = min(100, max(0, risk_score))
        
        # 3. Discipline Score (20% weight)
        discipline_score = 50
        
        # Check for overtrading
        recent_24h = sum(1 for t in transactions if datetime.fromisoformat(t['created_at']) > datetime.now() - timedelta(hours=24))
        if recent_24h > 15:
            discipline_score -= 30
        elif recent_24h < 5:
            discipline_score += 20
        
        # Check for revenge trading patterns
        cursor.execute("""
            SELECT COUNT(*) FROM psychological_patterns
            WHERE user_id = ? AND pattern_type = 'revenge_trading' AND status = 'active'
        """, (user_id,))
        revenge_patterns = cursor.fetchone()[0]
        if revenge_patterns > 0:
            discipline_score -= 20
        
        score_data['discipline_score'] = min(100, max(0, discipline_score))
        
        # 4. Strategy Consistency (15% weight)
        cursor.execute("""
            SELECT strategy, COUNT(*) as count
            FROM transactions
            WHERE user_id = ? AND strategy IS NOT NULL
            GROUP BY strategy
        """, (user_id,))
        strategies = cursor.fetchall()
        
        strategy_score = 50
        if strategies:
            # Reward using consistent strategies
            max_strategy_count = max(s[1] for s in strategies)
            total_with_strategy = sum(s[1] for s in strategies)
            consistency = (max_strategy_count / total_with_strategy) * 100 if total_with_strategy > 0 else 0
            strategy_score = min(100, consistency)
        
        score_data['strategy_consistency_score'] = strategy_score
        
        # 5. Emotional Control (10% weight)
        cursor.execute("""
            SELECT COUNT(*) FROM psychological_patterns
            WHERE user_id = ? AND status = 'active'
        """, (user_id,))
        active_patterns = cursor.fetchone()[0]
        
        emotional_score = 100 - (active_patterns * 15)
        score_data['emotional_control_score'] = min(100, max(0, emotional_score))
        
        # Calculate overall score (weighted average)
        score_data['overall_score'] = round(
            score_data['profitability_score'] * 0.30 +
            score_data['risk_management_score'] * 0.25 +
            score_data['discipline_score'] * 0.20 +
            score_data['strategy_consistency_score'] * 0.15 +
            score_data['emotional_control_score'] * 0.10,
            2
        )
        
        # Save to database
        cursor.execute("""
            INSERT INTO trader_scores 
            (user_id, date, overall_score, discipline_score, risk_management_score, 
             strategy_consistency_score, emotional_control_score, profitability_score,
             monthly_trades, win_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            datetime.now().isoformat(),
            score_data['overall_score'],
            score_data['discipline_score'],
            score_data['risk_management_score'],
            score_data['strategy_consistency_score'],
            score_data['emotional_control_score'],
            score_data['profitability_score'],
            len(transactions),
            win_rate
        ))
        
        conn.commit()
        conn.close()
    
    return score_data

def analyze_financial_report(data):
    """AI-powered financial report analysis"""
    try:
        insights = {
            'summary': "Analyse automatique du rapport financier",
            'recommendations': [],
            'risks': [],
            'opportunities': [],
            'anomalies': []
        }
        
        if 'revenue' in data and 'expenses' in data:
            profit_margin = ((data['revenue'] - data['expenses']) / data['revenue'] * 100) if data['revenue'] > 0 else 0
            
            if profit_margin > 20:
                insights['recommendations'].append("✅ Excellente marge bénéficiaire. Envisagez d'investir dans la croissance.")
                insights['opportunities'].append("Capacité d'investissement disponible")
            elif profit_margin < 10:
                insights['recommendations'].append("⚠️ Marge bénéficiaire faible. Optimisez vos dépenses.")
                insights['risks'].append("Risque de rentabilité")
            
            if data['expenses'] > data['revenue']:
                insights['risks'].append("🚨 Dépenses supérieures aux revenus - attention critique!")
                insights['recommendations'].append("Action immédiate requise: réduire les dépenses de " + 
                    f"{round((data['expenses'] - data['revenue']) / data['revenue'] * 100, 2)}%")
            
            # Anomaly detection
            if data['expenses'] > data['revenue'] * 1.5:
                insights['anomalies'].append("Dépenses anormalement élevées détectées")
        
        return insights
    except Exception as e:
        return {'error': str(e)}

def analyze_trade_image(image_path, trade_data):
    """Analyze trading chart image and provide insights"""
    insights = {
        'setup_quality': 'N/A',
        'entry_timing': 'N/A',
        'risk_reward': 'N/A',
        'recommendations': []
    }
    
    try:
        # Basic analysis based on trade data
        if trade_data.get('risk_reward_ratio'):
            rr = trade_data['risk_reward_ratio']
            if rr >= 2:
                insights['risk_reward'] = 'Excellent'
                insights['recommendations'].append('✅ Bon ratio risque/récompense')
            elif rr >= 1:
                insights['risk_reward'] = 'Acceptable'
                insights['recommendations'].append('⚠️ Ratio risque/récompense minimum atteint')
            else:
                insights['risk_reward'] = 'Mauvais'
                insights['recommendations'].append('❌ Ratio risque/récompense insuffisant')
        
        # Analyze based on profit/loss
        if trade_data.get('profit_loss'):
            pl = trade_data['profit_loss']
            if pl > 0:
                insights['recommendations'].append('✅ Trade gagnant - analysez ce qui a fonctionné')
            else:
                insights['recommendations'].append('📝 Trade perdant - identifiez les erreurs')
        
        # Entry timing analysis
        if trade_data.get('strategy'):
            insights['setup_quality'] = 'Défini'
            insights['recommendations'].append(f'Strategy utilisée: {trade_data["strategy"]}')
        
    except Exception as e:
        insights['error'] = str(e)
    
    return insights

def trading_recommendation(symbol, timeframe='1mo'):
    """AI trading recommendations based on market data"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=timeframe)
        
        if hist.empty:
            return {'error': 'Données non disponibles'}
        
        current_price = hist['Close'].iloc[-1]
        sma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else sma_20
        
        rsi = calculate_rsi(hist['Close'])
        
        # Volume analysis
        avg_volume = hist['Volume'].mean()
        recent_volume = hist['Volume'].iloc[-1]
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        recommendation = {
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'sma_20': round(sma_20, 2),
            'sma_50': round(sma_50, 2),
            'rsi': round(rsi, 2),
            'volume_ratio': round(volume_ratio, 2),
            'signal': 'NEUTRE',
            'confidence': 50,
            'analysis': [],
            'entry_points': [],
            'stop_loss': 0,
            'take_profit': 0
        }
        
        # Trend analysis
        if current_price > sma_20 and sma_20 > sma_50:
            recommendation['analysis'].append("📈 Tendance haussière confirmée")
            trend_score = 20
        elif current_price < sma_20 and sma_20 < sma_50:
            recommendation['analysis'].append("📉 Tendance baissière confirmée")
            trend_score = -20
        else:
            recommendation['analysis'].append("➡️ Tendance neutre/consolidation")
            trend_score = 0
        
        # RSI analysis
        if rsi > 70:
            recommendation['analysis'].append(f"🔴 RSI: {round(rsi, 2)} - Surachat détecté")
            rsi_score = -15
        elif rsi < 30:
            recommendation['analysis'].append(f"🟢 RSI: {round(rsi, 2)} - Survente détectée")
            rsi_score = 15
        else:
            recommendation['analysis'].append(f"🟡 RSI: {round(rsi, 2)} - Zone neutre")
            rsi_score = 0
        
        # Volume analysis
        if volume_ratio > 1.5:
            recommendation['analysis'].append(f"📊 Volume élevé ({round(volume_ratio, 2)}x) - Signal fort")
            volume_score = 10
        else:
            volume_score = 0
        
        # Generate signal
        total_score = trend_score + rsi_score + volume_score
        
        if total_score > 20:
            recommendation['signal'] = 'ACHAT FORT'
            recommendation['confidence'] = min(90, 50 + total_score)
            recommendation['entry_points'].append(round(current_price * 0.98, 2))
            recommendation['stop_loss'] = round(current_price * 0.95, 2)
            recommendation['take_profit'] = round(current_price * 1.10, 2)
        elif total_score > 5:
            recommendation['signal'] = 'ACHAT'
            recommendation['confidence'] = min(80, 50 + total_score)
            recommendation['entry_points'].append(round(current_price * 0.99, 2))
            recommendation['stop_loss'] = round(current_price * 0.96, 2)
            recommendation['take_profit'] = round(current_price * 1.08, 2)
        elif total_score < -20:
            recommendation['signal'] = 'VENTE FORTE'
            recommendation['confidence'] = min(90, 50 + abs(total_score))
            recommendation['entry_points'].append(round(current_price * 1.02, 2))
            recommendation['stop_loss'] = round(current_price * 1.05, 2)
            recommendation['take_profit'] = round(current_price * 0.90, 2)
        elif total_score < -5:
            recommendation['signal'] = 'VENTE'
            recommendation['confidence'] = min(80, 50 + abs(total_score))
            recommendation['entry_points'].append(round(current_price * 1.01, 2))
            recommendation['stop_loss'] = round(current_price * 1.04, 2)
            recommendation['take_profit'] = round(current_price * 0.92, 2)
        else:
            recommendation['signal'] = 'ATTENDRE'
            recommendation['confidence'] = 50
            recommendation['analysis'].append("⏸️ Pas de signal clair - attendre un meilleur setup")
        
        return recommendation
    except Exception as e:
        return {'error': str(e)}

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

@app.route('/verify-token', methods=['GET', 'POST'])
def verify_token_page():
    """Vérification du token 2FA"""
    email = request.args.get('email', session.get('pending_2fa_email', ''))
    
    if request.method == 'POST':
        entered_token = request.form.get('token', '').strip()
        stored_token  = session.get('pending_2fa_token', '')
        expires_str   = session.get('pending_2fa_expires', '')
        
        # Vérifier expiration
        expired = False
        if expires_str:
            try:
                expires = datetime.fromisoformat(expires_str)
                expired = datetime.now() > expires
            except Exception:
                expired = True
        
        if expired:
            # Nettoyer session
            for k in list(session.keys()):
                if k.startswith('pending_2fa_'):
                    session.pop(k, None)
            return render_template('verify_token.html',
                email=email, error='Token expiré. Veuillez vous reconnecter.',
                token=None, message=None)
        
        if entered_token == stored_token:
            # Token correct — compléter la session
            is_admin_login = session.pop('pending_2fa_is_admin_login', False)
            session['user_id']  = session.pop('pending_2fa_user_id',  None)
            session['username'] = session.pop('pending_2fa_username', '')
            session['email']    = session.pop('pending_2fa_email',    '')
            session['theme']    = session.pop('pending_2fa_theme',    'dark')
            session['role']     = session.pop('pending_2fa_role',     'user')
            session.pop('pending_2fa_token',   None)
            session.pop('pending_2fa_expires', None)
            session['admin_secondary_verified'] = False  # Reset secondary check on new login
            
            if is_admin_login:
                return redirect(url_for('admin_secondary_verify'))
            return redirect(url_for('dashboard'))
        else:
            return render_template('verify_token.html',
                email=email,
                token=session.get('pending_2fa_token'),
                error='Code incorrect. Vérifiez et réessayez.',
                message=None)
    
    # GET — afficher la page avec le token (démo)
    pending_token = session.get('pending_2fa_token')
    if not pending_token:
        return redirect(url_for('login'))
    
    return render_template('verify_token.html',
        email=email,
        token=pending_token,
        error=None,
        message='Un code de vérification a été généré. Entrez-le ci-dessous pour continuer.')


def create_notification(user_id, notif_type, title, message):
    """Helper to create a notification"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notifications (user_id, type, title, message)
                VALUES (?, ?, ?, ?)
            """, (user_id, notif_type, title, message))
            conn.commit()
            conn.close()
    except Exception:
        pass

# Routes

@app.route('/')
def index():
    """Landing page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form if request.is_json else request.form
        email = data.get('email')
        password = data.get('password')
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                # Générer le token 2FA
                token_2fa = str(random.randint(100000, 999999))
                
                # Stocker les infos en session en attente de vérification
                session['pending_2fa_token']    = token_2fa
                session['pending_2fa_user_id']  = user['id']
                session['pending_2fa_username'] = user['username']
                session['pending_2fa_email']    = user['email']
                session['pending_2fa_theme']    = user['theme']
                session['pending_2fa_role']     = user['role']
                session['pending_2fa_expires']  = (datetime.now() + timedelta(minutes=5)).isoformat()
                
                # Update last login
                cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", 
                             (datetime.now().isoformat(), user['id']))
                conn.commit()
                conn.close()
                
                if request.is_json:
                    return jsonify({'success': True, 'redirect': url_for('verify_token_page', email=email)})
                return redirect(url_for('verify_token_page', email=email))
            
            conn.close()
        
        if request.is_json:
            return jsonify({'success': False, 'message': 'Email ou mot de passe incorrect'}), 401
        return render_template('login.html', error='Email ou mot de passe incorrect')
    
    return render_template('login.html')

@app.route('/api/login-flyers', methods=['GET'])
def login_flyers():
    """
    Endpoint PUBLIC (sans login) pour la page de connexion.
    Retourne la liste des images du journal de trading + les flyers statiques,
    afin que le carrousel de la page login se synchronise automatiquement.
    """
    items = []

    # 1. Images uploadées dans le journal de trading (toutes, pas filtrées par user)
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tj.image_path, tj.symbol, tj.type, tj.profit_loss, tj.strategy,
                       tj.date, tj.entry_price, tj.exit_price
                FROM trading_journal tj
                WHERE tj.image_path IS NOT NULL AND tj.image_path != ''
                ORDER BY tj.created_at DESC
                LIMIT 20
            """)
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                row = dict(row)
                # Normalise le chemin pour url_for
                img = row['image_path'].replace('static/', '').replace('\\', '/')
                pl = row.get('profit_loss')
                pl_str = (f"+{pl:.0f}€" if pl and pl > 0 else f"{pl:.0f}€") if pl is not None else None
                items.append({
                    'type': 'journal',
                    'img_url': f"/static/{img}",
                    'name': f"{row['symbol']} — {row['date']}",
                    'spec': row.get('strategy') or ('Achat' if row['type'] == 'buy' else 'Vente'),
                    'price': None,
                    'promo': pl_str,
                    'link': None,
                    'badge': 'TRADE' if (pl is None or pl >= 0) else 'PERTE',
                    'badge_color': '#00ff88' if (pl is None or pl >= 0) else '#ff4757'
                })
    except Exception as e:
        print(f"login_flyers journal error: {e}")

    # 2. Produits statiques (flyers) avec liens
    static_products = [
        {
            'img': '71JOBadJCL__SL1500___1_.jpg',
            'name': 'PC Gamer High-End',
            'price': '950k',
            'promo': '849k',
            'spec': 'RTX 4060 | 32GB RAM',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé%20par%20le%20PC%20Gamer%20High-End'
        },
        {
            'img': 'access-point-cisco-CAP2602I.jpg',
            'name': 'Cisco AP Pro',
            'price': '85k',
            'promo': '70k',
            'spec': 'Dual Band | PoE',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé%20par%20Cisco%20AP%20Pro'
        },
        {
            'img': 'bat.jpg',
            'name': 'Batterie 12V 9Ah',
            'price': '25k',
            'promo': '18k',
            'spec': 'Cycle Profond',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé%20par%20la%20Batterie%2012V'
        },
        {
            'img': 'mg-858.jpg',
            'name': 'Routeur MG-858',
            'price': '45k',
            'promo': '39k',
            'spec': '4G LTE Ultra-Fast',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé%20par%20le%20Routeur%20MG-858'
        },
        {
            'img': 'rb750r2_01-1.jpg',
            'name': 'MikroTik hEX lite',
            'price': '40k',
            'promo': '32k',
            'spec': '5 Ports Fast Ethernet',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé%20par%20le%20MikroTik%20hEX%20lite'
        },
        {
            'img': 'render.png',
            'name': 'Workstation Render',
            'price': '1.5M',
            'promo': '1.2M',
            'spec': 'Dual Xeon | 128GB RAM',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé%20par%20la%20Workstation%20Render'
        },
        {
            'img': 'Y58.jpg',
            'name': 'Switch Industriel',
            'price': '120k',
            'promo': '95k',
            'spec': 'Giga 8 Ports Métal',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé%20par%20le%20Switch%20Industriel'
        },
        {
            'img': 'seche.jpg',
            'name': 'Produit Séché',
            'price': '35k',
            'promo': '28k',
            'spec': 'Qualité Premium',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé'
        },
        {
            'img': 't1000yellow_elqj3whe7jtl75gy.webp',
            'name': 'T1000 Yellow',
            'price': '60k',
            'promo': '49k',
            'spec': 'Design Industriel',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé%20par%20le%20T1000%20Yellow'
        },
        {
            'img': 'TL-WR841NEU14_0-288x202x86-L-7022505730_normal_1524475444511q.jpg',
            'name': 'TP-Link WR841N',
            'price': '18k',
            'promo': '14k',
            'spec': 'WiFi 300Mbps',
            'link': 'https://wa.me/237XXXXXXXXX?text=Je%20suis%20intéressé%20par%20le%20TP-Link%20WR841N'
        },
    ]
    for p in static_products:
        flyer_path = os.path.join(app.static_folder, 'flyers', p['img'])
        if not os.path.exists(flyer_path):
            continue  # Skip missing flyer images silently
        items.append({
            'type': 'product',
            'img_url': f"/static/flyers/{p['img']}",
            'name': p['name'],
            'spec': p['spec'],
            'price': p['price'],
            'promo': p['promo'],
            'link': p['link'],
            'badge': 'PROMO',
            'badge_color': '#00d4aa'
        })

    return jsonify({'success': True, 'items': items})


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        preferred_currency = data.get('preferred_currency', 'EUR')
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append("Le nom d'utilisateur doit contenir au moins 3 caractères")
        
        if not email or '@' not in email:
            errors.append("Email invalide")
        
        if not password or len(password) < 6:
            errors.append("Le mot de passe doit contenir au moins 6 caractères")
        
        if password != confirm_password:
            errors.append("Les mots de passe ne correspondent pas")
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            return render_template('register.html', error=', '.join(errors))
        
        # Check if user already exists
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                conn.close()
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Cet email est déjà utilisé'}), 400
                return render_template('register.html', error='Cet email est déjà utilisé')
            
            # Create new user
            try:
                hashed_password = generate_password_hash(password)
                cursor.execute("""
                    INSERT INTO users 
                    (username, email, password, preferred_currency, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (username, email, hashed_password, preferred_currency, datetime.now().isoformat()))
                
                conn.commit()
                user_id = cursor.lastrowid
                conn.close()
                
                # Auto-login after registration
                session['user_id'] = user_id
                session['username'] = username
                session['email'] = email
                session['theme'] = 'dark'
                
                if request.is_json:
                    return jsonify({'success': True, 'redirect': url_for('dashboard')})
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                conn.close()
                if request.is_json:
                    return jsonify({'success': False, 'message': str(e)}), 500
                return render_template('register.html', error=f"Erreur lors de la création du compte: {str(e)}")
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    stats = {
        'net_worth': 0,
        'monthly_cashflow': 0,
        'expense_ratio': 0,
        'savings_rate': 0,
        'total_revenue': 0,
        'total_expenses': 0,
        'trader_score': 0
    }
    
    if conn:
        cursor = conn.cursor()
        
        # Get financial stats
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN type = 'revenue' THEN amount ELSE 0 END) as total_revenue,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expenses
            FROM financial_transactions
            WHERE user_id = ? AND date >= date('now', '-30 days')
        """, (user_id,))
        
        result = cursor.fetchone()
        if result:
            stats['total_revenue'] = result['total_revenue'] or 0
            stats['total_expenses'] = result['total_expenses'] or 0
            stats['monthly_cashflow'] = stats['total_revenue'] - stats['total_expenses']
            
            if stats['total_revenue'] > 0:
                stats['expense_ratio'] = (stats['total_expenses'] / stats['total_revenue']) * 100
                stats['savings_rate'] = 100 - stats['expense_ratio']
        
        # Get trading value
        cursor.execute("""
            SELECT SUM(quantity * current_price) as portfolio_value
            FROM positions
            WHERE user_id = ? AND status = 'open'
        """, (user_id,))
        
        result = cursor.fetchone()
        portfolio_value = result['portfolio_value'] or 0
        
        stats['net_worth'] = stats['monthly_cashflow'] + portfolio_value
        
        # Get latest trader score
        cursor.execute("""
            SELECT overall_score FROM trader_scores
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        result = cursor.fetchone()
        if result:
            stats['trader_score'] = result['overall_score']
        
        # Get recent transactions
        cursor.execute("""
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,))
        recent_transactions = [dict(row) for row in cursor.fetchall()]
        
        # Get unread notifications
        cursor.execute("""
            SELECT COUNT(*) as unread FROM notifications
            WHERE user_id = ? AND is_read = 0
        """, (user_id,))
        unread_notifications = cursor.fetchone()['unread']
        
        # === Données pour graphique Performance (6 derniers mois) ===
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', date) as month,
                SUM(CASE WHEN type='revenue' THEN amount ELSE 0 END) as revenus,
                SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as depenses
            FROM financial_transactions
            WHERE user_id = ? AND date >= date('now', '-6 months')
            GROUP BY month
            ORDER BY month
        """, (user_id,))
        perf_rows = cursor.fetchall()
        month_names = {'01':'Jan','02':'Fév','03':'Mar','04':'Avr','05':'Mai',
                       '06':'Juin','07':'Juil','08':'Août','09':'Sep','10':'Oct','11':'Nov','12':'Déc'}
        chart_labels   = [month_names.get(r['month'][-2:], r['month']) for r in perf_rows]
        chart_revenus  = [round(r['revenus'] or 0, 2) for r in perf_rows]
        chart_depenses = [round(r['depenses'] or 0, 2) for r in perf_rows]
        chart_solde    = [round((r['revenus'] or 0) - (r['depenses'] or 0), 2) for r in perf_rows]

        # === Données pour graphique Répartition par catégorie ===
        cursor.execute("""
            SELECT category, SUM(amount) as total
            FROM financial_transactions
            WHERE user_id = ? AND type='expense'
            GROUP BY category
            ORDER BY total DESC
            LIMIT 6
        """, (user_id,))
        cat_rows = cursor.fetchall()
        donut_labels = [r['category'] for r in cat_rows]
        donut_data   = [round(r['total'] or 0, 2) for r in cat_rows]

        # === Formations / Training ===
        cursor.execute("""
            SELECT id, title, category, level, scheduled_date, duration_minutes,
                   participant_names, time_start, time_end, created_at
            FROM training_courses
            WHERE user_id = ?
            ORDER BY scheduled_date DESC, created_at DESC
            LIMIT 5
        """, (user_id,))
        recent_trainings = [dict(r) for r in cursor.fetchall()]

        # Stats formations
        cursor.execute("SELECT COUNT(*) as total FROM training_courses WHERE user_id = ?", (user_id,))
        training_total = cursor.fetchone()['total']

        cursor.execute("SELECT SUM(duration_minutes) as total_min FROM training_courses WHERE user_id = ?", (user_id,))
        training_total_min = cursor.fetchone()['total_min'] or 0

        cursor.execute("""
            SELECT COUNT(*) as cnt FROM training_courses
            WHERE user_id = ? AND scheduled_date >= date('now', '-30 days')
        """, (user_id,))
        training_this_month = cursor.fetchone()['cnt']

        conn.close()

        return render_template('dashboard.html',
                             stats=stats,
                             transactions=recent_transactions,
                             unread_notifications=unread_notifications,
                             user_role=session.get('role','user'),
                             chart_labels=chart_labels,
                             chart_revenus=chart_revenus,
                             chart_depenses=chart_depenses,
                             chart_solde=chart_solde,
                             donut_labels=donut_labels,
                             donut_data=donut_data,
                             recent_trainings=recent_trainings,
                             training_total=training_total,
                             training_total_min=training_total_min,
                             training_this_month=training_this_month)

    return render_template('dashboard.html', stats=stats, transactions=[], unread_notifications=0,
                           user_role=session.get('role','user'),
                           chart_labels=[], chart_revenus=[], chart_depenses=[],
                           chart_solde=[], donut_labels=[], donut_data=[],
                           recent_trainings=[], training_total=0,
                           training_total_min=0, training_this_month=0)
@app.route('/finances')
@login_required
def finances():
    """Gestion financière avancée avec filtres, statistiques et graphiques"""
    user_id = session['user_id']
    filter_cat = request.args.get('category', '')
    filter_month = request.args.get('month', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Requête avec filtres dynamiques
    query = "SELECT * FROM financial_transactions WHERE user_id = ?"
    params = [user_id]
    
    if filter_cat:
        query += " AND category = ?"
        params.append(filter_cat)
    if filter_month:
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(filter_month)
        
    query += " ORDER BY date DESC, time DESC"
    cursor.execute(query, tuple(params))
    transactions = [dict(row) for row in cursor.fetchall()]
    
    # Résumé financier
    total_rev = sum(t['amount'] for t in transactions if t['type'] in ('revenue', 'receivable', 'credit'))
    total_exp = sum(t['amount'] for t in transactions if t['type'] in ('expense', 'debt'))
    balance = total_rev - total_exp
    savings_rate = max((balance / total_rev * 100) if total_rev > 0 else 0, 0)

    summary = {
        'total_revenue':  total_rev,
        'total_expenses': total_exp,
        'net_balance':    balance,
        'balance':        balance,
        'savings_rate':   savings_rate,
        'period':         filter_month if filter_month else "Global"
    }
    
    # Données pour Chart.js (30 derniers jours — par jour)
    cursor.execute("""
        SELECT strftime('%Y-%m-%d', date) as day,
               SUM(CASE WHEN type='revenue' THEN amount ELSE 0 END) as rev,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as exp
        FROM financial_transactions
        WHERE user_id = ? AND date >= date('now', '-30 days')
        GROUP BY day ORDER BY day ASC
    """, (user_id,))
    chart_raw = [dict(row) for row in cursor.fetchall()]
    
    # Liste des catégories pour le menu déroulant
    cursor.execute("SELECT DISTINCT category FROM financial_transactions WHERE user_id = ?", (user_id,))
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return render_template('finances.html', 
                           transactions=transactions, 
                           summary=summary, 
                           categories=categories,
                           chart_data=json.dumps(chart_raw[::-1]))

@app.route('/api/add-transaction', methods=['POST'])
@login_required
def add_transaction():
    """Route API pour ajouter une transaction avec image sécurisée"""
    try:
        user_id  = session['user_id']
        t_type   = request.form.get('type')
        amount   = float(request.form.get('amount', 0))
        category = request.form.get('category')
        # Compatibilité champ reason OU description
        reason   = request.form.get('reason') or request.form.get('description') or ''
        # Compatibilité champ date OU transaction_date
        t_date   = request.form.get('transaction_date') or request.form.get('date') or datetime.now().strftime('%Y-%m-%d')
        t_time   = request.form.get('time') or datetime.now().strftime('%H:%M:%S')
        currency        = request.form.get('currency', 'EUR')
        payment_method  = request.form.get('payment_method', '')
        tags            = ','.join(request.form.getlist('tags'))
        notes           = request.form.get('notes', '')
        emotional_state = ','.join(request.form.getlist('emotional_state'))
        energy_level    = request.form.get('energy_level', '3')

        # Enrichir les notes avec le contexte psychologique si renseigné
        if emotional_state:
            notes = f"{notes} [Émotions: {emotional_state}] [Énergie: {energy_level}/5]".strip()

        # Gestion de l'image justificative
        img_tag = ""
        if 'receipt_image' in request.files:
            file = request.files['receipt_image']
            if file and file.filename != '':
                filename = secure_filename(f"rec_{user_id}_{datetime.now().strftime('%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                img_tag = f" [IMG:{filename}]"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO financial_transactions
            (user_id, type, amount, category, reason, date, time, status, currency, payment_method, tags, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, t_type, amount, category, f"{reason}{img_tag}",
              t_date, t_time, 'Terminé', currency, payment_method, tags, notes))
        conn.commit()
        conn.close()
        flash('Transaction et justificatif enregistrés !', 'success')
    except Exception as e:
        flash(f'Erreur : {str(e)}', 'error')
    return redirect(url_for('finances'))

@app.route('/delete-transaction/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Correction: suppression dans financial_transactions et non transactions
    cursor.execute("DELETE FROM financial_transactions WHERE id = ? AND user_id = ?", (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('finances'))


@app.route('/delete-journal/<int:id>', methods=['POST'])
@login_required
def delete_journal(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trading_journal WHERE id = ? AND user_id = ?", (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('trading_journal'))

@app.route('/api/financial-transaction', methods=['POST'])
@login_required
def add_financial_transaction():
    """Add new financial transaction"""
    data = request.get_json(silent=True) or request.form
    user_id = session['user_id']
    
    required_fields = ['type', 'category', 'reason', 'amount', 'date', 'time']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': 'Champs requis manquants'}), 400
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO financial_transactions 
                (user_id, type, category, subcategory, reason, usage, amount, currency, 
                 date, time, payment_method, reference, status, notes, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data['type'],
                data['category'],
                data.get('subcategory'),
                data['reason'],
                data.get('usage'),
                float(data['amount']),
                data.get('currency', 'EUR'),
                data['date'],
                data['time'],
                data.get('payment_method'),
                data.get('reference'),
                data.get('status', 'completed'),
                data.get('notes'),
                data.get('tags')
            ))
            
            conn.commit()
            transaction_id = cursor.lastrowid
            
            # Create notification for large transactions
            if float(data['amount']) > 1000:
                cursor.execute("""
                    INSERT INTO notifications (user_id, type, title, message)
                    VALUES (?, 'info', 'Transaction importante', ?)
                """, (user_id, f"Transaction de {data['amount']}€ enregistrée"))
                conn.commit()
            
            conn.close()
            return jsonify({'success': True, 'id': transaction_id})
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500

@app.route('/journal')
@login_required
def trading_journal():
    """Trading journal with images"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    entries = []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM trading_journal
            WHERE user_id = ?
            ORDER BY date DESC, time DESC
        """, (user_id,))
        entries = [dict(row) for row in cursor.fetchall()]
        conn.close()
    
    return render_template('trading_journal.html', entries=entries)

@app.route('/api/journal-entry', methods=['POST'])
@login_required
def add_journal_entry():
    """Add trading journal entry with optional image"""
    user_id = session['user_id']
    
    # Handle file upload
    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_path = filepath
    
    # Get form data
    data = request.form if not request.is_json else request.get_json(silent=True) or request.form
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO trading_journal 
                (user_id, symbol, date, time, type, quantity, entry_price, exit_price, 
                 profit_loss, strategy, setup_description, emotions, mistakes, 
                 lessons_learned, notes, image_path, market_conditions, risk_reward_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get('symbol'),
                data.get('date'),
                data.get('time'),
                data.get('type'),
                float(data.get('quantity', 0)),
                float(data.get('entry_price', 0)),
                float(data.get('exit_price', 0)) if data.get('exit_price') else None,
                float(data.get('profit_loss', 0)) if data.get('profit_loss') else None,
                data.get('strategy'),
                data.get('setup_description'),
                data.get('emotions'),
                data.get('mistakes'),
                data.get('lessons_learned'),
                data.get('notes'),
                image_path,
                data.get('market_conditions'),
                float(data.get('risk_reward_ratio', 0)) if data.get('risk_reward_ratio') else None
            ))
            
            entry_id = cursor.lastrowid
            
            # Analyze the trade if image provided
            if image_path:
                trade_data = {
                    'profit_loss': float(data.get('profit_loss', 0)) if data.get('profit_loss') else None,
                    'risk_reward_ratio': float(data.get('risk_reward_ratio', 0)) if data.get('risk_reward_ratio') else None,
                    'strategy': data.get('strategy')
                }
                analysis = analyze_trade_image(image_path, trade_data)
                
                # Save analysis
                cursor.execute("""
                    INSERT INTO ai_analysis (user_id, analysis_type, subject, insights)
                    VALUES (?, 'trading', ?, ?)
                """, (user_id, f"Journal Entry #{entry_id}", json.dumps(analysis)))
            
            conn.commit()
            conn.close()
            
            if request.is_json:
                return jsonify({'success': True, 'id': entry_id})
            return redirect(url_for('trading_journal'))
        
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500

@app.route('/trading')
@login_required
def trading():
    """Trading interface"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    positions = []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM positions
            WHERE user_id = ? AND status = 'open'
            ORDER BY created_at DESC
        """, (user_id,))
        positions = [dict(row) for row in cursor.fetchall()]
        conn.close()
    
    return render_template('trading.html', positions=positions)

@app.route('/api/execute-trade', methods=['POST'])
@login_required
def execute_trade():
    """Execute trade - accepte JSON et form-data"""
    if request.is_json:
        data = request.get_json(silent=True) or request.form
    else:
        data = request.form.to_dict()
    user_id = session['user_id']
    
    if not data:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400
    
    required_fields = ['symbol', 'type', 'quantity', 'price']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': 'Champs requis manquants'}), 400
    
    symbol = data['symbol'].upper()
    trade_type = data['type']
    quantity = float(data['quantity'])
    price = float(data['price'])
    fees = float(data.get('fees', 0))
    strategy = data.get('strategy')
    
    amount = quantity * price
    
    if trade_type == 'sell':
        amount = amount - fees
    else:
        amount = -(amount + fees)
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Insert transaction
            cursor.execute("""
                INSERT INTO transactions (user_id, symbol, type, quantity, price, amount, fees, strategy, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, symbol, trade_type, quantity, price, amount, fees, strategy, datetime.now().isoformat()))
            
            # Update positions
            if trade_type == 'buy':
                cursor.execute("""
                    SELECT * FROM positions 
                    WHERE user_id = ? AND symbol = ? AND status = 'open'
                """, (user_id, symbol))
                existing_position = cursor.fetchone()
                
                if existing_position:
                    new_quantity = existing_position['quantity'] + quantity
                    new_avg_price = ((existing_position['quantity'] * existing_position['avg_price']) + 
                                   (quantity * price)) / new_quantity
                    
                    cursor.execute("""
                        UPDATE positions 
                        SET quantity = ?, avg_price = ?, updated_at = ?
                        WHERE user_id = ? AND symbol = ? AND status = 'open'
                    """, (new_quantity, new_avg_price, datetime.now().isoformat(), user_id, symbol))
                else:
                    cursor.execute("""
                        INSERT INTO positions (user_id, symbol, quantity, avg_price, current_price, status)
                        VALUES (?, ?, ?, ?, ?, 'open')
                    """, (user_id, symbol, quantity, price, price))
            else:  # sell
                cursor.execute("""
                    UPDATE positions 
                    SET quantity = quantity - ?, updated_at = ?
                    WHERE user_id = ? AND symbol = ? AND status = 'open'
                """, (quantity, datetime.now().isoformat(), user_id, symbol))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Transaction exécutée avec succès'})
        
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500

@app.route('/portfolio')
@login_required
def portfolio():
    """Portfolio management with enhanced structure"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    positions = []
    portfolio_stats = {
        'total_value': 0,
        'total_cost': 0,
        'total_pnl': 0,
        'total_pnl_percent': 0,
        'best_performer': None,
        'worst_performer': None
    }
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM positions
            WHERE user_id = ? AND status = 'open'
            ORDER BY (quantity * current_price) DESC
        """, (user_id,))
        positions = [dict(row) for row in cursor.fetchall()]
        
        # Calculate portfolio statistics
        for pos in positions:
            pos['market_value'] = pos['quantity'] * pos['current_price']
            pos['cost_basis'] = pos['quantity'] * pos['avg_price']
            pos['pnl'] = pos['market_value'] - pos['cost_basis']
            pos['pnl_percent'] = (pos['pnl'] / pos['cost_basis'] * 100) if pos['cost_basis'] > 0 else 0
            
            portfolio_stats['total_value'] += pos['market_value']
            portfolio_stats['total_cost'] += pos['cost_basis']
            portfolio_stats['total_pnl'] += pos['pnl']
        
        if portfolio_stats['total_cost'] > 0:
            portfolio_stats['total_pnl_percent'] = (portfolio_stats['total_pnl'] / 
                                                   portfolio_stats['total_cost'] * 100)
        
        # Find best and worst performers
        if positions:
            positions_sorted = sorted(positions, key=lambda x: x['pnl_percent'], reverse=True)
            portfolio_stats['best_performer'] = positions_sorted[0]
            portfolio_stats['worst_performer'] = positions_sorted[-1]
        
        conn.close()
    
    return render_template('portfolio.html', 
                         positions=positions, 
                         stats=portfolio_stats)

@app.route('/api/add-position', methods=['POST'])
@login_required
def add_position():
    """Add new portfolio position"""
    data = request.get_json(silent=True) or request.form
    user_id = session['user_id']
    
    required_fields = ['symbol', 'quantity', 'avg_price']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': 'Champs requis manquants'}), 400
    
    try:
        # Valider les données
        quantity = float(data['quantity'])
        avg_price = float(data['avg_price'])
        
        if quantity <= 0 or avg_price <= 0:
            return jsonify({'success': False, 'message': 'La quantité et le prix doivent être positifs'}), 400
        
        # Obtenir le prix actuel avec yfinance
        current_price = avg_price
        try:
            ticker = yf.Ticker(data['symbol'])
            hist = ticker.history(period='1d')
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
        except:
            pass  # Utiliser avg_price si la récupération échoue
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO positions 
                    (user_id, symbol, asset_type, quantity, avg_price, current_price, 
                     status, platform, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    data['symbol'].upper(),
                    data.get('asset_type', 'stock'),
                    quantity,
                    avg_price,
                    current_price,
                    'open',
                    data.get('platform', 'Manual'),
                    data.get('notes', '')
                ))
                
                conn.commit()
                position_id = cursor.lastrowid
                conn.close()
                
                return jsonify({'success': True, 'id': position_id})
            except sqlite3.IntegrityError as e:
                conn.close()
                return jsonify({'success': False, 'message': 'Cette position existe déjà'}), 400
            except Exception as e:
                conn.rollback()
                conn.close()
                return jsonify({'success': False, 'message': str(e)}), 500
        
        return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
    except ValueError:
        return jsonify({'success': False, 'message': 'Valeurs numériques invalides'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/export-portfolio')
@login_required
def export_portfolio():
    """Export portfolio to various formats"""
    user_id = session['user_id']
    export_format = request.args.get('format', 'json')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM positions
        WHERE user_id = ? AND status = 'open'
        ORDER BY symbol
    """, (user_id,))
    positions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Calculer les valeurs
    for pos in positions:
        pos['market_value'] = pos['quantity'] * pos['current_price']
        pos['cost_basis'] = pos['quantity'] * pos['avg_price']
        pos['pnl'] = pos['market_value'] - pos['cost_basis']
        pos['pnl_percent'] = (pos['pnl'] / pos['cost_basis'] * 100) if pos['cost_basis'] > 0 else 0
    
    if export_format == 'json':
        return jsonify({'success': True, 'data': positions})
    
    elif export_format == 'excel':
        try:
            df = pd.DataFrame(positions)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Portfolio')
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'portfolio_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif export_format == 'csv':
        try:
            df = pd.DataFrame(positions)
            output = BytesIO()
            df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'portfolio_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif export_format == 'pdf':
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            
            output = BytesIO()
            doc = SimpleDocTemplate(output, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Titre
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=30,
                alignment=1
            )
            elements.append(Paragraph('Portfolio Report', title_style))
            elements.append(Spacer(1, 20))
            
            # Date
            date_style = ParagraphStyle(
                'DateStyle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                alignment=1
            )
            elements.append(Paragraph(f'Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")}', date_style))
            elements.append(Spacer(1, 30))
            
            # Données du tableau
            data = [['Symbol', 'Quantity', 'Avg Price', 'Current Price', 'P&L', 'P&L %']]
            total_value = 0
            total_cost = 0
            
            for pos in positions:
                data.append([
                    pos['symbol'],
                    f"{pos['quantity']:.2f}",
                    f"{pos['avg_price']:.2f}€",
                    f"{pos['current_price']:.2f}€",
                    f"{pos['pnl']:.2f}€",
                    f"{pos['pnl_percent']:.2f}%"
                ])
                total_value += pos['market_value']
                total_cost += pos['cost_basis']
            
            # Ligne de total
            total_pnl = total_value - total_cost
            total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0
            data.append(['TOTAL', '', '', '', f"{total_pnl:.2f}€", f"{total_pnl_percent:.2f}%"])
            
            # Créer le tableau
            table = Table(data, colWidths=[1.2*inch, 1*inch, 1*inch, 1.2*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')])
            ]))
            
            elements.append(table)
            doc.build(elements)
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'portfolio_{datetime.now().strftime("%Y%m%d")}.pdf'
            )
        except ImportError:
            return jsonify({'success': False, 'message': 'ReportLab non installé. Installez avec: pip install reportlab'}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Format non supporté'}), 400

@app.route('/api/export-finances')
@login_required
def export_finances():
    """Export financial transactions to various formats"""
    user_id = session['user_id']
    export_format = request.args.get('format', 'json')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM financial_transactions
        WHERE user_id = ?
        ORDER BY date DESC, time DESC
        LIMIT 1000
    """, (user_id,))
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if export_format == 'json':
        return jsonify({'success': True, 'data': transactions})
    
    elif export_format == 'excel':
        try:
            df = pd.DataFrame(transactions)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Transactions')
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'finances_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif export_format == 'csv':
        try:
            df = pd.DataFrame(transactions)
            output = BytesIO()
            df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'finances_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    elif export_format == 'pdf':
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            
            output = BytesIO()
            doc = SimpleDocTemplate(output, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Titre
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=30,
                alignment=1
            )
            elements.append(Paragraph('Transactions Financières', title_style))
            elements.append(Spacer(1, 20))
            
            # Date
            date_style = ParagraphStyle(
                'DateStyle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                alignment=1
            )
            elements.append(Paragraph(f'Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")}', date_style))
            elements.append(Spacer(1, 30))
            
            # Limiter à 50 transactions pour le PDF
            limited_transactions = transactions[:50]
            
            # Données du tableau
            data = [['Date', 'Type', 'Catégorie', 'Raison', 'Montant']]
            total_revenue = 0
            total_expense = 0
            
            for trans in limited_transactions:
                amount = float(trans['amount'])
                if trans['type'] == 'revenue':
                    total_revenue += amount
                    amount_str = f"+{amount:.2f}€"
                else:
                    total_expense += amount
                    amount_str = f"-{amount:.2f}€"
                
                data.append([
                    trans['date'],
                    trans['type'].capitalize(),
                    trans['category'][:15],
                    trans['reason'][:20],
                    amount_str
                ])
            
            # Ligne de total
            balance = total_revenue - total_expense
            data.append(['', '', '', 'SOLDE', f"{balance:.2f}€"])
            
            # Créer le tableau
            table = Table(data, colWidths=[1*inch, 1*inch, 1.2*inch, 1.5*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2196F3')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')]),
                ('FONTSIZE', (0, 1), (-1, -1), 9)
            ]))
            
            elements.append(table)
            
            # Note si tronqué
            if len(transactions) > 50:
                note_style = ParagraphStyle(
                    'NoteStyle',
                    parent=styles['Normal'],
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=1
                )
                elements.append(Spacer(1, 20))
                elements.append(Paragraph(f'Note: Affichage limité à 50 transactions sur {len(transactions)} au total', note_style))
            
            doc.build(elements)
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'finances_{datetime.now().strftime("%Y%m%d")}.pdf'
            )
        except ImportError:
            return jsonify({'success': False, 'message': 'ReportLab non installé. Installez avec: pip install reportlab'}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Format non supporté'}), 400

@app.route('/api/analyze-portfolio')
@login_required
def analyze_portfolio():
    """Analyze portfolio with AI insights"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM positions
        WHERE user_id = ? AND status = 'open'
    """, (user_id,))
    positions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not positions:
        return jsonify({
            'success': True,
            'analysis': 'Aucune position dans le portfolio pour l\'instant.'
        })
    
    # Calculer les statistiques
    total_value = 0
    total_cost = 0
    best_performer = None
    worst_performer = None
    max_pnl_percent = float('-inf')
    min_pnl_percent = float('inf')
    
    for pos in positions:
        market_value = pos['quantity'] * pos['current_price']
        cost_basis = pos['quantity'] * pos['avg_price']
        pnl_percent = ((market_value - cost_basis) / cost_basis * 100) if cost_basis > 0 else 0
        
        total_value += market_value
        total_cost += cost_basis
        
        if pnl_percent > max_pnl_percent:
            max_pnl_percent = pnl_percent
            best_performer = pos['symbol']
        
        if pnl_percent < min_pnl_percent:
            min_pnl_percent = pnl_percent
            worst_performer = pos['symbol']
    
    total_pnl = total_value - total_cost
    total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    
    # Générer l'analyse
    analysis = f"""📊 Analyse de votre Portfolio

💰 Valeur totale: {total_value:.2f}XAF
📈 P&L total: {total_pnl:+.2f}XAF ({total_pnl_percent:+.2f}%)
📦 Nombre de positions: {len(positions)}

🌟 Meilleure performance: {best_performer} ({max_pnl_percent:+.2f}%)
⚠️ Moins bonne performance: {worst_performer} ({min_pnl_percent:+.2f}%)

💡 Recommandations:
- {'Excellent rendement!' if total_pnl_percent > 10 else 'Continuez à diversifier votre portfolio'}
- {'Pensez à prendre des bénéfices sur ' + best_performer if max_pnl_percent > 20 else 'Surveillez les opportunités de renforcement'}
- {'Analysez ' + worst_performer + ' pour décider de conserver ou liquider' if min_pnl_percent < -10 else 'Portfolio bien équilibré'}
"""
    
    return jsonify({
        'success': True,
        'analysis': analysis,
        'stats': {
            'total_value': total_value,
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'positions_count': len(positions),
            'best_performer': best_performer,
            'worst_performer': worst_performer
        }
    })

@app.route('/api/ai-analyze-finances', methods=['GET', 'POST'])
@login_required
def ai_analyze_finances():
    """AI analysis of financial transactions"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500
    
    cursor = conn.cursor()
    
    # Get last 30 days transactions
    cursor.execute("""
        SELECT 
            type,
            category,
            SUM(amount) as total,
            COUNT(*) as count
        FROM financial_transactions
        WHERE user_id = ? AND date >= date('now', '-30 days')
        GROUP BY type, category
        ORDER BY total DESC
    """, (user_id,))
    
    categories = cursor.fetchall()
    
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN type = 'revenue' THEN amount ELSE 0 END) as total_revenue,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expenses
        FROM financial_transactions
        WHERE user_id = ? AND date >= date('now', '-30 days')
    """, (user_id,))
    
    totals = cursor.fetchone()
    conn.close()
    
    total_revenue = totals['total_revenue'] or 0
    total_expenses = totals['total_expenses'] or 0
    balance = total_revenue - total_expenses
    
    # Generate analysis
    analysis = f"""📊 Analyse Financière des 30 derniers jours

💰 Revenus: {total_revenue:.2f}XAF
💸 Dépenses: {total_expenses:.2f}XAF
📈 Solde: {balance:+.2f}XAF

📋 Répartition par catégorie:
"""
    
    for cat in categories[:5]:
        analysis += f"\n- {cat['category']}: {cat['total']:.2f}€ ({cat['count']} transactions)"
    
    analysis += f"""

💡 Recommandations:
- {'Excellente gestion!' if balance > 0 else 'Attention aux dépenses'}
- {'Augmentez votre épargne de ' + str(int(balance * 0.2)) + '€' if balance > 500 else 'Réduisez vos dépenses non essentielles'}
- Taux d'épargne: {(balance/total_revenue*100 if total_revenue > 0 else 0):.1f}%
"""
    
    return jsonify({
        'success': True,
        'analysis': analysis
    })


@app.route('/ai-assistant')
@login_required
def ai_assistant():
    """AI Assistant conversational page"""
    return render_template('ai_assistant.html')

@app.route('/api/ai-chat', methods=['POST'])
@login_required
def ai_chat():
    """AI conversational assistant endpoint"""
    data = request.get_json(silent=True) or request.form
    user_id = session['user_id']
    question = data.get('question', '').lower()
    
    conn = get_db_connection()
    response = {
        'answer': '',
        'data': None,
        'charts': []
    }
    
    if conn:
        cursor = conn.cursor()
        
        # Analyze question and provide intelligent response
        if 'pourquoi' in question and ('perdu' in question or 'perte' in question):
            # Why did I lose money this month?
            cursor.execute("""
                SELECT 
                    symbol,
                    SUM(CASE WHEN type = 'sell' THEN amount ELSE 0 END) as total_sell,
                    SUM(CASE WHEN type = 'buy' THEN amount ELSE 0 END) as total_buy,
                    COUNT(*) as trade_count
                FROM transactions
                WHERE user_id = ? AND created_at >= date('now', '-30 days')
                GROUP BY symbol
                HAVING (total_sell + total_buy) < 0
                ORDER BY (total_sell + total_buy) ASC
            """, (user_id,))
            
            losing_trades = [dict(row) for row in cursor.fetchall()]
            
            if losing_trades:
                total_loss = sum(t['total_sell'] + t['total_buy'] for t in losing_trades)
                response['answer'] = f"Vous avez perdu {abs(total_loss):.2f}€ ce mois-ci. "
                response['answer'] += f"Les principales pertes proviennent de: "
                response['answer'] += ", ".join([f"{t['symbol']} ({t['total_sell'] + t['total_buy']:.2f}€)" 
                                                for t in losing_trades[:3]])
                response['data'] = losing_trades
            else:
                response['answer'] = "Vous n'avez pas enregistré de pertes ce mois-ci. Bravo!"
        
        elif 'stratégie' in question and ('rentable' in question or 'meilleur' in question):
            # Which strategy is most profitable?
            cursor.execute("""
                SELECT 
                    strategy,
                    COUNT(*) as trade_count,
                    SUM(amount) as total_profit,
                    AVG(amount) as avg_profit,
                    SUM(CASE WHEN amount > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN amount < 0 THEN 1 ELSE 0 END) as losses
                FROM transactions
                WHERE user_id = ? AND strategy IS NOT NULL AND type = 'sell'
                GROUP BY strategy
                ORDER BY total_profit DESC
            """, (user_id,))
            
            strategies = [dict(row) for row in cursor.fetchall()]
            
            if strategies:
                best = strategies[0]
                win_rate = (best['wins'] / best['trade_count'] * 100) if best['trade_count'] > 0 else 0
                
                response['answer'] = f"Votre meilleure stratégie est '{best['strategy']}' avec:\n"
                response['answer'] += f"• Profit total: {best['total_profit']:.2f}€\n"
                response['answer'] += f"• {best['trade_count']} trades\n"
                response['answer'] += f"• Taux de réussite: {win_rate:.1f}%\n"
                response['answer'] += f"• Profit moyen: {best['avg_profit']:.2f}€"
                response['data'] = strategies
            else:
                response['answer'] = "Vous n'avez pas encore de données de stratégie enregistrées."
        
        elif 'score' in question or 'performance' in question:
            # What's my trader score?
            score_data = calculate_trader_score(user_id)
            
            response['answer'] = f"Votre score de trader est: {score_data['overall_score']:.1f}/100\n\n"
            response['answer'] += "Détails:\n"
            response['answer'] += f"• Rentabilité: {score_data['profitability_score']:.1f}/100\n"
            response['answer'] += f"• Gestion du risque: {score_data['risk_management_score']:.1f}/100\n"
            response['answer'] += f"• Discipline: {score_data['discipline_score']:.1f}/100\n"
            response['answer'] += f"• Cohérence stratégique: {score_data['strategy_consistency_score']:.1f}/100\n"
            response['answer'] += f"• Contrôle émotionnel: {score_data['emotional_control_score']:.1f}/100"
            
            if score_data['overall_score'] < 50:
                response['answer'] += "\n\n⚠️ Votre score est faible. Concentrez-vous sur la discipline et la gestion du risque."
            elif score_data['overall_score'] < 70:
                response['answer'] += "\n\n📈 Bon début ! Travaillez sur la cohérence de vos stratégies."
            else:
                response['answer'] += "\n\n✅ Excellent score ! Continuez ainsi!"
            
            response['data'] = score_data
        
        elif 'combien' in question and ('gagn' in question or 'perdu' in question):
            # How much did I make/lose?
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_gains,
                    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_losses,
                    SUM(amount) as net_profit
                FROM transactions
                WHERE user_id = ? AND type = 'sell'
            """, (user_id,))
            
            result = cursor.fetchone()
            
            if result and result['total_gains']:
                response['answer'] = f"Résultats de trading:\n"
                response['answer'] += f"• Gains totaux: {result['total_gains']:.2f}€\n"
                response['answer'] += f"• Pertes totales: {result['total_losses']:.2f}€\n"
                response['answer'] += f"• Profit net: {result['net_profit']:.2f}€"
                
                if result['net_profit'] > 0:
                    response['answer'] += "\n\n✅ Vous êtes profitable!"
                else:
                    response['answer'] += "\n\n⚠️ Vous êtes en perte. Analysez vos trades."
            else:
                response['answer'] = "Vous n'avez pas encore de trades fermés."
        
        elif 'problème' in question or 'erreur' in question:
            # What are my problems?
            patterns = analyze_trading_psychology(user_id)
            
            if patterns:
                response['answer'] = f"J'ai détecté {len(patterns)} problèmes:\n\n"
                for i, pattern in enumerate(patterns[:5], 1):
                    response['answer'] += f"{i}. {pattern['type'].upper()} ({pattern['severity']})\n"
                    response['answer'] += f"   {pattern['description']}\n"
                    response['answer'] += f"   💡 {pattern['recommendation']}\n\n"
                response['data'] = patterns
            else:
                response['answer'] = "Aucun problème majeur détecté. Continuez votre bon travail!"
        
        elif 'conseil' in question or 'recommandation' in question:
            # Give me advice
            patterns = analyze_trading_psychology(user_id)
            score_data = calculate_trader_score(user_id)
            
            response['answer'] = "Recommandations personnalisées:\n\n"
            
            if score_data['discipline_score'] < 60:
                response['answer'] += "1. 📋 Discipline: Créez un plan de trading et suivez-le strictement\n"
            
            if score_data['risk_management_score'] < 60:
                response['answer'] += "2. 🛡️ Risque: Utilisez toujours des stop-loss (max 2% par trade)\n"
            
            if score_data['emotional_control_score'] < 60:
                response['answer'] += "3. 🧘 Émotions: Prenez une pause après 2 pertes consécutives\n"
            
            if patterns:
                response['answer'] += f"4. ⚠️ Attention: Vous montrez des signes de {patterns[0]['type']}\n"
            
            response['answer'] += "\n💡 Conseil du jour: Tenez un journal de trading détaillé pour identifier vos patterns."
        
        elif 'finance' in question or 'dépense' in question or 'revenu' in question or 'solde' in question:
            # Financial summary
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN type IN ('revenue','receivable','credit') THEN amount ELSE 0 END) as rev,
                    SUM(CASE WHEN type IN ('expense','debt') THEN amount ELSE 0 END) as exp,
                    COUNT(*) as cnt
                FROM financial_transactions
                WHERE user_id = ? AND date >= date('now', '-30 days')
            """, (user_id,))
            row = cursor.fetchone()
            rev = row['rev'] or 0
            exp = row['exp'] or 0
            sol = rev - exp
            pct = (sol/rev*100) if rev > 0 else 0
            response['answer'] = f"📊 Résumé Financier (30 derniers jours)\n\n"
            response['answer'] += f"💰 Revenus  : {rev:.2f}€ ({rev*655.96:.0f} XAF)\n"
            response['answer'] += f"💸 Dépenses : {exp:.2f}€ ({exp*655.96:.0f} XAF)\n"
            response['answer'] += f"📈 Solde Net: {sol:+.2f}€  |  Taux épargne: {pct:.1f}%\n\n"
            if sol > 0:
                response['answer'] += "✅ Vous êtes en positif ce mois. Continuez ainsi!"
            else:
                response['answer'] += "⚠️ Vos dépenses dépassent vos revenus. Réduisez les dépenses non-essentielles."

        elif 'objectif' in question or 'goal' in question or 'target' in question:
            response['answer'] = "🎯 Objectifs recommandés basés sur votre profil:\n\n"
            response['answer'] += "1. 💰 Taux d'épargne minimum : 20% de vos revenus\n"
            response['answer'] += "2. 🛡️ Stop-loss systématique sur chaque trade (max 2% du capital)\n"
            response['answer'] += "3. 📓 Journal de trading après chaque session\n"
            response['answer'] += "4. 🧘 Pause obligatoire après 2 pertes consécutives\n"
            response['answer'] += "5. 📊 Win rate cible : ≥ 55% avec Risk/Reward ≥ 1:2"

        elif 'formation' in question or 'cours' in question or 'training' in question:
            cursor.execute("SELECT COUNT(*) as cnt, SUM(duration_minutes) as dur FROM training_courses WHERE user_id=?", (user_id,))
            row = cursor.fetchone()
            cnt = row['cnt'] or 0
            dur = row['dur'] or 0
            response['answer'] = f"🎓 Votre parcours de formation:\n\n"
            response['answer'] += f"📚 {cnt} sessions enregistrées\n"
            response['answer'] += f"⏱ {dur} minutes de formation ({dur//60}h{dur%60}min)\n\n"
            if cnt < 5:
                response['answer'] += "💡 Conseil: Augmentez la fréquence de vos formations.\nVisez au moins 1 session par jour."
            else:
                response['answer'] += "✅ Bonne régularité dans votre formation!"

        else:
            response['answer'] = "Je suis votre assistant IA trading et finance. Voici ce que je peux analyser :\n\n"
            response['answer'] += "📊 **Trading**\n"
            response['answer'] += "• 'Pourquoi j'ai perdu ce mois-ci?'\n"
            response['answer'] += "• 'Quelle est ma meilleure stratégie?'\n"
            response['answer'] += "• 'Quel est mon score de trader?'\n"
            response['answer'] += "• 'Quels sont mes problèmes psychologiques?'\n"
            response['answer'] += "• 'Combien j'ai gagné/perdu?'\n\n"
            response['answer'] += "💰 **Finance**\n"
            response['answer'] += "• 'Montre mon solde financier'\n"
            response['answer'] += "• 'Analyse mes dépenses'\n\n"
            response['answer'] += "🎓 **Formation**\n"
            response['answer'] += "• 'Combien de cours j'ai fait?'\n\n"
            response['answer'] += "🎯 **Objectifs**\n"
            response['answer'] += "• 'Quels sont mes objectifs?'\n"
            response['answer'] += "• 'Donne-moi des conseils'"
        
        conn.close()
    
    return jsonify(response)

@app.route('/analysis')
@login_required
def analysis():
    """Analysis and insights page"""
    user_id = session['user_id']
    
    # Calculate scores and patterns
    trader_score = calculate_trader_score(user_id)
    patterns = analyze_trading_psychology(user_id)
    
    conn = get_db_connection()
    recent_analyses = []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM ai_analysis
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,))
        recent_analyses = [dict(row) for row in cursor.fetchall()]
        conn.close()
    
    return render_template('analysis.html', 
                         trader_score=trader_score,
                         patterns=patterns,
                         analyses=recent_analyses)

@app.route('/api/analyze-finances', methods=['POST'])
@login_required
def analyze_finances():
    """Analyze financial data"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        # Get financial data
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN type = 'revenue' THEN amount ELSE 0 END) as revenue,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expenses
            FROM financial_transactions
            WHERE user_id = ? AND date >= date('now', '-30 days')
        """, (user_id,))
        
        result = cursor.fetchone()
        data = {
            'revenue': result['revenue'] or 0,
            'expenses': result['expenses'] or 0
        }
        
        insights = analyze_financial_report(data)
        
        # Save analysis
        cursor.execute("""
            INSERT INTO ai_analysis (user_id, analysis_type, subject, insights)
            VALUES (?, 'financial', 'Monthly Report', ?)
        """, (user_id, json.dumps(insights)))
        
        conn.commit()
        conn.close()
        
        return jsonify(insights)
    
    return jsonify({'error': 'Database connection failed'}), 500

@app.route('/api/trading-recommendation/<symbol>')
@login_required
def get_trading_recommendation(symbol):
    """Get AI trading recommendation for a symbol"""
    recommendation = trading_recommendation(symbol.upper())
    return jsonify(recommendation)

@app.route('/settings')
@login_required
def settings():
    """User settings page"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    user_settings = {}
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            user_settings = dict(user)
        conn.close()
    
    return render_template('settings.html', settings=user_settings, user_role=session.get('role','user'))

@app.route('/api/update-settings', methods=['POST'])
@login_required
def update_settings():
    """Update user settings"""
    data = request.get_json(silent=True) or request.form
    user_id = session['user_id']
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            updates = []
            params = []
            
            allowed_fields = ['username', 'email', 'preferred_currency', 'timezone', 
                            'theme', 'notifications_email', 'notifications_app']
            
            for field in allowed_fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])
            
            if 'password' in data and data['password']:
                updates.append("password = ?")
                params.append(generate_password_hash(data['password']))
            
            if updates:
                params.append(user_id)
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                
                # Update session theme
                if 'theme' in data:
                    session['theme'] = data['theme']
            
            conn.close()
            return jsonify({'success': True, 'message': 'Paramètres mis à jour'})
        
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Erreur de connexion'}), 500

@app.route('/notifications')
@login_required
def notifications():
    """Notifications page"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    notifications_list = []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,))
        notifications_list = [dict(row) for row in cursor.fetchall()]
        conn.close()
    
    return render_template('notifications.html', notifications=notifications_list)

@app.route('/api/mark-notification-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE notifications SET is_read = 1
            WHERE id = ? AND user_id = ?
        """, (notification_id, user_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 500

@app.route('/reports')
@login_required
def reports():
    """Reports page"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    reports_list = []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM reports
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        reports_list = [dict(row) for row in cursor.fetchall()]
        conn.close()
    
    return render_template('reports.html', reports=reports_list)

@app.route('/api/generate-report', methods=['POST'])
@login_required
def generate_report():
    """Generate financial report"""
    data = request.get_json(silent=True) or request.form
    user_id = session['user_id']
    
    report_type = data.get('type', 'monthly')
    period_start = data.get('start')
    period_end = data.get('end')
    
    # Générer des dates par défaut si non fournies
    if not period_start or not period_end:
        today = datetime.now()
        if report_type == 'monthly':
            period_start = today.replace(day=1).strftime('%Y-%m-%d')
            period_end = today.strftime('%Y-%m-%d')
        elif report_type == 'yearly':
            period_start = today.replace(month=1, day=1).strftime('%Y-%m-%d')
            period_end = today.strftime('%Y-%m-%d')
        else:  # weekly
            period_start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            period_end = today.strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        try:
            # Get financial data for period
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN type = 'revenue' THEN amount ELSE 0 END) as revenue,
                    SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expenses
                FROM financial_transactions
                WHERE user_id = ? AND date BETWEEN ? AND ?
            """, (user_id, period_start, period_end))
            
            result = cursor.fetchone()
            revenue = result['revenue'] or 0
            expenses = result['expenses'] or 0
            profit = revenue - expenses
            profit_margin = (profit / revenue * 100) if revenue > 0 else 0
            
            # Create report
            cursor.execute("""
                INSERT INTO reports 
                (user_id, title, report_type, period_start, period_end, revenue, expenses, profit, profit_margin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                f"Rapport {report_type} - {period_start} à {period_end}",
                report_type,
                period_start,
                period_end,
                revenue,
                expenses,
                profit,
                profit_margin
            ))
            
            conn.commit()
            report_id = cursor.lastrowid
            conn.close()
            
            return jsonify({'success': True, 'report_id': report_id})
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': False, 'message': 'Erreur de connexion à la base de données'}), 500

@app.route('/api/download-report/<int:report_id>', methods=['GET'])
@login_required
def download_report(report_id):
    """Télécharger un rapport en PDF"""
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'DB error'}), 500
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE id = ? AND user_id = ?", (report_id, user_id))
    report = cursor.fetchone()
    if not report:
        conn.close()
        return jsonify({'error': 'Rapport introuvable'}), 404
    report = dict(report)
    conn.close()
    try:
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from io import BytesIO
        buffer = BytesIO()
        c = pdf_canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        # Header vert
        c.setFillColor(colors.HexColor('#00d4aa'))
        c.rect(0, height-80, width, 80, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(width/2, height-45, "KENGNI FINANCE")
        c.setFont("Helvetica", 11)
        c.drawCentredString(width/2, height-65, "k-ni chez Htech-training | Rapport Certifié")
        # Infos rapport
        c.setFillColor(colors.HexColor('#1a1a2e'))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height-115, f"Rapport: {report.get('title', 'N/A')}")
        c.setFont("Helvetica", 11)
        c.drawString(50, height-140, f"Période: {report.get('period_start','N/A')} → {report.get('period_end','N/A')}")
        c.drawString(50, height-160, f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
        # Ligne séparatrice
        c.setStrokeColor(colors.HexColor('#00d4aa'))
        c.setLineWidth(2)
        c.line(50, height-175, width-50, height-175)
        # Données financières
        y = height-220
        revenue = float(report.get('revenue') or 0)
        expenses = float(report.get('expenses') or 0)
        profit = float(report.get('profit') or revenue - expenses)
        margin = float(report.get('profit_margin') or (profit/revenue*100 if revenue > 0 else 0))
        rows = [
            ("💰 Revenus Total",       f"{revenue:,.2f} €",  '#00c853'),
            ("💸 Dépenses Total",      f"{expenses:,.2f} €", '#d50000'),
            ("📈 Profit / Perte",      f"{profit:+,.2f} €",  '#00c853' if profit >= 0 else '#d50000'),
            ("📊 Marge Bénéficiaire",  f"{margin:.1f} %",    '#1565c0'),
        ]
        for label, value, color in rows:
            c.setFillColor(colors.HexColor('#f5f5f5'))
            c.rect(50, y-8, width-100, 30, fill=True, stroke=False)
            c.setFillColor(colors.HexColor('#333333'))
            c.setFont("Helvetica-Bold", 12)
            c.drawString(65, y+8, label)
            c.setFillColor(colors.HexColor(color))
            c.setFont("Helvetica-Bold", 13)
            c.drawRightString(width-65, y+8, value)
            y -= 42
        # Footer
        c.setFillColor(colors.HexColor('#f0f0f0'))
        c.rect(0, 0, width, 45, fill=True, stroke=False)
        c.setFillColor(colors.HexColor('#888888'))
        c.setFont("Helvetica", 9)
        c.drawCentredString(width/2, 28, "Document certifié — Kengni Finance v2.1 — © 2025 Tous droits réservés")
        c.drawCentredString(width/2, 14, "k-ni chez Htech-training")
        c.save()
        buffer.seek(0)
        filename = f"rapport_{report.get('report_type','custom')}_{report.get('period_start','').replace('-','')}.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': f'Erreur PDF: {str(e)}'}), 500


@app.route('/report/<int:report_id>')
@login_required
def view_report(report_id):
    """Alias vers download_report"""
    return redirect(url_for('download_report', report_id=report_id))


@app.route('/history')
@login_required
def history():
    """Transaction history"""
    user_id = session['user_id']
    
    conn = get_db_connection()
    transactions = []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 200
        """, (user_id,))
        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()
    
    return render_template('history.html', transactions=transactions)

@app.route('/delete-journal-entry/<int:id>', methods=['POST'])
@login_required
def delete_journal_entry(id):
    if session.get('role') not in ('admin', 'superadmin'):
        flash('Suppression réservée aux administrateurs', 'danger')
        return redirect(url_for('trading_journal'))
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM trading_journal WHERE id = ? AND user_id = ?",
                          (id, session['user_id']))
            conn.commit()
            conn.close()
            flash('Entrée supprimée', 'success')
            return redirect(url_for('trading_journal'))
    except Exception as e:
        flash(f'Erreur: {e}', 'danger')
        return redirect(url_for('trading_journal'))


@app.route('/api/delete-financial-transaction/<int:id>', methods=['DELETE', 'POST'])
@login_required
def delete_financial_transaction(id):
    """Delete a financial transaction"""
    if session.get('role') not in ('admin', 'superadmin'):
        return jsonify({'success': False, 'error': 'Suppression réservée aux administrateurs'}), 403
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM financial_transactions WHERE id = ? AND user_id = ?",
                          (id, session['user_id']))
            conn.commit()
            conn.close()
            
            create_notification(session['user_id'], 'success', 
                              'Transaction supprimée', 
                              f'La transaction #{id} a été supprimée')
            
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/delete-trade/<int:id>', methods=['DELETE', 'POST'])
@login_required
def delete_trade(id):
    """Delete a trade"""
    if session.get('role') not in ('admin', 'superadmin'):
        return jsonify({'success': False, 'error': 'Suppression réservée aux administrateurs'}), 403
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?",
                          (id, session['user_id']))
            conn.commit()
            conn.close()
            
            create_notification(session['user_id'], 'success', 
                              'Trade supprimé', 
                              f'Le trade #{id} a été supprimé')
            
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
        
@app.route('/image-spam')
@login_required
def image_spam():
    return render_template('image_spam_manager.html')

@app.route('/api/delete-position/<int:id>', methods=['DELETE', 'POST'])
@login_required
def delete_position(id):
    """Delete a position"""
    if session.get('role') not in ('admin', 'superadmin'):
        return jsonify({'success': False, 'error': 'Suppression réservée aux administrateurs'}), 403
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM positions WHERE id = ? AND user_id = ?",
                          (id, session['user_id']))
            conn.commit()
            conn.close()
            
            create_notification(session['user_id'], 'success', 
                              'Position supprimée', 
                              f'La position #{id} a été supprimée')
            
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



# ══════════════════════════════════════════════════════════════
# PANNEAU ADMIN SECRET
# ══════════════════════════════════════════════════════════════

@app.route(f'/{ADMIN_SECRET_TOKEN}')
def admin_secret_entry():
    if 'user_id' in session and session.get('role') in ('admin', 'superadmin'):
        return redirect(url_for('admin_panel'))
    return render_template('admin_login.html', token=ADMIN_SECRET_TOKEN)

@app.route(f'/{ADMIN_SECRET_TOKEN}/auth', methods=['POST'])
def admin_auth():
    data = request.get_json(silent=True) or request.form if request.is_json else request.form
    email    = data.get('email','').strip()
    password = data.get('password','').strip()
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND role IN ('admin','superadmin')", (email,))
        user = cursor.fetchone()
        if user and check_password_hash(user['password'], password):
            # 2FA for admin
            token_2fa = str(random.randint(100000, 999999))
            session['pending_2fa_token']    = token_2fa
            session['pending_2fa_user_id']  = user['id']
            session['pending_2fa_username'] = user['username']
            session['pending_2fa_email']    = user['email']
            session['pending_2fa_theme']    = user['theme']
            session['pending_2fa_role']     = user['role']
            session['pending_2fa_expires']  = (datetime.now() + timedelta(minutes=5)).isoformat()
            session['pending_2fa_is_admin_login'] = True
            cursor.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now().isoformat(), user['id']))
            conn.commit(); conn.close()
            if request.is_json: return jsonify({'success': True, 'redirect': url_for('verify_token_page', email=user['email'])})
            return redirect(url_for('verify_token_page', email=user['email']))
        conn.close()
    if request.is_json: return jsonify({'success': False, 'message': 'Identifiants incorrects'}), 401
    from flask import abort; abort(404)

@app.route('/admin')
@admin_required
def admin_panel():
    # Double sécurité admin — vérifier le mot de passe secondaire
    if not session.get('admin_secondary_verified'):
        return redirect(url_for('admin_secondary_verify'))
    conn = get_db_connection()
    users, stats = [], {}
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id,username,email,role,status,created_at,last_login FROM users ORDER BY created_at DESC")
        users = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) FROM users");               stats['total_users']      = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE status='active'"); stats['active_users'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE role IN ('admin','superadmin')"); stats['admins'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM financial_transactions"); stats['total_transactions'] = cursor.fetchone()[0]
        conn.close()
    return render_template('admin.html', users=users, stats=stats,
                           current_role=session.get('role'), token=ADMIN_SECRET_TOKEN)

@app.route('/admin/secondary-verify', methods=['GET', 'POST'])
@admin_required
def admin_secondary_verify():
    """Double sécurité admin — mot de passe secondaire Kengni@fablo12"""
    error = None
    if request.method == 'POST':
        pwd = (request.get_json(silent=True) or request.form or request.form).get('secondary_password', '')
        # Compteur de tentatives
        session['admin_sec_attempts'] = session.get('admin_sec_attempts', 0) + 1
        if session['admin_sec_attempts'] > 3:
            # Trop de tentatives — déconnexion forcée
            session.clear()
            if request.is_json:
                return jsonify({'success': False, 'message': 'Trop de tentatives — déconnexion'}), 403
            flash('Trop de tentatives incorrectes. Session terminée.', 'danger')
            return redirect(url_for('login'))
        if pwd == ADMIN_SECONDARY_PASSWORD:
            session['admin_secondary_verified'] = True
            session['admin_sec_attempts'] = 0
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('admin_panel')})
            return redirect(url_for('admin_panel'))
        else:
            remaining = 3 - session['admin_sec_attempts']
            error = f'Mot de passe secondaire incorrect. {remaining} tentative(s) restante(s).'
            if request.is_json:
                return jsonify({'success': False, 'message': error}), 401
    return render_template('admin_secondary.html', error=error)

@app.route('/admin/create-user', methods=['POST'])
@admin_required
def admin_create_user():
    data = request.get_json(silent=True) or request.form
    username,email,password = data.get('username','').strip(), data.get('email','').strip(), data.get('password','').strip()
    role, status = data.get('role','user'), data.get('status','active')
    allowed = ['viewer','user','editor','admin']
    if session.get('role')=='superadmin': allowed.append('superadmin')
    if not all([username,email,password]): return jsonify({'success':False,'message':'Tous les champs sont requis'}),400
    if role not in allowed: return jsonify({'success':False,'message':'Rôle non autorisé'}),403
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email=?", (email,))
        if cursor.fetchone(): conn.close(); return jsonify({'success':False,'message':'Email déjà utilisé'}),409
        cursor.execute("INSERT INTO users (username,email,password,role,status,created_at) VALUES (?,?,?,?,?,?)",
                       (username,email,generate_password_hash(password),role,status,datetime.now().isoformat()))
        conn.commit(); new_id=cursor.lastrowid; conn.close()
        return jsonify({'success':True,'message':f'Compte créé (ID {new_id})','id':new_id})
    return jsonify({'success':False,'message':'Erreur DB'}),500

@app.route('/admin/update-user/<int:user_id>', methods=['POST'])
@admin_required
def admin_update_user(user_id):
    data = request.get_json(silent=True) or request.form
    role, status = data.get('role'), data.get('status')
    allowed = ['viewer','user','editor','admin']
    if session.get('role')=='superadmin': allowed.append('superadmin')
    if role and role not in allowed: return jsonify({'success':False,'message':'Rôle non autorisé'}),403
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        if role:   cursor.execute("UPDATE users SET role=?,updated_at=? WHERE id=?",   (role,   datetime.now().isoformat(), user_id))
        if status: cursor.execute("UPDATE users SET status=?,updated_at=? WHERE id=?", (status, datetime.now().isoformat(), user_id))
        conn.commit(); conn.close()
        return jsonify({'success':True,'message':'Utilisateur mis à jour'})
    return jsonify({'success':False,'message':'Erreur DB'}),500

@app.route('/admin/reset-password/<int:user_id>', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    data = request.get_json(silent=True) or request.form
    password = data.get('password','').strip()
    if len(password)<6: return jsonify({'success':False,'message':'Mot de passe trop court'}),400
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password=?,updated_at=? WHERE id=?",
                       (generate_password_hash(password), datetime.now().isoformat(), user_id))
        conn.commit(); conn.close()
        return jsonify({'success':True,'message':'Mot de passe réinitialisé'})
    return jsonify({'success':False,'message':'Erreur DB'}),500

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    if user_id==session['user_id']: return jsonify({'success':False,'message':'Impossible de supprimer votre propre compte'}),400
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit(); conn.close()
        return jsonify({'success':True,'message':'Utilisateur supprimé'})
    return jsonify({'success':False,'message':'Erreur DB'}),500

# API pour le mini-panel admin intégré (dashboard + settings)
@app.route('/api/admin/users')
@admin_required
def api_admin_users():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id,username,email,role,status,last_login FROM users ORDER BY username")
        users = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'success':True,'users':users})
    return jsonify({'success':False}),500


# ══════════════════════════════════════════════════════════════
# MODULE TRAINING — Gestion des cours de formation
# ══════════════════════════════════════════════════════════════

def detect_thumbnail(url):
    """Détecte automatiquement la miniature selon la plateforme."""
    if not url:
        return '/static/img/course_default.svg'
    url_lower = url.lower()
    if 'claude.ai' in url_lower:
        return '/static/img/claude_thumb.svg'
    if 'chat.openai.com' in url_lower or 'chatgpt.com' in url_lower:
        return '/static/img/chatgpt_thumb.svg'
    yt = re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})', url)
    if yt:
        return f'https://img.youtube.com/vi/{yt.group(1)}/hqdefault.jpg'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read(30000).decode('utf-8', errors='ignore')
        og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']', html)
        if og:
            return og.group(1)
        og2 = re.search(r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:image["\']', html)
        if og2:
            return og2.group(1)
    except Exception:
        pass
    return '/static/img/course_default.svg'


@app.route('/training')
@login_required
def training():
    """Page de gestion des cours de formation."""
    conn = get_db_connection()
    if not conn:
        return render_template('training.html', courses_by_day={}, stats={})
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM training_courses
        WHERE user_id = ?
        ORDER BY day_of_week, created_at DESC
    ''', (session['user_id'],))
    courses = [dict(r) for r in cursor.fetchall()]
    conn.close()

    days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche', 'Non défini']
    courses_by_day = {d: [] for d in days_order}
    for c in courses:
        day = c.get('day_of_week', 'Non défini')
        if day not in days_order:
            day = 'Non défini'
        # Parse position_images JSON
        try:
            c['position_images'] = json.loads(c.get('position_images') or '[]')
        except Exception:
            c['position_images'] = []
        courses_by_day[day].append(c)

    stats = {
        'total': len(courses),
        'published': sum(1 for c in courses if c['is_published']),
        'scheduled': sum(1 for c in courses if c.get('scheduled_date')),
        'total_duration': sum((c['duration_minutes'] or 0) for c in courses),
    }
    return render_template('training.html', courses_by_day=courses_by_day, stats=stats)


@app.route('/training/add', methods=['POST'])
@login_required
def training_add():
    url = request.form.get('course_url', '').strip()
    thumbnail = request.form.get('thumbnail_url', '').strip() or detect_thumbnail(url)

    # Handle position images upload
    position_images = []
    for key in sorted(request.files.keys()):
        if key.startswith('position_img_') and not key.endswith('_caption'):
            file = request.files[key]
            if file and file.filename:
                fname = secure_filename(f"pos_{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                file.save(fpath)
                position_images.append(f'/static/uploads/{fname}')

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'DB error'}), 500
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO training_courses
        (user_id, title, description, course_url, thumbnail_url, category, level,
         day_of_week, scheduled_date, duration_minutes, tags, is_published,
         participant_names, analyses, strategies, position_images, time_start, time_end, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        session['user_id'],
        request.form.get('title', 'Sans titre'),
        request.form.get('description', ''),
        url,
        thumbnail,
        request.form.get('category', 'Général'),
        request.form.get('level', 'debutant'),
        request.form.get('day_of_week', 'Non défini'),
        request.form.get('scheduled_date', ''),
        int(request.form.get('duration_minutes', 0) or 0),
        request.form.get('tags', ''),
        1 if request.form.get('is_published') else 0,
        request.form.get('participants', ''),
        request.form.get('analyses', ''),
        request.form.get('strategies', ''),
        json.dumps(position_images),
        request.form.get('time_start', ''),
        request.form.get('time_end', ''),
        datetime.now().isoformat()
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': new_id, 'thumbnail': thumbnail})


@app.route('/training/update/<int:cid>', methods=['POST'])
@login_required
def training_update(cid):
    url = request.form.get('course_url', '').strip()
    thumbnail = request.form.get('thumbnail_url', '').strip() or detect_thumbnail(url)

    # Handle new position images
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False}), 500
    cursor = conn.cursor()
    cursor.execute('SELECT position_images FROM training_courses WHERE id=? AND user_id=?', (cid, session['user_id']))
    row = cursor.fetchone()
    try:
        existing_images = json.loads(row['position_images'] if row else '[]') or []
    except Exception:
        existing_images = []

    # Remove deleted images
    imgs_to_delete = request.form.getlist('delete_images')
    existing_images = [img for img in existing_images if img not in imgs_to_delete]

    # Add new images
    for key in sorted(request.files.keys()):
        if key.startswith('position_img_') and not key.endswith('_caption'):
            file = request.files[key]
            if file and file.filename:
                fname = secure_filename(f"pos_{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                fpath = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                file.save(fpath)
                existing_images.append(f'/static/uploads/{fname}')

    cursor.execute('''
        UPDATE training_courses SET
            title=?, description=?, course_url=?, thumbnail_url=?,
            category=?, level=?, day_of_week=?, scheduled_date=?,
            duration_minutes=?, tags=?, is_published=?,
            participant_names=?, analyses=?, strategies=?, position_images=?,
            time_start=?, time_end=?, updated_at=?
        WHERE id=? AND user_id=?
    ''', (
        request.form.get('title'), request.form.get('description'), url, thumbnail,
        request.form.get('category'), request.form.get('level'), request.form.get('day_of_week'),
        request.form.get('scheduled_date'), int(request.form.get('duration_minutes', 0) or 0),
        request.form.get('tags'), 1 if request.form.get('is_published') else 0,
        request.form.get('participants', ''),
        request.form.get('analyses', ''),
        request.form.get('strategies', ''),
        json.dumps(existing_images),
        request.form.get('time_start', ''),
        request.form.get('time_end', ''),
        datetime.now().isoformat(), cid, session['user_id']
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'thumbnail': thumbnail})


@app.route('/training/delete/<int:cid>', methods=['POST', 'DELETE'])
@login_required
def training_delete(cid):
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False}), 500
    cursor = conn.cursor()
    cursor.execute('DELETE FROM training_courses WHERE id=? AND user_id=?', (cid, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/training/fetch-thumb', methods=['POST'])
@login_required
def training_fetch_thumb():
    data = request.get_json(silent=True) or request.form or {}
    url = data.get('url', '')
    thumb = detect_thumbnail(url)
    return jsonify({'thumbnail': thumb})



# ══════════════════════════════════════════════════════════════
# MODULE KENGNI TRADING ACADEMY — Inscriptions & Gestion Leads
# ══════════════════════════════════════════════════════════════

@app.route('/inscription-trading', methods=['GET'])
def training_registration():
    """Page d'inscription publique à la Kengni Trading Academy."""
    success = request.args.get('success')
    wa      = request.args.get('wa', '')
    return render_template('inscription_trading.html', success=success, wa=wa)


@app.route('/inscription-trading', methods=['POST'])
def register_trading_lead():
    """Enregistre un nouveau lead avec vérification de doublon."""
    from urllib.parse import quote

    full_name      = request.form.get('full_name', '').strip()
    email          = request.form.get('email', '').strip().lower()
    whatsapp       = request.form.get('whatsapp', '').strip()
    level_selected = request.form.get('level_selected', '').strip()
    capital        = request.form.get('capital', '').strip()
    objective      = request.form.get('objective', '').strip()
    source         = request.form.get('source', 'Non renseigné').strip()

    # Validation serveur
    errors = []
    if not full_name or len(full_name) < 2:
        errors.append("Le nom complet est requis.")
    if not email or '@' not in email:
        errors.append("Adresse email invalide.")
    if not whatsapp or len(whatsapp.replace(' ', '')) < 8:
        errors.append("Numéro WhatsApp requis.")
    if not level_selected:
        errors.append("Veuillez choisir un niveau de formation.")

    if errors:
        for err in errors:
            flash(err, 'error')
        return redirect(url_for('training_registration'))

    conn = get_db_connection()
    if not conn:
        flash("Erreur de base de données. Veuillez réessayer.", 'error')
        return redirect(url_for('training_registration'))

    cursor = conn.cursor()

    # Vérification doublon
    cursor.execute(
        "SELECT id FROM training_leads WHERE email=? AND level_selected=?",
        (email, level_selected)
    )
    if cursor.fetchone():
        conn.close()
        flash(f"Vous êtes déjà inscrit(e) à la formation {level_selected} avec cet email. Notre équipe vous contactera bientôt !", 'error')
        return redirect(url_for('training_registration'))

    # Liaison user connecté si disponible
    user_id = session.get('user_id')

    cursor.execute('''
        INSERT INTO training_leads
        (full_name, email, whatsapp, level_selected, capital, objective, source, status, user_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, "Nouveau", ?, ?)
    ''', (
        full_name, email, whatsapp, level_selected,
        capital or None, objective or None, source,
        user_id, datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

    # ── Envoi automatique de l'email de paiement au prospect ──
    lead_dict = {
        'full_name':      full_name,
        'email':          email,
        'whatsapp':       whatsapp,
        'level_selected': level_selected,
        'capital':        capital,
        'objective':      objective,
    }
    threading.Thread(
        target=_send_inscription_payment_email,
        args=(lead_dict,),
        daemon=True
    ).start()

    flash(f"Inscription confirmée ! Un email de paiement a été envoyé à {email}. 🎉", 'success')
    return redirect(url_for('training_registration', success=1, wa=whatsapp))


@app.route('/admin/leads')
@login_required
@admin_required
def admin_leads():
    """Panneau admin : liste chronologique de tous les leads."""
    conn = get_db_connection()
    leads = []
    stats = {'total': 0, 'nouveau': 0, 'contacte': 0, 'inscrit': 0, 'paye': 0}
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM training_leads ORDER BY created_at DESC")
        leads = [dict(r) for r in cursor.fetchall()]
        conn.close()
        stats['total']    = len(leads)
        stats['nouveau']  = sum(1 for l in leads if l['status'] == 'Nouveau')
        stats['contacte'] = sum(1 for l in leads if l['status'] == 'Contacté')
        stats['inscrit']  = sum(1 for l in leads if l['status'] == 'Inscrit')
        stats['paye']     = sum(1 for l in leads if l['status'] == 'Payé')
    return render_template('admin_leads.html', leads=leads, stats=stats)


@app.route('/admin/leads/<int:lead_id>/status', methods=['POST'])
@login_required
@admin_required
def update_lead_status(lead_id):
    """Met à jour le statut d'un lead."""
    new_status = request.form.get('status', '').strip()
    if new_status not in ['Nouveau', 'Contacté', 'Inscrit', 'Payé']:
        flash("Statut invalide.", 'error')
        return redirect(url_for('admin_leads'))
    conn = get_db_connection()
    if conn:
        conn.execute("UPDATE training_leads SET status=? WHERE id=?", (new_status, lead_id))
        conn.commit()
        conn.close()
        flash(f"Statut mis à jour : {new_status}", 'success')
    return redirect(url_for('admin_leads'))


@app.route('/admin/leads/<int:lead_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_lead(lead_id):
    """Supprime un lead."""
    conn = get_db_connection()
    if conn:
        conn.execute("DELETE FROM training_leads WHERE id=?", (lead_id,))
        conn.commit()
        conn.close()
        flash("Lead supprimé.", 'success')
    return redirect(url_for('admin_leads'))


def _send_sincire_email(lead: dict) -> bool:
    """Envoie l'email 'sincire' (invitation à payer) au prospect."""
    cfg      = GMAIL_CONFIG
    level    = lead.get('level_selected', 'Formation')
    name     = lead.get('full_name', 'Cher(e) prospect(e)')
    prospect_email = lead.get('email', '')
    prices   = FORMATION_PRICES.get(level, {'xaf': 50000, 'eur': 76})
    pay      = PAYMENT_INFO

    if not prospect_email:
        return False

    html = f'''<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="margin:0;padding:0;background:#0a0f1a;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;padding:24px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#0d1b2a,#1a2a3a);border-radius:18px 18px 0 0;padding:36px 32px;text-align:center;border-bottom:3px solid #00d4aa;">
    <div style="font-size:3rem;margin-bottom:10px;">🎓</div>
    <h1 style="color:#fff;margin:0;font-size:22px;font-weight:800;">Kengni Trading Academy</h1>
    <p style="color:#00d4aa;margin:8px 0 0;font-size:14px;font-weight:600;">Votre place est réservée — Finalisez votre inscription</p>
  </div>

  <!-- Body -->
  <div style="background:#111827;padding:32px;border-radius:0 0 18px 18px;border:1px solid #1e2a3a;border-top:none;">

    <p style="color:#e0e0e0;font-size:15px;line-height:1.7;margin:0 0 20px;">
      Bonjour <strong style="color:#00d4aa;">{name}</strong>,<br><br>
      Merci pour votre intérêt pour la formation <strong style="color:#fff;">"{level}"</strong> !
      Votre dossier a été examiné et nous sommes ravis de vous confirmer que votre place est réservée.<br><br>
      Pour <strong style="color:#ffd700;">finaliser votre inscription</strong>, il vous suffit de procéder au règlement selon l'un des moyens ci-dessous.
    </p>

    <!-- Prix -->
    <div style="background:linear-gradient(135deg,rgba(0,212,170,.15),rgba(0,212,170,.05));border:1px solid rgba(0,212,170,.3);border-radius:12px;padding:20px;text-align:center;margin-bottom:24px;">
      <div style="font-size:.8rem;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Montant à régler — {level}</div>
      <div style="font-size:2rem;font-weight:800;color:#00d4aa;">{prices['xaf']:,} FCFA</div>
      <div style="font-size:.9rem;color:#888;margin-top:4px;">≈ {prices['eur']} EUR</div>
    </div>

    <!-- Méthodes de paiement -->
    <h3 style="color:#fff;font-size:15px;font-weight:700;margin:0 0 14px;">💳 Modes de paiement acceptés</h3>

    <!-- OM -->
    <div style="background:#0d1b2a;border-radius:12px;padding:16px 18px;margin-bottom:10px;display:flex;align-items:center;gap:14px;border-left:4px solid #ff6b00;">
      <div style="font-size:1.8rem;flex-shrink:0;">🟠</div>
      <div>
        <div style="color:#ff6b00;font-weight:700;font-size:13px;">Orange Money</div>
        <div style="color:#fff;font-size:1.1rem;font-weight:800;letter-spacing:1px;">{pay['orange_money']['numero']}</div>
        <div style="color:#888;font-size:12px;">Au nom de : {pay['orange_money']['nom']}</div>
      </div>
    </div>

    <!-- MTN -->
    <div style="background:#0d1b2a;border-radius:12px;padding:16px 18px;margin-bottom:10px;display:flex;align-items:center;gap:14px;border-left:4px solid #ffd700;">
      <div style="font-size:1.8rem;flex-shrink:0;">🟡</div>
      <div>
        <div style="color:#ffd700;font-weight:700;font-size:13px;">MTN Mobile Money</div>
        <div style="color:#fff;font-size:1.1rem;font-weight:800;letter-spacing:1px;">{pay['mtn_money']['numero']}</div>
        <div style="color:#888;font-size:12px;">Au nom de : {pay['mtn_money']['nom']}</div>
      </div>
    </div>

    <!-- PayPal -->
    <div style="background:#0d1b2a;border-radius:12px;padding:16px 18px;margin-bottom:10px;display:flex;align-items:center;gap:14px;border-left:4px solid #009cde;">
      <div style="font-size:1.8rem;flex-shrink:0;">🔵</div>
      <div>
        <div style="color:#009cde;font-weight:700;font-size:13px;">PayPal</div>
        <div style="color:#fff;font-size:1rem;font-weight:700;">{pay['paypal']['adresse']}</div>
        <div style="color:#888;font-size:12px;">Envoyer en "Amis &amp; Famille" pour éviter les frais</div>
      </div>
    </div>

    <!-- Crypto -->
    <div style="background:#0d1b2a;border-radius:12px;padding:16px 18px;margin-bottom:24px;display:flex;align-items:center;gap:14px;border-left:4px solid #f7931a;">
      <div style="font-size:1.8rem;flex-shrink:0;">₿</div>
      <div>
        <div style="color:#f7931a;font-weight:700;font-size:13px;">Crypto (BTC, USDT, ETH…)</div>
        <div style="color:#fff;font-size:1rem;font-weight:700;">{pay['crypto']['adresse']}</div>
        <div style="color:#888;font-size:12px;">Contactez-nous par email pour recevoir l'adresse de wallet</div>
      </div>
    </div>

    <!-- Instructions -->
    <div style="background:rgba(255,215,0,.07);border:1px solid rgba(255,215,0,.25);border-radius:12px;padding:16px 18px;margin-bottom:24px;">
      <p style="color:#ffd700;font-weight:700;font-size:13px;margin:0 0 8px;">📋 Après votre paiement</p>
      <ol style="color:#aaa;font-size:13px;margin:0;padding-left:18px;line-height:2;">
        <li>Envoyez la capture d'écran de votre paiement sur WhatsApp</li>
        <li>Numéro WhatsApp : <strong style="color:#fff;">+237 695 072 659</strong></li>
        <li>Votre accès à la formation sera activé sous 24h</li>
      </ol>
    </div>

    <!-- CTA -->
    <div style="text-align:center;margin-bottom:16px;">
      <a href="https://wa.me/237695072659?text=Bonjour%2C%20j%27ai%20effectu%C3%A9%20mon%20paiement%20pour%20la%20formation%20{level.replace(' ','%20')}"
         style="background:linear-gradient(135deg,#00d4aa,#00ff88);color:#000;font-weight:800;font-size:14px;padding:14px 32px;border-radius:10px;text-decoration:none;display:inline-block;box-shadow:0 4px 16px rgba(0,212,170,.4);">
        📲 Confirmer mon paiement sur WhatsApp
      </a>
    </div>

    <!-- Footer -->
    <div style="border-top:1px solid #1e2a3a;padding-top:16px;text-align:center;margin-top:8px;">
      <p style="color:#444;font-size:11px;margin:0;">Kengni Trading Academy · fabrice.kengni12@gmail.com</p>
      <p style="color:#333;font-size:10px;margin:4px 0 0;">Cet email vous a été envoyé suite à votre inscription sur notre plateforme.</p>
    </div>
  </div>
</div>
</body></html>'''

    text = (f"Bonjour {name},\n\n"
            f"Votre place pour la formation \"{level}\" est réservée !\n\n"
            f"MONTANT : {prices['xaf']:,} FCFA (≈ {prices['eur']} EUR)\n\n"
            f"PAIEMENT :\n"
            f"• Orange Money : {pay['orange_money']['numero']}\n"
            f"• MTN MoMo : {pay['mtn_money']['numero']}\n"
            f"• PayPal / Crypto : {pay['paypal']['adresse']}\n\n"
            f"Après paiement, envoyez la capture sur WhatsApp : +237 695 072 659\n\n"
            f"— Kengni Trading Academy")

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎓 Finalisez votre inscription — {level} | Kengni Trading Academy"
        msg['From']    = f"Kengni Trading Academy <{cfg['sender_email']}>"
        msg['To']      = prospect_email
        msg['Reply-To'] = cfg['sender_email']
        msg.attach(MIMEText(text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port']) as s:
            s.ehlo(); s.starttls()
            s.login(cfg['sender_email'], cfg['smtp_password'])
            s.sendmail(cfg['sender_email'], prospect_email, msg.as_string())

        print(f"[Sincire] ✅ Email envoyé à {prospect_email}")
        return True
    except Exception as e:
        print(f"[Sincire] ❌ Erreur : {e}")
        return False


@app.route('/admin/leads/<int:lead_id>/sincire', methods=['POST'])
@login_required
@admin_required
def sincire_lead(lead_id):
    """Envoie l'email de sinciration (invitation paiement) au prospect."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'DB error'}), 500
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM training_leads WHERE id=?", (lead_id,))
    lead = cursor.fetchone()
    if not lead:
        conn.close()
        return jsonify({'success': False, 'error': 'Lead introuvable'}), 404

    lead_dict = dict(lead)
    ok = _send_sincire_email(lead_dict)
    if ok:
        now_iso = datetime.now().isoformat()
        cursor.execute(
            "UPDATE training_leads SET sincire_sent_at=?, status='Contacté' WHERE id=?",
            (now_iso, lead_id)
        )
        conn.commit()
        conn.close()
        return jsonify({
            'success': True,
            'message': f"✅ Email sincire envoyé à {lead_dict.get('email')} !",
            'sent_at': now_iso[:16].replace('T', ' à '),
        })
    else:
        conn.close()
        return jsonify({
            'success': False,
            'error': "Échec de l'envoi — vérifiez la config Gmail.",
        }), 500


@app.route('/admin/leads/<int:lead_id>/update-payment', methods=['POST'])
@login_required
@admin_required
def update_lead_payment(lead_id):
    """Met à jour les infos de paiement d'un lead."""
    data = request.get_json(silent=True) or request.form or {}
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False}), 500
    conn.execute('''
        UPDATE training_leads
        SET payment_method=?, payment_ref=?, payment_status=?, amount_paid=?
        WHERE id=?
    ''', (
        data.get('payment_method',''),
        data.get('payment_ref',''),
        data.get('payment_status','En attente'),
        float(data.get('amount_paid', 0) or 0),
        lead_id
    ))
    conn.commit(); conn.close()
    return jsonify({'success': True})


@app.route('/api/export-leads')
@login_required
@admin_required
def export_leads():
    """Export CSV ou Excel des leads via Pandas."""
    fmt  = request.args.get('format', 'csv').lower()
    conn = get_db_connection()
    leads = []
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM training_leads ORDER BY created_at DESC")
        leads = [dict(r) for r in cursor.fetchall()]
        conn.close()

    data = [{
        'ID':        l['id'],
        'Nom':       l['full_name'],
        'Email':     l['email'],
        'WhatsApp':  l['whatsapp'],
        'Formation': l['level_selected'],
        'Capital':   l.get('capital') or '',
        'Objectif':  l.get('objective') or '',
        'Source':    l.get('source') or '',
        'Statut':    l['status'],
        'Date':      l['created_at'],
        'Lien WA':   f"https://wa.me/{l['whatsapp'].replace(' ','').replace('+','')}",
    } for l in leads]

    df = pd.DataFrame(data) if data else pd.DataFrame()
    output = BytesIO()
    ts = datetime.now().strftime('%Y%m%d_%H%M')

    if fmt == 'excel':
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Leads Trading')
            try:
                from openpyxl.styles import PatternFill, Font, Alignment
                ws = writer.sheets['Leads Trading']
                fill = PatternFill("solid", fgColor="0D3B2D")
                for cell in ws[1]:
                    cell.fill = fill
                    cell.font = Font(bold=True, color="00C77A")
                    cell.alignment = Alignment(horizontal='center')
                for col in ws.columns:
                    w = max(len(str(c.value or '')) for c in col) + 4
                    ws.column_dimensions[col[0].column_letter].width = min(w, 40)
            except Exception:
                pass
        output.seek(0)
        return send_file(output, as_attachment=True,
                         download_name=f'leads_trading_{ts}.xlsx',
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        return send_file(output, as_attachment=True,
                         download_name=f'leads_trading_{ts}.csv',
                         mimetype='text/csv')


@app.route('/api/leads/stats')
@login_required
@admin_required
def leads_stats_api():
    """Statistiques leads en JSON."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'DB'}), 500
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) as cnt FROM training_leads GROUP BY status")
    rows = {r['status']: r['cnt'] for r in cursor.fetchall()}
    cursor.execute("SELECT level_selected, COUNT(*) as cnt FROM training_leads GROUP BY level_selected")
    by_level = {r['level_selected']: r['cnt'] for r in cursor.fetchall()}
    total = sum(rows.values())
    paye  = rows.get('Payé', 0)
    conn.close()
    return jsonify({
        'total':           total,
        'par_statut':      rows,
        'par_formation':   by_level,
        'taux_conversion': round(paye / total * 100, 1) if total else 0,
    })


# ══════════════════════════════════════════════════════════════
# MODULE AGENDA — Email Gmail + Scheduler + Routes
# ══════════════════════════════════════════════════════════════

def _build_agenda_email_html(event: dict, minutes_before: int) -> str:
    """Construit le corps HTML de l'email de rappel."""
    etype  = event.get('event_type', 'personnel')
    cfg    = AGENDA_EVENT_COLORS.get(etype, AGENDA_EVENT_COLORS['personnel'])
    color  = cfg['bg']
    icon   = cfg['icon']
    label  = cfg['label']
    title  = event.get('title', '(Sans titre)')
    desc   = event.get('description') or ''
    loc    = event.get('location') or ''
    notes  = event.get('notes') or ''
    start  = (event.get('start_datetime') or '')[:16].replace('T', ' à ')
    end    = (event.get('end_datetime')   or '')[:16].replace('T', ' à ')

    if minutes_before >= 1440:
        remind_txt = f"{minutes_before // 1440} jour(s)"
    elif minutes_before >= 60:
        remind_txt = f"{minutes_before // 60} heure(s)"
    else:
        remind_txt = f"{minutes_before} minute(s)"

    loc_row   = f'<tr><td style="padding:8px 0;color:#888;font-size:13px;width:100px;">📍 Lieu</td><td style="padding:8px 0;color:#e0e0e0;font-size:13px;">{loc}</td></tr>' if loc else ''
    notes_blk = f'<div style="background:#1a2a3a;border-radius:8px;padding:16px;margin-top:18px;"><p style="color:#888;font-size:11px;margin:0 0 6px;">📝 Notes</p><p style="color:#ccc;font-size:13px;margin:0;">{notes}</p></div>' if notes else ''
    desc_blk  = f'<p style="color:#aaa;margin:4px 0 0;font-size:14px;">{desc}</p>' if desc else ''

    return f'''<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="margin:0;padding:0;background:#0a0f1a;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:580px;margin:0 auto;padding:24px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#0d1b2a,#1a2a3a);border-radius:16px 16px 0 0;padding:32px 28px;text-align:center;border-bottom:3px solid {color};">
    <div style="font-size:42px;margin-bottom:10px;">⏰</div>
    <h1 style="color:#fff;margin:0;font-size:22px;font-weight:800;letter-spacing:.3px;">Rappel d'Agenda</h1>
    <p style="color:{color};margin:8px 0 0;font-size:14px;font-weight:600;">{icon} {label} · dans {remind_txt}</p>
  </div>

  <!-- Body -->
  <div style="background:#111827;padding:28px;border-radius:0 0 16px 16px;border:1px solid #1e2a3a;border-top:none;">

    <!-- Event card -->
    <div style="background:linear-gradient(135deg,{color}18,{color}08);border:1px solid {color}44;border-left:5px solid {color};border-radius:10px;padding:20px;margin-bottom:22px;">
      <h2 style="color:#fff;margin:0 0 4px;font-size:20px;font-weight:700;">{title}</h2>
      {desc_blk}
    </div>

    <!-- Details table -->
    <table style="width:100%;border-collapse:collapse;margin-bottom:4px;">
      <tr><td style="padding:8px 0;color:#888;font-size:13px;width:100px;">🕐 Début</td><td style="padding:8px 0;color:#e0e0e0;font-size:13px;font-weight:600;">{start}</td></tr>
      <tr><td style="padding:8px 0;color:#888;font-size:13px;">🏁 Fin</td><td style="padding:8px 0;color:#e0e0e0;font-size:13px;">{end}</td></tr>
      {loc_row}
    </table>

    {notes_blk}

    <!-- CTA Button -->
    <div style="text-align:center;margin:26px 0 16px;">
      <a href="http://localhost:5001/agenda" style="background:linear-gradient(135deg,{color},{color}bb);color:#000;font-weight:800;font-size:14px;padding:14px 36px;border-radius:10px;text-decoration:none;display:inline-block;letter-spacing:.5px;box-shadow:0 4px 16px {color}44;">
        📅 Ouvrir mon Agenda
      </a>
    </div>

    <!-- Footer -->
    <div style="border-top:1px solid #1e2a3a;padding-top:14px;text-align:center;">
      <p style="color:#333;font-size:11px;margin:0;">Kengni Finance · Rappel automatique · fabricekengni90@gmail.com</p>
    </div>
  </div>
</div>
</body></html>'''


def _send_agenda_email(event: dict, minutes_before: int) -> bool:
    """Envoie un email de rappel via Gmail SMTP."""
    cfg = GMAIL_CONFIG
    try:
        msg = MIMEMultipart('alternative')
        h = f"{'%dh' % (minutes_before//60) if minutes_before >= 60 else '%dmin' % minutes_before}"
        msg['Subject'] = f"⏰ Rappel dans {h} : {event['title']}"
        msg['From']    = f"{cfg['sender_name']} <{cfg['sender_email']}>"
        msg['To']      = cfg['receiver_email']

        text = (f"RAPPEL — {event['title']}\n"
                f"Début   : {(event.get('start_datetime') or '')[:16]}\n"
                f"Fin     : {(event.get('end_datetime') or '')[:16]}\n"
                f"Lieu    : {event.get('location') or 'Non précisé'}\n\n"
                f"{event.get('description') or ''}\n\n---\nKengni Finance")
        msg.attach(MIMEText(text, 'plain', 'utf-8'))
        msg.attach(MIMEText(_build_agenda_email_html(event, minutes_before), 'html', 'utf-8'))

        with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port']) as s:
            s.ehlo(); s.starttls(); s.login(cfg['sender_email'], cfg['smtp_password'])
            s.sendmail(cfg['sender_email'], cfg['receiver_email'], msg.as_string())
        print(f"[Agenda] ✅ Email envoyé : {event['title']} ({minutes_before}min avant)")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"[Agenda] ❌ Auth Gmail échouée — vérifiez le mot de passe d'application")
        return False
    except Exception as e:
        print(f"[Agenda] ❌ Erreur email : {e}")
        return False


def _agenda_check_reminders():
    """Vérifie et envoie les rappels toutes les 60 secondes (thread background)."""
    while True:
        try:
            now = datetime.now()
            conn = get_db_connection()
            if not conn:
                time.sleep(60)
                continue
            cursor = conn.cursor()
            window = (now + timedelta(hours=48)).isoformat()
            PG = DATABASE_URL is not None
            PH = '%s' if PG else '?'

            cursor.execute(f'''
                SELECT * FROM agenda_events
                WHERE status = 'active'
                  AND start_datetime BETWEEN {PH} AND {PH}
                  AND (email_reminder = 1 OR app_reminder = 1)
            ''', (now.isoformat(), window))
            events = [dict(r) for r in cursor.fetchall()]

            for ev in events:
                try:
                    start_dt  = datetime.fromisoformat(ev['start_datetime'])
                    remind_at = start_dt - timedelta(minutes=ev['reminder_minutes'])
                    diff = abs((now - remind_at).total_seconds())
                    if diff > 90:
                        continue

                    # Anti-doublon
                    cursor.execute(f'''
                        SELECT id FROM agenda_reminders_sent
                        WHERE event_id = {PH} AND sent_at >= {PH}
                    ''', (ev['id'], (now - timedelta(minutes=3)).isoformat()))
                    if cursor.fetchone():
                        continue

                    # Email
                    if ev['email_reminder']:
                        ok = _send_agenda_email(ev, ev['reminder_minutes'])
                        if ok:
                            cursor.execute(f'INSERT INTO agenda_reminders_sent (event_id,sent_at,method) VALUES ({PH},{PH},{PH})',
                                           (ev['id'], now.isoformat(), 'email'))

                    # Notification in-app
                    if ev['app_reminder']:
                        h = ev['reminder_minutes']
                        label = f"{h//60}h" if h >= 60 else f"{h}min"
                        cursor.execute(f'''
                            INSERT INTO notifications (user_id, type, title, message, action_url, created_at)
                            VALUES ({PH},{PH},{PH},{PH},{PH},{PH})
                        ''', (ev['user_id'], 'warning' if h <= 15 else 'info',
                              f"⏰ Rappel dans {label} : {ev['title']}",
                              f"Votre événement commence à {ev['start_datetime'][11:16]}.",
                              '/agenda', now.isoformat()))
                        cursor.execute(f'INSERT INTO agenda_reminders_sent (event_id,sent_at,method) VALUES ({PH},{PH},{PH})',
                                       (ev['id'], now.isoformat(), 'app'))

                    conn.commit()
                except Exception as ex:
                    print(f"[Agenda] Erreur traitement event #{ev.get('id')}: {ex}")

            conn.close()
        except Exception as e:
            print(f"[Agenda Scheduler] Erreur : {e}")
        time.sleep(60)


def start_agenda_scheduler():
    """Lance le scheduler en thread daemon."""
    t = threading.Thread(target=_agenda_check_reminders, daemon=True, name='AgendaScheduler')
    t.start()
    print("✅ Agenda Scheduler démarré (Gmail → iCloud, toutes les 60s)")


# ── ROUTES AGENDA ──────────────────────────────────────────────────────────────

@app.route('/agenda')
@login_required
def agenda():
    """Page principale de l'agenda."""
    user_id = session['user_id']
    now     = datetime.now()
    conn    = get_db_connection()
    events, next_event, stats_raw = [], None, {}

    if conn:
        cursor = conn.cursor()
        start_w = (now - timedelta(days=60)).strftime('%Y-%m-%d')
        end_w   = (now + timedelta(days=90)).strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT * FROM agenda_events
            WHERE user_id=? AND status!='cancelled'
              AND DATE(start_datetime) BETWEEN ? AND ?
            ORDER BY start_datetime ASC
        ''', (user_id, start_w, end_w))
        events = [dict(r) for r in cursor.fetchall()]

        cursor.execute('''
            SELECT * FROM agenda_events
            WHERE user_id=? AND status='active' AND start_datetime >= ?
            ORDER BY start_datetime ASC LIMIT 1
        ''', (user_id, now.isoformat()))
        row = cursor.fetchone()
        next_event = dict(row) if row else None

        cursor.execute('''
            SELECT event_type, COUNT(*) as cnt FROM agenda_events
            WHERE user_id=? AND status='active' AND DATE(start_datetime)>=DATE('now')
            GROUP BY event_type
        ''', (user_id,))
        stats_raw = {r['event_type']: r['cnt'] for r in cursor.fetchall()}
        conn.close()

    # Préparer pour FullCalendar
    fc_events = []
    for e in events:
        cfg = AGENDA_EVENT_COLORS.get(e['event_type'], AGENDA_EVENT_COLORS['personnel'])
        fc_events.append({
            'id': e['id'], 'title': e['title'],
            'start': e['start_datetime'], 'end': e['end_datetime'],
            'allDay': bool(e['all_day']),
            'backgroundColor': cfg['bg'], 'borderColor': cfg['border'],
            'extendedProps': {
                'type': e['event_type'], 'icon': cfg['icon'],
                'description': e['description'] or '',
                'location': e['location'] or '',
                'notes': e['notes'] or '',
                'reminder': e['reminder_minutes'],
            }
        })

    return render_template('agenda.html',
        events_json  = json.dumps(fc_events),
        events       = events,
        next_event   = next_event,
        stats        = stats_raw,
        event_colors = AGENDA_EVENT_COLORS,
        now          = now,
    )


@app.route('/api/agenda/events', methods=['POST'])
@login_required
def agenda_create_event():
    user_id = session['user_id']
    data    = request.get_json(silent=True) or request.form or {}

    title      = (data.get('title') or '').strip()
    event_type = data.get('event_type', 'personnel')
    start_dt   = data.get('start_datetime', '')
    end_dt     = data.get('end_datetime', '')

    if not title or not start_dt or not end_dt:
        return jsonify({'success': False, 'error': 'Champs requis manquants'}), 400
    if event_type not in AGENDA_EVENT_COLORS:
        event_type = 'personnel'

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'DB error'}), 500
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO agenda_events
        (user_id,title,description,event_type,start_datetime,end_datetime,
         all_day,recurrence,reminder_minutes,email_reminder,app_reminder,
         location,notes,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        user_id, title,
        data.get('description',''), event_type, start_dt, end_dt,
        int(data.get('all_day', 0)), data.get('recurrence','none'),
        int(data.get('reminder_minutes', 30)),
        int(data.get('email_reminder', 1)), int(data.get('app_reminder', 1)),
        data.get('location',''), data.get('notes',''),
        datetime.now().isoformat(), datetime.now().isoformat()
    ))
    event_id = cursor.lastrowid
    cursor.execute('''
        INSERT INTO notifications (user_id,type,title,message,action_url,created_at)
        VALUES (?,?,?,?,?,?)
    ''', (user_id, 'success',
          f"📅 Événement créé : {title}",
          f'Planifié le {start_dt[:16].replace("T"," à ")}. Rappel dans {data.get("reminder_minutes",30)} min.',
          '/agenda', datetime.now().isoformat()))
    conn.commit(); conn.close()
    return jsonify({'success': True, 'event_id': event_id})


@app.route('/api/agenda/events')
@login_required
def agenda_get_events():
    user_id = session['user_id']
    start   = request.args.get('start', (datetime.now() - timedelta(days=30)).isoformat())
    end     = request.args.get('end',   (datetime.now() + timedelta(days=90)).isoformat())
    conn    = get_db_connection()
    result  = []
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM agenda_events
            WHERE user_id=? AND status!='cancelled'
              AND start_datetime BETWEEN ? AND ?
            ORDER BY start_datetime ASC
        ''', (user_id, start[:10], end[:10]))
        for e in cursor.fetchall():
            e = dict(e)
            cfg = AGENDA_EVENT_COLORS.get(e['event_type'], AGENDA_EVENT_COLORS['personnel'])
            result.append({
                'id': e['id'], 'title': e['title'],
                'start': e['start_datetime'], 'end': e['end_datetime'],
                'allDay': bool(e['all_day']),
                'backgroundColor': cfg['bg'], 'borderColor': cfg['border'],
                'extendedProps': {'type': e['event_type'], 'icon': cfg['icon'],
                                  'description': e['description'] or '',
                                  'location': e['location'] or '',
                                  'reminder': e['reminder_minutes']}
            })
        conn.close()
    return jsonify(result)


@app.route('/api/agenda/events/<int:event_id>', methods=['PUT', 'PATCH'])
@login_required
def agenda_update_event(event_id):
    user_id = session['user_id']
    data    = request.get_json(silent=True) or request.form or {}
    conn    = get_db_connection()
    if not conn:
        return jsonify({'success': False}), 500
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM agenda_events WHERE id=? AND user_id=?', (event_id, user_id))
    if not cursor.fetchone():
        conn.close(); return jsonify({'success': False, 'error': 'Non trouvé'}), 404

    fields = ['title','description','event_type','start_datetime','end_datetime',
              'all_day','recurrence','reminder_minutes','email_reminder',
              'app_reminder','location','notes','status']
    sets, vals = [], []
    for f in fields:
        if f in data:
            sets.append(f'{f}=?'); vals.append(data[f])
    if sets:
        vals += [datetime.now().isoformat(), event_id, user_id]
        cursor.execute(f"UPDATE agenda_events SET {', '.join(sets)}, updated_at=? WHERE id=? AND user_id=?", vals)
        conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/agenda/events/<int:event_id>', methods=['DELETE'])
@login_required
def agenda_delete_event(event_id):
    user_id = session['user_id']
    conn    = get_db_connection()
    if conn:
        conn.execute("UPDATE agenda_events SET status='cancelled' WHERE id=? AND user_id=?", (event_id, user_id))
        conn.commit(); conn.close()
    return jsonify({'success': True})


@app.route('/api/agenda/today')
@login_required
def agenda_today():
    user_id = session['user_id']
    today   = datetime.now().strftime('%Y-%m-%d')
    conn    = get_db_connection()
    events  = []
    if conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM agenda_events
            WHERE user_id=? AND status='active' AND DATE(start_datetime)=?
            ORDER BY start_datetime ASC
        ''', (user_id, today))
        events = [dict(r) for r in cursor.fetchall()]
        conn.close()
    return jsonify({'events': events, 'count': len(events), 'date': today})


@app.route('/api/agenda/test-email', methods=['POST'])
@login_required
def agenda_test_email():
    """Envoie un email de test pour vérifier la configuration Gmail."""
    now = datetime.now()
    fake_event = {
        'id':             0,
        'user_id':        session['user_id'],
        'title':          '✅ Test de configuration — Kengni Finance Agenda',
        'event_type':     'trading',
        'description':    'Ceci est un email de test envoyé depuis Kengni Finance pour vérifier que la configuration Gmail fonctionne correctement. Si vous recevez cet email, les rappels automatiques sont opérationnels !',
        'start_datetime': (now + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%S'),
        'end_datetime':   (now + timedelta(minutes=90)).strftime('%Y-%m-%dT%H:%M:%S'),
        'location':       'Kengni Finance — http://localhost:5001',
        'notes':          f'Test effectué le {now.strftime("%d/%m/%Y à %H:%M")} par {session.get("username","admin")}.',
    }
    ok = _send_agenda_email(fake_event, 30)
    if ok:
        return jsonify({
            'success': True,
            'message': f'✅ Email envoyé avec succès à {GMAIL_CONFIG["receiver_email"]} !',
            'from':    GMAIL_CONFIG['sender_email'],
            'to':      GMAIL_CONFIG['receiver_email'],
        })
    else:
        return jsonify({
            'success':  False,
            'message':  '❌ Échec — le mot de passe d\'application Gmail est incorrect ou manquant.',
            'help':     'Générez un mot de passe sur https://myaccount.google.com/apppasswords et mettez-le dans GMAIL_CONFIG dans app.py.',
        }), 500



# ══════════════════════════════════════════════════════════════
# EMAIL AUTOMATIQUE À L'INSCRIPTION — Paiement cliquable
# ══════════════════════════════════════════════════════════════

def _send_inscription_payment_email(lead: dict) -> bool:
    """
    Envoyé automatiquement dès qu'un prospect soumet le formulaire.
    Contient des boutons cliquables pour chaque moyen de paiement.
    """
    cfg    = GMAIL_CONFIG
    name   = lead.get('full_name', 'Cher(e) futur(e) trader')
    email  = lead.get('email', '')
    level  = lead.get('level_selected', 'Formation')
    wa_raw = lead.get('whatsapp', '').replace(' ', '').replace('+', '')
    prices = FORMATION_PRICES.get(level, {'xaf': 50000, 'eur': 76})
    xaf    = prices['xaf']
    eur    = prices['eur']

    # ── URLs de paiement cliquables ─────────────────────────────────────────
    wa_msg   = f"Bonjour,%20je%20viens%20de%20m%27inscrire%20à%20la%20formation%20{level.replace(' ','%20')}%20et%20je%20souhaite%20régler%20par%20"
    url_om   = f"https://wa.me/237695072759?text={wa_msg}Orange%20Money%20(695%20072%20759).%20Mon%20nom%20:%20{name.replace(' ','%20')}"
    url_mtn  = f"https://wa.me/237695072759?text={wa_msg}MTN%20MoMo%20(670%20695%20946).%20Mon%20nom%20:%20{name.replace(' ','%20')}"
    url_pp   = "https://www.paypal.com/paypalme/fabricekengni"
    url_wa   = f"https://wa.me/237695072759?text=Bonjour,%20j%27ai%20effectué%20mon%20paiement%20pour%20la%20formation%20{level.replace(' ','%20')}.%20Mon%20nom%20:%20{name.replace(' ','%20')}"

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Kengni Trading Academy — Paiement</title>
</head>
<body style="margin:0;padding:0;background:#060d17;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;padding:20px;">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#0a1628 0%,#0f2a1e 100%);border-radius:20px 20px 0 0;padding:40px 32px 32px;text-align:center;border-bottom:3px solid #00d4aa;">
    <div style="font-size:3.5rem;margin-bottom:12px;">🎓</div>
    <h1 style="color:#fff;margin:0 0 6px;font-size:24px;font-weight:900;letter-spacing:.3px;">Kengni Trading Academy</h1>
    <p style="color:#00d4aa;margin:0;font-size:15px;font-weight:700;">Votre inscription est confirmée ✅</p>
  </div>

  <!-- BODY -->
  <div style="background:#0d1421;padding:32px;border:1px solid #1a2a3a;border-top:none;border-radius:0 0 20px 20px;">

    <!-- Salutation -->
    <p style="color:#e0e0e0;font-size:15px;line-height:1.75;margin:0 0 24px;">
      Bonjour <strong style="color:#00d4aa;">{name}</strong> 👋<br><br>
      Merci pour votre inscription à la formation
      <strong style="color:#fff;background:rgba(0,212,170,.1);padding:2px 8px;border-radius:6px;">{level}</strong> !
      <br><br>
      Votre place est <strong style="color:#ffd700;">réservée pendant 48h</strong>.
      Pour la confirmer définitivement, veuillez procéder au paiement via l'un des boutons ci-dessous.
    </p>

    <!-- PRIX -->
    <div style="background:linear-gradient(135deg,rgba(0,212,170,.18),rgba(0,212,170,.06));border:1.5px solid rgba(0,212,170,.35);border-radius:16px;padding:24px;text-align:center;margin-bottom:28px;">
      <div style="font-size:.8rem;color:#888;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px;">Montant de la formation — {level}</div>
      <div style="font-size:2.6rem;font-weight:900;color:#00d4aa;line-height:1;">{xaf:,} <span style="font-size:1.2rem;">FCFA</span></div>
      <div style="font-size:1rem;color:#666;margin-top:6px;">≈ {eur} EUR</div>
    </div>

    <!-- TITRE BOUTONS -->
    <h2 style="color:#fff;font-size:16px;font-weight:800;margin:0 0 16px;text-align:center;">
      👇 Choisissez votre moyen de paiement
    </h2>

    <!-- BOUTON ORANGE MONEY -->
    <a href="{url_om}" target="_blank"
       style="display:block;text-decoration:none;margin-bottom:12px;">
      <div style="background:linear-gradient(135deg,#c44b00,#ff6b00);border-radius:14px;padding:18px 22px;display:flex;align-items:center;justify-content:space-between;transition:all .2s;box-shadow:0 4px 18px rgba(255,107,0,.3);">
        <div style="display:flex;align-items:center;gap:14px;">
          <div style="font-size:2rem;">🟠</div>
          <div>
            <div style="color:#fff;font-weight:800;font-size:15px;">Orange Money</div>
            <div style="color:rgba(255,255,255,.75);font-size:13px;margin-top:2px;">Numéro : <strong>695 072 759</strong> — Fabrice Kengni</div>
          </div>
        </div>
        <div style="color:#fff;font-size:1.4rem;">→</div>
      </div>
    </a>

    <!-- BOUTON MTN -->
    <a href="{url_mtn}" target="_blank"
       style="display:block;text-decoration:none;margin-bottom:12px;">
      <div style="background:linear-gradient(135deg,#b8860b,#ffd700);border-radius:14px;padding:18px 22px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 4px 18px rgba(255,215,0,.25);">
        <div style="display:flex;align-items:center;gap:14px;">
          <div style="font-size:2rem;">🟡</div>
          <div>
            <div style="color:#000;font-weight:800;font-size:15px;">MTN Mobile Money</div>
            <div style="color:rgba(0,0,0,.65);font-size:13px;margin-top:2px;">Numéro : <strong>670 695 946</strong> — Fabrice Kengni</div>
          </div>
        </div>
        <div style="color:#000;font-size:1.4rem;">→</div>
      </div>
    </a>

    <!-- BOUTON PAYPAL -->
    <a href="{url_pp}" target="_blank"
       style="display:block;text-decoration:none;margin-bottom:12px;">
      <div style="background:linear-gradient(135deg,#003087,#009cde);border-radius:14px;padding:18px 22px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 4px 18px rgba(0,156,222,.3);">
        <div style="display:flex;align-items:center;gap:14px;">
          <div style="font-size:2rem;">🔵</div>
          <div>
            <div style="color:#fff;font-weight:800;font-size:15px;">PayPal</div>
            <div style="color:rgba(255,255,255,.75);font-size:13px;margin-top:2px;">fabrice.kengni@icloud.com — <em>Amis &amp; Famille</em></div>
          </div>
        </div>
        <div style="color:#fff;font-size:1.4rem;">→</div>
      </div>
    </a>

    <!-- BOUTON CRYPTO -->
    <a href="mailto:fabrice.kengni12@gmail.com?subject=Paiement%20Crypto%20—%20{level.replace(' ','%20')}&body=Bonjour,%20je%20souhaite%20payer%20en%20crypto%20pour%20la%20formation%20{level.replace(' ','%20')}.%20Mon%20nom%20:%20{name.replace(' ','%20')}"
       style="display:block;text-decoration:none;margin-bottom:24px;">
      <div style="background:linear-gradient(135deg,#7a4500,#f7931a);border-radius:14px;padding:18px 22px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 4px 18px rgba(247,147,26,.3);">
        <div style="display:flex;align-items:center;gap:14px;">
          <div style="font-size:2rem;">₿</div>
          <div>
            <div style="color:#fff;font-weight:800;font-size:15px;">Crypto (BTC / USDT / ETH)</div>
            <div style="color:rgba(255,255,255,.75);font-size:13px;margin-top:2px;">Cliquez pour demander l'adresse de wallet par email</div>
          </div>
        </div>
        <div style="color:#fff;font-size:1.4rem;">→</div>
      </div>
    </a>

    <!-- SÉPARATEUR -->
    <div style="border-top:1px solid #1a2a3a;margin:4px 0 24px;"></div>

    <!-- INSTRUCTIONS -->
    <div style="background:rgba(255,215,0,.07);border:1px solid rgba(255,215,0,.2);border-radius:14px;padding:18px 20px;margin-bottom:24px;">
      <p style="color:#ffd700;font-weight:800;font-size:14px;margin:0 0 10px;">📋 Après votre paiement — 3 étapes</p>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <div style="display:flex;align-items:flex-start;gap:12px;">
          <div style="background:#ffd700;color:#000;border-radius:50%;width:22px;height:22px;min-width:22px;font-weight:800;font-size:12px;display:flex;align-items:center;justify-content:center;">1</div>
          <div style="color:#ccc;font-size:13px;line-height:1.5;">Prenez une <strong style="color:#fff;">capture d'écran</strong> de votre reçu de paiement</div>
        </div>
        <div style="display:flex;align-items:flex-start;gap:12px;">
          <div style="background:#ffd700;color:#000;border-radius:50%;width:22px;height:22px;min-width:22px;font-weight:800;font-size:12px;display:flex;align-items:center;justify-content:center;">2</div>
          <div style="color:#ccc;font-size:13px;line-height:1.5;">Envoyez-la sur <strong style="color:#25d366;">WhatsApp au +237 695 072 659</strong></div>
        </div>
        <div style="display:flex;align-items:flex-start;gap:12px;">
          <div style="background:#ffd700;color:#000;border-radius:50%;width:22px;height:22px;min-width:22px;font-weight:800;font-size:12px;display:flex;align-items:center;justify-content:center;">3</div>
          <div style="color:#ccc;font-size:13px;line-height:1.5;">Votre accès à la formation est <strong style="color:#00d4aa;">activé sous 24h</strong></div>
        </div>
      </div>
    </div>

    <!-- CTA WHATSAPP -->
    <div style="text-align:center;margin-bottom:8px;">
      <a href="{url_wa}" target="_blank"
         style="display:inline-block;background:linear-gradient(135deg,#128c7e,#25d366);color:#fff;font-weight:800;font-size:15px;padding:16px 36px;border-radius:12px;text-decoration:none;box-shadow:0 6px 20px rgba(37,211,102,.4);letter-spacing:.3px;">
        💬 Contacter sur WhatsApp
      </a>
    </div>

    <!-- FOOTER -->
    <div style="border-top:1px solid #1a2a3a;padding-top:18px;text-align:center;margin-top:24px;">
      <p style="color:#333;font-size:11px;margin:0 0 4px;">Kengni Trading Academy · fabrice.kengni12@gmail.com</p>
      <p style="color:#222;font-size:10px;margin:0;">Cet email vous a été envoyé automatiquement suite à votre inscription.</p>
    </div>
  </div>
</div>
</body>
</html>"""

    text = (
        f"Bonjour {name},\n\n"
        f"Merci pour votre inscription à la formation {level} !\n\n"
        f"MONTANT : {xaf:,} FCFA (≈ {eur} EUR)\n\n"
        f"MOYENS DE PAIEMENT :\n"
        f"• Orange Money   : 695 072 759 (Fabrice Kengni)\n"
        f"• MTN MoMo       : 670 695 946 (Fabrice Kengni)\n"
        f"• PayPal         : fabrice.kengni@icloud.com\n"
        f"• Crypto         : Écrivez à fabrice.kengni12@gmail.com\n\n"
        f"Après paiement, envoyez la capture sur WhatsApp : +237 695 072 759\n\n"
        f"— Kengni Trading Academy"
    )

    if not email:
        print("[Inscription] ⚠️  Pas d'email — envoi annulé")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject']  = f"🎓 {name}, finalisez votre inscription — {level} | Kengni Trading Academy"
        msg['From']     = f"Kengni Trading Academy <{cfg['sender_email']}>"
        msg['To']       = email
        msg['Reply-To'] = cfg['sender_email']
        msg.attach(MIMEText(text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html',  'utf-8'))

        # Copie admin
        admin_msg = MIMEMultipart('alternative')
        admin_msg['Subject'] = f"📥 Nouvelle inscription — {name} ({level})"
        admin_msg['From']    = f"Kengni Finance <{cfg['sender_email']}>"
        admin_msg['To']      = cfg['receiver_email']
        admin_body = (
            f"Nouveau prospect inscrit !\n\n"
            f"Nom      : {name}\n"
            f"Email    : {email}\n"
            f"WhatsApp : {lead.get('whatsapp','')}\n"
            f"Formation: {level}\n"
            f"Capital  : {lead.get('capital','—')}\n"
            f"Objectif : {lead.get('objective','—')}\n"
            f"Date     : {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n"
        )
        admin_msg.attach(MIMEText(admin_body, 'plain', 'utf-8'))

        with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port']) as s:
            s.ehlo(); s.starttls()
            s.login(cfg['sender_email'], cfg['smtp_password'])
            s.sendmail(cfg['sender_email'], email, msg.as_string())
            s.sendmail(cfg['sender_email'], cfg['receiver_email'], admin_msg.as_string())

        print(f"[Inscription] ✅ Email paiement → {email} | Notif admin → {cfg['receiver_email']}")
        return True
    except Exception as e:
        print(f"[Inscription] ❌ Erreur envoi : {e}")
        return False


# ══════════════════════════════════════════════════════════════
# RAPPORT AUTOMATIQUE — Matin 7h / Midi 12h / Soir 20h
# ══════════════════════════════════════════════════════════════

def _build_report_html(data: dict, period: str) -> str:
    """Construit le HTML du rapport journalier."""
    now_str  = datetime.now().strftime('%d/%m/%Y à %H:%M')
    emojis   = {'Matin': '🌅', 'Midi': '☀️', 'Soir': '🌙'}
    em       = emojis.get(period, '📊')

    leads    = data.get('leads', {})
    fin      = data.get('finances', {})
    agenda   = data.get('agenda', [])
    notifs   = data.get('notifications', 0)
    trades   = data.get('trades', {})

    agenda_rows = ''
    for ev in agenda[:8]:
        color = {'trading':'#00d4aa','finance':'#4a9eff','formation':'#a29bfe',
                 'reunion':'#ffd700','revue':'#ff7675','personnel':'#fd79a8'}.get(ev.get('event_type',''), '#888')
        agenda_rows += f"""
        <tr>
          <td style="padding:8px 12px;color:#e0e0e0;font-size:13px;border-bottom:1px solid #1a2a3a;">{ev.get('title','')}</td>
          <td style="padding:8px 12px;font-size:12px;border-bottom:1px solid #1a2a3a;">
            <span style="color:{color};font-weight:600;">{ev.get('event_type','').title()}</span>
          </td>
          <td style="padding:8px 12px;color:#888;font-size:12px;border-bottom:1px solid #1a2a3a;">
            {(ev.get('start_datetime') or '')[:16].replace('T',' ')}
          </td>
        </tr>"""

    if not agenda_rows:
        agenda_rows = '<tr><td colspan="3" style="padding:12px;color:#444;text-align:center;font-size:13px;">Aucun événement à venir</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="margin:0;padding:0;background:#060d17;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;padding:20px;">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#0a1628,#0d2a1a);border-radius:20px 20px 0 0;padding:36px 32px;text-align:center;border-bottom:3px solid #00d4aa;">
    <div style="font-size:3rem;margin-bottom:10px;">{em}</div>
    <h1 style="color:#fff;margin:0 0 6px;font-size:22px;font-weight:900;">Rapport {period}</h1>
    <p style="color:#00d4aa;margin:0;font-size:14px;font-weight:600;">Kengni Finance · {now_str}</p>
  </div>

  <div style="background:#0d1421;padding:28px 32px;border:1px solid #1a2a3a;border-top:none;border-radius:0 0 20px 20px;">

    <!-- ── LEADS ── -->
    <h2 style="color:#fff;font-size:15px;font-weight:800;margin:0 0 14px;padding-bottom:8px;border-bottom:1px solid #1a2a3a;">
      🎓 Prospects — Kengni Trading Academy
    </h2>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:22px;">
      <div style="background:#0a1628;border-radius:12px;padding:14px;text-align:center;border-top:2px solid #4a9eff;">
        <div style="font-size:1.8rem;font-weight:900;color:#4a9eff;">{leads.get('total',0)}</div>
        <div style="font-size:.7rem;color:#666;text-transform:uppercase;letter-spacing:.5px;margin-top:3px;">Total</div>
      </div>
      <div style="background:#0a1628;border-radius:12px;padding:14px;text-align:center;border-top:2px solid #ffd700;">
        <div style="font-size:1.8rem;font-weight:900;color:#ffd700;">{leads.get('nouveau',0)}</div>
        <div style="font-size:.7rem;color:#666;text-transform:uppercase;letter-spacing:.5px;margin-top:3px;">Nouveaux</div>
      </div>
      <div style="background:#0a1628;border-radius:12px;padding:14px;text-align:center;border-top:2px solid #00d4aa;">
        <div style="font-size:1.8rem;font-weight:900;color:#00d4aa;">{leads.get('paye',0)}</div>
        <div style="font-size:.7rem;color:#666;text-transform:uppercase;letter-spacing:.5px;margin-top:3px;">Payés ✅</div>
      </div>
    </div>
    <div style="background:#0a1628;border-radius:10px;padding:12px 16px;margin-bottom:22px;display:flex;justify-content:space-between;align-items:center;">
      <span style="color:#888;font-size:13px;">Taux de conversion</span>
      <span style="color:#00d4aa;font-weight:800;font-size:16px;">{leads.get('conversion','0%')}</span>
    </div>

    <!-- ── FINANCES ── -->
    <h2 style="color:#fff;font-size:15px;font-weight:800;margin:0 0 14px;padding-bottom:8px;border-bottom:1px solid #1a2a3a;">
      💰 Finances (30 derniers jours)
    </h2>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:22px;">
      <div style="background:#0a1628;border-radius:12px;padding:14px;text-align:center;border-top:2px solid #00ff88;">
        <div style="font-size:1.1rem;font-weight:800;color:#00ff88;">{fin.get('revenus','0')} €</div>
        <div style="font-size:.68rem;color:#666;text-transform:uppercase;margin-top:3px;">Revenus</div>
      </div>
      <div style="background:#0a1628;border-radius:12px;padding:14px;text-align:center;border-top:2px solid #ff4757;">
        <div style="font-size:1.1rem;font-weight:800;color:#ff4757;">{fin.get('depenses','0')} €</div>
        <div style="font-size:.68rem;color:#666;text-transform:uppercase;margin-top:3px;">Dépenses</div>
      </div>
      <div style="background:#0a1628;border-radius:12px;padding:14px;text-align:center;border-top:2px solid #ffd700;">
        <div style="font-size:1.1rem;font-weight:800;color:#ffd700;">{fin.get('solde','0')} €</div>
        <div style="font-size:.68rem;color:#666;text-transform:uppercase;margin-top:3px;">Solde net</div>
      </div>
    </div>

    <!-- ── TRADING ── -->
    <h2 style="color:#fff;font-size:15px;font-weight:800;margin:0 0 14px;padding-bottom:8px;border-bottom:1px solid #1a2a3a;">
      📈 Trading (30 derniers jours)
    </h2>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:22px;">
      <div style="background:#0a1628;border-radius:12px;padding:14px;text-align:center;border-top:2px solid #00d4aa;">
        <div style="font-size:1.6rem;font-weight:900;color:#00d4aa;">{trades.get('total',0)}</div>
        <div style="font-size:.68rem;color:#666;text-transform:uppercase;margin-top:3px;">Trades</div>
      </div>
      <div style="background:#0a1628;border-radius:12px;padding:14px;text-align:center;border-top:2px solid #00ff88;">
        <div style="font-size:1.6rem;font-weight:900;color:#00ff88;">{trades.get('gagnants',0)}</div>
        <div style="font-size:.68rem;color:#666;text-transform:uppercase;margin-top:3px;">Gagnants</div>
      </div>
      <div style="background:#0a1628;border-radius:12px;padding:14px;text-align:center;border-top:2px solid #a29bfe;">
        <div style="font-size:1.6rem;font-weight:900;color:#a29bfe;">{trades.get('winrate','0%')}</div>
        <div style="font-size:.68rem;color:#666;text-transform:uppercase;margin-top:3px;">Win Rate</div>
      </div>
    </div>

    <!-- ── AGENDA ── -->
    <h2 style="color:#fff;font-size:15px;font-weight:800;margin:0 0 14px;padding-bottom:8px;border-bottom:1px solid #1a2a3a;">
      📅 Prochains événements agenda
    </h2>
    <div style="background:#0a1628;border-radius:12px;overflow:hidden;margin-bottom:22px;">
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="background:#060d17;">
            <th style="padding:10px 12px;color:#555;font-size:.7rem;text-transform:uppercase;letter-spacing:.5px;text-align:left;">Événement</th>
            <th style="padding:10px 12px;color:#555;font-size:.7rem;text-transform:uppercase;letter-spacing:.5px;text-align:left;">Type</th>
            <th style="padding:10px 12px;color:#555;font-size:.7rem;text-transform:uppercase;letter-spacing:.5px;text-align:left;">Date</th>
          </tr>
        </thead>
        <tbody>{agenda_rows}</tbody>
      </table>
    </div>

    <!-- ── NOTIFICATIONS ── -->
    <div style="background:rgba(74,158,255,.08);border:1px solid rgba(74,158,255,.2);border-radius:12px;padding:14px 18px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;">
      <span style="color:#ccc;font-size:13px;">🔔 Notifications non lues</span>
      <span style="color:#4a9eff;font-weight:800;font-size:18px;">{notifs}</span>
    </div>

    <!-- FOOTER -->
    <div style="border-top:1px solid #1a2a3a;padding-top:16px;text-align:center;">
      <a href="http://localhost:5001/dashboard"
         style="display:inline-block;background:linear-gradient(135deg,#00d4aa,#00ff88);color:#000;font-weight:800;font-size:13px;padding:12px 28px;border-radius:10px;text-decoration:none;margin-bottom:12px;">
        📊 Ouvrir le Dashboard
      </a>
      <p style="color:#222;font-size:10px;margin:10px 0 0;">Kengni Finance v2.0 · Rapport automatique {period}</p>
    </div>
  </div>
</div>
</body>
</html>"""


def _collect_report_data() -> dict:
    """Collecte toutes les données pour le rapport."""
    try:
        conn = get_db_connection()
        if not conn:
            return {'leads': {}, 'finances': {}, 'trades': {}, 'agenda': [], 'notifications': 0}
        PG = DATABASE_URL is not None
        PH = '%s' if PG else '?'
        cur  = conn.cursor()
        now  = datetime.now()
        d30  = (now - timedelta(days=30)).isoformat()

        # Leads
        cur.execute("SELECT status FROM training_leads")
        rows = cur.fetchall()
        all_leads = [r[0] if PG else r['status'] for r in rows]
        total_l   = len(all_leads)
        paye_l    = all_leads.count('Payé')
        conv      = f"{round(paye_l/total_l*100,1)}%" if total_l else "0%"

        leads = {
            'total':      total_l,
            'nouveau':    all_leads.count('Nouveau'),
            'contacte':   all_leads.count('Contacté'),
            'inscrit':    all_leads.count('Inscrit'),
            'paye':       paye_l,
            'conversion': conv,
        }

        # Finances
        cur.execute(f"SELECT type, amount FROM transactions WHERE user_id=1 AND created_at>={PH}", (d30,))
        txns = [dict(r) for r in cur.fetchall()]
        rev  = sum(t['amount'] for t in txns if t['amount'] > 0)
        dep  = abs(sum(t['amount'] for t in txns if t['amount'] < 0))
        fin  = {
            'revenus':  f"{rev:,.2f}",
            'depenses': f"{dep:,.2f}",
            'solde':    f"{rev-dep:,.2f}",
        }

        # Trading
        try:
            cur.execute(f"SELECT COUNT(*) as c FROM transactions WHERE user_id=1 AND type IN ('buy','sell') AND created_at>={PH}", (d30,))
            row = cur.fetchone()
            total_tr = row[0] if PG else row['c']
            cur.execute(f"SELECT COUNT(*) as c FROM transactions WHERE user_id=1 AND type='sell' AND amount>0 AND created_at>={PH}", (d30,))
            row = cur.fetchone()
            win_tr = row[0] if PG else row['c']
            wr       = f"{round(win_tr/total_tr*100)}%" if total_tr else "0%"
        except Exception:
            total_tr, win_tr, wr = 0, 0, "0%"

        trades = {'total': total_tr, 'gagnants': win_tr, 'winrate': wr}

        # Agenda — 8 prochains événements
        cur.execute(f"""
            SELECT title, event_type, start_datetime FROM agenda_events
            WHERE status='active' AND start_datetime >= {PH}
            ORDER BY start_datetime ASC LIMIT 8
        """, (now.isoformat(),))
        agenda = [dict(zip(['title','event_type','start_datetime'], r)) if PG else dict(r) for r in cur.fetchall()]

        # Notifications non lues
        cur.execute(f"SELECT COUNT(*) as c FROM notifications WHERE is_read=0 AND user_id=1")
        row = cur.fetchone()
        notifs = row[0] if PG else row['c']

        conn.close()
        return {'leads': leads, 'finances': fin, 'trades': trades, 'agenda': agenda, 'notifications': notifs}
    except Exception as e:
        print(f"[Rapport] Erreur collecte données : {e}")
        return {'leads': {}, 'finances': {}, 'trades': {}, 'agenda': [], 'notifications': 0}


def _send_daily_report(period: str):
    """Envoie le rapport par email."""
    cfg  = GMAIL_CONFIG
    data = _collect_report_data()
    html = _build_report_html(data, period)
    now_str = datetime.now().strftime('%d/%m/%Y')

    emojis = {'Matin': '🌅', 'Midi': '☀️', 'Soir': '🌙'}
    em = emojis.get(period, '📊')

    leads = data.get('leads', {})
    text  = (
        f"RAPPORT {period.upper()} — Kengni Finance\n"
        f"Date : {now_str}\n\n"
        f"LEADS : {leads.get('total',0)} total · {leads.get('nouveau',0)} nouveaux · {leads.get('paye',0)} payés ({leads.get('conversion','0%')})\n"
        f"FINANCES : Revenus {data['finances'].get('revenus','0')}€ · Dépenses {data['finances'].get('depenses','0')}€ · Solde {data['finances'].get('solde','0')}€\n"
        f"TRADING : {data['trades'].get('total',0)} trades · {data['trades'].get('winrate','0%')} win rate\n"
        f"AGENDA : {len(data['agenda'])} événements à venir\n"
        f"NOTIFICATIONS : {data.get('notifications',0)} non lues\n"
    )

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"{em} Rapport {period} — Kengni Finance · {now_str}"
        msg['From']    = f"Kengni Finance <{cfg['sender_email']}>"
        msg['To']      = cfg['receiver_email']
        msg.attach(MIMEText(text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port']) as s:
            s.ehlo(); s.starttls()
            s.login(cfg['sender_email'], cfg['smtp_password'])
            s.sendmail(cfg['sender_email'], cfg['receiver_email'], msg.as_string())

        print(f"[Rapport {period}] ✅ Envoyé à {cfg['receiver_email']}")
    except Exception as e:
        print(f"[Rapport {period}] ❌ Erreur : {e}")


def _report_scheduler_loop():
    """Vérifie toutes les minutes si un rapport doit être envoyé (7h / 12h / 20h)."""
    sent_today = set()   # 'Matin·2025-01-15', 'Midi·...', 'Soir·...'

    SCHEDULE = {
        'Matin': (7,  0),
        'Midi':  (12, 0),
        'Soir':  (20, 0),
    }

    while True:
        now   = datetime.now()
        today = now.strftime('%Y-%m-%d')

        for period, (h, m) in SCHEDULE.items():
            key = f"{period}·{today}"
            if key in sent_today:
                continue
            # Déclenche si on est dans la bonne fenêtre (heure pile ±90s)
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            diff   = abs((now - target).total_seconds())
            if diff <= 90:
                _send_daily_report(period)
                sent_today.add(key)

        # Nettoyage quotidien du set
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        sent_today = {k for k in sent_today if yesterday not in k}

        time.sleep(60)


def start_report_scheduler():
    """Lance le scheduler de rapports en thread daemon."""
    t = threading.Thread(target=_report_scheduler_loop, daemon=True, name='ReportScheduler')
    t.start()
    print("✅ Report Scheduler démarré (rapports à 7h, 12h, 20h → iCloud)")


if __name__ == '__main__':

    # Initialize database on startup
    init_db()

    # Démarrer le scheduler d'agenda (rappels email Gmail)
    start_agenda_scheduler()
    start_report_scheduler()
    
    # Run the application
    print("=" * 60)
    print("🚀 Kengni Finance v2.0 - Démarrage")
    print("=" * 60)
    print("📊 Application de gestion financière et trading avec IA")
    print("🌐 Mode:", "PostgreSQL (Railway)" if DATABASE_URL else "SQLite (Local)")
    print("👤 Email: fabrice.kengni@icloud.com")
    print("📅 Agenda: /agenda")
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5001))
    debug = not DATABASE_URL  # debug=False en production Railway
    app.run(debug=debug, host='0.0.0.0', port=port)