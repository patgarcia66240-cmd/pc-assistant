import { useState, useEffect } from 'react'
import './App.css'
import ChatComponent from './components/ChatComponent'
import SystemMonitor from './components/SystemMonitor'
import FileManager from './components/FileManager'

export default function App() {
  const [activeTab, setActiveTab] = useState('chat')

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 p-4 border-b border-gray-700">
        <h1 className="text-2xl font-bold">🤖 ARIA - PC Assistant</h1>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <nav className="w-48 bg-gray-800 border-r border-gray-700 p-4">
          <ul className="space-y-2">
            <li>
              <button
                onClick={() => setActiveTab('chat')}
                className={`w-full text-left px-4 py-2 rounded ${activeTab === 'chat' ? 'bg-blue-600' : 'hover:bg-gray-700'}`}
              >
                💬 Chat
              </button>
            </li>
            <li>
              <button
                onClick={() => setActiveTab('system')}
                className={`w-full text-left px-4 py-2 rounded ${activeTab === 'system' ? 'bg-blue-600' : 'hover:bg-gray-700'}`}
              >
                📊 System
              </button>
            </li>
            <li>
              <button
                onClick={() => setActiveTab('files')}
                className={`w-full text-left px-4 py-2 rounded ${activeTab === 'files' ? 'bg-blue-600' : 'hover:bg-gray-700'}`}
              >
                📁 Files
              </button>
            </li>
          </ul>
        </nav>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {activeTab === 'chat' && <ChatComponent />}
          {activeTab === 'system' && <SystemMonitor />}
          {activeTab === 'files' && <FileManager />}
        </main>
      </div>
    </div>
  )
}
