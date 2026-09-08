import { useEffect, useState } from 'react'

function SaintIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-6 w-6" aria-hidden="true">
      <path d="M12 3v18M7 7h10M5 11h14M7 7 4 4M17 7l3-3M8 21h8" />
    </svg>
  )
}

export default function SaintOfDay() {
  const [saint, setSaint] = useState(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/saints/today')
      .then(async (response) => {
        const data = await response.json()
        if (!response.ok) throw new Error(data.detail || 'Impossible de charger le saint du jour')
        setSaint(data)
      })
      .catch((loadError) => setError(loadError.message))
  }, [])

  if (error) return <p className="rounded-md border border-red-800 bg-red-950/30 p-4 text-sm text-red-300">{error}</p>
  if (!saint) return <p className="text-sm text-gray-400">Chargement...</p>

  return (
    <section className="mx-auto w-full max-w-2xl rounded-xl border border-amber-900/50 bg-gradient-to-br from-gray-800 to-gray-900 p-5 shadow-xl">
      <div className="flex items-start gap-4">
        <div className="rounded-lg border border-amber-700/50 bg-amber-950/40 p-3 text-amber-300">
          <SaintIcon />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-400">Saint du jour</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">{saint.name}</h2>
          <p className="mt-1 text-sm capitalize text-gray-400">{saint.display_date}</p>
        </div>
        <button
          type="button"
          onClick={() => setDetailsOpen((open) => !open)}
          className="shrink-0 rounded-md border border-amber-700/60 px-3 py-2 text-sm font-medium text-amber-300 transition hover:bg-amber-950/50"
          aria-expanded={detailsOpen}
        >
          {detailsOpen ? 'Réduire' : 'Détails'}
        </button>
      </div>
      {detailsOpen && (
        <div className="mt-5 border-t border-gray-700 pt-4 text-sm leading-6 text-gray-300">
          {saint.story}
        </div>
      )}
      {saint.observances?.length > 0 && (
        <div className="mt-5 border-t border-amber-900/40 pt-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-400">Journées du jour</p>
          <div className="mt-3 space-y-3">
            {saint.observances.map((observance) => (
              <div key={observance.name} className="rounded-lg border border-gray-700 bg-gray-900/50 p-3">
                <p className="font-medium text-white">{observance.name}</p>
                <p className="mt-1 text-sm leading-6 text-gray-400">{observance.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}