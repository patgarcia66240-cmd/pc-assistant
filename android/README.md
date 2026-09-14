# ARIA Phone Bridge (Android)

App compagnon Kotlin qui expose une passerelle WebSocket en réseau local : ARIA (le backend
FastAPI, plugin `backend/plugins/android_bridge/`) s'y connecte pour lire des informations du
téléphone — les contacts pour commencer, puis les infos appareil (batterie, stockage, RAM...).
Rien n'est jamais exposé sur Internet : la connexion se fait uniquement entre ce téléphone et
ce PC, sur le même réseau Wi-Fi.

## Fonctionnement

1. Ouvre l'app sur le téléphone, appuie sur **Démarrer** : un service de premier plan lance un
   serveur WebSocket (Ktor) sur le port affiché (8765 par défaut) et affiche l'adresse IP
   locale du téléphone ainsi qu'un jeton d'appairage généré aléatoirement.
2. Dans ARIA (onglet **Téléphone**), saisis cette IP, ce port et ce jeton, puis appaire.
3. Le backend ouvre une connexion WebSocket persistante et authentifiée par jeton ; il peut
   ensuite demander la liste des contacts ou les infos appareil à la demande.
4. Régénérer le jeton (bouton dans l'app) déconnecte immédiatement tout PC déjà appairé.

Aucune donnée n'est poussée automatiquement vers le PC : chaque capacité (contacts, infos
appareil) est lue seulement quand ARIA la demande explicitement.

## Sécurité

- Le jeton d'appairage est l'unique protection de la passerelle : toute personne qui le
  connaît et se trouve sur le même réseau Wi-Fi peut s'y connecter. Ne le partage jamais.
- Stocké chiffré sur le téléphone (`androidx.security.crypto.EncryptedSharedPreferences`),
  jamais en clair.
- Chaque capacité (contacts, etc.) nécessite sa propre permission Android, demandée à la
  volée depuis l'app — jamais accordée automatiquement à l'installation.
- Le serveur écoute sur toutes les interfaces (`0.0.0.0`) pour rester joignable en Wi-Fi, mais
  n'a aucune raison d'être exposé au-delà du réseau local (pas de redirection de port sur ta
  box internet).

## Étendre avec une nouvelle capacité

Chaque capacité (contacts, infos appareil, et demain SMS/notifications/localisation...) est un
fichier sous `app/src/main/kotlin/com/aria/phonebridge/gateway/capabilities/` qui implémente
`PhoneCapability` (id, libellé, permissions requises, `fetch()`). Il suffit de l'ajouter à la
liste `all` dans `CapabilityRegistry.kt` — le routage de l'action WebSocket (`get_<id>`), l'affichage dans
l'écran de permissions et l'entrée dans `get_capabilities` suivent automatiquement. Côté PC,
ajoute la route correspondante dans `backend/plugins/android_bridge/router.py`.

## Compiler

Ouvre le dossier `android/` dans Android Studio (Koala ou plus récent) — il proposera de créer
le wrapper Gradle au premier sync. Prérequis : JDK 17, Android SDK avec API 34 installée.

```powershell
# Depuis android/, une fois le wrapper généré par Android Studio :
.\gradlew.bat assembleDebug
```

L'APK debug est ensuite dans `app/build/outputs/apk/debug/`. Aucune clé de signature n'est
nécessaire pour un usage personnel en debug — installe-le directement via
`adb install app-debug.apk` ou le bouton Run d'Android Studio.
