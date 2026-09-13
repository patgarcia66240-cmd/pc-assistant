# Audit technique — PC Assistant / ARIA

**Dépôt :** `patgarcia66240-cmd/pc-assistant`
**Branche auditée :** `main`
**Date :** 13 septembre 2026
**Périmètre actuel :** Backend Python / FastAPI
**Statut :** Audit étape 1

---

## 1. Synthèse exécutive

Le backend de PC Assistant / ARIA possède une base architecturale saine et suffisamment modulaire pour continuer son évolution sans réécriture complète.

Les choix suivants sont pertinents et doivent être conservés :

* FastAPI ;
* SQLAlchemy async ;
* séparation routes / services ;
* système de plugins ;
* handlers de chat par plugin ;
* service centralisé de gestion des fichiers ;
* streaming IA ;
* lifecycle des plugins ;
* configuration centralisée.

Le principal problème actuel concerne la **sécurisation homogène de l'API HTTP**.

Certaines fonctionnalités sensibles — fichiers, système, gestion des plugins et historique du chat — ne sont pas uniformément protégées par l'authentification API.

### Évaluation globale

| Domaine               | État            | Priorité |
| --------------------- | --------------- | -------- |
| Architecture backend  | 🟢 Bonne        | —        |
| Plugin system         | 🟢 Bon          | —        |
| FileService           | 🟢 Solide       | —        |
| SQLite                | 🟢 Correct      | —        |
| Streaming IA          | 🟢 Bon          | —        |
| Multi-provider IA     | 🟢 Bonne base   | P2       |
| Sécurité API          | 🔴 À renforcer  | P0       |
| API fichiers          | 🔴 À protéger   | P0       |
| API système           | 🔴 À protéger   | P0       |
| Gestion plugins       | 🔴 À protéger   | P0       |
| Historique chat       | 🔴 À protéger   | P0       |
| Upload                | 🟠 À renforcer  | P1       |
| Opérations synchrones | 🟠 À optimiser  | P1       |
| Docker                | 🔴 À corriger   | P1       |
| Tests backend         | 🟠 À développer | P1       |
| Gestion secrets       | 🟠 À améliorer  | P2       |
| Mémoire IA            | 🟠 À clarifier  | P2       |
| Architecture ARIA 1.0 | 🟢 Bonne base   | P3       |

---

# 2. Architecture actuelle

L'architecture observée suit globalement cette organisation :

```text
backend/
│
├── main.py
├── config.py
├── db.py
├── security.py
├── plugin_loader.py
│
├── routes/
│   ├── chat.py
│   └── plugins.py
│
├── services/
│   ├── claude_service.py
│   ├── file_service.py
│   └── ...
│
├── models/
│   └── conversation.py
│
└── plugins/
    ├── calendar/
    ├── files/
    ├── image_generation/
    ├── messaging/
    ├── quiz/
    ├── saints/
    ├── system/
    └── ...
```

Cette organisation est cohérente avec une application locale évolutive.

Le système permet notamment de séparer :

```text
API
 ↓
Routes
 ↓
Services
 ↓
Plugins
 ↓
Services externes / système
```

Cette séparation doit être conservée.

---

# 3. 🔴 Sécurité API

## 3.1 Authentification

Le backend dispose de `require_api_key()`.

Le comportement actuel permet cependant de fonctionner sans authentification lorsque `API_AUTH_TOKEN` n'est pas configuré.

Ce fonctionnement est pratique en développement local mais ne doit pas devenir le comportement d'une version exposée au réseau.

### Recommandation

Définir deux modes :

```text
DEVELOPMENT
    authentification facultative

PRODUCTION / LAN
    authentification obligatoire
```

Pour une installation locale :

```text
127.0.0.1
```

devrait rester la valeur par défaut.

---

# 4. 🔴 API fichiers

Le plugin `files` fournit plusieurs opérations sensibles :

```text
GET  /api/files/list
GET  /api/files/content
GET  /api/files/raw
GET  /api/files/search
GET  /api/files/summary

POST /api/files/upload
POST /api/files/folder
POST /api/files/file
POST /api/files/rename

DELETE /api/files/delete
```

Ces routes ne sont pas actuellement protégées de manière uniforme par `require_api_key()`.

## Risque

Un client pouvant joindre le backend pourrait accéder aux fichiers autorisés par `FILES_ROOT`.

Cela comprend potentiellement :

* lecture ;
* création ;
* upload ;
* renommage ;
* suppression.

### Priorité

**P0 — correction recommandée avant exposition réseau.**

---

# 5. 🟢 FileService

Le `FileService` constitue une bonne base de sécurité.

## Protection des chemins

La résolution utilise `Path.resolve()` et vérifie que le chemin final reste dans une racine autorisée.

Cette approche est nettement préférable à une simple recherche de :

```text
../
```

dans la chaîne reçue.

## Racines protégées

Le service empêche les opérations destructives directes sur les racines configurées.

## Renommage

Le nouveau nom est traité comme un nom de fichier et ne doit pas permettre de créer un chemin arbitraire.

## Alias

Les dossiers Windows courants sont centralisés derrière des alias.

## SQLite

Les bases SQLite visualisées sont ouvertes en lecture seule.

### Conclusion

Cette partie est à conserver.

**Ne pas remplacer le FileService par une implémentation plus simple.**

---

# 6. 🔴 API système

Le plugin système expose notamment des informations concernant :

* le système ;
* les processus.

La liste des processus est une information sensible sur une API accessible au LAN.

### Recommandation

Protéger toutes les routes système avec :

```python
Depends(require_api_key)
```

---

# 7. 🔴 Gestion des plugins

Les opérations :

```text
POST /api/plugins/{plugin_id}/enable
POST /api/plugins/{plugin_id}/disable
```

modifient l'état persistant du système de plugins.

Elles doivent être considérées comme des opérations d'administration.

### Recommandation

Authentification obligatoire pour :

```text
enable
disable
```

Le listing des plugins peut rester accessible en lecture seule selon le mode de fonctionnement souhaité.

---

# 8. 🔴 Historique des conversations

Le backend conserve les conversations et messages dans SQLite.

La route d'historique permet de récupérer ces informations.

L'historique doit être considéré comme une donnée privée.

### Recommandation

Protéger :

```text
GET /api/chat/history
```

avec l'authentification API.

---

# 9. 🟠 Chat comme système d'action

Le chat n'est pas uniquement un générateur de texte.

Les handlers de plugins peuvent déclencher :

```text
fichiers
agenda
messagerie
système
images
services externes
```

Il faut donc considérer les plugins comme des **outils exécutables**.

Une future architecture devrait attribuer un niveau de permission à chaque outil.

```text
READ
WRITE
DESTRUCTIVE
EXTERNAL
```

Exemple :

```text
files.list       READ
files.read       READ

files.create     WRITE
files.rename     WRITE

files.delete     DESTRUCTIVE

calendar.read    READ
calendar.create  WRITE / EXTERNAL

messaging.send   EXTERNAL
```

---

# 10. 🟠 Confirmation des opérations destructives

Le service de fichiers documente correctement que la suppression est irréversible.

La suppression ne doit jamais être considérée comme une simple opération équivalente à une lecture.

Pour ARIA, il est préférable d'avoir :

```text
Utilisateur
   ↓
ARIA comprend la demande
   ↓
ARIA identifie précisément l'élément
   ↓
Confirmation explicite
   ↓
Tool DELETE
```

et non :

```text
Utilisateur
   ↓
LLM
   ↓
DELETE immédiat
```

Cette règle doit devenir une contrainte d'architecture.

---

# 11. 🟠 Upload

L'upload utilise une lecture par blocs.

C'est une bonne solution pour éviter de charger tout le fichier en mémoire.

Il manque toutefois une limite globale de taille.

### Recommandation

Ajouter :

```env
MAX_UPLOAD_SIZE_MB=100
```

ou une valeur configurable.

La taille doit être contrôlée pendant le streaming.

Il ne faut pas remplacer :

```python
await file.read(...)
```

par une lecture complète du fichier en mémoire.

---

# 12. 🟠 Opérations synchrones

Certaines opérations fichiers peuvent être coûteuses :

```text
os.walk()
Path.stat()
extraction Office
recherche récursive
lecture SQLite
```

Même si elles sont appelées depuis des routes `async`, elles restent synchrones.

Sur de gros volumes, cela peut bloquer temporairement l'event loop.

### Recommandation

Utiliser ponctuellement :

```python
await asyncio.to_thread(...)
```

pour les opérations lourdes.

Cela permet de conserver les services actuels sans les réécrire.

---

# 13. 🟢 Streaming IA

Le système de streaming constitue une bonne base.

Architecture :

```text
Frontend
   │
   ▼
POST /api/chat/stream
   │
   ▼
FastAPI
   │
   ├── asyncio.Queue
   │
   ▼
AI Service
   │
   ├── Anthropic
   ├── OpenAI
   ├── Gemini
   └── Qwen
```

Le résultat final est persisté.

Cette conception évite de perdre l'échange lorsque le streaming est utilisé.

Le format NDJSON est adapté au fonctionnement actuel.

---

# 14. 🟠 Service IA

Le fichier `claude_service.py` représente désormais plusieurs fournisseurs IA.

Le nom historique `ClaudeService` devient donc moins représentatif.

À terme :

```text
AIService
│
├── AnthropicProvider
├── OpenAIProvider
├── GeminiProvider
└── QwenProvider
```

avec une interface commune :

```python
class AIProvider(Protocol):
    async def generate(...):
        ...

    async def stream(...):
        ...

    def is_configured(...):
        ...
```

### Important

Cette refactorisation doit être progressive.

**Ne pas casser les plugins existants uniquement pour renommer une classe.**

---

# 15. 🔴 Mémoire conversationnelle

La persistance existe :

```text
Conversation
Message
```

mais la persistance et la mémoire envoyée au modèle sont deux problématiques différentes.

Il faut distinguer :

```text
SQLite
    ↓
historique persistant
```

et :

```text
AI context
    ↓
messages réellement envoyés au modèle
```

Pour ARIA 1.0 :

```text
Memory
│
├── Conversation history
│
├── Short-term context
│
├── User preferences
│
└── Long-term semantic memory
```

Cette distinction doit être définie avant de construire une mémoire IA plus avancée.

---

# 16. 🟢 Plugin Loader

Le système de plugins est l'un des meilleurs choix architecturaux du projet.

Les plugins peuvent contenir :

```text
manifest.json
router.py
chat_handler.py
lifecycle.py
frontend
```

Le chargement au démarrage est simple et prévisible.

Il évite la complexité du hot-loading.

### Règle recommandée

L'état des plugins doit être considéré comme figé pendant le runtime.

```text
START
  ↓
load plugins
  ↓
backend actif
  ↓
plugin state stable
  ↓
restart nécessaire pour modification
```

Cette règle doit être documentée.

---

# 17. 🟠 Messaging

Le backend peut lancer des processus externes :

```text
WhatsApp bridge
Telegram bot
```

Le lifecycle gère leur démarrage et leur arrêt.

Points positifs :

* suivi des processus ;
* arrêt lors du shutdown ;
* logs séparés ;
* utilisation de `sys.executable` ;
* limitation des redémarrages inutiles.

### Recommandation

ARIA doit uniquement arrêter les processus qu'elle a elle-même lancés.

---

# 18. 🔴 Docker

Les fichiers Docker doivent être réalignés avec la structure actuelle du dépôt.

Le `docker-compose.yml` fait actuellement référence à des chemins qui ne correspondent pas exactement aux Dockerfiles présents.

Cela peut provoquer des erreurs lors d'un déploiement propre depuis le dépôt.

### Priorité

**P1**

---

# 19. 🟢 Configuration

La configuration est centralisée et couvre notamment :

```text
AI
Database
Files
ARIA
CORS
API
TTS
Google
WhatsApp
Telegram
```

La centralisation doit être conservée.

Les chemins SQLite doivent rester indépendants du répertoire depuis lequel le processus a été lancé.

---

# 20. 🟠 Secrets

Les secrets sont actuellement gérés par `.env`.

C'est acceptable pour le développement.

Pour une application Windows distribuée :

```text
ARIA.exe
   │
   └── Secret Store
       ├── Windows Credential Manager
       ├── DPAPI
       └── stockage sécurisé Tauri
```

Les clés suivantes sont particulièrement sensibles :

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
QWEN_API_KEY
TELEGRAM_BOT_TOKEN
WHATSAPP_BRIDGE_SECRET
```

À terme, éviter de considérer `.env` comme le coffre-fort de l'application.

---

# 21. 🟠 Tests

Le backend doit progressivement disposer d'une vraie suite de tests.

Structure recommandée :

```text
tests/
├── test_security.py
├── test_file_service.py
├── test_plugins.py
├── test_chat.py
├── test_calendar.py
├── test_messaging.py
└── test_image_generation.py
```

## Tests critiques

### Sécurité fichiers

```text
../
../../
chemin absolu
symlink
racine protégée
rename avec séparateur
delete dossier
```

### API

```text
sans API key
mauvaise API key
bonne API key
```

### Plugins

```text
plugin inconnu
plugin désactivé
enable
disable
```

### Upload

```text
fichier normal
fichier trop gros
nom invalide
extension problématique
```

---

# 22. Architecture cible ARIA 1.0

L'architecture actuelle peut évoluer progressivement vers :

```text
                         ARIA
                          │
                    ┌─────▼─────┐
                    │ API Layer │
                    └─────┬─────┘
                          │
                    Authentication
                          │
                    ┌─────▼─────┐
                    │ ARIA Core │
                    └─────┬─────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
     Memory            AI Service         Tool Bus
        │                 │                 │
   ┌────┴────┐       ┌────┼────┐       ┌────┼──────────┐
   │ Short   │       │Anthropic│       │ Files        │
   │ Long    │       │OpenAI   │       │ Calendar     │
   │ Profile │       │Gemini   │       │ Messaging    │
   └─────────┘       │Qwen     │       │ System       │
                     └─────────┘       │ Images       │
                                       └───────────────┘
```

---

# 23. Bus d'outils

Une évolution importante serait de faire converger les plugins vers un système d'outils standardisé.

Exemple :

```python
Tool(
    name="files.search",
    permission="READ",
    confirmation=False,
)
```

ou :

```python
Tool(
    name="files.delete",
    permission="DESTRUCTIVE",
    confirmation=True,
)
```

ARIA pourrait alors connaître automatiquement :

```text
nom
description
permissions
confirmation nécessaire
paramètres
résultat
erreurs
```

Cela simplifierait fortement l'intégration future de nouveaux outils.

---

# 24. Journal d'audit

Pour les actions sensibles, ARIA devrait conserver un journal :

```text
timestamp
user
conversation_id
tool
action
target
result
confirmation
```

Exemple :

```text
2026-09-13 20:45
tool=files.delete
target=C:\Users\...\test.txt
confirmation=true
result=success
```

Cela devient particulièrement utile pour :

* débogage ;
* sécurité ;
* historique ;
* analyse des erreurs ;
* confiance utilisateur.

---

# 25. Plan d'action

## P0 — Sécurité immédiate

* [ ] Protéger `/api/files/*`
* [ ] Protéger `/api/system/*`
* [ ] Protéger enable/disable plugins
* [ ] Protéger `/api/chat/history`
* [ ] Définir clairement le mode local/LAN
* [ ] Vérifier CORS
* [ ] Vérifier l'écoute réseau

## P1 — Robustesse

* [ ] Ajouter `MAX_UPLOAD_SIZE_MB`
* [ ] Déporter les opérations fichiers lourdes
* [ ] Corriger Docker Compose
* [ ] Ajouter tests de sécurité
* [ ] Ajouter tests FileService
* [ ] Ajouter tests plugins

## P2 — Architecture

* [ ] Clarifier le contexte conversationnel
* [ ] Introduire progressivement `AIService`
* [ ] Formaliser les permissions outils
* [ ] Formaliser les confirmations
* [ ] Préparer le secret store
* [ ] Préparer le journal d'audit

## P3 — ARIA 1.0

* [ ] Mémoire court terme
* [ ] Mémoire longue durée
* [ ] Profil utilisateur
* [ ] Tool Bus
* [ ] Audit Log
* [ ] Packaging Windows autonome
* [ ] Mise à jour automatique
* [ ] Système de récupération après crash

---

# 26. Principes à conserver

ARIA doit continuer à respecter les principes suivants :

### Ne pas réécrire ce qui fonctionne

Les services existants doivent être améliorés progressivement.

### Séparer les responsabilités

```text
Route
  ↓
Service
  ↓
Provider / Tool
```

### Centraliser les opérations dangereuses

Les fichiers doivent continuer à passer par `FileService`.

### Ne jamais donner directement au LLM un accès arbitraire au système

Le modèle doit demander l'exécution d'un outil contrôlé.

### Toute opération destructive doit être identifiable

```text
DELETE
EXECUTE
SEND
MOVE
OVERWRITE
```

doivent être considérées comme des opérations particulières.

---

# 27. Verdict

Le projet **PC Assistant / ARIA dispose d'une bonne base technique**.

Il n'est pas nécessaire de repartir de zéro.

La priorité est de passer d'un prototype avancé à une application robuste en renforçant progressivement :

```text
Sécurité
   ↓
Robustesse
   ↓
Tests
   ↓
Architecture outils
   ↓
Mémoire
   ↓
Distribution
```

### Évaluation finale de l'étape 1

**Architecture : 🟢 8/10**<br>
**Modularité : 🟢 8/10**<br>
**FileService : 🟢 8,5/10**<br>
**IA : 🟢 8/10**<br>
**Sécurité : 🟠 5/10**<br>
**Tests : 🟠 5/10**<br>
**Industrialisation : 🟠 5/10**<br>
**Potentiel ARIA 1.0 : 🟢 élevé**

Le backend doit donc être **consolidé, pas réécrit**.

---

# 28. Étape suivante

L'étape 2 consiste à auditer le frontend React et sa communication avec le backend.

Périmètre :

```text
frontend/
│
├── App
├── Chat
├── Voice
├── Files
├── Messaging
├── Calendar
├── Image Generation
├── Plugins
└── API / State management
```

L'objectif sera ensuite de fusionner les résultats :

```text
audit backend
      +
audit frontend
      +
audit desktop
      +
audit WhatsApp
      +
audit Docker
      ↓
AUDIT GLOBAL ARIA
```

Ce document deviendra alors la référence technique du projet.
