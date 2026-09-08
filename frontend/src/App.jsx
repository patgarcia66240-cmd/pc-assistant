import { useState, useEffect } from 'react'
import './App.css'
import ChatComponent from './components/ChatComponent'
import SystemMonitor from './components/SystemMonitor'
import FileManager from './components/FileManager'
import SaintOfDay from './components/SaintOfDay'

function MenuIcon({ type }) {
  const paths = {
    chat: <><path d="M4 5.5h16v10H9l-5 4v-14Z" /><path d="M8 9.5h8M8 13h5" /></>,
    system: <><rect x="4" y="4" width="16" height="16" rx="2" /><path d="M8 15v-3M12 15V8M16 15v-5" /></>,
    files: <><path d="M4 6.5h6l2 2h8v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2Z" /><path d="M2 10.5h18" /></>,
    saint: <><path d="M12 3v18M7 7h10M5 11h14M8 21h8" /><path d="m7 7-3-3M17 7l3-3" /></>,
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
      {paths[type]}
    </svg>
  )
}

export default function App() {
  const [activeTab, setActiveTab] = useState('chat')

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-900 text-white">
      <header className="shrink-0 border-b border-gray-700 bg-gray-800 p-4">
        <h1 className="text-2xl font-bold">ARIA <span className="font-normal text-gray-400">PC Assistant</span></h1>
      </header>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* Sidebar */}
        <nav className="shrink-0 border-b border-gray-700 bg-gray-800 p-3 md:w-48 md:border-b-0 md:border-r md:p-4">
          <ul className="flex gap-2 md:flex-col md:space-y-2">
            <li>
              <button
                onClick={() => setActiveTab('chat')}
                className={`flex w-full flex-row items-center justify-start gap-3 whitespace-nowrap rounded px-3 py-2 text-left text-sm md:px-4 ${activeTab === 'chat' ? 'bg-blue-600' : 'hover:bg-gray-700'}`}
              >
                <MenuIcon type="chat" />
                <span>Chat</span>
              </button>
            </li>
            <li>
              <button
                onClick={() => setActiveTab('saint')}
                className={`flex w-full flex-row items-center justify-start gap-3 whitespace-nowrap rounded px-3 py-2 text-left text-sm md:px-4 ${activeTab === 'saint' ? 'bg-blue-600' : 'hover:bg-gray-700'}`}
              >
                <MenuIcon type="saint" />
                <span>Saint du jour</span>
              </button>
            </li>
            <li>
              <button
                onClick={() => setActiveTab('system')}
                className={`flex w-full flex-row items-center justify-start gap-3 whitespace-nowrap rounded px-3 py-2 text-left text-sm md:px-4 ${activeTab === 'system' ? 'bg-blue-600' : 'hover:bg-gray-700'}`}
              >
                <MenuIcon type="system" />
                <span>Système</span>
              </button>
            </li>
            <li>
              <button
                onClick={() => setActiveTab('files')}
                className={`flex w-full flex-row items-center justify-start gap-3 whitespace-nowrap rounded px-3 py-2 text-left text-sm md:px-4 ${activeTab === 'files' ? 'bg-blue-600' : 'hover:bg-gray-700'}`}
              >
                <MenuIcon type="files" />
                <span>Fichiers</span>
              </button>
            </li>
          </ul>
        </nav>

        {/* Main Content */}
        <main className="min-h-0 min-w-0 flex-1 overflow-hidden p-3 sm:p-6">
          {activeTab === 'chat' && <ChatComponent />}
          {activeTab === 'system' && <SystemMonitor />}
          {activeTab === 'files' && <FileManager />}
          {activeTab === 'saint' && <SaintOfDay />}
        </main>
      </div>
    </div>
  )
}
