import { useEffect, useState } from 'react'
import { SkeletonBlock } from './Skeleton'

function SaintIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-6 w-6" aria-hidden="true">
      <path d="M12 3v18M7 7h10M5 11h14M7 7 4 4M17 7l3-3M8 21h8" />
    </svg>
  )
}

function StatCard({ label, value }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900/50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-gray-200">{value}</p>
    </div>
  )
}

function formatTime(isoDateTime) {
  if (!isoDateTime) return null
  const timePart = isoDateTime.split('T')[1]
  return timePart ? timePart.slice(0, 5) : null
}

// Reprend la forme réelle de la carte (en-tête + badges + météo + dicton) plutôt qu'une
// simple phrase "Chargement...", pour que l'œil comprenne tout de suite ce qui arrive.
function SaintSkeleton() {
  return (
    <section className="mx-auto w-full max-w-2xl rounded-xl border border-amber-900/50 bg-gradient-to-br from-gray-800 to-gray-900 p-5 shadow-xl">
      <div className="flex items-start gap-4">
        <SkeletonBlock className="h-11 w-11 shrink-0 rounded-lg" />
        <div className="min-w-0 flex-1 space-y-2">
          <SkeletonBlock className="h-3 w-28" />
          <SkeletonBlock className="h-6 w-48" />
          <SkeletonBlock className="h-3 w-40" />
        </div>
        <SkeletonBlock className="h-9 w-20 shrink-0 rounded-md" />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <SkeletonBlock className="h-6 w-28 rounded-full" />
        <SkeletonBlock className="h-6 w-36 rounded-full" />
      </div>
      <div className="mt-5 space-y-2 rounded-lg border border-gray-700 bg-gray-900/50 p-3">
        <SkeletonBlock className="h-3 w-32" />
        <SkeletonBlock className="h-6 w-24" />
      </div>
      <div className="mt-5 space-y-2 rounded-lg border border-amber-900/40 bg-amber-950/20 p-3">
        <SkeletonBlock className="h-3 w-28" />
        <SkeletonBlock className="h-3 w-full" />
        <SkeletonBlock className="h-3 w-3/4" />
      </div>
    </section>
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
  if (!saint) return <SaintSkeleton />

  const ephemeride = saint.ephemeride
  const prenomInfo = saint.prenom_info
  const hasPrenomStats = prenomInfo && (prenomInfo.total_births_since_1900 || prenomInfo.origine || prenomInfo.signification)

  return (
    <section className="mx-auto w-full max-w-2xl rounded-xl border border-amber-900/50 bg-gradient-to-br from-gray-800 to-gray-900 p-5 shadow-xl">
      <div className="flex items-start gap-4">
        <div className="rounded-lg border border-amber-700/50 bg-amber-950/40 p-3 text-amber-300">
          <SaintIcon />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-400">Saint du jour</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">{saint.name}</h2>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-gray-400">
            <span className="capitalize">{saint.display_date}</span>
            {ephemeride && (
              <span className="text-xs text-gray-500">
                · {ephemeride.day_of_year}ᵉ jour de l'année · {ephemeride.days_remaining} jours restants
              </span>
            )}
          </div>
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

      {(saint.moon_phase || saint.next_holiday) && (
        <div className="mt-4 flex flex-wrap gap-2">
          {saint.moon_phase && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-gray-700 bg-gray-900/50 px-3 py-1 text-xs text-gray-300">
              <span className="text-base leading-none">{saint.moon_phase.emoji}</span> {saint.moon_phase.name}
            </span>
          )}
          {saint.next_holiday && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-gray-700 bg-gray-900/50 px-3 py-1 text-xs text-gray-300">
              🎉{' '}
              {saint.next_holiday.is_today
                ? `${saint.next_holiday.name} — c'est aujourd'hui`
                : `${saint.next_holiday.name} dans ${saint.next_holiday.days_until} jour${saint.next_holiday.days_until > 1 ? 's' : ''}`}
            </span>
          )}
        </div>
      )}

      {saint.weather && (
        <div className="mt-5 rounded-lg border border-gray-700 bg-gray-900/50 p-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-400">Météo à {saint.weather.city}</p>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            {saint.weather.temperature !== null && saint.weather.temperature !== undefined && (
              <span className="text-xl font-semibold text-white">{Math.round(saint.weather.temperature)}°C</span>
            )}
            <span className="text-sm text-gray-300">{saint.weather.condition}</span>
          </div>
          <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
            {saint.weather.temperature_min !== null && saint.weather.temperature_max !== null && (
              <span>Min {Math.round(saint.weather.temperature_min)}° / Max {Math.round(saint.weather.temperature_max)}°</span>
            )}
            {formatTime(saint.weather.sunrise) && <span>☀️ Lever {formatTime(saint.weather.sunrise)}</span>}
            {formatTime(saint.weather.sunset) && <span>🌙 Coucher {formatTime(saint.weather.sunset)}</span>}
          </div>
        </div>
      )}

      {detailsOpen && (
        <div className="mt-5 border-t border-gray-700 pt-4 text-sm leading-6 text-gray-300">
          {saint.story}
        </div>
      )}

      {saint.dicton && (
        <div className="mt-5 rounded-lg border border-amber-900/40 bg-amber-950/20 p-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-400">Dicton du jour</p>
          <p className="mt-1.5 text-sm italic leading-6 text-gray-200">« {saint.dicton.text} »</p>
        </div>
      )}

      {hasPrenomStats && (
        <div className="mt-5 border-t border-amber-900/40 pt-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-400">Le prénom {prenomInfo.prenom}</p>
          {(prenomInfo.origine || prenomInfo.signification) && (
            <p className="mt-2 text-sm leading-6 text-gray-300">
              {prenomInfo.origine && <span>Origine : {prenomInfo.origine}. </span>}
              {prenomInfo.signification && <span>Signification : {prenomInfo.signification}.</span>}
            </p>
          )}
          {prenomInfo.total_births_since_1900 && (
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
              <StatCard label="Naissances en France depuis 1900" value={prenomInfo.total_births_since_1900.toLocaleString('fr-FR')} />
              {prenomInfo.peak_year && (
                <StatCard label="Année la plus donnée" value={`${prenomInfo.peak_year} (${prenomInfo.peak_year_births?.toLocaleString('fr-FR')})`} />
              )}
            </div>
          )}
          <p className="mt-2 text-[11px] text-gray-500">Source : données INSEE (naissances) et jeu de données ouvert « Super Prénom » (origine/signification).</p>
        </div>
      )}

      {saint.famous_birthdays?.length > 0 && (
        <div className="mt-5 border-t border-amber-900/40 pt-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-400">
            Né(e)s un {saint.display_date?.split(' ').slice(1, -1).join(' ')}
          </p>
          <ul className="mt-3 space-y-2">
            {saint.famous_birthdays.map((person) => (
              <li key={`${person.name}-${person.year}`} className="rounded-lg border border-gray-700 bg-gray-900/50 p-3 text-sm text-gray-300">
                <span className="font-medium text-white">{person.year}</span> — {person.name}
              </li>
            ))}
          </ul>
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
