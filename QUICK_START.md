# ⚡ Quick Start - Kengni Finance

Guide ultra-rapide pour démarrer en 5 minutes ! 🚀

## 🎯 Option 1 : Déploiement sur Render (Recommandé)

### En 3 étapes

1. **Extraire le ZIP**
   ```bash
   unzip kengni-finance-complet.zip
   cd kengni-finance-complet
   ```

2. **Pousser sur GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/VOTRE-USERNAME/kengni-finance.git
   git push -u origin main
   ```

3. **Déployer sur Render**
   - Aller sur [render.com](https://render.com)
   - New + → Web Service
   - Connecter GitHub
   - Sélectionner le dépôt
   - Cliquer "Create Web Service"
   - ✅ **TERMINÉ !**

## 🖥️ Option 2 : Test local

```bash
# 1. Extraire
unzip kengni-finance-complet.zip
cd kengni-finance-complet

# 2. Installer
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 3. Initialiser
python init_db.py

# 4. Lancer
python app.py
```

Ouvrir → `http://localhost:5000` ✅

## 📝 Première utilisation

1. **Créer un compte**
   - Aller sur la page d'accueil
   - Cliquer "S'inscrire"
   - Remplir le formulaire
   - ✅ Compte créé !

2. **Se connecter**
   - Email et mot de passe
   - ✅ Accès au dashboard !

3. **Ajouter une transaction**
   - Menu "Finances"
   - Cliquer "Nouvelle transaction"
   - Remplir le formulaire
   - ✅ Transaction enregistrée !

## 🔧 Si vous avez un problème

### ❌ Erreur de build sur Render
**Vérifier** : `runtime.txt` doit contenir `python-3.11.9`

### ❌ Page blanche après déploiement
**Vérifier** : Les templates sont bien dans le dossier `templates/`

### ❌ "no such table: users"
**Solution** : `python init_db.py`

## 📱 Accès à l'application

- **Local** : http://localhost:5000
- **Render** : https://votre-app.onrender.com

## 🎨 Fonctionnalités disponibles

✅ Gestion finances (revenus/dépenses)  
✅ Portfolio d'investissement  
✅ Journal de trading  
✅ Tableau de bord statistiques  
✅ Notifications  
✅ Paramètres utilisateur  

## 🚀 Mise à jour rapide

```bash
# Modifier vos fichiers
# ...

# Déployer
git add .
git commit -m "Update"
git push

# Render redéploie automatiquement !
```

## 💡 Astuces

- 🔒 **Sécurité** : Changez la SECRET_KEY en production
- 💾 **Sauvegarde** : Téléchargez régulièrement `kengni_finance.db`
- 📊 **Logs** : Vérifiez les logs sur le dashboard Render
- 🔄 **Auto-deploy** : Push sur GitHub = déploiement automatique

## 📚 Plus d'informations

- 📖 README complet : `README.md`
- 🚀 Guide déploiement : `GUIDE_DEPLOIEMENT.md`
- 🐛 Corrections erreurs : `GUIDE_CORRECTION_ERREURS.md`

---

**Besoin d'aide ?** Ouvrez une issue sur GitHub ! 💬
