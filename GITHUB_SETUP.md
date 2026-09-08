# 🚀 Setup GitHub pour PC Assistant

## Prérequis

1. **Compte GitHub** - https://github.com/signup
2. **Token d'accès** (pour HTTPS) - https://github.com/settings/tokens
3. **Clé SSH** (pour SSH) - https://github.com/settings/keys

## Option 1 : Script Automatisé (Recommandé) ⭐

```bash
cd /home/claude/pc-assistant
./setup-github.sh
```

Le script va :
1. ✓ Vérifier Git est installé
2. ✓ Vérifier l'état du repository
3. ✓ Demander tes infos GitHub
4. ✓ Configurer HTTPS ou SSH
5. ✓ Tester la connexion
6. ✓ Pousser automatiquement

## Option 2 : Manuel (Si le script ne fonctionne pas)

### 1. Créer le repository sur GitHub

1. Va sur https://github.com/new
2. **Repository name** : `pc-assistant`
3. **Description** : "ARIA - AI-powered PC Assistant"
4. **Public** : Oui
5. **Initialize** : Non (on a déjà le repo)
6. Clique **Create repository**

### 2. Configuration locale

```bash
cd /home/claude/pc-assistant

# Renommer la branche en main
git branch -M main

# Ajouter le remote (remplace USERNAME par ton username GitHub)
git remote add origin https://github.com/USERNAME/pc-assistant.git

# Configurer les credentials
git config user.email "ton.email@example.com"
git config user.name "Ton Nom"

# Pousser
git push -u origin main
```

### 3. Autentification HTTPS

**Option A : GitHub Token (recommandé)**
```bash
# Générer un token : https://github.com/settings/tokens
# Permissions : repo (full control)

git config --global credential.helper store
git push origin main
# Quand demandé : username = TON_USERNAME, password = TON_TOKEN
```

**Option B : SSH**
```bash
# Générer une clé SSH
ssh-keygen -t ed25519 -C "ton.email@example.com"

# Ajouter à GitHub : https://github.com/settings/keys
cat ~/.ssh/id_ed25519.pub

# Changer l'URL remote
git remote remove origin
git remote add origin git@github.com:USERNAME/pc-assistant.git

# Pousser
git push -u origin main
```

## Vérification

```bash
git remote -v
git log --oneline -5
git branch -a
```

## Après le push

1. Repo : `https://github.com/USERNAME/pc-assistant`
2. Continuer le développement avec branches feature
3. Faire des Pull Requests

Besoin d'aide ? Regarde `docs/GIT_WORKFLOW.md` ! 📚
