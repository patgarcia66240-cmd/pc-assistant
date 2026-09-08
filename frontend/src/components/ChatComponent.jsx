import { useState, useRef, useEffect } from 'react'

export default function ChatComponent() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    const newMessage = { text: input, sender: 'user' }
    setMessages(prev => [...prev, newMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      })
      const data = await response.json()
      setMessages(prev => [...prev, { text: data.response, sender: 'aria' }])
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, { text: 'Error sending message', sender: 'error' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs px-4 py-2 rounded-lg ${
                msg.sender === 'user' ? 'bg-blue-600' : 'bg-gray-700'
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          className="flex-1 px-4 py-2 bg-gray-800 rounded border border-gray-700 text-white"
          placeholder="Ask ARIA..."
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="px-6 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
