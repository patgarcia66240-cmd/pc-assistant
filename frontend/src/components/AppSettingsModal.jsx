import { useEffect, useState } from 'react'
import { getFrenchVoices, readVoicePreferences, writeVoicePreferences } from '../voicePreferences'
import Messaging from './Messaging'
import PointerCalibration from './PointerCalibration'
import PluginsPanel from './PluginsPanel'
import QuizPlayer from './QuizPlayer'

const COUNTRIES = [
  'France',
  'Belgique',
  'Suisse',
  'Canada',
  'Luxembourg',
  'Allemagne',
  'Espagne',
  'Italie',
  'Royaume-Uni',
  'États-Unis',
]

const AI_PROVIDERS = {
  anthropic: { label: 'Anthropic', model: 'claude-sonnet-4-5-20250929' },
  openai: { label: 'OpenAI', model: 'gpt-4.1-mini' },
  gemini: { label: 'Google Gemini', model: 'gemini-2.5-flash' },
  qwen: { label: 'Qwen', model: 'qwen-plus' },
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="m6 6 12 12M18 6 6 18" />
    </svg>
  )
}

function GearIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className} aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21h-4v-.1A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.2 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H2.4v-4h.1A1.7 1.7 0 0 0 4.2 8.6a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 8.6 4.2a1.7 1.7 0 0 0 1-.6A1.7 1.7 0 0 0 10 2.5v-.1h4v.1a1.7 1.7 0 0 0 1 1.7 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 8.6a1.7 1.7 0 0 0 .6 1 1.7 1.7 0 0 0 1.1.4h.1v4h-.1a1.7 1.7 0 0 0-1.7 1Z" />
    </svg>
  )
}

function MessageIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className} aria-hidden="true">
      <path d="M4 5.5h13v8.5H9.5L6 17.5V14H4Z" />
      <path d="M12.5 9h6.5v7.5H16v3l-3.5-3H10" />
    </svg>
  )
}

function PointerIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className} aria-hidden="true">
      <path d="M8 4.5v9M8 4.5a2 2 0 1 1 4 0v6M12 8.2a2 2 0 1 1 4 0v2.3M16 9.4a2 2 0 1 1 4 0v4.6c0 3.6-2.7 6.5-6.5 6.5h-1c-2 0-3.2-.6-4.4-2l-3.2-3.8a1.7 1.7 0 0 1 2.5-2.3l1.6 1.5v-6.3" />
    </svg>
  )
}

function PluginsIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className} aria-hidden="true">
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <path d="M9 9h1.6v1.6H9zM13.4 9H15v1.6h-1.6zM9 13.4h1.6V15H9zM13.4 13.4H15V15h-1.6z" />
    </svg>
  )
}

function QuizIcon({ className = "h-4 w-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className} aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M9.8 9a2.3 2.3 0 1 1 3.6 1.9c-.9.6-1.4 1-1.4 2.1M12 16.8h.01" />
    </svg>
  )
}

// pluginId: null pour les sous-onglets qui ne correspondent à aucun plugin désactivable
// (Général = préférences de base, Plugins = le panneau lui-même) — les autres sont grisés
// et rendent un message à la place de leur contenu quand le plugin correspondant est désactivé.
const SUB_TABS = [
  { id: 'general', label: 'Général', Icon: GearIcon, pluginId: null },
  { id: 'messaging', label: 'Messagerie', Icon: MessageIcon, pluginId: 'messaging' },
  { id: 'pointer', label: 'Calibrage Pointeur', Icon: PointerIcon, pluginId: 'pointer_calibration' },
  { id: 'quiz', label: 'Quiz', Icon: QuizIcon, pluginId: 'quiz' },
  { id: 'plugins', label: 'Plugins', Icon: PluginsIcon, pluginId: null },
]

function PluginDisabledNotice({ label }) {
  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/60 p-4 text-sm text-gray-400">
      Le plugin « {label} » est désactivé. Active-le depuis l’onglet <span className="text-gray-200">Plugins</span> pour accéder à cette section.
    </div>
  )
}

export default function AppSettingsModal({ open, onClose, initialTab = 'general', onPluginsChanged }) {
  const [activeSubTab, setActiveSubTab] = useState(initialTab || 'general')
  const [preferences, setPreferences] = useState({
    country: 'France',
    city: '',
    ai_provider: 'anthropic',
    ai_model: '',
    ai_api_key: '',
    ai_api_key_configured: false,
    ai_providers: {},
  })
  const [voicePreferences, setVoicePreferences] = useState(readVoicePreferences)
  const [voices, setVoices] = useState([])
  const [ttsStatuses, setTtsStatuses] = useState({})
  const [savedAiProvider, setSavedAiProvider] = useState('anthropic')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  // État "enabled" des plugins (par id) tel que déclaré par le backend — sert à griser les
  // sous-onglets Messagerie/Calibrage Pointeur/Quiz quand le plugin correspondant est désactivé
  // depuis l'onglet Plugins (voir PluginsPanel.jsx et SUB_TABS ci-dessus).
  const [pluginsById, setPluginsById] = useState({})

  useEffect(() => {
    if (open) {
      setActiveSubTab(initialTab || 'general')
    }
  }, [open, initialTab])

  // Extraite en fonction nommée (plutôt qu'inline dans l'effet) pour pouvoir la rappeler à la
  // demande — notamment juste après un activer/désactiver dans le sous-onglet Plugins, afin que
  // le grisage des sous-onglets Messagerie/Calibrage Pointeur/Quiz se mette à jour immédiatement,
  // sans attendre un changement de sous-onglet ou une réouverture de la modale.
  function refreshPluginsById() {
    fetch('/api/plugins')
      .then((response) => (response.ok ? response.json() : []))
      .then((plugins) => {
        setPluginsById(Object.fromEntries(plugins.map((plugin) => [plugin.id, plugin])))
      })
      .catch((requestError) => console.error('Impossible de charger l’état des plugins :', requestError))
  }

  // Rechargé à l'ouverture et à chaque changement de sous-onglet (pas seulement au montage) :
  // si l'utilisateur active/désactive un plugin depuis le sous-onglet Plugins puis revient sur
  // Messagerie/Calibrage Pointeur/Quiz, le grisage doit refléter l'état à jour sans réouvrir la modale.
  useEffect(() => {
    if (!open) return
    refreshPluginsById()
  }, [open, activeSubTab])

  // Appelé par PluginsPanel juste après un activer/désactiver réussi : rafraîchit le grisage des
  // sous-onglets ici, et prévient App.jsx (via onPluginsChanged) pour que le menu gauche
  // apparaisse/disparaisse immédiatement lui aussi.
  function handlePluginsChanged() {
    refreshPluginsById()
    onPluginsChanged?.()
  }

  useEffect(() => {
    if (!open) return undefined
    let cancelled = false
    setLoading(true)
    setError(null)
    setVoicePreferences(readVoicePreferences())

    Promise.all([
      fetch('/api/config/preferences').then(async (response) => {
        if (!response.ok) throw new Error((await response.json()).detail || `Erreur HTTP ${response.status}`)
        return response.json()
      }),
      fetch('/api/tts/status').then((response) => (response.ok ? response.json() : { available: false })),
      fetch('/api/piper-tts/status').then((response) => (response.ok ? response.json() : { available: false })),
    ])
      .then(([appPreferences, kokoroStatus, piperStatus]) => {
        if (cancelled) return
        setPreferences(appPreferences)
        setSavedAiProvider(appPreferences.ai_provider)
        setTtsStatuses({ kokoro: kokoroStatus, piper: piperStatus })
      })
      .catch((requestError) => {
        if (!cancelled) setError(requestError.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    const speechSynthesis = window.speechSynthesis
    const refreshVoices = () => setVoices(getFrenchVoices(speechSynthesis?.getVoices() || []))
    refreshVoices()
    speechSynthesis?.addEventListener('voiceschanged', refreshVoices)
    return () => {
      cancelled = true
      speechSynthesis?.removeEventListener('voiceschanged', refreshVoices)
    }
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const closeOnEscape = (event) => {
      if (event.key === 'Escape' && !saving) onClose()
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [open, onClose, saving])

  if (!open) return null

  const countries = COUNTRIES.includes(preferences.country)
    ? COUNTRIES
    : [preferences.country, ...COUNTRIES].filter(Boolean)

  async function save(event) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const response = await fetch('/api/config/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || `Erreur HTTP ${response.status}`)
      writeVoicePreferences(voicePreferences)
      setSavedAiProvider(result.ai_provider)
      onClose()
    } catch (saveError) {
      setError(saveError.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="app-settings-title">
      <button type="button" aria-label="Fermer les paramètres" className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-gray-700 bg-gray-800 shadow-2xl">
        <header className="border-b border-gray-700 bg-gray-800/90 px-5 pt-4 pb-0 backdrop-blur">
          <div className="flex items-center justify-between">
            <div>
              <h2 id="app-settings-title" className="text-lg font-semibold text-white">Paramètres d’ARIA</h2>
              <p className="mt-0.5 text-xs text-gray-400">Configuration centrale, services, calibrage et extensions</p>
            </div>
            <button type="button" onClick={onClose} className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-700 hover:text-white" aria-label="Fermer">
              <CloseIcon />
            </button>
          </div>
          <div className="mt-4 flex space-x-1 border-b border-gray-700/60 pb-px">
            {SUB_TABS.map(({ id, label, Icon, pluginId }) => {
              const active = activeSubTab === id
              const disabled = pluginId ? pluginsById[pluginId]?.enabled === false : false
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setActiveSubTab(id)}
                  disabled={disabled}
                  title={disabled ? 'Plugin désactivé — active-le depuis l’onglet Plugins' : undefined}
                  className={`flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                    disabled
                      ? 'cursor-not-allowed border-transparent text-gray-600 opacity-50'
                      : active
                        ? 'border-blue-500 text-blue-400'
                        : 'border-transparent text-gray-400 hover:border-gray-600 hover:text-gray-200'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              )
            })}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-5">
          {activeSubTab === 'general' && (
            <form onSubmit={save} className="space-y-6">
              {loading ? (
                <p className="text-sm text-gray-400">Chargement des paramètres…</p>
              ) : (
                <>
                  <section>
                    <h3 className="mb-3 text-sm font-semibold text-blue-300">Localisation</h3>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label className="text-sm text-gray-300">
                        Pays
                        <select
                          value={preferences.country}
                          onChange={(event) => setPreferences((current) => ({ ...current, country: event.target.value }))}
                          className="mt-1 min-h-[42px] w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-white"
                        >
                          {countries.map((country) => <option key={country}>{country}</option>)}
                        </select>
                      </label>
                      <label className="text-sm text-gray-300">
                        Ville
                        <input
                          required
                          value={preferences.city}
                          onChange={(event) => setPreferences((current) => ({ ...current, city: event.target.value }))}
                          className="mt-1 min-h-[42px] w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-white"
                        />
                      </label>
                    </div>
                    <p className="mt-2 text-xs text-gray-500">La ville est vérifiée et utilisée pour la météo et les services locaux.</p>
                  </section>

                  <section className="border-t border-gray-700 pt-5">
                    <h3 className="mb-3 text-sm font-semibold text-violet-300">Préférences IA</h3>
                    <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-violet-500/40 bg-violet-500/10 px-3 py-2">
                      <div>
                        <p className="text-xs text-violet-200">IA actuellement sélectionnée</p>
                        <p className="font-semibold text-white">
                          {AI_PROVIDERS[savedAiProvider]?.label || savedAiProvider}
                        </p>
                      </div>
                      <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-300">
                        Active
                      </span>
                    </div>
                    {preferences.ai_provider !== savedAiProvider && (
                      <p className="mb-3 text-xs text-amber-300">
                        Nouveau choix : {AI_PROVIDERS[preferences.ai_provider]?.label || preferences.ai_provider}. Enregistrez pour l’activer.
                      </p>
                    )}
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label className="text-sm text-gray-300">
                        Fournisseur
                        <select
                          value={preferences.ai_provider}
                          onChange={(event) => {
                            const provider = event.target.value
                            const savedProvider = preferences.ai_providers?.[provider]
                            setPreferences((current) => ({
                              ...current,
                              ai_provider: provider,
                              ai_model: savedProvider?.model || AI_PROVIDERS[provider].model,
                              ai_api_key: '',
                              ai_api_key_configured: Boolean(savedProvider?.api_key_configured),
                            }))
                          }}
                          className="mt-1 min-h-[42px] w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-white"
                        >
                          {Object.entries(AI_PROVIDERS).map(([value, provider]) => (
                            <option key={value} value={value}>{provider.label}</option>
                          ))}
                        </select>
                      </label>
                      <label className="text-sm text-gray-300">
                        Modèle
                        <input
                          required
                          value={preferences.ai_model}
                          onChange={(event) => setPreferences((current) => ({ ...current, ai_model: event.target.value }))}
                          className="mt-1 min-h-[42px] w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-white"
                        />
                      </label>
                    </div>
                    <label className="mt-3 block text-sm text-gray-300">
                      Clé API
                      <input
                        type="password"
                        value={preferences.ai_api_key || ''}
                        onChange={(event) => setPreferences((current) => ({ ...current, ai_api_key: event.target.value }))}
                        placeholder={preferences.ai_api_key_configured ? 'Déjà enregistrée — laisser vide pour la conserver' : 'Saisir la clé API'}
                        autoComplete="off"
                        className="mt-1 min-h-[42px] w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-white"
                      />
                    </label>
                    <p className="mt-2 text-xs text-gray-500">La clé est enregistrée localement et n’est jamais renvoyée par l’API.</p>
                  </section>

                  <section className="border-t border-gray-700 pt-5">
                    <h3 className="mb-3 text-sm font-semibold text-cyan-300">Synthèse vocale</h3>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label className="text-sm text-gray-300">
                        Moteur TTS
                        <select
                          value={voicePreferences.engine}
                          onChange={(event) => setVoicePreferences((current) => ({ ...current, engine: event.target.value }))}
                          className="mt-1 min-h-[42px] w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-white"
                        >
                          <option value="kokoro">Kokoro local</option>
                          <option value="piper">Piper local (rapide)</option>
                          <option value="browser">Voix du navigateur</option>
                        </select>
                      </label>
                      <label className="text-sm text-gray-300">
                        Voix française de repli
                        <select
                          value={voicePreferences.voiceURI}
                          onChange={(event) => setVoicePreferences((current) => ({ ...current, voiceURI: event.target.value }))}
                          disabled={voices.length === 0}
                          className="mt-1 min-h-[42px] w-full rounded-lg border border-gray-600 bg-gray-900 px-3 text-white disabled:opacity-50"
                        >
                          <option value="">Meilleure voix disponible</option>
                          {voices.map((voice) => (
                            <option key={`${voice.voiceURI}-${voice.lang}`} value={voice.voiceURI}>
                              {voice.name} ({voice.lang})
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                    <label className="mt-3 block text-sm text-gray-300">
                      Débit vocal : {voicePreferences.rate.toFixed(2)}×
                      <input
                        type="range"
                        min="0.75"
                        max="1.1"
                        step="0.05"
                        value={voicePreferences.rate}
                        onChange={(event) => setVoicePreferences((current) => ({ ...current, rate: Number(event.target.value) }))}
                        className="mt-1 w-full accent-blue-500"
                      />
                    </label>
                    <label className="mt-3 flex items-center gap-3 text-sm text-gray-300">
                      <input
                        type="checkbox"
                        checked={voicePreferences.streaming}
                        onChange={(event) => setVoicePreferences((current) => ({ ...current, streaming: event.target.checked }))}
                        className="h-4 w-4 accent-blue-500"
                      />
                      Lire la réponse en streaming dès la première phrase
                    </label>
                    <div className="mt-2 space-y-1 text-xs">
                      <p className={ttsStatuses.kokoro?.available ? 'text-emerald-400' : 'text-amber-300'}>
                        {ttsStatuses.kokoro?.available
                          ? `Kokoro est prêt avec la voix ${ttsStatuses.kokoro.voice} (${ttsStatuses.kokoro.provider === 'CUDAExecutionProvider' ? 'GPU CUDA' : 'CPU'}).`
                          : 'Kokoro est indisponible.'}
                      </p>
                      <p className={ttsStatuses.piper?.available ? 'text-emerald-400' : 'text-amber-300'}>
                        {ttsStatuses.piper?.available
                          ? `Piper est prêt avec la voix ${ttsStatuses.piper.voice}.`
                          : 'Piper est indisponible.'}
                      </p>
                      <p className="text-gray-500">La voix du navigateur est utilisée automatiquement si le moteur choisi échoue.</p>
                    </div>
                  </section>
                </>
              )}

              {error && <p className="rounded-lg border border-red-800/70 bg-red-950/40 px-3 py-2 text-sm text-red-300">{error}</p>}

              <footer className="mt-6 flex justify-end gap-3 border-t border-gray-700 pt-4">
                <button type="button" onClick={onClose} disabled={saving} className="min-h-[42px] rounded-lg border border-gray-600 px-4 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-50">
                  Annuler
                </button>
                <button type="submit" disabled={loading || saving} className="min-h-[42px] rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50">
                  {saving ? 'Enregistrement…' : 'Enregistrer'}
                </button>
              </footer>
            </form>
          )}

          {activeSubTab === 'messaging' && (
            pluginsById.messaging?.enabled === false
              ? <PluginDisabledNotice label="Messagerie" />
              : <Messaging />
          )}
          {activeSubTab === 'pointer' && (
            pluginsById.pointer_calibration?.enabled === false
              ? <PluginDisabledNotice label="Calibrage Pointeur" />
              : <PointerCalibration />
          )}
          {activeSubTab === 'quiz' && (
            pluginsById.quiz?.enabled === false
              ? <PluginDisabledNotice label="Quiz" />
              : <QuizPlayer />
          )}
          {activeSubTab === 'plugins' && <PluginsPanel onChanged={handlePluginsChanged} />}
        </div>
      </div>
    </div>
  )
}
