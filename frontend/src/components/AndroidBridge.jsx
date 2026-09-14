import { useEffect, useState } from 'react'
import { SkeletonBlock } from './Skeleton'

function PhoneIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-5 w-5" aria-hidden="true">
      <rect x="7" y="2.5" width="10" height="19" rx="2" /><path d="M11 18.5h2" />
    </svg>
  )
}

function StatusDot({ connected }) {
  return (
    <span className="relative flex h-2 w-2">
      {connected && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />}
      <span className={`relative inline-flex h-2 w-2 rounded-full ${connected ? 'bg-emerald-400' : 'bg-gray-600'}`} />
    </span>
  )
}

function Card({ children, className = '' }) {
  return (
    <div className={`rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-5 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)] ${className}`}>
      {children}
    </div>
  )
}

async function readError(response, fallback) {
  try {
    const data = await response.json()
    return data.detail || data.error || fallback
  } catch {
    return fallback
  }
}

function PairingForm({ onPaired }) {
  const [host, setHost] = useState('')
  const [port, setPort] = useState('8765')
  const [token, setToken] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const response = await fetch('/api/android/pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host: host.trim(), port: Number(port), token: token.trim() }),
      })
      if (!response.ok) throw new Error(await readError(response, "Échec de l'appairage"))
      onPaired(await response.json())
    } catch (submitError) {
      setError(submitError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <h3 className="text-lg font-semibold text-white">Appairer un téléphone</h3>
      <p className="mt-1 text-sm text-gray-400">
        Ouvre l'app <strong>ARIA Phone Bridge</strong> sur ton Android, démarre la passerelle depuis
        l'écran principal, et recopie ici l'adresse IP, le port et le jeton affichés — ton téléphone et
        ce PC doivent être sur le même réseau Wi-Fi.
      </p>
      <form onSubmit={handleSubmit} className="mt-4 grid gap-3 sm:grid-cols-[2fr_1fr]">
        <label className="text-xs text-gray-400 sm:col-span-2">
          Adresse IP du téléphone
          <input
            required value={host} onChange={(event) => setHost(event.target.value)}
            placeholder="192.168.1.42"
            className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-900/70 px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:border-blue-500 focus:outline-none"
          />
        </label>
        <label className="text-xs text-gray-400">
          Port
          <input
            required type="number" value={port} onChange={(event) => setPort(event.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-900/70 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
          />
        </label>
        <label className="text-xs text-gray-400">
          Jeton d'appairage
          <input
            required value={token} onChange={(event) => setToken(event.target.value)}
            placeholder="ex. 7f3a-9c21"
            className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-900/70 px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:border-blue-500 focus:outline-none"
          />
        </label>
        <button
          type="submit" disabled={submitting}
          className="rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-blue-950/30 transition-opacity hover:opacity-90 disabled:opacity-50 sm:col-span-2"
        >
          {submitting ? 'Connexion...' : 'Appairer'}
        </button>
      </form>
      {error && <p className="mt-3 rounded-lg border border-red-800 bg-red-950/30 p-3 text-sm text-red-300">{error}</p>}
    </Card>
  )
}

function DeviceCard({ device, onDisconnect, onForget, busy }) {
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="shrink-0 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 p-2 text-white shadow-sm shadow-blue-950/30">
            <PhoneIcon />
          </span>
          <div>
            <h3 className="text-lg font-semibold text-white">{device?.model || 'Téléphone connecté'}</h3>
            <p className="text-sm text-gray-500">{device?.manufacturer ? `${device.manufacturer} · ` : ''}Android {device?.android_version || '?'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-gray-800 bg-gray-900/60 px-3 py-1.5 text-xs text-gray-300">
          <StatusDot connected /> Connecté
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={onDisconnect} disabled={busy}
          className="rounded-lg border border-gray-700 bg-gray-900/60 px-3 py-1.5 text-xs text-gray-300 transition-colors hover:border-gray-600 hover:text-white disabled:opacity-50"
        >
          Déconnecter
        </button>
        <button
          onClick={onForget} disabled={busy}
          className="rounded-lg border border-red-900/60 bg-red-950/20 px-3 py-1.5 text-xs text-red-300 transition-colors hover:border-red-700 hover:text-red-200 disabled:opacity-50"
        >
          Oublier l'appairage
        </button>
      </div>
    </Card>
  )
}

function ContactsSection() {
  const [contacts, setContacts] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')

  const loadContacts = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch('/api/android/contacts')
      if (!response.ok) throw new Error(await readError(response, 'Impossible de charger les contacts'))
      setContacts((await response.json()).contacts || [])
    } catch (loadError) {
      setError(loadError.message)
    } finally {
      setLoading(false)
    }
  }

  const filtered = (contacts || []).filter((contact) => {
    if (!search.trim()) return true
    const needle = search.trim().toLowerCase()
    return (
      contact.name?.toLowerCase().includes(needle) ||
      (contact.numbers || []).some((number) => number.includes(needle))
    )
  })

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Contacts</h3>
          <p className="text-sm text-gray-500">Lus depuis le téléphone à la demande, jamais synchronisés automatiquement</p>
        </div>
        <button
          onClick={loadContacts} disabled={loading}
          className="rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm shadow-blue-950/30 transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {loading ? 'Chargement...' : contacts ? 'Actualiser' : 'Charger les contacts'}
        </button>
      </div>

      {error && <p className="mt-3 rounded-lg border border-red-800 bg-red-950/30 p-3 text-sm text-red-300">{error}</p>}

      {contacts && (
        <>
          <input
            value={search} onChange={(event) => setSearch(event.target.value)}
            placeholder="Rechercher un nom ou un numéro..."
            className="mt-4 w-full rounded-lg border border-gray-700 bg-gray-900/70 px-3 py-2 text-sm text-white placeholder:text-gray-600 focus:border-blue-500 focus:outline-none"
          />
          <div className="mt-3 max-h-96 overflow-y-auto rounded-lg border border-gray-800">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 border-b border-gray-700 bg-gray-900/95 text-xs uppercase tracking-wider text-gray-500">
                <tr>
                  <th className="px-3 py-2.5">Nom</th>
                  <th className="px-3 py-2.5">Numéros</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {filtered.map((contact) => (
                  <tr key={contact.id} className="text-gray-300 transition-colors hover:bg-blue-500/5">
                    <td className="px-3 py-2.5 font-medium text-white">{contact.name || 'Sans nom'}</td>
                    <td className="px-3 py-2.5 tabular-nums text-gray-400">{(contact.numbers || []).join(', ') || '—'}</td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan={2} className="px-3 py-4 text-center text-gray-500">Aucun contact{search ? ' pour cette recherche' : ''}</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-gray-500">{filtered.length} sur {contacts.length} contacts</p>
        </>
      )}
    </Card>
  )
}

function AndroidBridgeSkeleton() {
  return (
    <section className="h-full overflow-y-auto pr-1">
      <div className="mb-6 space-y-2">
        <SkeletonBlock className="h-3 w-32" />
        <SkeletonBlock className="h-7 w-48" />
      </div>
      <SkeletonBlock className="h-40 w-full rounded-xl" />
    </section>
  )
}

export default function AndroidBridge({ isActive = true }) {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!isActive) return undefined
    const controller = new AbortController()
    let refreshTimer = null

    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/android/status', { signal: controller.signal })
        if (!response.ok) throw new Error('Impossible de charger le statut de la passerelle')
        setStatus(await response.json())
        setError('')
      } catch (fetchError) {
        if (fetchError.name !== 'AbortError') setError(fetchError.message)
      } finally {
        if (!controller.signal.aborted) refreshTimer = setTimeout(fetchStatus, 5000)
      }
    }
    fetchStatus()
    return () => {
      controller.abort()
      if (refreshTimer) clearTimeout(refreshTimer)
    }
  }, [isActive])

  const handleDisconnect = async () => {
    setBusy(true)
    try {
      await fetch('/api/android/disconnect', { method: 'POST' })
      setStatus({ connected: false, endpoint: null, device: null })
    } finally {
      setBusy(false)
    }
  }

  const handleForget = async () => {
    setBusy(true)
    try {
      await fetch('/api/android/forget', { method: 'POST' })
      setStatus({ connected: false, endpoint: null, device: null })
    } finally {
      setBusy(false)
    }
  }

  if (error) return <p className="rounded-lg border border-red-800 bg-red-950/30 p-4 text-sm text-red-300">{error}</p>
  if (!status) return <AndroidBridgeSkeleton />

  return (
    <section className="h-full overflow-y-auto pr-1">
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-blue-400">Passerelle</p>
        <h2 className="mt-1 text-2xl font-semibold text-white">Téléphone Android</h2>
        <p className="mt-1 text-sm text-gray-400">Connexion locale (Wi-Fi) vers l'app compagnon ARIA Phone Bridge</p>
      </div>

      <div className="space-y-4">
        {status.connected ? (
          <DeviceCard device={status.device} onDisconnect={handleDisconnect} onForget={handleForget} busy={busy} />
        ) : (
          <PairingForm onPaired={setStatus} />
        )}
        {status.connected && <ContactsSection />}
      </div>
    </section>
  )
}
