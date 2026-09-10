import { useState } from 'react'
import './App.css'
import ChatComponent from './components/ChatComponent'
import SystemMonitor from './components/SystemMonitor'
import FileManager from './components/FileManager'
import SaintOfDay from './components/SaintOfDay'
import VoiceAssistant from './components/VoiceAssistant'
import CalendarAgenda from './components/CalendarAgenda'

function MenuIcon({ type }) {
  const paths = {
    chat: <><path d="M4 5.5h16v10H9l-5 4v-14Z" /><path d="M8 9.5h8M8 13h5" /></>,
    system: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M8 15v-3M12 15V8M16 15v-5" /></>,
    files: <><path d="M4 6.5h6l2 2h8v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2Z" /><path d="M2 10.5h18" /></>,
    saint: <><path d="M12 3v18M7 7h10M5 11h14M8 21h8" /><path d="m7 7-3-3M17 7l3-3" /></>,
    voice: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" /></>,
    calendar: <><rect x="3.5" y="5" width="17" height="15" rx="2" /><path d="M8 3v4M16 3v4M3.5 10h17" /></>,
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5 shrink-0" aria-hidden="true">
      {paths[type]}
    </svg>
  )
}

// Icône de l'app : reprend le badge dégradé bleu->cyan de desktop/icons/icon.ico, pour que le
// logo dans l'en-tête et l'icône de la fenêtre Tauri soient cohérents (même identité visuelle).
function AppMark() {
  return (
    <span
      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 text-base font-bold text-white shadow-md shadow-blue-950/40"
      aria-hidden="true"
    >
      A
    </span>
  )
}

const TABS = [
  { id: 'chat', label: 'Chat', icon: 'chat' },
  { id: 'voice', label: 'Assistant vocal', icon: 'voice' },
  { id: 'calendar', label: 'Agenda', icon: 'calendar' },
  { id: 'saint', label: 'Saint du jour', icon: 'saint' },
  { id: 'system', label: 'Système', icon: 'system' },
  { id: 'files', label: 'Fichiers', icon: 'files' },
]

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

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-900 text-white">
      <header className="flex shrink-0 items-center gap-3 border-b border-gray-700 bg-gray-800 p-4">
        <AppMark />
        <h1 className="text-2xl font-bold leading-none">ARIA <span className="font-normal text-gray-400">PC Assistant</span></h1>
      </header>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* Sidebar */}
        <nav className="shrink-0 overflow-x-auto border-b border-gray-700 bg-gray-800 p-3 md:w-52 md:overflow-visible md:border-b-0 md:border-r md:p-4" aria-label="Sections de l'application">
          <ul className="flex gap-2 md:flex-col md:space-y-1.5">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.id
              return (
                <li key={tab.id}>
                  <button
                    onClick={() => setActiveTab(tab.id)}
                    aria-current={isActive ? 'page' : undefined}
                    className={`relative flex min-h-[44px] w-full flex-row items-center justify-start gap-3 whitespace-nowrap rounded-md px-3 py-2.5 text-left text-sm font-medium transition-colors md:px-4 ${
                      isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    }`}
                  >
                    {isActive && <span className="absolute inset-y-1.5 left-0 hidden w-0.5 rounded-full bg-blue-300 md:block" aria-hidden="true" />}
                    <MenuIcon type={tab.icon} />
                    <span>{tab.label}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Main Content */}
        <main className="min-h-0 min-w-0 flex-1 overflow-hidden p-3 sm:p-6">
          {activeTab === 'chat' && <ChatComponent />}
          {activeTab === 'voice' && <VoiceAssistant />}
          {activeTab === 'calendar' && <CalendarAgenda />}
          {activeTab === 'system' && <SystemMonitor />}
          {activeTab === 'files' && <FileManager />}
          {activeTab === 'saint' && <SaintOfDay />}
        </main>
      </div>
    </div>
  )
}
