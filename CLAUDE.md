# Conventions pour Claude sur ce repo

## Numéro de version du projet

L'historique Git utilise un compteur de version global du projet, indépendant des champs
`"version"` des manifests de plugins (ceux-ci ont leur propre versionnage, ex. `messaging` à
`0.4.0` pendant que le projet en est à `1.0`). Chaque étape de travail significative se
termine par un commit dont le message est simplement le prochain chiffre, incrémenté de 0.1
(`0.1`, `0.2`, `0.3`, ... `0.9`, `1.0`, `1.1`, ...) — voir l'historique de `main` pour
l'exemple (commits `1978bc8` à `3a82009`).

Dernier numéro constaté avant cette session : **0.9** (commit `3a82009`, 13/09/2026).

Donc, à chaque push contenant un lot de travail terminé : faire un commit (ou nommer le
commit final du lot) avec pour message uniquement le prochain numéro, en continuant la
séquence — le suivant est **1.0**.
