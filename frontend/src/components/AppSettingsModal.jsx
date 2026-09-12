import { useEffect, useState } from 'react'
import { getFrenchVoices, readVoicePreferences, writeVoicePreferences } from '../voicePreferences'

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

export default function AppSettingsModal({ open, onClose }) {
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
      <form onSubmit={save} className="relative z-10 flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-gray-700 bg-gray-800 shadow-2xl">
        <header className="flex items-center justify-between border-b border-gray-700 px-5 py-4">
          <div>
            <h2 id="app-settings-title" className="text-lg font-semibold text-white">Paramètres d’ARIA</h2>
            <p className="mt-0.5 text-xs text-gray-400">Localisation, intelligence artificielle et voix</p>
          </div>
          <button type="button" onClick={onClose} className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-700 hover:text-white" aria-label="Fermer">
            <CloseIcon />
          </button>
        </header>

        <div className="space-y-6 overflow-y-auto p-5">
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
        </div>

        <footer className="flex justify-end gap-3 border-t border-gray-700 px-5 py-4">
          <button type="button" onClick={onClose} disabled={saving} className="min-h-[42px] rounded-lg border border-gray-600 px-4 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-50">
            Annuler
          </button>
          <button type="submit" disabled={loading || saving} className="min-h-[42px] rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50">
            {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </footer>
      </form>
    </div>
  )
}
