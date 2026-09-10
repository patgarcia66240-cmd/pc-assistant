// Bloc de base d'un "skeleton" de chargement : gris uni + reflet lumineux qui balaie de
// gauche à droite (animation "shimmer" définie dans tailwind.config.js), pour un rendu plus
// soigné qu'un simple animate-pulse plat. Partagé par tous les onglets (Agenda, Système,
// Chat, Saint du jour, Fichiers) pour une même identité visuelle de chargement dans toute
// l'appli — `className` porte la forme (taille, arrondi) propre à chaque usage.
export function SkeletonBlock({ className = '' }) {
  return (
    <div className={`relative overflow-hidden rounded-md bg-gray-700/50 ${className}`} aria-hidden="true">
      <span className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent" />
    </div>
  )
}
