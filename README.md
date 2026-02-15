# 💰 Kengni Finance v2.1

Application web complète de gestion financière personnelle développée avec Flask.

## 🚀 Fonctionnalités

- ✅ **Gestion des finances** - Suivi des revenus et dépenses
- 📊 **Analyse des données** - Visualisation graphique
- 💼 **Portfolio d'investissement** - Gestion de portefeuille
- 📝 **Journal de trading** - Historique des transactions
- 🔔 **Notifications** - Alertes personnalisées
- ⚙️ **Paramètres utilisateur** - Configuration personnalisée

## 📦 Technologies utilisées

- **Backend**: Flask 3.0.3, Python 3.11
- **Base de données**: SQLite3
- **Frontend**: Bootstrap 5.3, Chart.js
- **Déploiement**: Gunicorn, Render

## 🛠️ Installation locale

### Prérequis
- Python 3.11 ou supérieur
- pip (gestionnaire de paquets Python)

### Étapes d'installation

1. **Cloner le projet**
```bash
git clone https://github.com/kengni1234/kengni-finance.git
cd kengni-finance
```

2. **Créer un environnement virtuel**
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Initialiser la base de données**
```bash
python init_db.py
```

5. **Lancer l'application**
```bash
python app.py
```

L'application sera accessible sur `http://localhost:5000`

## 🌐 Déploiement sur Render

### Méthode automatique

1. Créez un compte sur [Render.com](https://render.com)
2. Connectez votre dépôt GitHub
3. Créez un nouveau "Web Service"
4. Render détectera automatiquement la configuration depuis `render.yaml`
5. Cliquez sur "Create Web Service"

### Configuration manuelle

Si vous préférez configurer manuellement :

- **Build Command**: 
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt && python init_db.py
  ```
- **Start Command**: 
  ```bash
  gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
  ```

## 📁 Structure du projet

```
kengni-finance/
├── app.py                 # Application Flask principale
├── init_db.py            # Script d'initialisation DB
├── requirements.txt      # Dépendances Python
├── runtime.txt          # Version Python
├── render.yaml          # Configuration Render
├── Procfile             # Configuration processus
├── templates/           # Templates HTML
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── finances.html
│   ├── portfolio.html
│   ├── trading.html
│   ├── trading_journal.html
│   ├── analysis.html
│   ├── reports.html
│   ├── notifications.html
│   ├── settings.html
│   ├── ai_assistant.html
│   └── history.html
└── static/              # Fichiers statiques
    ├── css/
    ├── js/
    ├── img/
    └── uploads/
```

## 🗄️ Base de données

L'application utilise SQLite avec les tables suivantes :

- **users** - Utilisateurs de l'application
- **financial_transactions** - Transactions financières
- **portfolio** - Actifs en portefeuille
- **trading_journal** - Journal des trades
- **notifications** - Notifications utilisateur
- **settings** - Paramètres utilisateur

## 🔒 Sécurité

- ⚠️ **Important**: Cette version utilise des mots de passe en clair
- 🔐 **Production**: Ajoutez le hachage des mots de passe (bcrypt/werkzeug)
- 🔑 **Secret Key**: Utilisez une clé secrète sécurisée en production

## 🐛 Résolution des problèmes

### Erreur "no such table: users"
```bash
python init_db.py
```

### Erreur de dépendances
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Erreur Python 3.14
Assurez-vous d'utiliser Python 3.11 (voir `runtime.txt`)

## 📝 TODO

- [ ] Ajouter le hachage des mots de passe
- [ ] Implémenter l'assistant IA
- [ ] Ajouter l'export de rapports PDF
- [ ] Intégrer des API financières réelles
- [ ] Ajouter l'authentification 2FA
- [ ] Implémenter les graphiques avancés

## 👨‍💻 Auteur

**Kengni**
- GitHub: [@kengni1234](https://github.com/kengni1234)

## 📄 Licence

Ce projet est sous licence MIT - voir le fichier LICENSE pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📧 Support

Pour toute question ou problème, ouvrez une issue sur GitHub.

---

**Version**: 2.1.0  
**Dernière mise à jour**: Février 2026
