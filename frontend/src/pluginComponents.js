import { lazy } from 'react'

// Associe le nom de composant déclaré par un plugin backend (manifest.json → frontend.component)
// au fichier réel dans components/. Vite résout ce glob une fois au build ; ajouter un nouveau
// plugin ne demande donc aucune modification ici tant que son composant vit dans ce dossier —
// seule la liste des plugins ACTIFS est dynamique (vient de GET /api/plugins, voir App.jsx).
const componentModules = import.meta.glob('./components/*.jsx')

export function lazyPluginComponent(componentName) {
  const path = `./components/${componentName}.jsx`
  const loader = componentModules[path]
  if (!loader) {
    console.error(`Plugin : composant "${componentName}" introuvable dans src/components/`)
    return null
  }
  return lazy(loader)
}
