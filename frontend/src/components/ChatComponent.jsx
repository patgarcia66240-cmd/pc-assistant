import { useState, useRef, useEffect } from 'react'

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

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-3.5 w-3.5" aria-hidden="true">
      <path d="M4 5.5h16v10H9l-5 4v-14Z" />
      <path d="M8 9.5h8M8 13h5" />
    </svg>
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

function CityInfoIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
      <path d="M4 21V5l8-3 8 3v16M8 9h1M15 9h1M8 13h1M15 13h1M8 17h8" />
    </svg>
  )
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

export default function ChatComponent() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const sentMessagesRef = useRef([])
  const historyIndexRef = useRef(-1)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    const sentText = input.trim()
    const newMessage = { text: sentText, sender: 'user' }
    const history = sentMessagesRef.current
    if (history[history.length - 1] !== sentText) {
      history.push(sentText)
    }
    historyIndexRef.current = -1
    setMessages(prev => [...prev, newMessage])
    setInput('')
    setLoading(true)
    const isCityInfoRequest = /^(infos?|informations?)(\s+sur)?\s+/i.test(sentText)
    const pendingId = isCityInfoRequest ? `pending-${Date.now()}` : null
    if (pendingId) {
      setMessages(prev => [...prev, { id: pendingId, text: 'Chargement de la fiche...', sender: 'aria', source: 'local', sourceType: 'city_info', loading: true }])
    }

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
      <div className="mb-3 flex shrink-0 items-center justify-between border-b border-gray-800 pb-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-400">Assistant</p>
          <h2 className="mt-1 text-xl font-semibold text-white">Conversation avec ARIA</h2>
        </div>
        <span className="rounded-full border border-emerald-800 bg-emerald-950/30 px-2 py-1 text-xs text-emerald-400">Prête</span>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain pr-1">
        {messages.length === 0 && (
          <div className="flex h-full min-h-40 items-center justify-center text-center text-sm text-gray-500">
            <p>Écrivez un message pour commencer la conversation.</p>
          </div>
        )}
          {messages.map((msg, i) => (
          <div
            key={msg.id || i}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-4 py-2 text-sm leading-6 sm:max-w-[70%] ${
                msg.sender === 'user' ? 'bg-blue-600' : 'bg-gray-700'
              }`}
            >
              {msg.sender === 'aria' && (
                <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
                  <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 ${msg.source === 'local' ? (msg.sourceType === 'weather' ? 'border-sky-700/60 bg-sky-950/40 text-sky-300' : 'border-emerald-700/60 bg-emerald-950/40 text-emerald-300') : 'border-violet-700/60 bg-violet-950/40 text-violet-300'}`}>
                    {msg.loading ? <LoadingIcon /> : <SourceIcon type={msg.source === 'local' ? (msg.sourceType === 'weather' ? msg.weatherType : msg.sourceType) : 'ai'} />}
                    {msg.source === 'local' ? (msg.sourceType === 'weather' ? 'Météo locale' : msg.sourceType === 'time' ? (msg.timeLabel || 'Heure France') : msg.sourceType === 'city_info' ? 'Infos ville' : 'API système') : 'IA'}
                  </span>
                </div>
              )}
              {msg.loading ? (
                <div className="flex items-center gap-2 py-2 text-sm text-gray-300"><LoadingIcon /> Récupération des informations...</div>
              ) : msg.sourceType === 'city_info' ? (
                <CityInfoCard data={msg.data} title={msg.text} />
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
              ) : msg.text}
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
          className="min-w-0 flex-1 rounded-md border border-gray-700 bg-gray-800 px-4 py-3 text-sm text-white outline-none transition placeholder:text-gray-500 focus:border-blue-500"
          placeholder="Écrire un message..."
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="shrink-0 rounded-md bg-blue-600 px-4 py-3 text-sm font-medium transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50 sm:px-6"
        >
          <span className="flex items-center justify-center gap-2">
            {!loading && <SendIcon />}
            {loading ? 'Envoi...' : 'Envoyer'}
          </span>
        </button>
      </form>
    </section>
  )
}

function CityInfoCard({ data, title }) {
  const [detailsOpen, setDetailsOpen] = useState(false)

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
        <InfoMetric label="Marchés" value={data.markets} />
      </div>
      <p className="mt-4 text-sm leading-6 text-gray-300">{data.economy}</p>
      <button type="button" onClick={() => setDetailsOpen((open) => !open)} className="mt-4 rounded-md border border-cyan-700/60 px-3 py-2 text-sm font-medium text-cyan-300 hover:bg-cyan-950/40">
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
          <DetailBlock title="Prix indicatif au m²" value={data.housing_price} />
          <DetailBlock title="Budget pour vivre correctement" value={data.comfortable_budget} />
          <DetailBlock title="Repère historique" value={data.history} />
        </div>
      )}
    </div>
  )
}

function InfoMetric({ label, value }) {
  return <div className="min-w-0 rounded-lg border border-gray-600/60 bg-gray-900/40 p-3"><p className="text-[11px] uppercase tracking-wide text-gray-500">{label}</p><p className="mt-1 break-words text-sm font-medium text-gray-200">{value}</p></div>
}

function DetailBlock({ title, value }) {
  return <div><p className="font-semibold text-cyan-300">{title}</p><p>{value}</p></div>
}
