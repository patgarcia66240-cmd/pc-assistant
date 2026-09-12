# Etat de l'application ARIA

Derniere mise a jour : 11 septembre 2026

## Synthese

ARIA est une application d'assistance personnelle pour PC composee de trois couches :

- une API locale FastAPI en Python ;
- une interface React construite avec Vite ;
- une application de bureau Tauri en Rust.

L'application est actuellement fonctionnelle en developpement. Les tests automatises du backend,
la compilation du frontend et la verification Rust passent. Plusieurs integrations externes
restent toutefois dependantes de cles API ou d'une configuration OAuth locale. L'architecture
prend desormais en charge des plugins backend et frontend activables par l'utilisatrice.

## Etat global

| Domaine | Etat | Commentaire |
| --- | --- | --- |
| Backend FastAPI | Operationnel | 22 tests API passent |
| Frontend React | Operationnel | Build Vite de production reussi |
| Application Tauri | Operationnelle en developpement | `cargo check` reussi |
| Chat Claude | Conditionnel | Necessite `CLAUDE_API_KEY` |
| Reponses locales | Operationnel | Heure, date, meteo, villes, marches et informations systeme |
| Google Agenda | Conditionnel | Necessite les identifiants OAuth Google |
| Systeme de plugins | Operationnel | Decouverte, activation et onglets dynamiques |
| Voix locale Kokoro | Operationnelle | Moteur ONNX local, voix francaise `ff_siwis` |
| Voix locale Piper | Operationnelle | Moteur ONNX local rapide, voix francaise `fr_FR-siwis-medium` |
| Persistance SQLite | Operationnelle | Conversations, messages et cache des villes |
| Docker | A corriger | Les chemins des Dockerfiles dans Compose ne correspondent pas aux fichiers presents |
| Distribution desktop | Non finalisee | Le backend Python n'est pas encore package en sidecar |

## Versions et technologies

### Backend

- Python 3.11 ou superieur
- FastAPI
- Uvicorn
- SQLAlchemy asynchrone
- SQLite avec `aiosqlite`
- Anthropic SDK
- HTTPX
- psutil
- Kokoro ONNX 0.6 avec acceleration CUDA quand un GPU NVIDIA compatible est disponible
- Piper TTS 1.8
- ONNX Runtime et SoundFile

### Frontend

- React 18
- Vite 8
- Tailwind CSS 3
- Axios est installe, mais les composants utilisent principalement `fetch`

### Desktop

- Tauri 1
- Rust edition 2021
- WebView locale chargeant le frontend Vite en developpement ou son build en production

## Fonctionnalites disponibles

### Chat

- conversation avec Claude lorsque la cle Anthropic est configuree ;
- reponses locales sans Claude pour plusieurs demandes ;
- historique des conversations en base ;
- informations d'heure et de date ;
- heures mondiales ;
- meteo et recherche de villes ;
- fiches de villes avec mise en cache SQLite ;
- informations financieres et marches selon les fournisseurs configures.

### Assistant vocal

- onglet dedie dans l'interface ;
- interface de commande vocale integree au frontend ;
- synthese locale avec Kokoro ONNX et la voix francaise `ff_siwis` ;
- synthese locale rapide avec Piper et la voix francaise `fr_FR-siwis-medium` ;
- repli automatique sur la synthese vocale du navigateur si le moteur local est indisponible ;
- choix du moteur entre Kokoro, Piper et le navigateur ;
- selection automatique prioritaire des voix francaises `Natural`, `Enhanced`, `Premium` ou
  `Online` disponibles sur le systeme pour le mode navigateur ;
- choix manuel de la voix francaise du navigateur depuis les parametres ;
- debit vocal reglable et ralenti par defaut a `0.92x` pour un rendu moins robotique ;
- streaming active par defaut : la premiere phrase est affichee et prononcee pendant que Claude
  genere encore la suite, avec possibilite de le desactiver dans les parametres ;
- choix du moteur, de la voix et du debit conserves dans le stockage local du navigateur.

### Pointeur main

- curseur global en suivi absolu du bout de l'index, avec clic par pincement entre le pouce et
  un doigt configurable ;
- compensation de distance, stabilisation des mouvements et attraction des boutons du menu ;
- plugin frontend **Calibrage pointeur** avec assistant en quatre points ;
- calibration enregistree dans le stockage local du navigateur et appliquee immediatement ;
- panneau d'essai pour la resolution camera et les seuils MediaPipe de detection, presence et suivi ;
- reinitialisation disponible depuis l'onglet du plugin pour revenir au reglage automatique.

### Agenda

- connexion OAuth a Google Agenda ;
- affichage des evenements ;
- creation, modification et suppression d'evenements ;
- deconnexion du compte Google ;
- retour automatique sur l'onglet Agenda apres le callback OAuth.

### Systeme

- informations CPU, memoire et disques ;
- liste des processus ;
- rafraichissement depuis l'interface.

### Fichiers

- liste des emplacements accessibles ;
- navigation dans les dossiers sous `FILES_ROOT` ;
- televersement limite a la racine de fichiers configuree.

### Saint du jour

- saint ou fete du calendrier ;
- evenements et journees internationales associes ;
- donnees locales de date et de localisation.

### Personnalisation

- nom, avatar et langue d'ARIA configurables ;
- persistance de cette configuration dans l'environnement backend ;
- bouton **Parametres** disponible dans l'en-tete de toute l'application ;
- modale centralisee pour le pays, la ville, le fournisseur IA, le modele et le moteur TTS ;
- geocodage de la ville lors de l'enregistrement pour actualiser ses coordonnees ;
- application immediate du modele Anthropic et des preferences vocales.

### Plugins

ARIA dispose d'un systeme de plugins local. Chaque plugin est installe dans
`backend/plugins/<id>/` et contient :

- un `manifest.json` avec son identifiant, son nom, sa version et, si necessaire, sa route API
  ou la declaration de son interface ;
- un `router.py` exposant le routeur FastAPI uniquement lorsque le plugin fournit une API.

Au demarrage, le chargeur :

1. decouvre les dossiers de plugins ;
2. lit leur manifeste ;
3. consulte leur etat active ou desactive ;
4. importe et monte le routeur de chaque plugin actif qui en declare un ;
5. signale dans les journaux les manifestes invalides et les erreurs de chargement.

L'interface comporte un onglet **Plugins** qui liste les extensions installees, leur version et
leur etat, puis permet de les activer ou de les desactiver. Le changement est persiste
immediatement, mais le backend doit etre redemarre pour monter ou retirer effectivement les routes.

Les onglets fournis par les plugins sont construits dynamiquement depuis les informations
`frontend` du manifeste. Le composant React correspondant est charge a la demande avec
`import.meta.glob` et `React.lazy`.

Plugins integres actuellement :

| Plugin | Type | Route | Interface | Actif par defaut |
| --- | --- | --- | --- | --- |
| `calendar` | Backend et frontend | `/api/calendar` | Onglet Agenda | Oui |
| `saints` | Backend et frontend | `/api/saints` | Onglet Saint du jour | Oui |
| `city_details` | Backend uniquement | `/api/city-details` | Utilise par le chat | Oui |
| `kokoro_tts` | Backend uniquement | `/api/tts` | Utilise par l'assistant vocal | Oui |
| `piper_tts` | Backend uniquement | `/api/piper-tts` | Utilise par l'assistant vocal | Oui |
| `pointer_calibration` | Frontend uniquement | Aucune | Onglet Calibrage pointeur | Oui |
| `quiz` | Backend et frontend | `/api/quiz` | Onglet Quiz | Oui |
| `image_generation` | Backend et frontend | `/api/images` | Onglet Images IA | Oui |

Le plugin `quiz` demande a ARIA de produire un tableau JSON valide, puis enregistre chaque
question dans `quiz_questions` avec le theme, le type (`qcm` ou `true_false`), la difficulte
(`facile`, `moyen` ou `difficile`), les choix, la bonne reponse, l'explication et le nombre
d'utilisations. Un quiz stocke peut ensuite etre rejoue sans nouvel appel a l'IA. L'ordre des
questions et des choix est remelange au debut de chaque partie. A la fin, le joueur peut demander
une nouvelle serie generee par ARIA, rejouer la serie actuelle ou revenir au choix du quiz. Chaque
serie generee est conservee separement dans `saved_quizzes` et reste accessible depuis la
bibliotheque "Mes quiz sauvegardes", y compris les anciennes series regroupees retroactivement.
Apres chaque reponse, la correction reste affichee deux secondes avant le passage automatique a
la question suivante ou au score final. Le bouton "Oui, nouvelle serie" cherche d'abord un quiz
sauvegarde avec la meme configuration et ne demande une nouvelle generation a ARIA que si aucun
quiz correspondant n'existe.

Sur WhatsApp, un numero autorise doit envoyer `@aria start` pour ouvrir une session de dialogue.
ARIA traite ensuite ses messages jusqu'a `@aria stop`. L'etat actif est persiste dans
`backend/data/whatsapp_aria_sessions.json` et reste donc valable apres un redemarrage.
Le plugin WhatsApp fournit aussi un onglet dedie avec menu, formulaire d'envoi par contact,
etat de connexion et consultation des conversations. Les messages envoyes depuis ce formulaire
sont ajoutes a l'historique SQLite de la conversation.
Chaque conversation dispose d'un composeur en bas de l'historique. Le bouton trombone permet
d'envoyer une image, un document ou un fichier audio (10 Mo maximum) avec les formats natifs
WhatsApp. Ces fichiers sont conserves dans SQLite, affiches ou lisibles dans la conversation,
et restent telechargeables.
Le plugin Messagerie permet de deconnecter chaque canal avec confirmation. WhatsApp est
dissocie et propose ensuite un nouveau QR code. Pour Telegram, le processus du bot est arrete
et son token local est efface, sans supprimer le bot du compte Telegram.
Dans le Chat, les commandes `WhatsApp`, `ouvre WhatsApp` ou `ouvre le plugin WhatsApp` ouvrent
directement cet onglet sans appel a l'IA.

Le carnet de contacts WhatsApp/Telegram est stocke dans la table SQLite `messaging_contacts`.
Lors de la premiere lecture, l'ancien fichier `backend/data/messaging_contacts.json` est importe
automatiquement puis conserve comme sauvegarde `messaging_contacts.migrated.json`.

Le chat, l'assistant vocal, le moniteur systeme, les fichiers et la configuration restent des
fonctionnalites centrales toujours chargees.
Les parametres IA proposent Anthropic, OpenAI, Google Gemini et Qwen. Chaque fournisseur garde
son propre modele et sa propre cle API locale. Les cles ne sont jamais renvoyees au frontend.
Le Chat et la generation de quiz utilisent le fournisseur selectionne, avec streaming des
reponses. L'assistant Google Agenda conserve Anthropic pour ses appels d'outils specialises.
Le plugin Images IA utilise la cle OpenAI configuree et le modele `gpt-image-2`. Il propose
les formats carre, paysage et portrait, trois niveaux de qualite, une galerie SQLite locale,
le telechargement et la suppression des images generees.

## API disponible

L'API expose notamment :

- `GET /` et `GET /health` ;
- `POST /api/chat/` et `GET /api/chat/history` ;
- `POST /api/chat/stream` pour les reponses progressives au format NDJSON ;
- `GET /api/system/info` et `GET /api/system/processes` ;
- `GET /api/files/locations`, `GET /api/files/list` et `POST /api/files/upload` ;
- `GET /api/config/aria` et `PUT /api/config/aria` ;
- `GET /api/config/preferences` et `PUT /api/config/preferences` ;
- `GET /api/plugins` ;
- `POST /api/plugins/{plugin_id}/enable` et
  `POST /api/plugins/{plugin_id}/disable` ;
- `GET /api/tts/status` et `POST /api/tts/synthesize` ;
- `GET /api/piper-tts/status` et `POST /api/piper-tts/synthesize` ;
- `GET /api/saints/today` ;
- les routes de statut et de rafraichissement des fiches de villes ;
- les routes OAuth et CRUD de `/api/calendar`.

La documentation interactive est disponible sur `http://localhost:8000/docs` lorsque le backend
est demarre.

## Donnees et configuration

La base SQLite principale est, par defaut, `backend/pc_assistant.db`. Son chemin est transforme en
chemin absolu par le backend afin d'eviter la creation de plusieurs bases selon le dossier de
lancement.

Tables applicatives confirmees :

- `conversations` ;
- `messages` ;
- `city_info_cache`.

L'etat d'activation des plugins est stocke dans `backend/data/plugins_state.json`. Le fichier est
cree automatiquement avec les valeurs `enabled_by_default` des manifestes lors du premier
chargement. Il ne contient pas les donnees propres aux plugins et est ignore par Git.

Variables importantes :

- `CLAUDE_API_KEY` et `CLAUDE_MODEL` ;
- `TWELVE_DATA_API_KEY`, `EODHD_API_KEY` et `METAL_SENTINEL_API_KEY` ;
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` et `GOOGLE_CALENDAR_REDIRECT_URI` ;
- `DATABASE_URL` et `FILES_ROOT` ;
- `ARIA_NAME`, `ARIA_AVATAR` et `ARIA_LANGUAGE` ;
- `USER_COUNTRY`, `USER_CITY_LABEL`, `USER_LATITUDE` et `USER_LONGITUDE` ;
- `AI_PROVIDER` et `CLAUDE_MODEL` ;
- `KOKORO_MODEL_PATH`, `KOKORO_VOICES_PATH` et `KOKORO_VOICE` ;
- `PIPER_MODEL_PATH`, `PIPER_CONFIG_PATH` et `PIPER_USE_CUDA` ;
- `API_HOST`, `API_PORT`, `CORS_ORIGINS` et `API_AUTH_TOKEN`.

Les fichiers du modele vocal sont stockes localement dans `backend/data/tts/` :

- `kokoro-v1.0.onnx` : environ 310 Mo ;
- `voices-v1.0.bin` : environ 27 Mo.
- `fr_FR-siwis-medium.onnx` : environ 63 Mo ;
- `fr_FR-siwis-medium.onnx.json` : configuration de la voix Piper.

Ils sont ignores par Git. Le texte envoye aux routes TTS reste sur la machine. Kokoro
fonctionne avec `kokoro-onnx`, choisi a la place du paquet `kokoro` classique car le venv actuel
utilise Python 3.13. La version 0.9.4 du paquet classique exige Python inferieur a 3.13, tandis que
`kokoro-onnx` 0.6.1 prend en charge Python 3.13 sous Windows. Sur Windows, l'extra CUDA/cuDNN
d'ONNX Runtime est installe explicitement pour utiliser le GPU NVIDIA sans dependre d'une
installation CUDA globale.

Le backend ecoute par defaut uniquement sur `127.0.0.1:8000`. C'est le comportement recommande
tant que les routes locales de fichiers et de systeme ne sont pas toutes authentifiees.

## Verification du 11 septembre 2026

| Verification | Resultat |
| --- | --- |
| `python -m pytest tests/test_api.py -q` | 26 tests reussis, 1 avertissement de deprecation dans Starlette |
| `npm run build` dans `frontend` | Reussi avec Vite 8.2.2, avec 5 avertissements d'import dynamique inefficace |
| `cargo check` dans `desktop` | Reussi |
| Synthese Kokoro reelle | WAV valide de 157 898 octets, en-tete `RIFF`, voix `ff_siwis` |

Le build frontend produit environ 272 Ko de JavaScript repartis entre le coeur et les plugins,
ainsi que 40 Ko de CSS avant compression. `CalendarAgenda` et `SaintOfDay` sont bien generes dans
des chunks separes.

## Points d'attention

1. **Versions incoherentes** : les manifests et l'API annoncent encore `0.1.0`, alors que le
   dernier commit est nomme `0.3`.
2. **Docker Compose non fonctionnel tel quel** : `docker-compose.yml` cherche
   `backend/Dockerfile` et `frontend/Dockerfile`, mais les fichiers presents sont
   `Dockerfile.backend` et `Dockerfile.frontend` a la racine. Leur contexte de copie correspond
   actuellement a la racine du depot.
3. **Script de production incomplet** : `start-production.sh` appelle Gunicorn, absent des
   dependances declarees, et utilise une syntaxe WSGI qui n'est pas adaptee directement a
   FastAPI/ASGI.
4. **Scripts shell peu adaptes a Windows** : les scripts `.sh` utilisent Bash et l'activation
   Unix du venv, alors que le poste de developpement actuel est Windows.
5. **Authentification frontend a completer** : si `API_AUTH_TOKEN` est defini, le frontend
   n'envoie actuellement pas l'en-tete `X-API-Key` aux routes protegees de configuration et
   d'agenda.
6. **Protection partielle de l'API** : l'authentification est optionnelle et ne couvre pas toutes
   les routes sensibles, notamment les informations systeme et les fichiers.
7. **Distribution Tauri non autonome** : l'application desktop lance directement le Python du
   venv local. Elle depend donc de `backend/venv` et n'est pas encore distribuable telle quelle
   sur une autre machine.
8. **Couverture de tests limitee** : le backend possede une suite API de base, mais aucun test
   automatise frontend ou desktop n'est present. La decouverte, les manifestes, la persistance
   d'etat et les routes d'activation des plugins n'ont pas encore de tests dedies.
9. **Fichier backend duplique** : `backend/routes/chat-1.py` semble etre une ancienne copie de la
   route de chat et n'est pas branche dans l'application.
10. **Documentation a actualiser** : le README ne mentionne pas encore l'Agenda, le Saint du jour,
    les fournisseurs de donnees financieres, le systeme de plugins ni les nouvelles variables
    d'environnement.
11. **Redemarrage requis pour les plugins** : l'activation et la desactivation ne modifient pas
    les routeurs FastAPI a chaud. Le panneau l'indique, mais ARIA doit etre redemarree avant que le
    changement soit effectif.
12. **Gestion des plugins non protegee** : les routes d'activation et de desactivation ne
    dependent actuellement pas de `require_api_key`. Elles doivent rester accessibles uniquement
    en local tant qu'une protection n'est pas ajoutee.
13. **Glob frontend trop large** : `pluginComponents.js` recherche tous les composants JSX. Vite
    avertit donc que cinq composants centraux, deja importes statiquement, sont aussi candidats a
    un import dynamique inefficace. Le build reussit et les deux composants de plugins sont bien
    separes, mais un dossier reserve aux composants de plugins supprimerait ces avertissements.
14. **Taille du modele vocal** : les fichiers Kokoro occupent environ 337 Mo. Ils ne sont pas
    inclus dans Git et devront etre distribues ou telecharges lors d'une future installation sur
    une autre machine.

## Etat Git au moment du rapport

- Branche : `main`
- Dernier commit observe : `863881c` (`0.3`, 10 septembre 2026)
- Modifications locales deja presentes :
  - `backend/main.py`
  - `backend/plugin_loader.py`
  - `backend/plugins/`
  - `backend/routes/plugins.py`
  - anciens routeurs de `calendar`, `city_details` et `saints` remplaces par des indications de
    migration
  - `frontend/index.html`
  - `frontend/src/App.jsx`
  - `frontend/src/components/ChatComponent.jsx`
  - `frontend/src/components/PluginsPanel.jsx`
  - `frontend/src/pluginComponents.js`
  - `frontend/src/assets/`

Ces modifications locales n'ont pas ete annulees ni modifiees lors de la creation de ce rapport.

## Priorites recommandees

1. Aligner les numeros de version sur la version reelle du projet.
2. Corriger et valider le lancement Docker.
3. Corriger le demarrage de production ASGI.
4. Finaliser la strategie d'authentification locale et son integration frontend.
5. Packager le backend comme sidecar Tauri pour obtenir une application desktop autonome.
6. Ajouter des tests frontend sur les parcours critiques et des tests de l'integration Agenda.
7. Ajouter des tests dedies au chargeur et aux routes de gestion des plugins.
8. Proteger les changements d'etat des plugins avec la strategie d'authentification locale.
9. Mettre a jour le README avec les fonctionnalites, les plugins et la configuration actuels.

## Demarrage en developpement

Backend :

```powershell
Set-Location backend
.\venv\Scripts\python.exe main.py
```

Frontend, dans un second terminal :

```powershell
Set-Location frontend
npm run dev
```

Acces :

- application : `http://localhost:5173`
- API : `http://localhost:8000`
- documentation API : `http://localhost:8000/docs`
