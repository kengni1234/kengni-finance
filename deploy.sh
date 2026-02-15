#!/bin/bash
# Script de déploiement rapide pour Kengni Finance

echo "🚀 Script de déploiement Kengni Finance"
echo "========================================"
echo ""

# Vérifier si on est dans un dépôt git
if [ ! -d .git ]; then
    echo "❌ Pas de dépôt Git détecté"
    echo "📝 Initialisation du dépôt..."
    git init
    echo "✅ Dépôt Git initialisé"
fi

# Afficher le statut
echo ""
echo "📊 Statut du dépôt:"
git status

# Demander confirmation
echo ""
read -p "Voulez-vous commiter et pousser les changements ? (o/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Oo]$ ]]; then
    # Ajouter tous les fichiers
    echo "📦 Ajout des fichiers..."
    git add .
    
    # Demander le message de commit
    echo ""
    read -p "Message de commit (ou appuyez sur Entrée pour le message par défaut): " commit_msg
    
    if [ -z "$commit_msg" ]; then
        commit_msg="Update: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # Commit
    echo "💾 Création du commit..."
    git commit -m "$commit_msg"
    
    # Vérifier si origin existe
    if ! git remote | grep -q origin; then
        echo ""
        read -p "URL du dépôt GitHub (ex: https://github.com/username/repo.git): " repo_url
        git remote add origin "$repo_url"
        echo "✅ Remote 'origin' ajouté"
    fi
    
    # Pousser vers GitHub
    echo "🚀 Push vers GitHub..."
    git push -u origin main || git push -u origin master
    
    echo ""
    echo "✅ Déploiement terminé !"
    echo "📱 Render va automatiquement redéployer votre application"
    echo "🌐 Vérifiez les logs sur https://dashboard.render.com"
else
    echo "❌ Déploiement annulé"
fi
