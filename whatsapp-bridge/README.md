# Pont WhatsApp pour ARIA

Service Node.js séparé du backend Python, qui connecte ARIA à WhatsApp via **Baileys**, une
bibliothèque non officielle (elle se connecte comme WhatsApp Web, sans passer par l'API
Business payante de Meta). Non affiliée à WhatsApp/Meta — voir la note sur les risques plus bas.

## Ce que ça fait

- Se lie à un numéro WhatsApp dédié (recommandé : pas ton numéro personnel habituel) via un QR
  code, une seule fois.
- Relaie chaque message reçu (conversations privées seulement, pas les groupes) au backend ARIA,
  qui répond comme dans le chat normal de l'app (heure/météo, bourse, rois de France, agenda IA,
  Claude en dernier recours).
- Poste la réponse d'ARIA sur WhatsApp.
- **N'accepte de répondre qu'aux numéros listés dans `WHATSAPP_ALLOWED_NUMBERS` (backend/.env)** —
  vide par défaut, donc rien ne se passe tant que tu n'y as pas ajouté au moins un numéro.

## Installation (une fois)

```bash
cd whatsapp-bridge
npm install
cp .env.example .env   # sauf si .env existe déjà (déployé avec le secret pré-rempli)
```

Vérifie que `WHATSAPP_BRIDGE_SECRET` dans `whatsapp-bridge/.env` est **exactement identique** à
celui de `backend/.env` (déjà fait si les deux fichiers ont été déployés ensemble).

Dans `backend/.env`, ajoute le numéro WhatsApp dédié à `WHATSAPP_ALLOWED_NUMBERS` (format
international sans "+", ex: `33612345678` — plusieurs numéros séparés par des virgules), puis
active le plugin dans l'onglet **Plugins** de l'app (ou `POST /api/plugins/whatsapp/enable`) et
redémarre le backend.

## Démarrage

```bash
cd whatsapp-bridge
npm start
```

La première fois, un QR code s'affiche dans le terminal : ouvre WhatsApp sur le téléphone dédié
à ARIA → **Appareils liés** → **Lier un appareil** → scanne le code. Une fois lié, la session est
sauvegardée dans `auth/` : plus besoin de rescanner aux démarrages suivants, sauf si tu
supprimes ce dossier ou que WhatsApp invalide la session (le terminal l'indique clairement).

Le backend ARIA (`python main.py`, port 8000 par défaut) doit tourner en même temps pour que les
messages soient traités.

## Vérifier que ça marche

`GET http://localhost:8000/api/whatsapp/status` (depuis l'app ou un navigateur, avec l'en-tête
`X-API-Key` si `API_AUTH_TOKEN` est configuré) renvoie l'état du pont (`bridge_reachable`,
`connected`).

## À savoir avant d'utiliser

- **Bibliothèque non officielle** : pas couverte par les CGU de WhatsApp. Un usage personnel
  normal (pas d'envoi en masse, pas de spam) réduit fortement le risque, mais il n'est pas nul —
  d'où la recommandation d'un numéro dédié plutôt que ton numéro personnel.
- **Le dossier `auth/` contient les identifiants de session** (équivalent d'un mot de passe) —
  ne jamais le commit, le partager, ni l'envoyer où que ce soit (déjà exclu par `.gitignore`).
- Si WhatsApp change son protocole, la librairie peut temporairement cesser de fonctionner
  jusqu'à une mise à jour — normal pour une lib non officielle, pas un bug de ce pont.
