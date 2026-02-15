#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kengni Finance v2.1 - Application de gestion financière
Version corrigée et optimisée pour déploiement
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import secrets
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['DATABASE'] = os.environ.get('DATABASE_PATH', 'kengni_finance.db')

# Configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def get_db_connection():
    """Connexion à la base de données avec meilleure gestion"""
    conn = sqlite3.connect(app.config['DATABASE'], timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn

def init_db():
    """Initialise la base de données avec toutes les tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table users
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Table financial_transactions
    cursor.execute('''CREATE TABLE IF NOT EXISTS financial_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        reason TEXT,
        date TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Table portfolio
    cursor.execute('''CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        quantity REAL NOT NULL,
        purchase_price REAL NOT NULL,
        purchase_date TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Table trading_journal
    cursor.execute('''CREATE TABLE IF NOT EXISTS trading_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        action TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        date TEXT NOT NULL,
        notes TEXT,
        profit_loss REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Table notifications
    cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        type TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Table settings
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        setting_key TEXT NOT NULL,
        setting_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE(user_id, setting_key)
    )''')
    
    conn.commit()
    conn.close()

# Décorateur pour routes protégées
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes principales
@app.route('/')
def index():
    """Page d'accueil"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        
        if not email or not password:
            flash('Email et mot de passe requis', 'error')
            return render_template('register.html')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)',
                         (email, password, name))
            conn.commit()
            conn.close()
            
            flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Cet email est déjà utilisé', 'error')
        except Exception as e:
            flash(f'Erreur lors de l\'inscription: {str(e)}', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['user_name'] = user['name']
                flash('Connexion réussie !', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Email ou mot de passe incorrect', 'error')
        except Exception as e:
            flash(f'Erreur de connexion: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Déconnexion"""
    session.clear()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord principal"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Statistiques financières
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expenses,
            COUNT(*) as total_transactions
        FROM financial_transactions 
        WHERE user_id = ?
    ''', (session['user_id'],))
    stats = cursor.fetchone()
    
    # Transactions récentes
    cursor.execute('''
        SELECT * FROM financial_transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 10
    ''', (session['user_id'],))
    recent_transactions = cursor.fetchall()
    
    # Notifications non lues
    cursor.execute('''
        SELECT COUNT(*) as unread_count 
        FROM notifications 
        WHERE user_id = ? AND is_read = 0
    ''', (session['user_id'],))
    notifications = cursor.fetchone()
    
    conn.close()
    
    return render_template('dashboard.html',
                         stats=stats,
                         recent_transactions=recent_transactions,
                         unread_notifications=notifications['unread_count'])

@app.route('/finances')
@login_required
def finances():
    """Page de gestion des finances"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM financial_transactions 
        WHERE user_id = ? 
        ORDER BY date DESC
    ''', (session['user_id'],))
    transactions = cursor.fetchall()
    
    conn.close()
    return render_template('finances.html', transactions=transactions)

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    """Ajouter une transaction financière"""
    try:
        transaction_type = request.form.get('type')
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category', '')
        reason = request.form.get('reason', '')
        date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO financial_transactions (user_id, type, amount, category, reason, date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], transaction_type, amount, category, reason, date))
        conn.commit()
        conn.close()
        
        flash('Transaction ajoutée avec succès !', 'success')
    except Exception as e:
        flash(f'Erreur lors de l\'ajout: {str(e)}', 'error')
    
    return redirect(url_for('finances'))

@app.route('/portfolio')
@login_required
def portfolio():
    """Page du portefeuille d'investissement"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM portfolio 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (session['user_id'],))
    portfolio_items = cursor.fetchall()
    
    conn.close()
    return render_template('portfolio.html', portfolio=portfolio_items)

@app.route('/add_portfolio', methods=['POST'])
@login_required
def add_portfolio():
    """Ajouter un actif au portefeuille"""
    try:
        symbol = request.form.get('symbol', '').upper()
        quantity = float(request.form.get('quantity', 0))
        purchase_price = float(request.form.get('purchase_price', 0))
        purchase_date = request.form.get('purchase_date', datetime.now().strftime('%Y-%m-%d'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO portfolio (user_id, symbol, quantity, purchase_price, purchase_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['user_id'], symbol, quantity, purchase_price, purchase_date))
        conn.commit()
        conn.close()
        
        flash(f'Actif {symbol} ajouté au portefeuille !', 'success')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
    
    return redirect(url_for('portfolio'))

@app.route('/trading')
@login_required
def trading():
    """Page de trading/investissement"""
    return render_template('trading.html')

@app.route('/trading_journal')
@login_required
def trading_journal():
    """Journal de trading"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM trading_journal 
        WHERE user_id = ? 
        ORDER BY date DESC
    ''', (session['user_id'],))
    trades = cursor.fetchall()
    
    conn.close()
    return render_template('trading_journal.html', trades=trades)

@app.route('/add_trade', methods=['POST'])
@login_required
def add_trade():
    """Ajouter un trade au journal"""
    try:
        symbol = request.form.get('symbol', '').upper()
        action = request.form.get('action')
        quantity = float(request.form.get('quantity', 0))
        price = float(request.form.get('price', 0))
        date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        notes = request.form.get('notes', '')
        profit_loss = float(request.form.get('profit_loss', 0))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trading_journal (user_id, symbol, action, quantity, price, date, notes, profit_loss)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], symbol, action, quantity, price, date, notes, profit_loss))
        conn.commit()
        conn.close()
        
        flash('Trade enregistré avec succès !', 'success')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
    
    return redirect(url_for('trading_journal'))

@app.route('/analysis')
@login_required
def analysis():
    """Page d'analyse financière"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Données pour les graphiques
    cursor.execute('''
        SELECT 
            strftime('%Y-%m', date) as month,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expenses
        FROM financial_transactions 
        WHERE user_id = ?
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    ''', (session['user_id'],))
    monthly_data = cursor.fetchall()
    
    # Dépenses par catégorie
    cursor.execute('''
        SELECT category, SUM(amount) as total
        FROM financial_transactions 
        WHERE user_id = ? AND type = 'expense'
        GROUP BY category
        ORDER BY total DESC
    ''', (session['user_id'],))
    category_data = cursor.fetchall()
    
    conn.close()
    return render_template('analysis.html', monthly_data=monthly_data, category_data=category_data)

@app.route('/reports')
@login_required
def reports():
    """Page des rapports"""
    return render_template('reports.html')

@app.route('/notifications')
@login_required
def notifications():
    """Page des notifications"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (session['user_id'],))
    notifs = cursor.fetchall()
    
    conn.close()
    return render_template('notifications.html', notifications=notifs)

@app.route('/mark_notification_read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """Marquer une notification comme lue"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE notifications 
            SET is_read = 1 
            WHERE id = ? AND user_id = ?
        ''', (notif_id, session['user_id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Page des paramètres"""
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Mettre à jour les paramètres
            for key, value in request.form.items():
                if key != 'csrf_token':
                    cursor.execute('''
                        INSERT OR REPLACE INTO settings (user_id, setting_key, setting_value)
                        VALUES (?, ?, ?)
                    ''', (session['user_id'], key, value))
            
            conn.commit()
            conn.close()
            flash('Paramètres mis à jour !', 'success')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
    
    # Récupérer les paramètres actuels
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings WHERE user_id = ?', (session['user_id'],))
    user_settings = cursor.fetchall()
    conn.close()
    
    return render_template('settings.html', settings=user_settings)

@app.route('/ai_assistant')
@login_required
def ai_assistant():
    """Assistant IA financier"""
    return render_template('ai_assistant.html')

@app.route('/history')
@login_required
def history():
    """Historique des transactions"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM financial_transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC
        LIMIT 100
    ''', (session['user_id'],))
    history = cursor.fetchall()
    
    conn.close()
    return render_template('history.html', history=history)

# API Routes
@app.route('/api/stats')
@login_required
def api_stats():
    """API pour les statistiques"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expenses,
            COUNT(*) as total_transactions
        FROM financial_transactions 
        WHERE user_id = ?
    ''', (session['user_id'],))
    stats = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'total_income': stats['total_income'] or 0,
        'total_expenses': stats['total_expenses'] or 0,
        'balance': (stats['total_income'] or 0) - (stats['total_expenses'] or 0),
        'total_transactions': stats['total_transactions']
    })

# Initialisation de la base de données au démarrage
with app.app_context():
    init_db()

# Gestion des erreurs
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return "Erreur interne du serveur", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
