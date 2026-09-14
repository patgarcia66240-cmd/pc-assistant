# Conventions pour Claude sur ce repo

## Versioning de la passerelle Android

À chaque push contenant un changement dans l'un de ces deux composants, incrémenter la
version de 0.1 (ex. 0.1.0 → 0.2.0) :

- `backend/plugins/android_bridge/manifest.json` — champ `"version"`.
- `android/app/build.gradle.kts` — `versionName` (incrémenter aussi `versionCode` de 1).

Les deux versions évoluent ensemble, même si un seul des deux côtés a changé dans le push.
