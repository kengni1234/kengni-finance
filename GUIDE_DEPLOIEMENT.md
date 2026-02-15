# 🚀 Guide de Déploiement - Kengni Finance

## Déploiement sur Render.com (Gratuit)

### Étape 1 : Préparation du projet

1. **Assurez-vous que tous les fichiers sont présents** :
   - ✅ `app.py`
   - ✅ `init_db.py`
   - ✅ `requirements.txt`
   - ✅ `runtime.txt`
   - ✅ `render.yaml`
   - ✅ `Procfile`
   - ✅ Dossier `templates/` avec tous les fichiers HTML
   - ✅ Dossier `static/`

### Étape 2 : Pousser sur GitHub

```bash
# Initialiser git (si ce n'est pas déjà fait)
git init

# Ajouter tous les fichiers
git add .

# Créer le premier commit
git commit -m "Initial commit - Kengni Finance v2.1"

# Ajouter votre dépôt distant
git remote add origin https://github.com/votre-username/kengni-finance.git

# Pousser vers GitHub
git push -u origin main
```

### Étape 3 : Déployer sur Render

1. **Créer un compte** sur [https://render.com](https://render.com)

2. **Connecter GitHub** :
   - Cliquez sur "New +" → "Web Service"
   - Connectez votre compte GitHub
   - Sélectionnez le dépôt `kengni-finance`

3. **Configuration automatique** :
   Render détectera automatiquement `render.yaml` et configurera :
   - ✅ Build Command
   - ✅ Start Command
   - ✅ Variables d'environnement
   - ✅ Version Python 3.11.9

4. **Lancer le déploiement** :
   - Cliquez sur "Create Web Service"
   - Attendez 3-5 minutes pendant le build

5. **Vérifier le déploiement** :
   - Une fois terminé, vous verrez "Live" en vert
   - Cliquez sur le lien pour accéder à votre application

### Étape 4 : Configuration post-déploiement

1. **Variables d'environnement** (optionnel) :
   - Dans Render Dashboard → Votre service → Environment
   - Ajoutez des variables si nécessaire

2. **Vérifier la base de données** :
   - Connectez-vous à l'application
   - Créez un compte de test
   - Vérifiez que tout fonctionne

## Déploiement sur Heroku (Alternative)

### Prérequis
- Compte Heroku
- Heroku CLI installé

### Commandes

```bash
# Login Heroku
heroku login

# Créer l'application
heroku create kengni-finance

# Pousser le code
git push heroku main

# Ouvrir l'application
heroku open
```

## Déploiement sur Railway (Alternative)

1. Créer un compte sur [Railway.app](https://railway.app)
2. Nouveau projet → Deploy from GitHub
3. Sélectionner le dépôt
4. Railway détecte automatiquement la configuration
5. Déployer !

## Déploiement local pour développement

```bash
# Cloner le projet
git clone https://github.com/votre-username/kengni-finance.git
cd kengni-finance

# Créer l'environnement virtuel
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Initialiser la DB
python init_db.py

# Lancer l'application
python app.py
```

Accédez à `http://localhost:5000`

## Vérifications importantes

### ✅ Avant de déployer

- [ ] Tous les fichiers sont commités
- [ ] `runtime.txt` spécifie Python 3.11.9
- [ ] `requirements.txt` contient toutes les dépendances
- [ ] `render.yaml` est configuré correctement
- [ ] Templates HTML sont tous présents

### ✅ Après déploiement

- [ ] L'application se lance sans erreur
- [ ] La page d'accueil s'affiche
- [ ] Inscription fonctionne
- [ ] Connexion fonctionne
- [ ] Dashboard s'affiche correctement
- [ ] Ajout de transactions fonctionne

## Résolution des problèmes courants

### Erreur : "Application Error"
**Cause** : Erreur dans le code ou dépendances manquantes  
**Solution** : Vérifiez les logs dans Render Dashboard

### Erreur : "no such table: users"
**Cause** : Base de données non initialisée  
**Solution** : Assurez-vous que `init_db.py` s'exécute dans le buildCommand

### Erreur : Build échoue
**Cause** : Version Python ou dépendances incompatibles  
**Solution** : Vérifiez `runtime.txt` et `requirements.txt`

### Erreur : Page blanche
**Cause** : Templates manquants ou chemin incorrect  
**Solution** : Vérifiez que le dossier `templates/` est bien poussé

## Mise à jour de l'application

```bash
# Faire vos modifications
# ...

# Commit
git add .
git commit -m "Description des changements"

# Pousser vers GitHub
git push origin main

# Render redéploie automatiquement !
```

## Surveillance et maintenance

### Logs
- **Render** : Dashboard → Logs
- **Heroku** : `heroku logs --tail`

### Sauvegardes
- Téléchargez régulièrement `kengni_finance.db`
- Gardez des backups de votre code

### Mises à jour
- Mettez à jour les dépendances régulièrement
- Testez localement avant de déployer

## Support

En cas de problème :
1. Vérifiez les logs
2. Consultez la documentation Render
3. Ouvrez une issue sur GitHub

---

**Bonne chance avec votre déploiement ! 🚀**
