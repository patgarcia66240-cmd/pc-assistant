#!/bin/bash

# Push vers le repo GitHub configur√©

echo "🚀 Push vers GitHub"
echo "=================="
echo ""
echo "Repository: https://github.com/patgarcia66240-cmd/pc-assistant"
echo ""

# V√©rifier que tout est commit√©
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Il y a des modifications non commit√©es"
    git status --short
    exit 1
fi

echo "📤 Pushing to GitHub..."
echo ""
echo "Options d'authentification:"
echo "1. Token GitHub (Personal Access Token)"
echo "2. GitHub CLI (si install√©)"
echo "3. SSH (si configur√©)"
echo ""
read -p "Choix (1, 2, ou 3): " auth_choice

case $auth_choice in
    1)
        echo ""
        echo "Pour cr√©er un token:"
        echo "1. Va sur: https://github.com/settings/tokens"
        echo "2. Clique 'Generate new token'"
        echo "3. S√©lectionne: repo (full control)"
        echo "4. Copie le token"
        echo ""
        read -p "Paste ton token: " token
        
        if [ -z "$token" ]; then
            echo "❌ Token vide"
            exit 1
        fi
        
        # Configure le credential helper
        git config --global credential.helper store
        
        # Push avec le token
        echo "https://patgarcia66240-cmd:${token}@github.com/patgarcia66240-cmd/pc-assistant.git" | \
            git credential approve
        
        git push -u origin main
        ;;
    2)
        if ! command -v gh &> /dev/null; then
            echo "❌ GitHub CLI pas install√©"
            echo "Installe avec: brew install gh (macOS) ou apt install gh (Linux)"
            exit 1
        fi
        
        echo "Login avec GitHub CLI..."
        gh auth login
        git push -u origin main
        ;;
    3)
        echo "Utilisant SSH..."
        git push -u origin main
        ;;
    *)
        echo "❌ Choix invalide"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Push r√©ussi!"
    echo ""
    echo "Repo GitHub: https://github.com/patgarcia66240-cmd/pc-assistant"
else
    echo "❌ Push √©chou√©"
    exit 1
fi
