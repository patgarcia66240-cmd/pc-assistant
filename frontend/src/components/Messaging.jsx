import { useEffect, useRef, useState } from 'react'

// Statut affiché pour chaque canal externe (WhatsApp, Telegram) — voir backend/plugins/whatsapp
// et backend/plugins/telegram pour ce que ces champs signifient exactement. 404 = le plugin
// backend correspondant est désactivé (pas encore configuré, ou volontairement coupé depuis
// l'onglet Plugins) : ce n'est pas une erreur, juste un état à part — dans ce cas le formulaire
// de configuration ci-dessous reste utilisable quand même (voir backend/plugins/messaging/
// router.py, toujours actif lui, indépendamment de whatsapp/telegram).
const LEVEL_STYLES = {
  ok: { dot: 'bg-emerald-500', badge: 'bg-emerald-900/60 text-emerald-200' },
  warn: { dot: 'bg-amber-500', badge: 'bg-amber-900/60 text-amber-200' },
  off: { dot: 'bg-gray-500', badge: 'bg-gray-700 text-gray-300' },
  error: { dot: 'bg-red-500', badge: 'bg-red-900/60 text-red-200' },
}

function describeWhatsapp(status) {
  if (status.disabled) {
    return { level: 'off', title: 'Pas encore activé', detail: 'Renseigne au moins un numéro autorisé ci-dessous et enregistre pour activer.' }
  }
  if (!status.available) {
    return { level: 'error', title: 'Injoignable', detail: status.error || 'Le backend ARIA ne répond pas.' }
  }
  if (!status.configured) {
    return { level: 'off', title: 'Non configuré', detail: status.reason || 'Secret de pont manquant.' }
  }
  if (!status.bridge_reachable) {
    return { level: 'error', title: 'Pont Node.js injoignable', detail: "whatsapp-bridge/ ne répond pas. ARIA le relance normalement tout seul avec le backend — si ça persiste, regarde run-logs/whatsapp-bridge.log à la racine du projet (node absent du PATH, npm install jamais fait...)." }
  }
  if (!status.connected) {
    // Ce pont tourne désormais en arrière-plan (lancé automatiquement avec le backend, voir
    // plugins/messaging/lifecycle.py) : plus de terminal visible à regarder — le QR code apparaît
    // ici, dans une fenêtre modale, dès que le pont l'a généré (quelques secondes après son
    // lancement). Message différent selon qu'il est déjà là ou encore en cours de génération.
    return status.qr
      ? { level: 'warn', title: 'QR code prêt', detail: 'Clique sur "Afficher le QR code" ci-dessous (ou la fenêtre s\'est déjà ouverte toute seule).' }
      : { level: 'warn', title: 'En attente du QR code', detail: 'Le pont vient de démarrer, génération du QR code en cours — il s\'affichera ici automatiquement dans quelques secondes.' }
  }
  return { level: 'ok', title: 'Connecté', detail: 'ARIA répond aux messages du numéro dédié.' }
}

function describeTelegram(status) {
  if (status.disabled) {
    return { level: 'off', title: 'Pas encore activé', detail: 'Renseigne le token du bot ci-dessous et enregistre pour activer.' }
  }
  if (!status.available) {
    return { level: 'error', title: 'Injoignable', detail: status.error || 'Le backend ARIA ne répond pas.' }
  }
  if (!status.configured) {
    return status.token_configured
      ? { level: 'warn', title: 'Configuration incomplète', detail: 'Ajoute ton identifiant Telegram numérique ci-dessous, puis enregistre.' }
      : { level: 'off', title: 'Non configuré', detail: 'Token du bot manquant.' }
  }
  if (!status.running) {
    return { level: 'warn', title: 'Bot arrêté', detail: "ARIA le lance automatiquement avec le backend — si ça persiste plus d'une minute, regarde run-logs/telegram_bot.log à la racine du projet (token invalide, pas de réseau...)." }
  }
  if (!status.allowed_users_configured) {
    return { level: 'warn', title: 'Bot en ligne, personne autorisé', detail: "Ajoute ton identifiant Telegram ci-dessous : tant que la liste est vide, ARIA ignore tous les messages." }
  }
  return { level: 'ok', title: `Connecté${status.bot_username ? ` (@${status.bot_username})` : ''}`, detail: 'ARIA répond aux messages des utilisateurs autorisés.' }
}

function formatLastSeen(iso) {
  if (!iso) return null
  try {
    return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return null
  }
}

// Bouton "oeil" pour révéler le token Telegram (ajouté le 12/09/2026, demande de Sarah — elle
// veut pouvoir vérifier ce qu'elle a tapé/collé sans avoir à le retaper en aveugle).
function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
      <path d="M2.5 12s3.5-7 9.5-7 9.5 7 9.5 7-3.5 7-9.5 7-9.5-7-9.5-7Z" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="2.8" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4" aria-hidden="true">
      <path
        d="M3 3l18 18M10.6 10.6a2.8 2.8 0 0 0 3.95 3.95M9.3 5.3A9.9 9.9 0 0 1 12 5c6 0 9.5 7 9.5 7a13.5 13.5 0 0 1-2.7 3.6M6.3 6.4A13.6 13.6 0 0 0 2.5 12s3.5 7 9.5 7a9.7 9.7 0 0 0 3.4-.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ChannelIcon({ type }) {
  const paths = {
    whatsapp: <path d="M12 3.5a8.5 8.5 0 0 0-7.3 12.8L3.5 20.5l4.3-1.2A8.5 8.5 0 1 0 12 3.5Zm0 15.4a6.8 6.8 0 0 1-3.5-.96l-.25-.15-2.5.7.7-2.44-.16-.25A6.87 6.87 0 1 1 12 18.9Zm3.75-5.13c-.2-.1-1.2-.6-1.4-.66-.19-.07-.32-.1-.46.1-.13.2-.52.66-.64.8-.12.13-.24.15-.44.05-.2-.1-.86-.32-1.63-1-.6-.55-1-1.22-1.13-1.42-.12-.2-.01-.31.09-.4.09-.1.2-.24.3-.36.1-.13.13-.2.2-.34.06-.13.03-.25-.02-.36-.05-.1-.46-1.12-.63-1.53-.17-.4-.34-.34-.46-.35h-.4c-.13 0-.35.05-.53.25-.18.2-.7.68-.7 1.66s.72 1.93.82 2.06c.1.13 1.4 2.16 3.42 3.02.48.2.85.33 1.14.42.48.15.92.13 1.26.08.39-.06 1.2-.49 1.36-.96.17-.47.17-.87.12-.96-.05-.09-.18-.14-.38-.24Z" />,
    telegram: <path d="M21 4.5 3 11.4c-.5.2-.5.9.05 1.07l4.4 1.38 1.7 5.3c.16.5.8.6 1.13.18l2.16-2.7 4.3 3.2c.45.34 1.1.1 1.22-.45l2.9-13.3c.13-.6-.46-1.1-1-.87ZM8.9 13.4l-1.15-.36 8.9-5.5-6.5 6.9-.1.1-1.15 3.6-.6-3.44a.6.6 0 0 0 .1-.3Z" />,
  }
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="h-6 w-6 shrink-0" aria-hidden="true">
      {paths[type]}
    </svg>
  )
}

// QR code WhatsApp affiché en fenêtre modale plutôt que dans le terminal du pont
// (whatsapp-bridge/) — ajouté le 12/09/2026 à la demande de Sarah. L'image (data URL PNG) vient
// de whatsapp-bridge/index.js (génération via la lib "qrcode"), relayée telle quelle par
// GET /api/whatsapp/status (voir backend/plugins/whatsapp/router.py, qui fusionne déjà tous les
// champs renvoyés par le pont — aucun changement backend n'a été nécessaire pour ce champ "qr").
function QrModal({ qr, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="whatsapp-qr-title">
      <button type="button" aria-label="Fermer" className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 flex w-full max-w-sm flex-col items-center rounded-2xl border border-gray-700 bg-gray-800 p-6 shadow-2xl">
        <div className="flex w-full items-center justify-between">
          <h3 id="whatsapp-qr-title" className="text-base font-semibold text-white">Scanner ce QR code</h3>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-700 hover:text-white"
            aria-label="Fermer"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
        <p className="mt-1 text-center text-xs text-gray-400">
          Sur le téléphone dédié à ARIA : WhatsApp → Appareils liés → Lier un appareil
        </p>
        <img src={qr} alt="QR code WhatsApp à scanner" className="mt-4 h-64 w-64 rounded-lg bg-white p-2" />
        <p className="mt-3 text-center text-xs text-gray-500">
          Laisse cette fenêtre ouverte le temps de scanner — elle se ferme toute seule une fois connecté.
        </p>
      </div>
    </div>
  )
}

function StatusHeader({ icon, name, description, status, describe }) {
  if (!status) {
    return (
      <div className="flex items-center gap-3">
        <ChannelIcon type={icon} />
        <div className="min-w-0">
          <p className="font-medium text-gray-100">{name}</p>
          <p className="text-xs text-gray-500">Chargement…</p>
        </div>
      </div>
    )
  }

  const { level, title, detail } = describe(status)
  const style = LEVEL_STYLES[level]
  const lastSeen = formatLastSeen(status.last_seen)

  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 shrink-0 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 p-2 text-white shadow-sm shadow-blue-950/30">
        <ChannelIcon type={icon} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium text-gray-100">{name}</p>
          <span className="flex items-center gap-1.5 rounded-full px-2 py-0.5">
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden="true" />
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style.badge}`}>{title}</span>
          </span>
        </div>
        <p className="mt-0.5 text-xs text-gray-500">{description}</p>
        <p className="mt-2 text-sm text-gray-300">{detail}</p>
        {lastSeen && <p className="mt-1.5 text-xs text-gray-500">Dernier signe de vie : {lastSeen}</p>}
      </div>
    </div>
  )
}

function FormField({ label, hint, children }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-gray-300">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-gray-500">{hint}</span>}
    </label>
  )
}

const inputClass = 'mt-1 w-full rounded-md border border-gray-700 bg-gray-900/60 px-3 py-1.5 text-sm text-gray-100 placeholder:text-gray-600 focus:border-blue-500 focus:outline-none'

// Le message dépend de ce qui s'est réellement passé côté backend — depuis l'ajout du
// lancement automatique des ponts (12/09/2026, lifecycle.py), un enregistrement classique
// (juste un changement de numéros/identifiants) ne nécessite plus AUCUN redémarrage : le
// réclamer à chaque fois comme avant serait faux et anxiogène. Seule la toute première
// activation d'un canal en a encore besoin (plugin_newly_enabled côté backend), pour que
// FastAPI monte son routeur.
function SaveNotice({ result }) {
  if (!result) return null
  if (result.error) {
    return <p className="mt-3 rounded-md border border-red-800 bg-red-950/30 px-3 py-2 text-xs text-red-300">{result.error}</p>
  }
  if (result.info) {
    return <p className="mt-3 rounded-md border border-blue-800 bg-blue-950/30 px-3 py-2 text-xs text-blue-200">{result.info}</p>
  }
  const lines = []
  if (result.restartRequired) {
    lines.push('Première activation : redémarre le backend ARIA pour que ce canal soit pris en compte.')
  }
  if (result.bridgeAutoStarted) {
    lines.push('Le pont whatsapp-bridge/ a été lancé — le QR code va apparaître ci-dessus dans quelques secondes.')
  }
  if (result.botRestarted) {
    lines.push('Le bot Telegram a redémarré pour prendre en compte le nouveau token.')
  } else if (result.botAutoStarted) {
    lines.push('Le bot Telegram a été lancé.')
  }
  if (!lines.length) {
    lines.push('Configuration enregistrée — déjà prise en compte, rien de plus à faire.')
  }
  return (
    <p className="mt-3 rounded-md border border-amber-800/60 bg-amber-950/40 px-3 py-2 text-xs text-amber-200">
      {lines.join(' ')}
    </p>
  )
}

// La notice de succès ("texte jaune") se referme toute seule au bout de 2s — demandé par Sarah
// le 12/09/2026 : une fois lue, elle n'a plus de raison de rester affichée indéfiniment tant que
// le formulaire n'est pas ressaisi. Les erreurs (result.error), elles, restent visibles — pas de
// raison de les faire disparaître avant qu'elle ait pu les lire et corriger.
function useAutoDismiss(result, setResult) {
  useEffect(() => {
    if (!result || result.error) return undefined
    const timer = setTimeout(() => setResult(null), result.info ? 6000 : 2000)
    return () => clearTimeout(timer)
  }, [result, setResult])
}

function WhatsappConfigForm({ config, onSaved }) {
  const [numbers, setNumbers] = useState('')
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState(null)
  useAutoDismiss(result, setResult)

  useEffect(() => {
    if (config) setNumbers(config.allowed_numbers || '')
  }, [config])

  async function handleSave(event) {
    event.preventDefault()
    setSaving(true)
    setResult(null)
    try {
      const response = await fetch('/api/messaging/whatsapp-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ allowed_numbers: numbers }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`)
      setResult({
        secretGenerated: data.secret_generated,
        restartRequired: data.restart_required,
        bridgeAutoStarted: data.bridge_auto_started,
      })
      onSaved()
    } catch (error) {
      setResult({ error: error.message })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSave} className="mt-4 border-t border-gray-800 pt-4">
      <FormField label="Numéros autorisés" hint="Séparés par des virgules, avec l'indicatif pays (ex : 33612345678, 33698765432). Tant que cette liste est vide, ARIA ignore tous les messages WhatsApp.">
        <input
          type="text"
          className={inputClass}
          value={numbers}
          onChange={(event) => setNumbers(event.target.value)}
          placeholder="33612345678, 33698765432"
        />
      </FormField>
      <button
        type="submit"
        disabled={saving}
        className="mt-3 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
      >
        {saving ? 'Enregistrement…' : 'Enregistrer et activer'}
      </button>
      <SaveNotice result={result} />
    </form>
  )
}

function TelegramConfigForm({ config, onSaved }) {
  const [botToken, setBotToken] = useState('')
  const [showToken, setShowToken] = useState(false)
  const [userIds, setUserIds] = useState('')
  const [detectedUsers, setDetectedUsers] = useState([])
  const [detecting, setDetecting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState(null)
  useAutoDismiss(result, setResult)

  useEffect(() => {
    if (config) setUserIds(config.allowed_user_ids || '')
  }, [config])

  async function detectUserId() {
    setDetecting(true)
    setResult(null)
    try {
      const response = await fetch('/api/messaging/telegram-users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bot_token: botToken || null }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`)
      const users = data.users || []
      setDetectedUsers(users)
      if (users.length === 1) {
        setUserIds(users[0].id)
        setResult({ info: 'Identifiant détecté. Clique maintenant sur « Enregistrer et activer ».' })
      } else if (users.length === 0) {
        setResult({ error: 'Aucun compte détecté. Envoie d’abord un message à ton bot Telegram, puis réessaie.' })
      }
    } catch (error) {
      setResult({ error: error.message })
    } finally {
      setDetecting(false)
    }
  }

  async function handleSave(event) {
    event.preventDefault()
    setSaving(true)
    setResult(null)
    try {
      const response = await fetch('/api/messaging/telegram-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bot_token: botToken || null, allowed_user_ids: userIds }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`)
      setBotToken('')
      setResult({
        restartRequired: data.restart_required,
        botAutoStarted: data.bot_auto_started,
        botRestarted: data.bot_restarted,
      })
      onSaved()
    } catch (error) {
      setResult({ error: error.message })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSave} className="mt-4 border-t border-gray-800 pt-4">
      <FormField
        label="Token du bot"
        hint={config?.bot_token_configured ? 'Déjà enregistré — laisse vide pour ne pas le changer.' : 'Créé en écrivant à @BotFather sur Telegram (/newbot).'}
      >
        <div className="relative">
          <input
            type={showToken ? 'text' : 'password'}
            className={`${inputClass} pr-9`}
            value={botToken}
            onChange={(event) => setBotToken(event.target.value)}
            placeholder={config?.bot_token_configured ? '••••••••••••' : '1234567890:AAbecdEFghij...'}
            autoComplete="off"
          />
          <button
            type="button"
            onClick={() => setShowToken((visible) => !visible)}
            className="absolute inset-y-0 right-0 mt-1 flex w-9 items-center justify-center text-gray-500 hover:text-gray-300"
            aria-label={showToken ? 'Masquer le token' : 'Afficher le token'}
          >
            {showToken ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        </div>
      </FormField>
      <div className="mt-3">
        <FormField label="Identifiants Telegram autorisés" hint="Séparés par des virgules — demande le tien à @userinfobot sur Telegram. Tant que cette liste est vide, ARIA ignore tous les messages.">
          <input
            type="text"
            className={inputClass}
            value={userIds}
            onChange={(event) => setUserIds(event.target.value)}
            placeholder="123456789"
            inputMode="numeric"
            pattern="[0-9,\s]+"
            required
          />
        </FormField>
        <button
          type="button"
          onClick={detectUserId}
          disabled={detecting}
          className="mt-2 rounded-md border border-blue-700 px-3 py-1.5 text-xs font-medium text-blue-200 transition-colors hover:bg-blue-950/50 disabled:opacity-50"
        >
          {detecting ? 'Détection…' : 'Détecter mon ID'}
        </button>
        {detectedUsers.length > 1 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {detectedUsers.map((user) => (
              <button
                key={user.id}
                type="button"
                onClick={() => setUserIds(user.id)}
                className="rounded-md border border-gray-700 bg-gray-900/60 px-3 py-1.5 text-left text-xs text-gray-200 hover:border-blue-600"
              >
                {[user.first_name, user.last_name].filter(Boolean).join(' ') || 'Compte Telegram'}
                {user.username ? ` (@${user.username})` : ''} — {user.id}
              </button>
            ))}
          </div>
        )}
      </div>
      <button
        type="submit"
        disabled={saving}
        className="mt-3 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
      >
        {saving ? 'Enregistrement…' : 'Enregistrer et activer'}
      </button>
      <SaveNotice result={result} />
    </form>
  )
}

// Carnet de contacts (nom -> numéro WhatsApp / identifiant Telegram) — ajouté le 12/09/2026 :
// sans ça, dire "envoie un message whatsapp à Sophie" depuis le Chat ou le Vocal (voir
// backend/plugins/messaging/chat_handler.py) ne peut pas savoir à quel numéro ça correspond, il
// faudrait le redonner en toutes lettres à chaque fois.
function ContactsCard() {
  const [contacts, setContacts] = useState([])
  const [name, setName] = useState('')
  const [whatsapp, setWhatsapp] = useState('')
  const [telegram, setTelegram] = useState('')
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState(null)
  useAutoDismiss(result, setResult)

  // Import depuis WhatsApp/Telegram (WhatsApp le 12/09/2026, Telegram ajouté juste après) :
  // liste brute des contacts connus côté pont, séparée du carnet lui-même (`contacts`
  // ci-dessus) — un clic sur "Ajouter" appelle importContact, qui réutilise le même
  // PUT /api/messaging/contacts que le formulaire manuel. importChannel vaut null (fermé),
  // 'whatsapp' ou 'telegram' — un seul panneau ouvert à la fois.
  // Les deux canaux n'ont PAS la même nature : WhatsApp (Baileys) simule un vrai appareil lié et
  // reçoit donc une vraie synchronisation du répertoire téléphonique ; un bot Telegram, lui, n'a
  // accès qu'aux personnes qui lui ont déjà écrit au moins une fois (l'API Bot ne permet rien de
  // plus) — voir GET /api/telegram/contacts côté backend pour le détail.
  const [importChannel, setImportChannel] = useState(null)
  const [importLoading, setImportLoading] = useState(false)
  const [importError, setImportError] = useState(null)
  const [importCandidates, setImportCandidates] = useState([])
  const [addingValue, setAddingValue] = useState(null)

  async function loadContacts() {
    try {
      const response = await fetch('/api/messaging/contacts')
      if (!response.ok) return
      const data = await response.json()
      setContacts(data.contacts || [])
    } catch {
      // Best-effort : la liste reste juste vide/périmée si le backend ne répond pas.
    }
  }

  useEffect(() => {
    loadContacts()
  }, [])

  async function openImport(channel) {
    if (importChannel === channel) {
      setImportChannel(null) // déjà ouvert sur ce canal -> un second clic referme
      return
    }
    setImportChannel(channel)
    setImportError(null)
    setImportCandidates([])
    setImportLoading(true)
    try {
      const response = await fetch(`/api/${channel}/contacts`)
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`)
      // Le pont WhatsApp renvoie {number, name} (voir GET /api/whatsapp/contacts), le carnet
      // Telegram {id, name} (voir GET /api/telegram/contacts) — normalisé ici en {value, name}
      // pour que le reste du composant n'ait pas à distinguer les deux canaux.
      const normalized = (data.contacts || []).map((item) => ({ value: item.number ?? item.id, name: item.name }))
      setImportCandidates(normalized)
    } catch (error) {
      setImportError(error.message)
    } finally {
      setImportLoading(false)
    }
  }

  function alreadySaved(channel, value) {
    return contacts.some((contact) => contact[channel] === value)
  }

  async function importContact(channel, candidate) {
    setAddingValue(candidate.value)
    try {
      // Le champ de l'autre canal est laissé à null ("non fourni", pas "à effacer") :
      // upsert_contact (backend) fusionne avec ce qui existe déjà pour ce nom plutôt que de
      // l'écraser — voir le commentaire de upsert_contact dans contacts.py.
      const response = await fetch('/api/messaging/contacts', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: candidate.name,
          whatsapp: channel === 'whatsapp' ? candidate.value : null,
          telegram: channel === 'telegram' ? candidate.value : null,
        }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      await loadContacts()
    } catch {
      // Best-effort : le contact reste dans la liste d'import, réessayable.
    } finally {
      setAddingValue(null)
    }
  }

  async function handleSave(event) {
    event.preventDefault()
    setSaving(true)
    setResult(null)
    try {
      const response = await fetch('/api/messaging/contacts', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, whatsapp: whatsapp || null, telegram: telegram || null }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`)
      setName('')
      setWhatsapp('')
      setTelegram('')
      setResult({})
      loadContacts()
    } catch (error) {
      setResult({ error: error.message })
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(contactName) {
    try {
      await fetch(`/api/messaging/contacts/${encodeURIComponent(contactName)}`, { method: 'DELETE' })
    } finally {
      loadContacts()
    }
  }

  return (
    <div className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-4 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-gray-100">Carnet de contacts</p>
        <div className="flex shrink-0 gap-3">
          <button
            type="button"
            onClick={() => openImport('whatsapp')}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            {importChannel === 'whatsapp' ? 'Fermer' : 'Importer depuis WhatsApp'}
          </button>
          <button
            type="button"
            onClick={() => openImport('telegram')}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            {importChannel === 'telegram' ? 'Fermer' : 'Importer depuis Telegram'}
          </button>
        </div>
      </div>
      <p className="mt-0.5 text-xs text-gray-500">
        Pour dire « envoie un message whatsapp à Sophie... » depuis le Chat ou le Vocal, sans redonner son numéro à chaque fois.
      </p>

      {importChannel && (
        <div className="mt-3 rounded-md border border-gray-800 bg-gray-900/40 p-3">
          {importLoading && (
            <p className="text-xs text-gray-500">
              Récupération des contacts {importChannel === 'whatsapp' ? 'WhatsApp' : 'Telegram'}…
            </p>
          )}
          {importError && <p className="text-xs text-red-300">{importError}</p>}
          {!importLoading && !importError && importCandidates.length === 0 && (
            <p className="text-xs text-gray-500">
              {importChannel === 'whatsapp'
                ? "Aucun contact synchronisé pour l'instant depuis le téléphone lié à ARIA — WhatsApp envoie ses contacts peu après la connexion, réessaie dans un instant si tu viens de scanner le QR code."
                : "Aucun contact Telegram connu pour l'instant : contrairement à WhatsApp, un bot Telegram n'a pas accès à un répertoire — seules les personnes qui ont déjà écrit au bot ARIA apparaîtront ici."}
            </p>
          )}
          {!importLoading && importCandidates.length > 0 && (
            <ul className="max-h-64 space-y-1 overflow-y-auto">
              {importCandidates.map((candidate) => {
                const saved = alreadySaved(importChannel, candidate.value)
                return (
                  <li
                    key={candidate.value}
                    className="flex items-center justify-between gap-2 rounded-md px-2 py-1 text-sm hover:bg-gray-800/50"
                  >
                    <span className="text-gray-200">
                      {candidate.name} <span className="text-xs text-gray-500">({candidate.value})</span>
                    </span>
                    <button
                      type="button"
                      disabled={saved || addingValue === candidate.value}
                      onClick={() => importContact(importChannel, candidate)}
                      className="shrink-0 text-xs text-blue-400 hover:text-blue-300 disabled:text-gray-600"
                    >
                      {saved ? 'Déjà ajouté' : addingValue === candidate.value ? 'Ajout…' : 'Ajouter'}
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}

      {contacts.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {contacts.map((contact) => (
            <li key={contact.name} className="flex items-center justify-between gap-2 rounded-md bg-gray-900/40 px-3 py-1.5 text-sm">
              <span className="text-gray-200">
                {contact.name}
                {contact.whatsapp && <span className="ml-2 text-xs text-gray-500">WhatsApp : {contact.whatsapp}</span>}
                {contact.telegram && <span className="ml-2 text-xs text-gray-500">Telegram : {contact.telegram}</span>}
              </span>
              <button
                type="button"
                onClick={() => handleDelete(contact.name)}
                className="shrink-0 text-xs text-red-400 hover:text-red-300"
              >
                Supprimer
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSave} className="mt-4 border-t border-gray-800 pt-4">
        <FormField label="Nom">
          <input
            type="text"
            className={inputClass}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Sophie"
          />
        </FormField>
        <div className="mt-3">
          <FormField label="Numéro WhatsApp" hint="Avec indicatif pays, ex : 33612345678">
            <input
              type="text"
              className={inputClass}
              value={whatsapp}
              onChange={(event) => setWhatsapp(event.target.value)}
              placeholder="33612345678"
            />
          </FormField>
        </div>
        <div className="mt-3">
          <FormField label="Identifiant Telegram" hint="Numérique — demande-le à @userinfobot sur Telegram">
            <input
              type="text"
              className={inputClass}
              value={telegram}
              onChange={(event) => setTelegram(event.target.value)}
              placeholder="123456789"
            />
          </FormField>
        </div>
        <button
          type="submit"
          disabled={saving || !name.trim()}
          className="mt-3 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
        >
          {saving ? 'Enregistrement…' : 'Ajouter / mettre à jour'}
        </button>
        {result?.error && (
          <p className="mt-3 rounded-md border border-red-800 bg-red-950/30 px-3 py-2 text-xs text-red-300">{result.error}</p>
        )}
      </form>
    </div>
  )
}

async function fetchStatus(url, signal) {
  try {
    const response = await fetch(url, { signal })
    if (response.status === 404) return { available: true, disabled: true }
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    return { available: true, ...data }
  } catch (error) {
    if (error.name === 'AbortError') throw error
    return { available: false, error: error.message }
  }
}

async function fetchConfig(url, signal) {
  try {
    const response = await fetch(url, { signal })
    if (!response.ok) return null
    return await response.json()
  } catch (error) {
    if (error.name === 'AbortError') throw error
    return null
  }
}

const REFRESH_MS = 15000

export default function Messaging({ isActive = true }) {
  const [whatsapp, setWhatsapp] = useState(null)
  const [telegram, setTelegram] = useState(null)
  const [waConfig, setWaConfig] = useState(null)
  const [tgConfig, setTgConfig] = useState(null)
  const [error, setError] = useState('')
  const [configVersion, setConfigVersion] = useState(0)
  const [statusVersion, setStatusVersion] = useState(0)
  const [disconnectCandidate, setDisconnectCandidate] = useState('')
  const [disconnecting, setDisconnecting] = useState('')
  const [actionNotice, setActionNotice] = useState('')
  const [qrModalOpen, setQrModalOpen] = useState(false)
  const qrAutoOpenedRef = useRef(false)

  // Statuts : sondés en boucle toutes les 15s tant que l'onglet est actif (voir SystemMonitor.jsx
  // pour le même principe). Suspendu quand l'onglet est masqué.
  useEffect(() => {
    if (!isActive) return undefined
    const controller = new AbortController()
    let refreshTimer = null

    const fetchAll = async () => {
      try {
        const [wa, tg] = await Promise.all([
          fetchStatus('/api/whatsapp/status', controller.signal),
          fetchStatus('/api/telegram/status', controller.signal),
        ])
        if (controller.signal.aborted) return
        setWhatsapp(wa)
        setTelegram(tg)
        setError('')
      } catch (loadError) {
        if (loadError.name !== 'AbortError') setError(loadError.message)
      } finally {
        if (!controller.signal.aborted) refreshTimer = setTimeout(fetchAll, REFRESH_MS)
      }
    }
    fetchAll()
    return () => {
      controller.abort()
      if (refreshTimer) clearTimeout(refreshTimer)
    }
  }, [isActive, statusVersion])

  // Config des formulaires : chargée une fois (et rechargée après un enregistrement réussi, voir
  // configVersion) — contrairement au statut, pas besoin de la ressonder toutes les 15s, rien ne
  // la change de l'extérieur.
  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      fetchConfig('/api/messaging/whatsapp-config', controller.signal),
      fetchConfig('/api/messaging/telegram-config', controller.signal),
    ]).then(([wa, tg]) => {
      if (controller.signal.aborted) return
      setWaConfig(wa)
      setTgConfig(tg)
    }).catch((error) => {
      // fetchConfig() relance volontairement l'AbortError (pour la distinguer d'un vrai échec
      // réseau, voir sa définition) plutôt que de l'avaler comme les autres erreurs — sans ce
      // .catch(), ce rejet remontait tel quel jusqu'à la console au démontage/re-render (bug
      // trouvé le 12/09/2026 via la console de Sarah : "AbortError: signal is aborted without
      // reason"). Rien d'autre à faire ici : c'est l'annulation normale d'un fetch en cours
      // quand configVersion change ou que l'onglet se démonte, pas une vraie erreur à afficher.
      if (error.name !== 'AbortError') {
        // Ne devrait normalement jamais arriver : fetchConfig() attrape déjà toute erreur non-abort
        // en interne et renvoie null. Gardé par prudence, juste pour ne pas la laisser silencieuse.
        console.error('[Messagerie] Échec du chargement de la config', error)
      }
    })
    return () => controller.abort()
  }, [configVersion])

  function refreshConfig() {
    setConfigVersion((version) => version + 1)
  }

  async function disconnectChannel(channel) {
    setDisconnecting(channel)
    setError('')
    setActionNotice('')
    try {
      const response = await fetch(`/api/messaging/${channel}-disconnect`, { method: 'POST' })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`)
      setDisconnectCandidate('')
      setActionNotice(data.detail || `${channel} déconnecté.`)
      setStatusVersion((version) => version + 1)
      refreshConfig()
    } catch (disconnectError) {
      setError(disconnectError.message)
    } finally {
      setDisconnecting('')
    }
  }

  function DisconnectControl({ channel, visible }) {
    if (!visible) return null
    const label = channel === 'whatsapp' ? 'WhatsApp' : 'Telegram'
    if (disconnectCandidate !== channel) {
      return (
        <button
          type="button"
          onClick={() => setDisconnectCandidate(channel)}
          className="mt-3 rounded-md border border-red-800 px-3 py-1.5 text-xs font-medium text-red-300 transition-colors hover:bg-red-950/40"
        >
          Déconnecter {label}
        </button>
      )
    }
    return (
      <div className="mt-3 rounded-lg border border-red-900 bg-red-950/20 p-3">
        <p className="text-xs text-red-200">
          {channel === 'whatsapp'
            ? 'Dissocier cet appareil WhatsApp et générer un nouveau QR code ?'
            : 'Arrêter le bot et supprimer son token enregistré localement ?'}
        </p>
        <div className="mt-2 flex gap-2">
          <button type="button" onClick={() => setDisconnectCandidate('')} className="rounded-md border border-gray-600 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-700">Annuler</button>
          <button
            type="button"
            onClick={() => disconnectChannel(channel)}
            disabled={disconnecting === channel}
            className="rounded-md bg-red-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-600 disabled:opacity-50"
          >
            {disconnecting === channel ? 'Déconnexion…' : 'Confirmer'}
          </button>
        </div>
      </div>
    )
  }

  // QR code WhatsApp : ouvert automatiquement la première fois qu'il apparaît (pas besoin de
  // cliquer), pour ne plus dépendre du terminal de whatsapp-bridge/. Le ref évite de le
  // rouvrir tout seul à chaque sondage de 15s si Sarah l'a fermé volontairement ; il ne se
  // réarme que si le QR disparaît puis revient (nouvelle tentative de connexion).
  useEffect(() => {
    if (whatsapp?.qr) {
      if (!qrAutoOpenedRef.current) {
        setQrModalOpen(true)
        qrAutoOpenedRef.current = true
      }
    } else {
      qrAutoOpenedRef.current = false
      if (whatsapp?.connected) setQrModalOpen(false)
    }
  }, [whatsapp?.qr, whatsapp?.connected])

  useEffect(() => {
    if (whatsapp?.connected && actionNotice.startsWith('WhatsApp est dissocié')) {
      setActionNotice('')
    }
  }, [actionNotice, whatsapp?.connected])

  return (
    <section className="h-full overflow-y-auto pr-1">
      <div className="mx-auto max-w-2xl">
        <p className="text-xs font-semibold uppercase tracking-widest text-blue-400">Canaux externes</p>
        <h2 className="mt-1 text-lg font-semibold text-white">Messagerie</h2>
        <p className="mt-1 mb-5 text-sm text-gray-400">
          ARIA peut répondre directement sur WhatsApp et Telegram, en plus de cette app. Configure chaque canal ci-dessous, puis enregistre.
        </p>

        {error && <p className="mb-4 rounded-lg border border-red-800 bg-red-950/30 p-3 text-sm text-red-300">{error}</p>}
        {actionNotice && <p className="mb-4 rounded-lg border border-emerald-800 bg-emerald-950/30 p-3 text-sm text-emerald-300">{actionNotice}</p>}

        <div className="space-y-3">
          <div className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-4 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)]">
            <StatusHeader
              icon="whatsapp"
              name="WhatsApp"
              description="Via un numéro dédié, connecté par QR code (whatsapp-bridge/)."
              status={whatsapp}
              describe={describeWhatsapp}
            />
            {whatsapp?.qr && !whatsapp?.connected && (
              <button
                type="button"
                onClick={() => setQrModalOpen(true)}
                className="mt-3 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-emerald-500"
              >
                Afficher le QR code
              </button>
            )}
            <DisconnectControl channel="whatsapp" visible={Boolean(whatsapp?.connected)} />
            <WhatsappConfigForm config={waConfig} onSaved={refreshConfig} />
          </div>

          <div className="rounded-xl border border-gray-800 bg-gradient-to-br from-gray-800/95 via-gray-800/80 to-gray-900/70 p-4 shadow-[0_4px_14px_rgba(8,15,35,0.35),inset_0_1px_0_rgba(255,255,255,0.04)]">
            <StatusHeader
              icon="telegram"
              name="Telegram"
              description="Via un bot officiel Telegram (backend/telegram_bot.py)."
              status={telegram}
              describe={describeTelegram}
            />
            <DisconnectControl channel="telegram" visible={Boolean(telegram?.configured || tgConfig?.bot_token_configured)} />
            <TelegramConfigForm config={tgConfig} onSaved={refreshConfig} />
          </div>

          <ContactsCard />
        </div>

        <p className="mt-5 text-xs text-gray-500">
          Chaque conversation WhatsApp ou Telegram garde son propre historique en base, séparé de celui de cette app — consultable et pilotable depuis le Chat ou le Vocal ("envoie un message whatsapp à...", "mes derniers messages telegram...").
        </p>
      </div>

      {qrModalOpen && whatsapp?.qr && (
        <QrModal qr={whatsapp.qr} onClose={() => setQrModalOpen(false)} />
      )}
    </section>
  )
}
