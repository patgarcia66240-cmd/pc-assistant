# Configurer Google Agenda pour ARIA

L'onglet Agenda est installé, mais il a besoin d'identifiants OAuth Google pour se connecter à ton vrai agenda. Ça prend 5 minutes, à faire une seule fois.

## 1. Créer un projet Google Cloud

1. Va sur https://console.cloud.google.com/
2. En haut, clique sur le sélecteur de projet → **Nouveau projet**
3. Nom au choix (ex: "ARIA PC Assistant") → **Créer**
4. Attends que le projet soit sélectionné (en haut de la page)

## 2. Activer l'API Google Calendar

1. Menu ☰ → **API et services** → **Bibliothèque**
2. Cherche "Google Calendar API"
3. Clique dessus → **Activer**

## 3. Configurer "Google Auth Platform" (l'écran de consentement)

Google a renommé et redesigné cette partie récemment — c'est maintenant sa propre section dans le menu, plus l'ancien "écran de consentement OAuth" caché dans API et services.

1. Menu ☰ → **Google Auth Platform**
2. Au premier lancement, un assistant "Prise en main" te demande le type d'utilisateur : choisis **Externe**
3. Renseigne le nom de l'appli (ex: "ARIA") et ton email (les seuls champs obligatoires) → continue sur les écrans suivants (rien d'autre à changer)
4. Une fois créé, va dans l'onglet **Audience** de Google Auth Platform → section **Utilisateurs test** → ajoute ton propre email Google (sinon Google refusera la connexion tant que l'appli n'est pas publiée publiquement)

## 4. Créer les identifiants OAuth

1. Toujours dans **Google Auth Platform**, va dans l'onglet **Clients**
2. **Créer un client**
3. Type d'application : **Application Web** (⚠️ pas "Application de bureau" — sinon le champ d'URI de redirection ci-dessous n'existe pas)
4. Nom au choix
5. Dans **URI de redirection autorisés**, ajoute exactement :
   ```
   http://127.0.0.1:8000/api/calendar/oauth/callback
   ```
6. **Créer**

Une fenêtre affiche ton **ID client** et ta **clé secrète** — garde-les sous la main pour l'étape suivante.

## 5. Mettre les identifiants dans ARIA

Dans `backend/.env` (crée le fichier à partir de `backend/.env.example` si tu ne l'as pas encore), ajoute ou complète ces deux lignes :

```
GOOGLE_CLIENT_ID=colle_ton_id_client_ici
GOOGLE_CLIENT_SECRET=colle_ta_clé_secrète_ici
```

La ligne `GOOGLE_CALENDAR_REDIRECT_URI` n'a rien à changer si l'appli tourne sur le port 8000 par défaut (c'est déjà la bonne valeur dans `.env.example`).

## 6. Se connecter

Redémarre le backend, ouvre l'onglet **Agenda** dans ARIA, clique sur **Se connecter à Google Agenda**. Une fenêtre Google s'ouvre pour autoriser l'accès — accepte, tu es redirigée automatiquement vers l'onglet Agenda avec tes événements.

*Note : les libellés exacts en français ("Google Auth Platform", "Audience", "Clients"...) peuvent varier légèrement selon la langue de ton compte Google — la structure (Prise en main → Audience → Clients) reste la même.*
