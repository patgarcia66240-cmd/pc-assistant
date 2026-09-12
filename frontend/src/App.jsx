import { useEffect, useState, Suspense } from 'react'
import './App.css'
import ChatComponent from './components/ChatComponent'
import VoiceAssistant from './components/VoiceAssistant'
import PluginsPanel from './components/PluginsPanel'
import AppSettingsModal from './components/AppSettingsModal'
import HandPointerOverlay from './components/HandPointerOverlay'
import ariaMark from './assets/aria-mark.svg'
import { lazyPluginComponent } from './pluginComponents'
import { POINTER_MODE_EVENT, POINTER_MODE_REQUEST_EVENT } from './pointerCalibration'
import { QUIZ_NAVIGATE_EVENT } from './quizNavigation'
import { PLUGIN_NAVIGATE_EVENT } from './pluginNavigation'

function MenuIcon({ type }) {
  const paths = {
    chat: <><path d="M4 5.5h16v10H9l-5 4v-14Z" /><path d="M8 9.5h8M8 13h5" /></>,
    system: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M8 15v-3M12 15V8M16 15v-5" /></>,
    files: <><path d="M4 6.5h6l2 2h8v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2Z" /><path d="M2 10.5h18" /></>,
    saint: <><path d="M12 3v18M7 7h10M5 11h14M8 21h8" /><path d="m7 7-3-3M17 7l3-3" /></>,
    voice: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" /></>,
    calendar: <><rect x="3.5" y="5" width="17" height="15" rx="2" /><path d="M8 3v4M16 3v4M3.5 10h17" /></>,
    pointer: <><path d="M8 4.5v9M8 4.5a2 2 0 1 1 4 0v6M12 8.2a2 2 0 1 1 4 0v2.3M16 9.4a2 2 0 1 1 4 0v4.6c0 3.6-2.7 6.5-6.5 6.5h-1c-2 0-3.2-.6-4.4-2l-3.2-3.8a1.7 1.7 0 0 1 2.5-2.3l1.6 1.5v-6.3" /></>,
    quiz: <><circle cx="12" cy="12" r="9" /><path d="M9.8 9a2.3 2.3 0 1 1 3.6 1.9c-.9.6-1.4 1-1.4 2.1M12 16.8h.01" /></>,
    image: <><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9" cy="9" r="2" /><path d="m4 17 5-5 3.5 3.5 2.5-2.5 5 5" /></>,
    message: <><path d="M4 5.5h13v8.5H9.5L6 17.5V14H4Z" /><path d="M12.5 9h6.5v7.5H16v3l-3.5-3H10" /></>,
    plugins: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M9 9h1.6v1.6H9zM13.4 9H15v1.6h-1.6zM9 13.4h1.6V15H9zM13.4 13.4H15V15h-1.6z" /></>,
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5 shrink-0" aria-hidden="true">
      {paths[type] ?? paths.plugins}
    </svg>
  )
}

function AppMark() {
  return (
    <img src={ariaMark} alt="Logo ARIA" className="h-9 w-9 shrink-0 rounded-lg shadow-md shadow-blue-950/40" />
  )
}

function SettingsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21h-4v-.1A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.2 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H2.4v-4h.1A1.7 1.7 0 0 0 4.2 8.6a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 8.6 4.2a1.7 1.7 0 0 0 1-.6A1.7 1.7 0 0 0 10 2.5v-.1h4v.1a1.7 1.7 0 0 0 1 1.7 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 8.6a1.7 1.7 0 0 0 .6 1 1.7 1.7 0 0 0 1.1.4h.1v4h-.1a1.7 1.7 0 0 0-1.7 1Z" />
    </svg>
  )
}

function PointerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      <path d="M8 4.5v9M8 4.5a2 2 0 1 1 4 0v6M12 8.2a2 2 0 1 1 4 0v2.3M16 9.4a2 2 0 1 1 4 0v4.6c0 3.6-2.7 6.5-6.5 6.5h-1c-2 0-3.2-.6-4.4-2l-3.2-3.8a1.7 1.7 0 0 1 2.5-2.3l1.6 1.5v-6.3" />
    </svg>
  )
}

// Tabs core : "Chat" et "Assistant vocal" sont les deux seuls qui restent statiques — tout le
// reste (calendar, saint, system, files) est fourni par des plugins depuis le 11/09/2026 (voir
// backend/plugins/*), ajouté dynamiquement selon la réponse de GET /api/plugins. `order` fixe
// la position dans la sidebar (mêmes valeurs que du temps où tout était un seul tableau
// statique : chat, voice, calendar, saint, system, files).
const CORE_TABS = [
  { id: 'chat', label: 'Chat', icon: 'chat', Component: ChatComponent, order: 10 },
  { id: 'voice', label: 'Assistant vocal', icon: 'voice', Component: VoiceAssistant, order: 20 },
]

const SETTINGS_TAB = { id: 'plugins', label: 'Plugins', icon: 'plugins', Component: PluginsPanel, order: 1000 }

// Après le retour de la redirection OAuth Google (voir CalendarAgenda.jsx), l'URL contient
// ?calendar_connected=1 ou ?calendar_error=... : on doit atterrir directement sur l'onglet Agenda
// pour que la bannière de statut (et le nettoyage de l'URL) s'affiche au bon endroit, plutôt que
// de rouvrir Chat par défaut et laisser ces paramètres invisibles à l'utilisatrice.
function getInitialTab() {
  if (typeof window === 'undefined') return 'chat'
  const params = new URLSearchParams(window.location.search)
  if (params.has('calendar_connected') || params.has('calendar_error')) return 'calendar'
  return 'chat'
}

export default function App() {
  const [activeTab, setActiveTab] = useState(getInitialTab)
  const [settingsOpen, setSettingsOpen] = useState(false)
  // Mode pointeur (curseur piloté par l'index de la main gauche, voir HandPointerOverlay) :
  // volontairement indépendant de VoiceAssistant.jsx (qui a son propre réglage caméra pour les
  // yeux/gestes, limité à son onglet) — celui-ci doit pouvoir cliquer n'importe où dans l'app, donc
  // il est monté ici, au niveau racine, et pas dans un onglet.
  const [pointerMode, setPointerMode] = useState(() => {
    try {
      return localStorage.getItem('aria-pointer-mode') === '1'
    } catch {
      return false
    }
  })
  const [pointerError, setPointerError] = useState(null)

  useEffect(() => {
    const handlePointerModeRequest = (event) => {
      const enabled = Boolean(event.detail?.enabled)
      setPointerError(null)
      setPointerMode(enabled)
      try {
        localStorage.setItem('aria-pointer-mode', enabled ? '1' : '0')
      } catch {
        // stockage indisponible : le choix reste actif pour la session en cours.
      }
      window.dispatchEvent(new CustomEvent(POINTER_MODE_EVENT, { detail: { enabled } }))
    }
    window.addEventListener(POINTER_MODE_REQUEST_EVENT, handlePointerModeRequest)
    return () => window.removeEventListener(POINTER_MODE_REQUEST_EVENT, handlePointerModeRequest)
  }, [])

  useEffect(() => {
    const openPlugin = (event) => {
      const pluginId = event.detail?.pluginId
      if (!pluginId) return
      setActiveTab(pluginId)
      setVisitedTabs((previous) => (
        previous.has(pluginId) ? previous : new Set(previous).add(pluginId)
      ))
    }
    window.addEventListener(PLUGIN_NAVIGATE_EVENT, openPlugin)
    return () => window.removeEventListener(PLUGIN_NAVIGATE_EVENT, openPlugin)
  }, [])

  function togglePointerMode() {
    setPointerError(null)
    setPointerMode((current) => {
      const next = !current
      try {
        localStorage.setItem('aria-pointer-mode', next ? '1' : '0')
      } catch {
        // stockage indisponible (navigation privée, etc.) : le choix reste actif pour la session en cours.
      }
      window.dispatchEvent(new CustomEvent(POINTER_MODE_EVENT, { detail: { enabled: next } }))
      return next
    })
  }

  function handlePointerError(err) {
    setPointerMode(false)
    try {
      localStorage.setItem('aria-pointer-mode', '0')
    } catch {
      // stockage indisponible : l'option reste simplement désactivée pour cette session.
    }
    window.dispatchEvent(new CustomEvent(POINTER_MODE_EVENT, { detail: { enabled: false } }))
    if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError' || err?.name === 'SecurityError') {
      setPointerError("Accès à la caméra refusé. Autorisez la caméra pour ce site, puis réessayez.")
    } else if (err?.name === 'NotFoundError' || err?.name === 'DevicesNotFoundError') {
      setPointerError('Aucune caméra détectée sur cet appareil.')
    } else if (err?.name === 'NotReadableError' || err?.name === 'TrackStartError') {
      setPointerError('La caméra est déjà utilisée par une autre application.')
    } else {
      setPointerError(`Pointeur indisponible (${err?.name || 'erreur'}) : ${err?.message || err}`)
    }
  }
  // Onglets déjà ouverts au moins une fois : on les laisse montés (juste masqués en CSS, voir
  // plus bas) au lieu de les démonter à chaque changement d'onglet. Les composants reçoivent
  // toutefois `isActive` pour suspendre leurs tâches périodiques lorsqu'ils sont masqués
  // (notamment les relevés de l'onglet Système). 'chat' est ajouté par
  // sécurité : si l'onglet initial vient de l'URL (retour OAuth Agenda) et que la liste des
  // plugins n'a pas encore fini de charger, on peut quand même retomber sur Chat sans écran vide.
  const [visitedTabs, setVisitedTabs] = useState(() => new Set([getInitialTab(), 'chat']))
  const [pluginTabs, setPluginTabs] = useState([])

  useEffect(() => {
    const openQuiz = () => {
      setActiveTab('quiz')
      setVisitedTabs((previous) => (
        previous.has('quiz') ? previous : new Set(previous).add('quiz')
      ))
    }
    window.addEventListener(QUIZ_NAVIGATE_EVENT, openQuiz)
    return () => window.removeEventListener(QUIZ_NAVIGATE_EVENT, openQuiz)
  }, [])

  // Construit les tabs à partir des plugins ACTIFS déclarés par le backend (GET /api/plugins).
  // Un plugin désactivé, en erreur de chargement, ou sans section `frontend.tab` dans son
  // manifest (ex. city_details ou config, backend-only) n'ajoute simplement aucun tab.
  useEffect(() => {
    let cancelled = false
    fetch('/api/plugins')
      .then((response) => (response.ok ? response.json() : []))
      .then((plugins) => {
        if (cancelled) return
        const tabs = plugins
          .filter((plugin) => plugin.enabled && !plugin.load_error && plugin.frontend?.tab && plugin.frontend?.component)
          .map((plugin) => ({
            id: plugin.frontend.tab.id ?? plugin.id,
            label: plugin.frontend.tab.label ?? plugin.name,
            icon: plugin.frontend.tab.icon ?? 'plugins',
            order: plugin.frontend.tab.order ?? 500,
            Component: lazyPluginComponent(plugin.frontend.component),
          }))
          .filter((tab) => tab.Component)
        setPluginTabs(tabs)
      })
      .catch((error) => console.error('Impossible de charger la liste des plugins ARIA :', error))
    return () => {
      cancelled = true
    }
  }, [])

  const tabs = [...CORE_TABS, ...pluginTabs, SETTINGS_TAB].sort((a, b) => a.order - b.order)
  // Si activeTab ne correspond à aucun tab connu pour l'instant (ex. 'calendar' visé par l'URL
  // mais /api/plugins pas encore répondu), on retombe temporairement sur Chat plutôt qu'un
  // écran vide — même filet de sécurité que l'ancien `?? ChatComponent`.
  const effectiveActiveTab = tabs.some((tab) => tab.id === activeTab) ? activeTab : 'chat'

  function selectTab(id) {
    setActiveTab(id)
    setVisitedTabs((prev) => (prev.has(id) ? prev : new Set(prev).add(id)))
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-900 text-white">
      <header className="flex shrink-0 items-center gap-3 border-b border-gray-700 bg-gray-800 p-4">
        <AppMark />
        <h1 className="text-2xl font-bold leading-none">ARIA <span className="font-normal text-gray-400">PC Assistant</span></h1>
        <button
          type="button"
          onClick={togglePointerMode}
          className={`ml-auto flex min-h-[44px] items-center gap-2 rounded-lg border px-3 text-sm font-medium transition ${
            pointerMode
              ? 'border-blue-500 bg-blue-600 text-white hover:bg-blue-500'
              : 'border-gray-600 text-gray-200 hover:bg-gray-700 hover:text-white'
          }`}
          aria-pressed={pointerMode}
          aria-label="Activer ou désactiver le pointeur main (index gauche)"
          title="Pointeur main : déplace le curseur avec l'index gauche, pincez les doigts pour cliquer"
        >
          <PointerIcon />
          <span className="hidden sm:inline">Pointeur</span>
        </button>
        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          className="flex min-h-[44px] items-center gap-2 rounded-lg border border-gray-600 px-3 text-sm font-medium text-gray-200 transition hover:bg-gray-700 hover:text-white"
          aria-label="Ouvrir les paramètres"
        >
          <SettingsIcon />
          <span className="hidden sm:inline">Paramètres</span>
        </button>
      </header>
      {pointerError && (
        <p className="shrink-0 border-b border-orange-900/60 bg-orange-950/40 px-4 py-1.5 text-xs text-orange-300">
          {pointerError}
        </p>
      )}

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* Sidebar */}
        <nav className="shrink-0 overflow-x-auto border-b border-gray-700 bg-gray-800 p-3 md:w-52 md:overflow-visible md:border-b-0 md:border-r md:p-4" aria-label="Sections de l'application">
          <ul className="flex gap-3 md:flex-col">
            {tabs.map((tab, index) => {
              const isActive = effectiveActiveTab === tab.id
              const hasSeparatorAfter = index === 1 || index === tabs.length - 2
              return (
                <li key={tab.id} className="flex items-center gap-3 md:block">
                  <button
                    onClick={() => selectTab(tab.id)}
                    data-hand-pointer-target="menu"
                    aria-current={isActive ? 'page' : undefined}
                    className={`relative flex min-h-[44px] w-full flex-row items-center justify-start gap-3 whitespace-nowrap rounded-md px-3 py-2.5 text-left text-sm font-medium transition-colors md:px-4 ${
                      isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    }`}
                  >
                    {isActive && <span className="absolute inset-y-1.5 left-0 hidden w-0.5 rounded-full bg-blue-300 md:block" aria-hidden="true" />}
                    <MenuIcon type={tab.icon} />
                    <span>{tab.label}</span>
                  </button>
                  {hasSeparatorAfter && (
                    <div
                      role="separator"
                      className="h-8 w-px shrink-0 bg-gray-600 md:my-2 md:h-px md:w-full"
                    />
                  )}
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Main Content */}
        <main className="min-h-0 min-w-0 flex-1 overflow-hidden p-3 sm:p-6">
          <Suspense fallback={<p className="text-sm text-gray-400">Chargement…</p>}>
            {/* Tous les onglets déjà visités restent montés, seul celui actif est visible
                (attribut `hidden`, pas de démontage) — voir le commentaire sur visitedTabs. */}
            {tabs
              .filter((tab) => visitedTabs.has(tab.id))
              .map((tab) => (
                <div key={tab.id} hidden={effectiveActiveTab !== tab.id} className="h-full">
                  <tab.Component isActive={effectiveActiveTab === tab.id} />
                </div>
              ))}
          </Suspense>
        </main>
      </div>
      <AppSettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <HandPointerOverlay enabled={pointerMode} onError={handlePointerError} />
    </div>
  )
}
