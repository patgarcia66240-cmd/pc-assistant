import { useEffect, useState } from 'react'

function StatusBadge({ enabled, loadError }) {
  if (loadError) {
    return <span className="rounded-full bg-red-900/60 px-2.5 py-0.5 text-xs font-medium text-red-200">Erreur</span>
  }
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${enabled ? 'bg-emerald-900/60 text-emerald-200' : 'bg-gray-700 text-gray-400'}`}>
      {enabled ? 'Activé' : 'Désactivé'}
    </span>
  )
}

export default function PluginsPanel({ onChanged } = {}) {
  const [plugins, setPlugins] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(null)
  const [restartNotice, setRestartNotice] = useState(false)

  function loadPlugins() {
    setLoading(true)
    setError(null)
    fetch('/api/plugins')
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json()
      })
      .then(setPlugins)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(loadPlugins, [])

  async function toggle(plugin) {
    setPending(plugin.id)
    try {
      const action = plugin.enabled ? 'disable' : 'enable'
      const response = await fetch(`/api/plugins/${plugin.id}/${action}`, { method: 'POST' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      setRestartNotice(true)
      loadPlugins()
      // Prévient AppSettingsModal (grisage des sous-onglets) et App.jsx (menu gauche) pour que
      // le changement soit visible immédiatement, sans attendre un changement d'onglet ou un
      // rechargement de page.
      onChanged?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="mx-auto h-full max-w-2xl overflow-y-auto">
      <h2 className="mb-1 text-lg font-semibold text-white">Plugins</h2>
      <p className="mb-4 text-sm text-gray-400">
        Les fonctionnalités d'ARIA installées sous forme de plugins. Active ou désactive-les ici.
      </p>

      {restartNotice && (
        <div className="mb-4 rounded-lg border border-amber-800/60 bg-amber-950/40 px-3 py-2 text-sm text-amber-200">
          Redémarre ARIA pour que ce changement prenne effet.
        </div>
      )}

      {loading && <p className="text-sm text-gray-400">Chargement…</p>}
      {error && <p className="text-sm text-red-300">Erreur : {error}</p>}

      {!loading && !error && plugins.length === 0 && (
        <p className="text-sm text-gray-400">Aucun plugin installé pour l'instant.</p>
      )}

      <ul className="space-y-2">
        {plugins.map((plugin) => (
          <li key={plugin.id} className="rounded-lg border border-gray-700 bg-gray-800/60 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate font-medium text-gray-100">{plugin.name}</span>
                  <span className="shrink-0 text-xs text-gray-500">v{plugin.version}</span>
                </div>
                {plugin.description && (
                  <p className="mt-0.5 truncate text-xs text-gray-400">{plugin.description}</p>
                )}
                {plugin.load_error && (
                  <p className="mt-1 text-xs text-red-300">Échec du chargement : {plugin.load_error}</p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <StatusBadge enabled={plugin.enabled} loadError={plugin.load_error} />
                <button
                  onClick={() => toggle(plugin)}
                  disabled={pending === plugin.id}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
                    plugin.enabled
                      ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
                      : 'bg-blue-600 text-white hover:bg-blue-500'
                  }`}
                >
                  {plugin.enabled ? 'Désactiver' : 'Activer'}
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
