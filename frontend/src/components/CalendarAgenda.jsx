import { useCallback, useEffect, useRef, useState } from 'react'
import { SkeletonBlock } from './Skeleton'

const API_URL = '/api/calendar'
const WEEKDAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

function CalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-6 w-6" aria-hidden="true">
      <rect x="3.5" y="5" width="17" height="15" rx="2" />
      <path d="M3.5 9.5h17M8 3v4M16 3v4" />
    </svg>
  )
}

// Anneau tournant plutôt qu'un texte "Chargement..." — cohérent avec les indicateurs de
// chargement déjà utilisés ailleurs dans ARIA (Chat, Assistant vocal), moins envahissant dans une
// barre d'outils compacte.
function LoadingSpinner() {
  return (
    <span
      className="h-4 w-4 animate-spin rounded-full border-2 border-gray-600 border-t-blue-400"
      role="status"
      aria-label="Chargement"
    />
  )
}

// Skeleton affiché pendant statusLoading (tout premier chargement de l'onglet, avant de
// savoir si Google Agenda est configuré/connecté) : reprend la forme de la barre d'outils +
// grille du mois (le cas le plus probable une fois connectée), plutôt qu'un espace vide.
function AgendaSkeleton() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <div className="flex items-center gap-4 rounded-xl border border-gray-800 bg-gradient-to-b from-gray-800/90 to-gray-800/60 p-2 shadow-md shadow-black/20">
        <SkeletonBlock className="h-10 w-32 rounded-md" />
        <SkeletonBlock className="h-7 w-40" />
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-gray-800 bg-gray-800/70 shadow-lg shadow-black/30">
        <div className="grid grid-cols-7 border-b border-gray-700 bg-gradient-to-b from-gray-800/80 to-transparent">
          {WEEKDAY_LABELS.map((label) => (
            <div key={label} className="flex justify-center py-3">
              <SkeletonBlock className="h-2.5 w-6" />
            </div>
          ))}
        </div>
        <div className="grid flex-1 grid-cols-7 auto-rows-fr">
          {Array.from({ length: 35 }).map((_, i) => (
            <div key={i} className="flex flex-col gap-1.5 border-b border-r border-gray-700 p-1.5 last:border-r-0 sm:p-2">
              <SkeletonBlock className="h-5 w-5 rounded-full" />
              {i % 3 === 0 && <SkeletonBlock className="h-3 w-full" />}
              {i % 5 === 1 && <SkeletonBlock className="h-3 w-2/3" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function pad(n) {
  return String(n).padStart(2, '0')
}

function dateKey(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// Grille de 5 ou 6 semaines selon le mois (35 ou 42 jours), en commençant le lundi (convention
// française) — inclut les quelques jours du mois précédent/suivant nécessaires pour compléter la
// première et la dernière semaine, comme Google Agenda. Le nombre de rangées varie donc d'un mois
// à l'autre ; la grille (voir plus bas, `auto-rows-fr`) répartit la hauteur disponible entre le
// nombre réel de rangées, pour toujours tenir sur un écran sans rangée vide ni scroll inutile.
function buildMonthGrid(monthDate) {
  const year = monthDate.getFullYear()
  const month = monthDate.getMonth()
  const firstOfMonth = new Date(year, month, 1)
  const firstWeekday = (firstOfMonth.getDay() + 6) % 7 // 0 = lundi
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const totalCells = Math.ceil((firstWeekday + daysInMonth) / 7) * 7 // 35 (5 semaines) ou 42 (6)
  const gridStart = new Date(year, month, 1 - firstWeekday)
  const days = []
  for (let i = 0; i < totalCells; i += 1) {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    days.push(d)
  }
  return days
}

// Clé de regroupement d'un événement Google (date-only pour "toute la journée", dateTime sinon) —
// toujours interprétée en heure LOCALE du navigateur, pour tomber dans la bonne case de la grille.
function eventDateKey(event) {
  if (event.start?.date) {
    const [y, m, d] = event.start.date.split('-').map(Number)
    return `${y}-${pad(m)}-${pad(d)}`
  }
  if (event.start?.dateTime) {
    return dateKey(new Date(event.start.dateTime))
  }
  return null
}

function eventTimeLabel(event) {
  if (!event.start?.dateTime) return ''
  const d = new Date(event.start.dateTime)
  return `${pad(d.getHours())}:${pad(d.getMinutes())} `
}

// Construit le payload attendu par l'API Calendar (start/end.date pour toute la journée —
// end.date exclusif, donc +1 jour ; start/end.dateTime + timeZone sinon) à partir du formulaire.
function buildEventPayload(form) {
  const payload = { summary: form.summary.trim() }
  if (form.description.trim()) payload.description = form.description.trim()
  if (form.location.trim()) payload.location = form.location.trim()

  if (form.allDay) {
    const [y, m, d] = form.date.split('-').map(Number)
    const endDate = new Date(y, m - 1, d + 1)
    payload.start = { date: form.date }
    payload.end = { date: dateKey(endDate) }
  } else {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
    payload.start = { dateTime: `${form.date}T${form.startTime}:00`, timeZone }
    payload.end = { dateTime: `${form.date}T${form.endTime}:00`, timeZone }
  }
  return payload
}

function parseEventForForm(event) {
  const allDay = Boolean(event.start?.date)
  if (allDay) {
    return {
      eventId: event.id,
      calendarId: event.calendarId || 'primary',
      summary: event.summary || '',
      description: event.description || '',
      location: event.location || '',
      allDay: true,
      date: event.start.date,
      startTime: '09:00',
      endTime: '10:00',
      htmlLink: event.htmlLink,
    }
  }
  const start = new Date(event.start.dateTime)
  const end = new Date(event.end.dateTime)
  return {
    eventId: event.id,
    calendarId: event.calendarId || 'primary',
    summary: event.summary || '',
    description: event.description || '',
    location: event.location || '',
    allDay: false,
    date: dateKey(start),
    startTime: `${pad(start.getHours())}:${pad(start.getMinutes())}`,
    endTime: `${pad(end.getHours())}:${pad(end.getMinutes())}`,
    htmlLink: event.htmlLink,
  }
}

function emptyFormForDate(date) {
  return {
    eventId: null,
    calendarId: 'primary',
    summary: '',
    description: '',
    location: '',
    allDay: false,
    date: dateKey(date),
    startTime: '09:00',
    endTime: '10:00',
    htmlLink: null,
  }
}

function DayCell({ date, isCurrentMonth, isToday, events, onOpenDay, onCreate, onEventClick }) {
  const visibleEvents = events.slice(0, 3)
  const overflowCount = events.length - visibleEvents.length
  return (
    <div
      className={`group relative flex min-h-[3.5rem] flex-col gap-1 overflow-hidden border-b border-r border-gray-700 p-1.5 transition-colors last:border-r-0 hover:bg-gray-800/30 sm:p-2 ${
        isCurrentMonth ? '' : 'bg-gray-900/30'
      }`}
    >
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => onOpenDay(date)}
          className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium tabular-nums transition ${
            isToday
              ? 'bg-gradient-to-br from-blue-500 to-cyan-400 text-white shadow-sm shadow-blue-950/50'
              : isCurrentMonth
                ? 'text-gray-300 hover:bg-gray-700'
                : 'text-gray-600 hover:bg-gray-800'
          }`}
        >
          {date.getDate()}
        </button>
        {/* Bouton "+" visible au survol/focus seulement : évite d'alourdir visuellement une
            grille déjà dense (35 à 42 cases selon le mois). Le numéro du jour reste toujours
            cliquable comme second point d'entrée (utile au tactile, sans hover). */}
        <button
          type="button"
          onClick={() => onCreate(date)}
          aria-label={`Ajouter un événement le ${date.toLocaleDateString('fr-FR')}`}
          title="Ajouter un événement"
          className="flex h-5 w-5 items-center justify-center rounded text-gray-600 opacity-0 transition hover:bg-gray-700 hover:text-gray-200 group-focus-within:opacity-100 group-hover:opacity-100"
        >
          +
        </button>
      </div>
      <div className="flex flex-1 flex-col gap-0.5 overflow-hidden">
        {visibleEvents.map((event) => (
          <button
            key={event.id}
            type="button"
            onClick={() => onEventClick(event)}
            title={event.summary || '(Sans titre)'}
            className="truncate rounded-md border-l-2 border-blue-400 bg-gradient-to-r from-blue-500/25 to-blue-500/10 px-1.5 py-0.5 text-left text-[11px] font-medium text-blue-200 shadow-sm shadow-black/10 transition hover:from-blue-500/35 hover:to-blue-500/15"
          >
            {eventTimeLabel(event)}
            {event.summary || '(Sans titre)'}
          </button>
        ))}
        {overflowCount > 0 && (
          <button
            type="button"
            onClick={() => onOpenDay(date)}
            className="px-1.5 text-left text-[11px] font-medium text-gray-400 transition hover:text-gray-200"
          >
            +{overflowCount} de plus
          </button>
        )}
      </div>
    </div>
  )
}

// role="dialog" + focus initial + fermeture Échap, même pattern que ConfirmModal dans
// ChatComponent.jsx — cohérence d'accessibilité entre les deux onglets.
function DayEventsModal({ date, events, onClose, onCreate, onEventClick }) {
  const closeRef = useRef(null)
  useEffect(() => {
    closeRef.current?.focus()
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="day-modal-title"
        className="max-h-[80vh] w-full max-w-md overflow-y-auto rounded-xl border border-gray-700 bg-gray-800 p-5 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3">
          <h3 id="day-modal-title" className="text-lg font-semibold capitalize text-white">
            {date.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}
          </h3>
          <button ref={closeRef} type="button" onClick={onClose} aria-label="Fermer" className="rounded-md p-1.5 text-gray-400 hover:bg-gray-700 hover:text-white">
            ✕
          </button>
        </div>
        <div className="mt-4 space-y-2">
          {events.length === 0 && <p className="text-sm text-gray-400">Aucun événement ce jour-là.</p>}
          {events.map((event) => (
            <button
              key={event.id}
              type="button"
              onClick={() => onEventClick(event)}
              className="flex min-h-[44px] w-full items-center gap-2 rounded-md border border-gray-700 px-3 py-2 text-left text-sm text-gray-200 transition hover:bg-gray-700"
            >
              {eventTimeLabel(event) && <span className="tabular-nums text-blue-300">{eventTimeLabel(event)}</span>}
              <span className="truncate">{event.summary || '(Sans titre)'}</span>
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => onCreate(date)}
          className="mt-4 inline-flex min-h-[44px] items-center gap-2 rounded-md bg-gradient-to-br from-blue-600 to-cyan-500 px-4 text-sm font-medium text-white shadow-md shadow-blue-950/30 transition hover:from-blue-500 hover:to-cyan-400"
        >
          + Ajouter un événement
        </button>
      </div>
    </div>
  )
}

function EventFormModal({ initial, onClose, onSave, onDelete, saving, serverError }) {
  const [summary, setSummary] = useState(initial.summary)
  const [description, setDescription] = useState(initial.description)
  const [location, setLocation] = useState(initial.location)
  const [allDay, setAllDay] = useState(initial.allDay)
  const [date, setDate] = useState(initial.date)
  const [startTime, setStartTime] = useState(initial.startTime)
  const [endTime, setEndTime] = useState(initial.endTime)
  const [formError, setFormError] = useState('')
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const firstFieldRef = useRef(null)

  useEffect(() => {
    firstFieldRef.current?.focus()
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const handleSubmit = (event) => {
    event.preventDefault()
    if (!summary.trim()) {
      setFormError('Le titre est obligatoire.')
      return
    }
    if (!allDay && startTime >= endTime) {
      setFormError("L'heure de fin doit être après l'heure de début.")
      return
    }
    setFormError('')
    onSave({ eventId: initial.eventId, summary, description, location, allDay, date, startTime, endTime })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="event-modal-title"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
        className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-xl border border-gray-700 bg-gray-800 p-5 shadow-xl"
      >
        <div className="flex items-center justify-between gap-3">
          <h3 id="event-modal-title" className="text-lg font-semibold text-white">
            {initial.eventId ? "Modifier l'événement" : 'Nouvel événement'}
          </h3>
          <button type="button" onClick={onClose} aria-label="Fermer" className="rounded-md p-1.5 text-gray-400 hover:bg-gray-700 hover:text-white">
            ✕
          </button>
        </div>

        <div className="mt-4 space-y-3">
          <div>
            <label htmlFor="event-summary" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
              Titre
            </label>
            <input
              id="event-summary"
              ref={firstFieldRef}
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="Titre de l'événement"
              className="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-500"
              required
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={allDay}
              onChange={(event) => setAllDay(event.target.checked)}
              className="h-3.5 w-3.5 rounded border-gray-600 bg-gray-800"
            />
            Toute la journée
          </label>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label htmlFor="event-date" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
                Date
              </label>
              <input
                id="event-date"
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
                className="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-500"
                required
              />
            </div>
            {!allDay && (
              <>
                <div>
                  <label htmlFor="event-start" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
                    Début
                  </label>
                  <input
                    id="event-start"
                    type="time"
                    value={startTime}
                    onChange={(event) => setStartTime(event.target.value)}
                    className="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-500"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="event-end" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
                    Fin
                  </label>
                  <input
                    id="event-end"
                    type="time"
                    value={endTime}
                    onChange={(event) => setEndTime(event.target.value)}
                    className="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-500"
                    required
                  />
                </div>
              </>
            )}
          </div>

          <div>
            <label htmlFor="event-location" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
              Lieu (optionnel)
            </label>
            <input
              id="event-location"
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              className="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-500"
            />
          </div>

          <div>
            <label htmlFor="event-description" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-400">
              Description (optionnel)
            </label>
            <textarea
              id="event-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              className="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-500"
            />
          </div>

          {initial.htmlLink && (
            <a href={initial.htmlLink} target="_blank" rel="noopener noreferrer" className="inline-block text-xs text-blue-300 underline hover:text-blue-200">
              Voir dans Google Agenda
            </a>
          )}

          {(formError || serverError) && (
            <p role="alert" className="text-sm text-red-300">
              {formError || serverError}
            </p>
          )}
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
          {initial.eventId ? (
            confirmingDelete ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-red-300">Supprimer définitivement ?</span>
                <button
                  type="button"
                  onClick={() => setConfirmingDelete(false)}
                  className="inline-flex min-h-[44px] items-center rounded-md border border-gray-600 px-3 text-sm text-gray-300 hover:bg-gray-700"
                >
                  Non
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(initial.eventId, initial.calendarId)}
                  disabled={saving}
                  className="inline-flex min-h-[44px] items-center rounded-md bg-red-700 px-3 text-sm font-medium text-white hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Oui, supprimer
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmingDelete(true)}
                className="inline-flex min-h-[44px] items-center rounded-md border border-red-800/60 px-3 text-sm font-medium text-red-300 hover:bg-red-950/40"
              >
                Supprimer
              </button>
            )
          ) : (
            <span />
          )}
          <div className="flex items-center gap-2">
            <button type="button" onClick={onClose} className="inline-flex min-h-[44px] items-center rounded-md border border-gray-600 px-3 text-sm text-gray-300 hover:bg-gray-700">
              Annuler
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex min-h-[44px] items-center rounded-md bg-gradient-to-br from-blue-600 to-cyan-500 px-4 text-sm font-medium text-white shadow-md shadow-blue-950/30 transition hover:from-blue-500 hover:to-cyan-400 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
            >
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}

export default function CalendarAgenda() {
  const [status, setStatus] = useState({ configured: false, connected: false })
  const [statusLoading, setStatusLoading] = useState(true)
  const [currentMonth, setCurrentMonth] = useState(() => {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), 1)
  })
  const [events, setEvents] = useState([])
  const [eventsLoading, setEventsLoading] = useState(false)
  const [eventsError, setEventsError] = useState('')
  const [banner, setBanner] = useState(null)
  const [connectError, setConnectError] = useState('')
  const [dayModal, setDayModal] = useState(null) // Date | null
  const [formModal, setFormModal] = useState(null) // objet form | null
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')

  const loadStatus = useCallback(async () => {
    setStatusLoading(true)
    try {
      const response = await fetch(`${API_URL}/status`)
      const data = await response.json()
      setStatus(data)
    } catch {
      setStatus({ configured: false, connected: false })
    } finally {
      setStatusLoading(false)
    }
  }, [])

  // Lit calendar_connected / calendar_error déposés dans l'URL par le callback OAuth du backend
  // (voir routes/calendar.py) au premier montage, affiche le résultat, puis nettoie l'URL pour
  // qu'un rechargement de page ne redéclenche pas la bannière.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const connected = params.get('calendar_connected')
    const error = params.get('calendar_error')
    if (connected || error) {
      setBanner(
        connected
          ? { type: 'success', message: 'Google Agenda connecté avec succès.' }
          : { type: 'error', message: `Connexion à Google Agenda impossible (${error}).` },
      )
      params.delete('calendar_connected')
      params.delete('calendar_error')
      const newSearch = params.toString()
      window.history.replaceState({}, '', window.location.pathname + (newSearch ? `?${newSearch}` : ''))
    }
    loadStatus()
  }, [loadStatus])

  // La bannière de succès se referme toute seule après quelques secondes (juste une confirmation,
  // pas besoin de garder de la place) ; l'erreur reste affichée — elle contient un code utile pour
  // diagnostiquer, la personne doit avoir le temps de la lire ou de la copier.
  useEffect(() => {
    if (banner?.type !== 'success') return
    const timer = setTimeout(() => setBanner(null), 5000)
    return () => clearTimeout(timer)
  }, [banner])

  const loadEvents = useCallback(async () => {
    if (!status.connected) return
    setEventsLoading(true)
    setEventsError('')
    try {
      const days = buildMonthGrid(currentMonth)
      const timeMin = days[0].toISOString()
      const timeMaxDate = new Date(days[days.length - 1])
      timeMaxDate.setDate(timeMaxDate.getDate() + 1)
      const timeMax = timeMaxDate.toISOString()
      const response = await fetch(`${API_URL}/events?time_min=${encodeURIComponent(timeMin)}&time_max=${encodeURIComponent(timeMax)}`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || `Erreur (${response.status})`)
      setEvents(data.events || [])
    } catch (error) {
      setEventsError(error.message || 'Impossible de charger les événements')
    } finally {
      setEventsLoading(false)
    }
  }, [status.connected, currentMonth])

  useEffect(() => {
    loadEvents()
  }, [loadEvents])

  const handleConnect = async () => {
    setConnectError('')
    try {
      const response = await fetch(`${API_URL}/auth-url`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || `Erreur (${response.status})`)
      window.location.href = data.url
    } catch (error) {
      setConnectError(error.message || 'Impossible de démarrer la connexion Google')
    }
  }

  const handleDisconnect = async () => {
    await fetch(`${API_URL}/disconnect`, { method: 'POST' })
    setEvents([])
    loadStatus()
  }

  const handleSaveEvent = async (form) => {
    setSaving(true)
    setSaveError('')
    try {
      const payload = buildEventPayload(form)
      const endpoint = form.eventId
        ? `${API_URL}/events/${form.eventId}?calendar_id=${encodeURIComponent(form.calendarId || 'primary')}`
        : `${API_URL}/events`
      const method = form.eventId ? 'PATCH' : 'POST'
      const response = await fetch(endpoint, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || `Erreur (${response.status})`)
      setFormModal(null)
      await loadEvents()
    } catch (error) {
      setSaveError(error.message || "Impossible d'enregistrer l'événement")
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteEvent = async (eventId, calendarId) => {
    setSaving(true)
    setSaveError('')
    try {
      const response = await fetch(
        `${API_URL}/events/${eventId}?calendar_id=${encodeURIComponent(calendarId || 'primary')}`,
        { method: 'DELETE' },
      )
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || `Erreur (${response.status})`)
      }
      setFormModal(null)
      await loadEvents()
    } catch (error) {
      setSaveError(error.message || "Impossible de supprimer l'événement")
    } finally {
      setSaving(false)
    }
  }

  const openCreate = (date) => {
    setDayModal(null)
    setSaveError('')
    setFormModal(emptyFormForDate(date))
  }

  const openEdit = (event) => {
    setDayModal(null)
    setSaveError('')
    setFormModal(parseEventForForm(event))
  }

  const days = buildMonthGrid(currentMonth)
  const eventsByDay = events.reduce((acc, event) => {
    const key = eventDateKey(event)
    if (!key) return acc
    if (!acc[key]) acc[key] = []
    acc[key].push(event)
    return acc
  }, {})
  const today = new Date()
  const todayKey = dateKey(today)
  const monthLabel = currentMonth.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })

  const changeMonth = (delta) => {
    setCurrentMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1))
  }
  const goToday = () => {
    const now = new Date()
    setCurrentMonth(new Date(now.getFullYear(), now.getMonth(), 1))
  }

  return (
    <section className="flex h-full min-h-[32rem] flex-col gap-4 overflow-y-auto pr-1">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-cyan-400 text-white shadow-md shadow-blue-950/40"
            aria-hidden="true"
          >
            <CalendarIcon />
          </span>
          <h2 className="text-2xl font-semibold leading-none text-white">Agenda</h2>
        </div>
        {status.connected && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => openCreate(new Date())}
              aria-label="Ajouter un événement"
              title="Ajouter un événement"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-md shadow-blue-950/30 transition hover:from-blue-500 hover:to-cyan-400"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="h-4 w-4" aria-hidden="true">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </button>
            <button
              type="button"
              onClick={handleDisconnect}
              aria-label="Déconnecter Google Agenda"
              title="Déconnecter Google Agenda"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-700 text-gray-400 transition hover:border-red-700/60 hover:text-red-300"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" className="h-4 w-4" aria-hidden="true">
                <path d="M12 3v9" />
                <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {banner && (
        <div
          className={`flex items-center justify-between gap-3 rounded-lg border px-4 py-3 text-sm ${
            banner.type === 'success' ? 'border-emerald-800 bg-emerald-950/30 text-emerald-300' : 'border-red-800 bg-red-950/40 text-red-300'
          }`}
        >
          <span>{banner.message}</span>
          <button type="button" onClick={() => setBanner(null)} aria-label="Fermer" className="text-current opacity-70 transition hover:opacity-100">
            ✕
          </button>
        </div>
      )}

      {statusLoading && <AgendaSkeleton />}

      {!statusLoading && !status.configured && (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-gray-800 bg-gray-800/70 p-8 text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-400/20 text-blue-300 shadow-inner shadow-blue-950/20 ring-1 ring-white/5">
            <CalendarIcon />
          </span>
          <div>
            <p className="text-sm font-medium text-gray-300">Google Agenda n'est pas encore configuré</p>
            <p className="mt-1 max-w-sm text-sm text-gray-500">
              Il faut d'abord créer des identifiants OAuth dans Google Cloud Console et les ajouter à backend/.env
              (GOOGLE_CLIENT_ID et GOOGLE_CLIENT_SECRET) — voir les instructions de configuration fournies séparément.
            </p>
          </div>
        </div>
      )}

      {!statusLoading && status.configured && !status.connected && (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-gray-800 bg-gray-800/70 p-8 text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-400/20 text-blue-300 shadow-inner shadow-blue-950/20 ring-1 ring-white/5">
            <CalendarIcon />
          </span>
          <div>
            <p className="text-sm font-medium text-gray-300">Connectez votre Google Agenda</p>
            <p className="mt-1 max-w-sm text-sm text-gray-500">Affichez et gérez vos événements directement depuis ARIA.</p>
          </div>
          <button
            type="button"
            onClick={handleConnect}
            className="mt-2 inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 px-5 text-sm font-semibold text-white shadow-md shadow-blue-950/30 transition hover:from-blue-500 hover:to-cyan-400"
          >
            Connecter Google Agenda
          </button>
          {connectError && (
            <p role="alert" className="text-xs text-red-300">
              {connectError}
            </p>
          )}
        </div>
      )}

      {status.connected && (
        <div className="flex min-h-0 flex-1 flex-col gap-4">
          <div className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-800 bg-gradient-to-b from-gray-800/90 to-gray-800/60 p-2 shadow-md shadow-black/20">
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => changeMonth(-1)}
                aria-label="Mois précédent"
                className="inline-flex h-10 w-10 items-center justify-center rounded-md text-lg text-gray-300 transition hover:bg-gray-700"
              >
                ‹
              </button>
              <button
                type="button"
                onClick={goToday}
                className="inline-flex min-h-[44px] items-center rounded-md border border-gray-700 px-3 text-sm font-medium text-gray-300 transition hover:bg-gray-700"
              >
                Aujourd'hui
              </button>
              <button
                type="button"
                onClick={() => changeMonth(1)}
                aria-label="Mois suivant"
                className="inline-flex h-10 w-10 items-center justify-center rounded-md text-lg text-gray-300 transition hover:bg-gray-700"
              >
                ›
              </button>
            </div>
            <p className="whitespace-nowrap text-2xl font-semibold capitalize text-white">{monthLabel}</p>
            <div className="ml-auto flex">{eventsLoading && <LoadingSpinner />}</div>
          </div>

          {eventsError && <p role="alert" className="rounded-lg border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-300">{eventsError}</p>}

          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-gray-800 bg-gray-800/70 shadow-lg shadow-black/30">
            <div className="grid grid-cols-7 border-b border-gray-700 bg-gradient-to-b from-gray-800/80 to-transparent text-center text-[11px] font-semibold uppercase tracking-wider text-gray-500">
              {WEEKDAY_LABELS.map((label) => (
                <div key={label} className="py-2">
                  {label}
                </div>
              ))}
            </div>
            {/* auto-rows-fr répartit la hauteur restante (flex-1 du parent) à parts égales entre
                les rangées réellement présentes (5 ou 6 selon le mois, voir buildMonthGrid) — la
                grille remplit l'espace disponible sans rangée vide ni scroll de page. */}
            <div className="grid flex-1 grid-cols-7 auto-rows-fr">
              {days.map((day) => {
                const key = dateKey(day)
                return (
                  <DayCell
                    key={key}
                    date={day}
                    isCurrentMonth={day.getMonth() === currentMonth.getMonth()}
                    isToday={key === todayKey}
                    events={eventsByDay[key] || []}
                    onOpenDay={setDayModal}
                    onCreate={openCreate}
                    onEventClick={openEdit}
                  />
                )
              })}
            </div>
          </div>
        </div>
      )}

      {dayModal && (
        <DayEventsModal
          date={dayModal}
          events={eventsByDay[dateKey(dayModal)] || []}
          onClose={() => setDayModal(null)}
          onCreate={openCreate}
          onEventClick={openEdit}
        />
      )}

      {formModal && (
        <EventFormModal
          initial={formModal}
          onClose={() => setFormModal(null)}
          onSave={handleSaveEvent}
          onDelete={handleDeleteEvent}
          saving={saving}
          serverError={saveError}
        />
      )}
    </section>
  )
}
