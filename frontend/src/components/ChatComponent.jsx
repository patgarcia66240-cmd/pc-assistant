import { useState, useRef, useEffect } from 'react'
import { SkeletonBlock } from './Skeleton'

// Remplace le spinner + "Récupération des informations..." pendant qu'ARIA prépare sa
// réponse : quelques lignes de texte grisées d'une largeur irrégulière, pour suggérer une
// réponse en cours d'écriture plutôt qu'un simple indicateur d'attente.
function TypingSkeleton() {
  return (
    <div className="space-y-2 py-1">
      <SkeletonBlock className="h-3 w-full" />
      <SkeletonBlock className="h-3 w-4/5" />
      <SkeletonBlock className="h-3 w-1/2" />
    </div>
  )
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
      <path d="m21 3-7.5 18-3.5-7-7-3.5L21 3Z" />
      <path d="M10 14 21 3" />
    </svg>
  )
}

function SourceIcon({ type }) {
  if (type === 'clear') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </svg>
    )
  }

  if (type === 'cloud') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
        <path d="M7 18h10a4 4 0 0 0 .5-8A5.5 5.5 0 0 0 7 8.5 4.5 4.5 0 0 0 7 18Z" />
      </svg>
    )
  }

  if (type === 'rain') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
        <path d="M7 15h10a4 4 0 0 0 .5-8A5.5 5.5 0 0 0 7 5.5 4.5 4.5 0 0 0 7 15Z" />
        <path d="m8 18-1 2M12 18l-1 2M16 18l-1 2" />
      </svg>
    )
  }

  if (type === 'snow') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
        <path d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9M7 5l5 3 5-3M7 19l5-3 5 3" />
      </svg>
    )
  }

  if (type === 'storm') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
        <path d="M7 15h10a4 4 0 0 0 .5-8A5.5 5.5 0 0 0 7 5.5 4.5 4.5 0 0 0 7 15Z" />
        <path d="m13 13-3 5h3l-1 4 4-6h-3l2-3" />
      </svg>
    )
  }

  if (type === 'system') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
        <rect x="3" y="4" width="18" height="13" rx="2" />
        <path d="M8 21h8M12 17v4M7 13l2-3 2 2 2-4 2 3" />
      </svg>
    )
  }

  if (type === 'city_info') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
        <path d="M4 21V5l8-3 8 3v16M8 9h1M15 9h1M8 13h1M15 13h1M8 17h8" />
      </svg>
    )
  }

  if (type === 'time') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" />
        <path d="M12 7v5l3 2" />
      </svg>
    )
  }

  if (type === 'forex') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5" aria-hidden="true">
        <path d="M6 8h11M17 8l-3-3M17 8l-3 3" />
        <path d="M18 16H7M7 16l3-3M7 16l3 3" />
      </svg>
    )
  }

  if (type === 'market_overview' || type === 'stock' || type === 'etf' || type === 'cac40' || type === 'commodities' || type === 'bourse_unknown') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5" aria-hidden="true">
        <path d="M4 16.5 9.5 11l4 4L21 7" />
        <path d="M15 7h6v6" />
      </svg>
    )
  }

  if (type === 'king') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5" aria-hidden="true">
        <path d="M3 18h18l-1.6-8.5-4 3.3L12 6l-3.4 6.8-4-3.3L3 18Z" />
        <circle cx="3" cy="7.3" r="1.2" fill="currentColor" stroke="none" />
        <circle cx="12" cy="4.8" r="1.2" fill="currentColor" stroke="none" />
        <circle cx="21" cy="7.3" r="1.2" fill="currentColor" stroke="none" />
      </svg>
    )
  }

  // Même glyphe que CalendarIcon (CalendarAgenda.jsx) / l'icône d'onglet Agenda (App.jsx), pour une
  // identité visuelle cohérente entre la grille et les réponses de l'assistant agenda.
  if (type === 'calendar') {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" className="h-3.5 w-3.5" aria-hidden="true">
        <rect x="3.5" y="5" width="17" height="15" rx="2" />
        <path d="M8 3v4M16 3v4M3.5 10h17" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
      <path d="M4 5.5h16v10H9l-5 4v-14Z" />
      <path d="M8 9.5h8M8 13h5" />
    </svg>
  )
}

// Rendu minimal du gras markdown (**texte**) en HTML réel : certaines réponses de l'IA (ex.
// l'assistant agenda) utilisent **gras** pour mettre en valeur une info clé, mais l'interface
// n'a pas de parseur markdown complet — plutôt que d'afficher les ** littéralement, on ne
// convertit que le gras (seul style utilisé ici). Le texte hors ** reste du texte brut, échappé
// normalement par React (pas de dangerouslySetInnerHTML).
function FormattedText({ text }) {
  if (typeof text !== 'string' || !text.includes('**')) return text
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4
      ? <strong key={i} className="font-semibold text-white">{part.slice(2, -2)}</strong>
      : <span key={i}>{part}</span>
  )
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}

function LoadingIcon() {
  return <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-500 border-t-cyan-300" aria-hidden="true" />
}

// Avatar affiché à côté des messages d'ARIA (badge dégradé "A", identique à l'icône de l'app dans
// l'en-tête de App.jsx pour une identité visuelle cohérente) ou d'un message d'erreur (icône
// d'alerte distincte, pour ne plus confondre visuellement une erreur avec une réponse d'ARIA).
// Masqué sur mobile (sm:flex) pour laisser le maximum de largeur aux bulles sur petit écran.
function MessageAvatar({ sender }) {
  if (sender === 'error') {
    return (
      <span className="mb-1 hidden h-7 w-7 shrink-0 items-center justify-center rounded-full border border-red-700/60 bg-red-950/60 text-red-300 sm:flex" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5">
          <circle cx="12" cy="12" r="8.5" />
          <path d="M12 8v5M12 16h.01" />
        </svg>
      </span>
    )
  }
  return (
    <span className="mb-1 hidden h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 text-xs font-bold text-white shadow-sm shadow-blue-950/40 sm:flex" aria-hidden="true">
      A
    </span>
  )
}

function ChatEmptyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="h-6 w-6" aria-hidden="true">
      <path d="M4 5.5h16v10H9l-5 4v-14Z" />
      <path d="M8 9.5h1M12 9.5h1M16 9.5h1" />
    </svg>
  )
}

function CityInfoIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
      <path d="M4 21V5l8-3 8 3v16M8 9h1M15 9h1M8 13h1M15 13h1M8 17h8" />
    </svg>
  )
}

function ExchangeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
      <path d="M6 8h11M17 8l-3-3M17 8l-3 3" />
      <path d="M18 16H7M7 16l3-3M7 16l3 3" />
    </svg>
  )
}

function TrendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
      <path d="M4 16.5 9.5 11l4 4L21 7" />
      <path d="M15 7h6v6" />
    </svg>
  )
}

function CrownIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
      <path d="M3 18h18l-1.6-8.5-4 3.3L12 6l-3.4 6.8-4-3.3L3 18Z" />
      <circle cx="3" cy="7.3" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="12" cy="4.8" r="1.2" fill="currentColor" stroke="none" />
      <circle cx="21" cy="7.3" r="1.2" fill="currentColor" stroke="none" />
    </svg>
  )
}

// Libellé et couleur du badge affiché au-dessus d'une réponse d'ARIA, selon sa catégorie
// (source_type renvoyé par /api/chat/). Regroupés ici pour rester faciles à étendre quand une
// nouvelle catégorie API est ajoutée côté backend.
function sourceBadgeLabel(msg) {
  if (msg.sourceType === 'calendar_assistant') return 'Agenda'
  if (msg.source !== 'local') return 'IA'
  switch (msg.sourceType) {
    case 'weather':
      return 'Météo locale'
    case 'time':
      return msg.timeLabel || 'Heure France'
    case 'city_info':
      return 'Infos ville'
    case 'departement_info':
      return 'Infos département'
    case 'region_info':
      return 'Infos région'
    case 'forex':
      return 'Devises'
    case 'market_overview':
      return 'Tendances marchés'
    case 'stock':
      return 'Action'
    case 'etf':
      return 'ETF'
    case 'cac40':
      return 'CAC 40'
    case 'commodities':
      return 'Matières premières'
    case 'bourse_unknown':
      return 'Bourse'
    case 'king':
      return 'Rois de France'
    default:
      return 'API système'
  }
}

function sourceBadgeClass(msg) {
  if (msg.sourceType === 'calendar_assistant') {
    return 'border-blue-700/60 bg-gradient-to-r from-blue-950/60 to-cyan-950/40 text-blue-300'
  }
  if (msg.source !== 'local') return 'border-violet-700/60 bg-violet-950/40 text-violet-300'
  if (msg.sourceType === 'weather') return 'border-sky-700/60 bg-sky-950/40 text-sky-300'
  if (['forex', 'market_overview', 'stock', 'etf', 'cac40', 'commodities', 'bourse_unknown'].includes(msg.sourceType)) {
    return 'border-amber-700/60 bg-amber-950/40 text-amber-300'
  }
  if (msg.sourceType === 'king') return 'border-yellow-700/60 bg-yellow-950/40 text-yellow-300'
  return 'border-emerald-700/60 bg-emerald-950/40 text-emerald-300'
}

function getBrowserLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null)
      return
    }

    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ latitude: coords.latitude, longitude: coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: false, maximumAge: 300000, timeout: 5000 },
    )
  })
}

// Clé localStorage pour garder l'historique de conversation entre deux ouvertures de l'appli
// (demande explicite : "garde en memoire les messages sauf si je clear tout") — persiste tant que
// le bouton "Effacer" n'a pas été utilisé.
const CHAT_STORAGE_KEY = 'aria_chat_history'

function loadStoredMessages() {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return [] // stockage indisponible/corrompu : on repart d'une conversation vide, pas de crash
  }
}

export default function ChatComponent() {
  const [messages, setMessages] = useState(loadStoredMessages)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [confirmClearOpen, setConfirmClearOpen] = useState(false)
  const messagesEndRef = useRef(null)
  const sentMessagesRef = useRef([])
  const historyIndexRef = useRef(-1)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    try {
      // On ne persiste pas les messages "loading" transitoires (ex. fiche ville en cours de
      // récupération) : un rechargement pendant l'appel laisserait un message "Chargement..."
      // bloqué pour toujours, la requête réelle étant perdue.
      const toStore = messages.filter((message) => !message.loading)
      localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(toStore))
    } catch {
      // stockage plein ou indisponible : pas bloquant, la conversation reste utilisable en mémoire
    }
  }, [messages])

  const handleClearHistory = () => {
    setMessages([])
    try {
      localStorage.removeItem(CHAT_STORAGE_KEY)
    } catch {
      // rien à faire si le stockage est indisponible : setMessages([]) a déjà vidé l'affichage
    }
    setConfirmClearOpen(false)
  }

  // overrideText : permet d'envoyer un message précis sans passer par le champ de saisie (ex.
  // clic sur un roi dans la frise -> "roi <nom>"), tout en gardant le même flux d'appel API/
  // affichage que la saisie manuelle. Sans argument, se comporte comme avant (lit `input`).
  const handleSend = async (overrideText) => {
    const sentText = (overrideText ?? input).trim()
    if (!sentText || loading) return

    const newMessage = { text: sentText, sender: 'user' }
    const history = sentMessagesRef.current
    if (history[history.length - 1] !== sentText) {
      history.push(sentText)
    }
    historyIndexRef.current = -1
    setMessages(prev => [...prev, newMessage])
    if (overrideText === undefined) setInput('')
    setLoading(true)
    // Bulle "en cours" systématique (avant : seulement pour les fiches ville) — remplacée par
    // la vraie réponse ou une erreur une fois arrivée, voir plus bas. Pour une fiche ville, on
    // garde le badge "Infos ville" pendant le chargement ; sinon badge générique "IA".
    const isCityInfoRequest = /^(infos?|informations?)(\s+sur)?\s+/i.test(sentText)
    const pendingId = `pending-${Date.now()}`
    setMessages(prev => [...prev, isCityInfoRequest
      ? { id: pendingId, text: 'Chargement de la fiche...', sender: 'aria', source: 'local', sourceType: 'city_info', loading: true }
      : { id: pendingId, text: '', sender: 'aria', loading: true }])

    try {
      const context = /météo|meteo|heure|date/i.test(sentText)
        ? { location: await getBrowserLocation() }
        : {}
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: sentText, context })
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || `Chat request failed (${response.status})`)
      }
      const responseMessage = { id: pendingId || `response-${Date.now()}`, text: data.response, data: data.data, timeData: data.time_data, timeLabel: data.time_label, sender: 'aria', source: data.source || 'ai', sourceType: data.source_type, weatherType: data.weather_type }
      setMessages(prev => pendingId
        ? prev.map((message) => message.id === pendingId ? responseMessage : message)
        : [...prev, responseMessage])
    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage = { id: pendingId || `error-${Date.now()}`, text: error.message || 'Erreur lors du chargement', sender: 'error' }
      setMessages(prev => pendingId
        ? prev.map((message) => message.id === pendingId ? errorMessage : message)
        : [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleInputKeyDown = (event) => {
    const history = sentMessagesRef.current
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return
    if (history.length === 0) return

    event.preventDefault()
    if (event.key === 'ArrowUp') {
      const nextIndex = historyIndexRef.current < 0
        ? history.length - 1
        : Math.max(0, historyIndexRef.current - 1)
      historyIndexRef.current = nextIndex
      setInput(history[nextIndex])
      return
    }

    if (historyIndexRef.current < 0) return
    const nextIndex = historyIndexRef.current + 1
    if (nextIndex >= history.length) {
      historyIndexRef.current = -1
      setInput('')
    } else {
      historyIndexRef.current = nextIndex
      setInput(history[nextIndex])
    }
  }

  return (
    <section className="flex h-full min-h-0 flex-col">
      <div className="mb-4 flex shrink-0 items-center justify-between gap-3 rounded-xl border border-gray-800 bg-gray-800/70 px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 text-sm font-bold text-white shadow-md shadow-blue-950/40"
            aria-hidden="true"
          >
            A
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-400">Assistant</p>
            <h2 className="truncate text-lg font-semibold leading-tight text-white">Conversation avec ARIA</h2>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={() => setConfirmClearOpen(true)}
              aria-label="Effacer toute la conversation"
              title="Effacer toute la conversation"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-700 text-gray-400 transition hover:border-red-700/60 hover:text-red-300"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden="true">
                <path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-8 0 1 13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-13" />
              </svg>
            </button>
          )}
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-800 bg-emerald-950/30 px-2.5 py-1 text-xs font-medium text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
            Prête
          </span>
        </div>
      </div>

      {confirmClearOpen && (
        <ConfirmModal
          message="Effacer toute la conversation ? Cette action est irréversible."
          confirmLabel="Effacer"
          cancelLabel="Annuler"
          onConfirm={handleClearHistory}
          onCancel={() => setConfirmClearOpen(false)}
        />
      )}

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain pr-1">
        {messages.length === 0 && (
          <div className="flex h-full min-h-40 flex-col items-center justify-center gap-3 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-400/20 text-blue-300">
              <ChatEmptyIcon />
            </span>
            <div>
              <p className="text-sm font-medium text-gray-300">Commencez la conversation</p>
              <p className="mt-1 max-w-sm text-sm text-gray-500">
                Posez une question, demandez la météo, un cours de bourse ou de devise, une fiche de roi de France...
              </p>
            </div>
          </div>
        )}
          {messages.map((msg, i) => (
          <div
            key={msg.id || i}
            className={`flex items-end gap-2 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.sender !== 'user' && <MessageAvatar sender={msg.sender} />}
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-6 sm:max-w-[70%] ${
                msg.sender === 'user'
                  ? // Bords blancs fins + ombre portée + liseré clair en haut (inset) pour un effet
                    // 3D/relief, plutôt que le simple shadow-sm plat des autres bulles.
                    'border border-white/25 bg-gradient-to-br from-blue-600 to-blue-500 text-white shadow-[0_4px_14px_rgba(8,15,35,0.45),inset_0_1px_0_rgba(255,255,255,0.35)]'
                  : msg.sender === 'error'
                    ? 'border border-red-800/60 bg-red-950/40 text-red-200 shadow-sm'
                    : msg.sourceType === 'calendar_assistant'
                      ? 'border border-blue-800/40 bg-gradient-to-br from-gray-800 to-blue-950/30 text-gray-100 shadow-sm shadow-blue-950/20'
                      : 'border border-gray-700/60 bg-gray-800 text-gray-100 shadow-sm'
              }`}
            >
              {msg.sender === 'aria' && (
                <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
                  <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 ${sourceBadgeClass(msg)}`}>
                    {msg.loading ? (
                      <LoadingIcon />
                    ) : (
                      <SourceIcon
                        type={
                          msg.sourceType === 'calendar_assistant'
                            ? 'calendar'
                            : msg.source === 'local'
                              ? (msg.sourceType === 'weather' ? msg.weatherType : msg.sourceType)
                              : 'ai'
                        }
                      />
                    )}
                    {sourceBadgeLabel(msg)}
                  </span>
                </div>
              )}
              {msg.loading ? (
                <TypingSkeleton />
              ) : msg.sourceType === 'city_info' ? (
                <CityInfoCard data={msg.data} title={msg.text} />
              ) : (msg.sourceType === 'departement_info' || msg.sourceType === 'region_info') ? (
                <AreaInfoCard data={msg.data} />
              ) : msg.sourceType === 'time' && msg.timeData ? (
                <div className="min-w-[17rem] sm:min-w-[28rem]">
                  <div className="flex flex-wrap items-end justify-between gap-4 border-b border-gray-600/60 pb-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Heure locale</p>
                      <p className="mt-1 text-4xl font-semibold tracking-tight text-white">{msg.timeData.time}</p>
                      <p className="mt-1 text-sm text-gray-300">{msg.timeData.location}</p>
                    </div>
                    <div className="rounded-lg border border-blue-400/30 bg-blue-500/10 px-3 py-2 text-right">
                      <p className="text-xs text-gray-400">Décalage</p>
                      <p className="font-semibold text-blue-300">{msg.timeData.offset}</p>
                    </div>
                  </div>
                  <p className="mt-4 text-sm font-medium capitalize text-gray-200">{msg.timeData.date}</p>
                  <p className="mt-1 text-xs text-gray-400">{msg.timeData.season}</p>
                  <div className="mt-4 grid grid-cols-2 gap-2">
                    <div className="rounded-lg border border-amber-400/20 bg-amber-400/10 p-3">
                      <p className="text-xs text-gray-400">Lever du soleil</p>
                      <p className="mt-1 text-lg font-semibold text-amber-200">{msg.timeData.sunrise}</p>
                    </div>
                    <div className="rounded-lg border border-indigo-400/20 bg-indigo-400/10 p-3">
                      <p className="text-xs text-gray-400">Coucher du soleil</p>
                      <p className="mt-1 text-lg font-semibold text-indigo-200">{msg.timeData.sunset}</p>
                    </div>
                  </div>
                </div>
              ) : msg.sourceType === 'world_time' ? (
                <div className="min-w-[15rem] sm:min-w-[20rem]">
                  <div className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
                    <span className="rounded-md bg-blue-500/15 p-2 text-blue-300"><ClockIcon /></span>
                    {msg.text}
                  </div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {msg.data?.map((item) => (
                      <div key={item.city} className="flex items-center justify-between rounded-md border border-gray-600/60 bg-gray-900/40 px-3 py-2">
                        <span className="text-gray-300">{item.city}</span>
                        <span className="font-semibold tabular-nums text-blue-300">{item.time}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : msg.sourceType === 'forex' ? (
                <ForexCard data={msg.data} />
              ) : msg.sourceType === 'market_overview' ? (
                <MarketOverviewCard data={msg.data} title={msg.text} />
              ) : (msg.sourceType === 'stock' || msg.sourceType === 'etf') && msg.data ? (
                <QuoteCard quote={msg.data} fallbackText={msg.text} />
              ) : msg.sourceType === 'cac40' && msg.data ? (
                <QuoteCard quote={msg.data} fallbackText={msg.text} note="EODHD · clôture de fin de journée, pas temps réel." />
              ) : msg.sourceType === 'commodities' && msg.data ? (
                <QuoteCard quote={msg.data} fallbackText={msg.text} note="Twelve Data · métaux précieux." />
              ) : msg.sourceType === 'king' && Array.isArray(msg.data) ? (
                <KingsTimeline kings={msg.data} onSelectKing={(king) => handleSend(`roi ${kingBaseName(king.name)}`)} />
              ) : msg.sourceType === 'king' && msg.data ? (
                <KingCard king={msg.data} />
              ) : (
                // whitespace-pre-wrap : respecte les retours à la ligne que l'IA écrit (utile pour
                // les listes de plusieurs rendez-vous, un par ligne) tout en gardant le retour à la
                // ligne automatique sur les lignes longues.
                <div className="whitespace-pre-wrap">
                  <FormattedText text={msg.text} />
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form
        className="sticky bottom-0 mt-3 flex shrink-0 gap-2 border-t border-gray-800 bg-gray-900 pt-3"
        onSubmit={(event) => {
          event.preventDefault()
          handleSend()
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleInputKeyDown}
          title="Flèche haut/bas : parcourir les messages envoyés"
          className="min-w-0 flex-1 rounded-xl border border-gray-700 bg-gray-800 px-4 py-3 text-sm text-white outline-none transition placeholder:text-gray-500 focus:border-blue-500"
          placeholder="Écrire un message..."
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-2 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 px-4 text-sm font-semibold text-white shadow-md shadow-blue-950/30 transition hover:from-blue-500 hover:to-cyan-400 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none sm:px-6"
        >
          {!loading && <SendIcon />}
          {loading ? 'Envoi...' : 'Envoyer'}
        </button>
      </form>
    </section>
  )
}

function AreaInfoCard({ data }) {
  const kindLabel = data.kind === 'region' ? 'Région' : 'Département'
  return (
    <div className="w-full min-w-0 max-w-2xl">
      <div className="flex flex-col gap-3 border-b border-gray-600/60 pb-4 sm:flex-row sm:items-start">
        <span className="w-fit rounded-lg bg-cyan-500/15 p-3 text-cyan-300"><CityInfoIcon /></span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan-300">{kindLabel}</p>
          <h3 className="mt-1 text-xl font-semibold text-white">{data.nom}</h3>
          <p className="text-sm text-gray-400">{data.parent_label}</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 min-[420px]:grid-cols-2 xl:grid-cols-4">
        <InfoMetric label="Population" value={data.population} />
        <InfoMetric label="Superficie" value={data.area} />
        <InfoMetric label="Communes" value={data.nb_communes} />
        <InfoMetric label="Ville principale" value={data.largest_city} />
      </div>
      <div className="mt-4 grid gap-3 border-t border-gray-600/60 pt-4 text-sm leading-6 text-gray-300">
        <DetailBlock title="Niveau de vie" value={data.living_level} />
        <DetailBlock title="Budget pour vivre correctement" value={data.comfortable_budget} />
        <DetailBlock title="Repère historique" value={data.history} />
      </div>
    </div>
  )
}

function CityInfoCard({ data, title }) {
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState(null)
  const [detailsOverride, setDetailsOverride] = useState(null)
  const [confirmRefresh, setConfirmRefresh] = useState(false)

  const cityKey = (data.city || '').toLowerCase()
  const housingPrice = detailsOverride?.housing_price ?? data.housing_price
  const comfortableBudget = detailsOverride?.comfortable_budget ?? data.comfortable_budget

  const refreshDetails = async () => {
    setDetailsLoading(true)
    setDetailsError(null)
    try {
      const res = await fetch(`/api/city-details/${encodeURIComponent(cityKey)}/refresh`, { method: 'POST' })
      const body = await res.json()
      if (!res.ok) throw new Error(body.detail || `Erreur (${res.status})`)
      setDetailsOverride(body.data)
    } catch (error) {
      setDetailsError(error.message || 'Erreur lors de la récupération des détails')
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleToggleDetails = async () => {
    if (detailsOpen) {
      setDetailsOpen(false)
      return
    }
    setDetailsOpen(true)
    if (detailsOverride) return // déjà actualisé cette session, pas besoin de re-vérifier

    setDetailsLoading(true)
    setDetailsError(null)
    try {
      const res = await fetch(`/api/city-details/${encodeURIComponent(cityKey)}/status`)
      const body = await res.json()
      if (!res.ok) throw new Error(body.detail || `Erreur (${res.status})`)
      setDetailsLoading(false)
      if (body.has_cached_details) {
        setConfirmRefresh(true) // des détails existent déjà : on demande avant de relancer les API
      } else {
        await refreshDetails()
      }
    } catch (error) {
      setDetailsLoading(false)
      setDetailsError(error.message || 'Erreur lors de la vérification des détails')
    }
  }

  return (
    <div className="w-full min-w-0 max-w-2xl">
      <div className="flex flex-col gap-3 border-b border-gray-600/60 pb-4 sm:flex-row sm:items-start">
        <span className="w-fit rounded-lg bg-cyan-500/15 p-3 text-cyan-300"><CityInfoIcon /></span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-cyan-300">Fiche locale</p>
          <h3 className="mt-1 text-xl font-semibold text-white">{data.city}</h3>
          <p className="text-sm text-gray-400">{data.country}</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 min-[420px]:grid-cols-2 xl:grid-cols-4">
        <InfoMetric label="Population" value={data.population} />
        <InfoMetric label="Superficie" value={data.area} />
        <InfoMetric label="Division" value={data.division} />
        <InfoMetric label="Endroits à visiter" value={data.places_to_visit} />
      </div>
      <p className="mt-4 text-sm leading-6 text-gray-300">{data.economy}</p>
      <button type="button" onClick={handleToggleDetails} className="mt-4 inline-flex min-h-[44px] items-center rounded-md border border-cyan-700/60 px-3 text-sm font-medium text-cyan-300 hover:bg-cyan-950/40">
        {detailsOpen ? 'Réduire les détails' : 'Voir les détails'}
      </button>
      {detailsOpen && (
        <div className="mt-4 grid gap-3 border-t border-gray-600/60 pt-4 text-sm leading-6 text-gray-300">
          <DetailBlock title="Découpage du pays" value={data.country_division} />
          <DetailBlock title="Diversité" value={data.ethnicity} />
          <DetailBlock title="Points forts" value={data.strengths.join(' • ')} />
          <DetailBlock title="Points de vigilance" value={data.weaknesses.join(' • ')} />
          <DetailBlock title="Position" value={data.position} />
          <DetailBlock title="Niveau de vie" value={data.living_level} />
          <DetailBlock title="Prix indicatif au m²" value={detailsLoading ? 'Récupération en cours...' : housingPrice} />
          <DetailBlock title="Budget pour vivre correctement" value={detailsLoading ? 'Récupération en cours...' : comfortableBudget} />
          <DetailBlock title="Repère historique" value={data.history} />
          {detailsError && <p className="text-xs text-red-400">{detailsError}</p>}
        </div>
      )}
      {confirmRefresh && (
        <ConfirmModal
          message={`Le prix au m² et le budget de vie de ${data.city} sont déjà enregistrés. Les actualiser avec des données fraîches ?`}
          confirmLabel="Actualiser"
          cancelLabel="Garder les données actuelles"
          onConfirm={() => { setConfirmRefresh(false); refreshDetails() }}
          onCancel={() => setConfirmRefresh(false)}
        />
      )}
    </div>
  )
}

// role="dialog"/aria-modal + focus initial sur "Annuler" (l'action la moins destructive) +
// fermeture au clavier avec Échap : avant cette passe, l'ouverture n'était ni annoncée aux
// lecteurs d'écran, ni pilotable au clavier autrement que par Tab. Corrigé lors de l'audit
// accessibilité du 10/09/2026.
function ConfirmModal({ message, confirmLabel, cancelLabel, onConfirm, onCancel }) {
  const cancelRef = useRef(null)

  useEffect(() => {
    cancelRef.current?.focus()
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onCancel])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onCancel}>
      <div
        role="dialog"
        aria-modal="true"
        aria-describedby="confirm-modal-message"
        className="w-full max-w-sm rounded-xl border border-gray-700 bg-gray-800 p-5 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <p id="confirm-modal-message" className="text-sm leading-6 text-gray-200">{message}</p>
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <button ref={cancelRef} type="button" onClick={onCancel} className="inline-flex min-h-[44px] items-center rounded-md border border-gray-600 px-3 text-sm text-gray-300 hover:bg-gray-700">
            {cancelLabel}
          </button>
          <button type="button" onClick={onConfirm} className="inline-flex min-h-[44px] items-center rounded-md bg-cyan-600 px-3 text-sm font-medium text-white hover:bg-cyan-500">
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

function InfoMetric({ label, value }) {
  return <div className="min-w-0 rounded-lg border border-gray-600/60 bg-gray-900/40 p-3"><p className="text-[11px] uppercase tracking-wide text-gray-500">{label}</p><p className="mt-1 break-words text-sm font-medium text-gray-200">{value}</p></div>
}

function DetailBlock({ title, value }) {
  return <div><p className="font-semibold text-cyan-300">{title}</p><p>{value}</p></div>
}

// Vignette prix + variation (flèche + couleur selon le signe), réutilisée par MarketOverviewCard
// et QuoteCard (actions/ETF partagent le même format de cours chez Twelve Data).
function QuoteMetric({ label, price, currency, change, percentChange, large }) {
  const changeValue = Number(change)
  const isUp = Number.isFinite(changeValue) && changeValue > 0
  const isDown = Number.isFinite(changeValue) && changeValue < 0
  const colorClass = isUp ? 'text-emerald-300' : isDown ? 'text-rose-300' : 'text-gray-300'
  const hasChange = change !== undefined && change !== null && percentChange !== undefined && percentChange !== null
  return (
    <div className="min-w-0 rounded-lg border border-gray-600/60 bg-gray-900/40 p-3">
      <p className="text-[11px] uppercase tracking-wide text-gray-500">{label}</p>
      <p className={`mt-1 font-semibold tabular-nums text-white ${large ? 'text-2xl' : 'text-sm'}`}>
        {price} <span className="text-xs font-normal text-gray-400">{currency}</span>
      </p>
      {hasChange && (
        <p className={`mt-1 text-xs font-medium tabular-nums ${colorClass}`}>
          {isUp ? '▲' : isDown ? '▼' : '·'} {change} ({percentChange} %)
        </p>
      )}
    </div>
  )
}

function ForexCard({ data }) {
  const rates = data?.rates || []
  return (
    <div className="w-full min-w-0 max-w-md">
      <div className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
        <span className="rounded-md bg-emerald-500/15 p-2 text-emerald-300"><ExchangeIcon /></span>
        Cours des devises
      </div>
      {rates.length ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {rates.map((item) => (
            <div key={item.pair} className="rounded-lg border border-gray-600/60 bg-gray-900/40 px-3 py-2 text-center">
              <p className="text-[11px] uppercase tracking-wide text-gray-500">{item.pair}</p>
              <p className="mt-1 text-sm font-semibold tabular-nums text-emerald-300">{item.rate}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-400">Cours indisponibles pour le moment.</p>
      )}
      <p className="mt-3 text-xs text-gray-500">
        Banque Centrale Européenne{data?.date ? ` · ${data.date}` : ''} · cours quotidien, pas temps réel.
      </p>
    </div>
  )
}

function MarketOverviewCard({ data, title }) {
  const indices = data || []
  return (
    <div className="w-full min-w-0 max-w-md">
      <div className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
        <span className="rounded-md bg-amber-500/15 p-2 text-amber-300"><TrendIcon /></span>
        {title}
      </div>
      {indices.length ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          {indices.map((item) => (
            <QuoteMetric
              key={item.symbol}
              label={item.label}
              price={item.price}
              currency={item.currency}
              change={item.change}
              percentChange={item.percent_change}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-400">Tendances indisponibles pour le moment.</p>
      )}
      <p className="mt-3 text-xs text-gray-500">
        Via ETF de référence (SPY, DIA, QQQ) — marchés américains uniquement pour l'instant.
      </p>
    </div>
  )
}

function QuoteCard({ quote, fallbackText, note }) {
  if (!quote) return fallbackText
  return (
    <div className="w-full min-w-0 max-w-xs">
      <div className="mb-3 flex items-start gap-2 text-base font-semibold text-white">
        <span className="rounded-md bg-amber-500/15 p-2 text-amber-300"><TrendIcon /></span>
        <div className="min-w-0">
          <p className="truncate">{quote.name}</p>
          <p className="truncate text-xs font-normal text-gray-400">
            {quote.symbol}
            {quote.exchange ? ` · ${quote.exchange}` : ''}
          </p>
        </div>
      </div>
      <QuoteMetric
        label="Cours"
        price={quote.price}
        currency={quote.currency}
        change={quote.change}
        percentChange={quote.percent_change}
        large
      />
      {note && <p className="mt-3 text-xs text-gray-500">{note}</p>}
    </div>
  )
}

const FRENCH_MONTHS = [
  'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
  'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
]

// "1643-05-14" -> "14 mai 1643". Les autres formats renvoyés par kings_service.py (année seule
// "481", approximatif "vers 466") n'ont pas de mois/jour à convertir : on les affiche tels quels.
function formatKingDate(raw) {
  if (!raw) return null
  const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!match) return raw
  const [, year, month, day] = match
  const monthName = FRENCH_MONTHS[Number(month) - 1]
  return monthName ? `${Number(day)} ${monthName} ${year}` : raw
}

// "Louis IX (Saint Louis)" -> "Louis IX" : le nom affiché dans la frise inclut le surnom entre
// parenthèses (voir _display_name côté backend), mais "roi louis ix saint louis" ne matcherait
// rien en base — kings_service.py cherche sur le nom OU l'alt_name séparément, pas la
// concatenation des deux. On renvoie donc juste le nom principal pour la requête au clic.
function kingBaseName(name) {
  return name.replace(/\s*\([^)]*\)\s*$/, '').trim()
}

// Bloc "titre + liste à puces (nom + notes)" partagé par les sections dépliables de KingCard
// (épouses, favorites, enfants, guerres/événements) — même esprit que DetailBlock pour les fiches
// ville/département, adapté aux tableaux d'éléments plutôt qu'à une valeur unique.
function KingListBlock({ title, items }) {
  return (
    <div>
      <p className="font-semibold text-yellow-300">{title}</p>
      <ul className="mt-1 list-disc space-y-1 pl-5">
        {items.map((item, i) => (
          <li key={i}>
            <span className="font-medium text-gray-200">{item.name}</span>
            {item.notes && <span className="text-gray-400"> — {item.notes}</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}

// Couleurs par dynastie pour la frise (KingsTimeline) — repère visuel rapide entre Mérovingiens/
// Carolingiens/Capétiens/Valois/Bourbon sans avoir à lire chaque ligne. Dynastie absente ou non
// reconnue -> gris neutre, jamais une couleur au hasard. Trois variantes de la même teinte : le
// point (contour clair + remplissage), le fil vertical (semi-transparent, discret) et un badge
// (fond très sombre + texte clair) réutilisé pour le libellé de dynastie dans chaque en-tête.
const DYNASTY_STYLE = {
  'Mérovingiens': { dot: 'border-purple-200 bg-purple-400', line: 'bg-purple-500/40', badge: 'bg-purple-950/50 text-purple-300' },
  'Carolingiens': { dot: 'border-sky-200 bg-sky-400', line: 'bg-sky-500/40', badge: 'bg-sky-950/50 text-sky-300' },
  'Capétiens': { dot: 'border-emerald-200 bg-emerald-400', line: 'bg-emerald-500/40', badge: 'bg-emerald-950/50 text-emerald-300' },
  'Valois': { dot: 'border-rose-200 bg-rose-400', line: 'bg-rose-500/40', badge: 'bg-rose-950/50 text-rose-300' },
  'Bourbon': { dot: 'border-yellow-200 bg-yellow-400', line: 'bg-yellow-500/40', badge: 'bg-yellow-950/50 text-yellow-300' },
}
const DYNASTY_STYLE_DEFAULT = { dot: 'border-gray-200 bg-gray-400', line: 'bg-gray-600/40', badge: 'bg-gray-800/60 text-gray-300' }
const DYNASTY_LEGEND_ORDER = ['Mérovingiens', 'Carolingiens', 'Capétiens', 'Valois', 'Bourbon']

function dynastyStyle(dynasty) {
  return DYNASTY_STYLE[dynasty] || DYNASTY_STYLE_DEFAULT
}

// Frise chronologique verticale des rois de France (source_type "king", quand la réponse est une
// liste — liste complète "rois"/"rois de france", ou désambiguïsation d'un nom porté par
// plusieurs rois type "rois louis"). Groupée par dynastie, avec un fil coloré continu qui change
// de teinte à chaque changement de dynastie, pour rester lisible et sympa à parcourir même sur
// les 85 rois (demande explicite : "faire une frise pour rois de france, un truc sympa et très
// lisible", puis "améliore encore l'apparence de la frise"). Toutes les données viennent de
// SQLite (kings_service.py), jamais inventées. Chaque ligne est cliquable (onSelectKing) : le
// clic renvoie "roi <nom>" via handleSend pour récupérer la fiche complète (KingCard) du roi
// choisi — demande explicite : "qd je clique sur un roi je recupere sa card".
function KingsTimeline({ kings, onSelectKing }) {
  if (!kings?.length) return null
  const title = kings.length > 20 ? `Frise des rois de France (${kings.length})` : `Rois trouvés (${kings.length})`
  const dynastiesPresent = DYNASTY_LEGEND_ORDER.filter((d) => kings.some((k) => k.dynasty === d))
  const dynastyCounts = kings.reduce((acc, k) => {
    if (k.dynasty) acc[k.dynasty] = (acc[k.dynasty] || 0) + 1
    return acc
  }, {})
  let lastDynasty = null

  return (
    <div className="w-full min-w-0 max-w-2xl">
      <div className="mb-3 flex items-center gap-2 text-base font-semibold text-white">
        <span className="rounded-md bg-yellow-500/15 p-2 text-yellow-300"><CrownIcon /></span>
        {title}
      </div>

      {dynastiesPresent.length > 1 && (
        <div className="mb-3 flex flex-wrap gap-x-2 gap-y-1.5">
          {dynastiesPresent.map((d) => (
            <span key={d} className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ${dynastyStyle(d).badge}`}>
              <span className={`h-2 w-2 rounded-full border ${dynastyStyle(d).dot}`} />
              {d} <span className="opacity-70">· {dynastyCounts[d]}</span>
            </span>
          ))}
        </div>
      )}

      <div className="relative overflow-hidden rounded-lg border border-gray-700/60 bg-gradient-to-b from-gray-900/60 to-gray-950/60 shadow-inner">
        <div className="max-h-[26rem] overflow-y-auto overscroll-contain pr-2">
          <ol className="relative py-4 pl-6 pr-3">
            {kings.map((king, index) => {
              const showDynastyHeader = king.dynasty !== lastDynasty
              lastDynasty = king.dynasty
              const style = dynastyStyle(king.dynasty)
              const reignStart = formatKingDate(king.reign_start)
              const reignEnd = formatKingDate(king.reign_end)
              return (
                <li key={`${king.name}-${index}`} className="relative pb-5 last:pb-0">
                  <span className={`absolute -left-[1.125rem] top-0 bottom-0 w-0.5 rounded-full ${style.line}`} aria-hidden="true" />
                  {showDynastyHeader && king.dynasty && (
                    <p className="sticky top-0 z-10 -ml-6 mb-2 flex items-baseline gap-1.5 bg-gray-950/95 py-1.5 pl-6 text-[11px] font-semibold uppercase tracking-wider text-gray-300 backdrop-blur-sm">
                      {king.dynasty}
                      <span className="text-[10px] font-normal normal-case text-gray-500">
                        · {dynastyCounts[king.dynasty]} roi{dynastyCounts[king.dynasty] > 1 ? 's' : ''}
                      </span>
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={() => onSelectKing?.(king)}
                    title={`Voir la fiche complète de ${king.name}`}
                    className="-mx-2 w-[calc(100%+1rem)] rounded-md px-2 py-1 text-left transition-colors hover:bg-gray-800/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-yellow-500/60"
                  >
                    {/* Le point est ancré à cette ligne (nom + dates) et centré via top-1/2 +
                        -translate-y-1/2 par rapport à SA propre hauteur — donc toujours aligné
                        sur le texte quel que soit le line-height, au lieu d'un décalage fixe en
                        pixels calé sur le <li> entier qui se désynchronisait du texte. */}
                    <div className="relative flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                      <span
                        className={`absolute -left-[1.3rem] top-1/2 h-3.5 w-3.5 -translate-y-1/2 rounded-full border-2 shadow-sm shadow-black/40 ${style.dot}`}
                        aria-hidden="true"
                      />
                      <p className="font-medium text-gray-100">{king.name}</p>
                      <span className="whitespace-nowrap rounded-md bg-gray-800/70 px-2 py-0.5 text-xs font-medium tabular-nums text-gray-300">
                        {reignStart || '?'} <span className="text-gray-600">→</span> {reignEnd || '?'}
                      </span>
                    </div>
                    {king.reign_end_reason && (
                      <span className="mt-1 inline-block rounded-full border border-amber-700/50 bg-amber-950/40 px-2 py-0.5 text-[10px] font-medium text-amber-300">
                        {king.reign_end_reason}
                      </span>
                    )}
                  </button>
                </li>
              )
            })}
          </ol>
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-gray-950/90 to-transparent" aria-hidden="true" />
      </div>
    </div>
  )
}

// Fiche d'un roi de France (source_type "king", uniquement quand un roi précis a été résolu —
// la liste complète et les messages de désambiguïsation/roi introuvable restent en texte simple,
// voir le rendu dans ChatComponent). Toujours construite depuis kings_service.py/SQLite, jamais
// depuis l'IA générale (demande explicite : pas d'appel IA pour des faits déjà en base).
function KingCard({ king }) {
  const [expanded, setExpanded] = useState(false)
  if (!king) return null

  const reignStart = formatKingDate(king.reign_start)
  const reignEnd = formatKingDate(king.reign_end)
  const birth = formatKingDate(king.birth_date)
  const death = formatKingDate(king.death_date)

  const warsAsItems = (king.wars_events || []).map((w) => ({
    name: w.name,
    notes: [w.years, w.notes].filter(Boolean).join(' — ') || null,
  }))

  const hasDetails = Boolean(
    king.spouses?.length || king.favorites?.length || king.children?.length ||
    warsAsItems.length || king.anecdotes?.length
  )

  return (
    <div className="w-full min-w-0 max-w-2xl">
      <div className="flex flex-col gap-3 border-b border-yellow-700/40 pb-4 sm:flex-row sm:items-start">
        <span className="w-fit rounded-lg bg-yellow-500/15 p-3 text-yellow-300"><CrownIcon /></span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-yellow-300">{king.dynasty || 'Rois de France'}</p>
          <h3 className="mt-1 text-xl font-semibold text-white">{king.name}</h3>
          {(reignStart || reignEnd) && (
            <p className="mt-1 text-sm font-medium tabular-nums text-yellow-200">
              {reignStart || '?'} <span className="text-gray-500">→</span> {reignEnd || '?'}
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 min-[420px]:grid-cols-2">
        <InfoMetric label="Naissance" value={birth || 'inconnue'} />
        <InfoMetric label="Mort" value={death || 'inconnue'} />
      </div>

      {hasDetails && (
        <>
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            className="mt-4 inline-flex min-h-[44px] items-center rounded-md border border-yellow-700/60 px-3 text-sm font-medium text-yellow-300 hover:bg-yellow-950/40"
          >
            {expanded ? 'Réduire les détails' : 'Voir les détails'}
          </button>

          {expanded && (
            <div className="mt-4 grid gap-3 border-t border-gray-600/60 pt-4 text-sm leading-6 text-gray-300">
              {king.spouses?.length > 0 && <KingListBlock title="Épouse(s)" items={king.spouses} />}
              {king.favorites?.length > 0 && <KingListBlock title="Favorites" items={king.favorites} />}
              {king.children?.length > 0 && <KingListBlock title="Enfants notables" items={king.children} />}
              {warsAsItems.length > 0 && <KingListBlock title="Guerres / événements" items={warsAsItems} />}
              {king.anecdotes?.length > 0 && (
                <div>
                  <p className="font-semibold text-yellow-300">Anecdotes</p>
                  <p>{king.anecdotes.join(' ')}</p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
