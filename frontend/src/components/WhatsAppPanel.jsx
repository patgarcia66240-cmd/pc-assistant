import { useCallback, useEffect, useRef, useState } from 'react'

async function readResponse(response) {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || `Erreur HTTP ${response.status}`)
  return data
}

function normalizeWhatsAppNumber(value) {
  let digits = String(value || '').replace(/\D/g, '')
  if (digits.startsWith('0033')) digits = digits.slice(2)
  else if (digits.length === 10 && digits.startsWith('0')) digits = `33${digits.slice(1)}`
  else if (digits.length === 9) digits = `33${digits}`
  return digits
}

function formatWhatsAppNumber(value) {
  const digits = normalizeWhatsAppNumber(value)
  if (digits.startsWith('33') && digits.length === 11) {
    return `+33 ${digits.slice(2, 3)} ${digits.slice(3).match(/.{1,2}/g).join(' ')}`
  }
  return digits ? `+${digits}` : ''
}

function formatMessageDate(value) {
  const timestamp = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`
  return new Date(timestamp).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

function DeliveryStatus({ status }) {
  const states = {
    pending: ['En attente…', 'text-amber-200'],
    sent: ['✓ Envoyé', 'text-white/60'],
    delivered: ['✓✓ Distribué', 'text-white/70'],
    read: ['✓✓ Lu', 'text-cyan-200'],
    failed: ['Échec de l’envoi', 'text-red-200'],
  }
  const state = states[status]
  if (!state) return null
  return <span className={state[1]}>{state[0]}</span>
}

function MenuCard({ title, description, action, onClick }) {
  return (
    <button type="button" onClick={onClick} className="rounded-2xl border border-gray-700 bg-gray-800/70 p-5 text-left transition hover:border-emerald-500 hover:bg-gray-800">
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-gray-400">{description}</p>
      <span className="mt-4 inline-block text-sm font-semibold text-emerald-300">{action} →</span>
    </button>
  )
}

function BackButton({ onClick }) {
  return (
    <button type="button" onClick={onClick} className="mb-2 self-start rounded-lg border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-800">
      ← Retour
    </button>
  )
}

function WhatsAppLogo() {
  return (
    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-600 text-white shadow-lg shadow-emerald-950/30">
      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-6 w-6 fill-current">
        <path d="M12 2a9.5 9.5 0 0 0-8.18 14.34L2.5 21.5l5.28-1.28A9.5 9.5 0 1 0 12 2Zm0 17.1a7.55 7.55 0 0 1-3.85-1.05l-.28-.17-3.12.76.79-3.04-.18-.29A7.6 7.6 0 1 1 12 19.1Zm4.17-5.68c-.23-.12-1.36-.67-1.57-.75-.21-.07-.36-.11-.52.12-.15.23-.59.75-.72.9-.13.15-.27.17-.5.06-.23-.12-.96-.36-1.83-1.12-.68-.6-1.13-1.35-1.27-1.58-.13-.23-.01-.35.1-.46.1-.1.23-.27.34-.4.12-.14.16-.23.23-.38.08-.15.04-.29-.02-.4-.06-.12-.52-1.25-.71-1.71-.18-.45-.38-.39-.52-.4h-.44c-.15 0-.4.06-.6.29-.21.23-.8.78-.8 1.9s.82 2.2.93 2.35c.12.15 1.59 2.43 3.85 3.41.54.23.96.37 1.29.48.54.17 1.03.15 1.42.09.43-.07 1.36-.56 1.55-1.1.19-.53.19-.99.13-1.08-.05-.1-.21-.16-.44-.27Z" />
      </svg>
    </span>
  )
}

export default function WhatsAppPanel({ isActive = true }) {
  const [view, setView] = useState('menu')
  const [status, setStatus] = useState(null)
  const [contacts, setContacts] = useState([])
  const [conversations, setConversations] = useState([])
  const [selectedNumber, setSelectedNumber] = useState('')
  const [message, setMessage] = useState('')
  const [attachment, setAttachment] = useState(null)
  const [attachmentMenuOpen, setAttachmentMenuOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState('')
  const [deleteCandidate, setDeleteCandidate] = useState('')
  const [error, setError] = useState('')
  const messagesEndRef = useRef(null)
  const documentInputRef = useRef(null)

  const loadData = useCallback(async () => {
    const responses = await Promise.all([
      fetch('/api/whatsapp/status'),
      fetch('/api/messaging/contacts'),
      fetch('/api/whatsapp/conversations'),
    ])
    const [nextStatus, contactData, conversationData] = await Promise.all(responses.map(readResponse))
    setStatus(nextStatus)
    setContacts((contactData.contacts || []).filter((contact) => contact.whatsapp))
    setConversations(conversationData.conversations || [])
  }, [])

  const loadConversationMessages = useCallback(async (number) => {
    const response = await fetch(`/api/whatsapp/conversations/${encodeURIComponent(number)}`)
    const data = await readResponse(response)
    setMessages(data.messages || [])
  }, [])

  useEffect(() => {
    if (!isActive) return undefined
    const load = async () => {
      try {
        await loadData()
        setError('')
      } catch (loadError) {
        setError(loadError.message)
      }
    }
    load()
    const timer = window.setInterval(load, 15000)
    return () => window.clearInterval(timer)
  }, [isActive, loadData])

  useEffect(() => {
    if (!isActive || view !== 'conversation' || !selectedNumber) return undefined
    const refresh = async () => {
      try {
        await loadConversationMessages(selectedNumber)
        setError('')
      } catch (loadError) {
        setError(loadError.message)
      }
    }
    const timer = window.setInterval(refresh, 3000)
    return () => window.clearInterval(timer)
  }, [isActive, loadConversationMessages, selectedNumber, view])

  const lastMessageId = messages.at(-1)?.id
  useEffect(() => {
    if (view === 'conversation' && lastMessageId) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [lastMessageId, view])

  async function sendMessage(event) {
    event.preventDefault()
    if (!selectedNumber || (!message.trim() && !attachment)) return
    if (attachment && attachment.file.size > 10 * 1024 * 1024) {
      setError('Le fichier ne doit pas dépasser 10 Mo.')
      return
    }
    setLoading('send')
    setError('')
    try {
      let response
      if (attachment) {
        const body = new FormData()
        body.append('to', selectedNumber)
        body.append('message', message.trim())
        body.append('document', attachment.file)
        response = await fetch('/api/whatsapp/send-media', { method: 'POST', body })
      } else {
        response = await fetch('/api/whatsapp/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ to: selectedNumber, message: message.trim() }),
        })
      }
      await readResponse(response)
      setMessage('')
      setAttachment(null)
      setAttachmentMenuOpen(false)
      if (documentInputRef.current) documentInputRef.current.value = ''
      await loadData()
      if (view === 'conversation') await loadConversationMessages(selectedNumber)
    } catch (sendError) {
      setError(sendError.message)
    } finally {
      setLoading('')
    }
  }

  async function openConversation(conversation) {
    setLoading(conversation.number)
    setError('')
    try {
      setSelectedNumber(conversation.number)
      await loadConversationMessages(conversation.number)
      setView('conversation')
    } catch (loadError) {
      setError(loadError.message)
    } finally {
      setLoading('')
    }
  }

  async function deleteConversation(number) {
    setLoading(`delete:${number}`)
    setError('')
    try {
      const response = await fetch(`/api/whatsapp/conversations/${encodeURIComponent(number)}`, {
        method: 'DELETE',
      })
      await readResponse(response)
      setDeleteCandidate('')
      if (selectedNumber === number) {
        setSelectedNumber('')
        setMessages([])
      }
      await loadData()
    } catch (deleteError) {
      setError(deleteError.message)
    } finally {
      setLoading('')
    }
  }

  const connected = Boolean(status?.configured && status?.bridge_reachable && status?.connected)
  const selectedContact = contacts.find(
    (contact) => normalizeWhatsAppNumber(contact.whatsapp) === normalizeWhatsAppNumber(selectedNumber),
  )

  function handleMessagePaste(event) {
    const clipboardImage = [...event.clipboardData.items]
      .find((item) => item.kind === 'file' && item.type.startsWith('image/'))
      ?.getAsFile()
    if (!clipboardImage) return
    event.preventDefault()
    if (clipboardImage.size > 10 * 1024 * 1024) {
      setError('L’image collée ne doit pas dépasser 10 Mo.')
      return
    }
    const extension = clipboardImage.type.split('/')[1]?.replace('jpeg', 'jpg') || 'png'
    const pastedImage = new File(
      [clipboardImage],
      `image-collee-${new Date().toISOString().replace(/[:.]/g, '-')}.${extension}`,
      { type: clipboardImage.type },
    )
    setError('')
    setAttachment({ file: pastedImage, kind: 'Image' })
  }

  return (
    <section className={`h-full ${view === 'conversation' ? 'overflow-hidden' : 'overflow-y-auto'}`}>
      <div className={`mx-auto w-full max-w-4xl ${view === 'conversation' ? 'flex h-full min-h-0 flex-col' : ''}`}>
        <header className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <WhatsAppLogo />
            <h2 className="text-xl font-semibold text-white">WhatsApp</h2>
          </div>
          <span className={`rounded-full px-3 py-1.5 text-sm font-medium ${connected ? 'bg-emerald-950 text-emerald-300' : 'bg-gray-800 text-gray-400'}`}>
            {connected ? '● Connecté' : '○ Non connecté'}
          </span>
        </header>

        {error && <p className="mb-4 rounded-xl border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
        {view === 'menu' && (
          <div className="grid gap-4 sm:grid-cols-2">
            <MenuCard title="Nouveau message" description="Choisir un contact enregistré et rédiger un message WhatsApp." action="Ouvrir le formulaire" onClick={() => setView('compose')} />
            <MenuCard title="Conversations" description="Consulter les échanges WhatsApp enregistrés par ARIA." action={`${conversations.length} conversation${conversations.length > 1 ? 's' : ''}`} onClick={() => setView('conversations')} />
            <MenuCard title="Contacts" description={`${contacts.length} contact${contacts.length > 1 ? 's' : ''} WhatsApp disponible${contacts.length > 1 ? 's' : ''}.`} action="Choisir un contact" onClick={() => setView('compose')} />
            <MenuCard title="État de la connexion" description={connected ? 'Le pont WhatsApp est prêt à envoyer et recevoir.' : 'Configure ou reconnecte WhatsApp depuis l’onglet Messagerie.'} action="Actualiser" onClick={loadData} />
          </div>
        )}

        {view === 'compose' && (
          <div>
            <BackButton onClick={() => setView('menu')} />
            <form onSubmit={sendMessage} className="rounded-2xl border border-gray-700 bg-gray-800/70 p-6">
              <h3 className="text-xl font-semibold text-white">Rédiger un message</h3>
              <label className="mt-5 block text-sm text-gray-300">
                Contact
                <select value={selectedNumber} onChange={(event) => setSelectedNumber(event.target.value)} required className="mt-1 block w-full rounded-lg border border-gray-600 bg-gray-900 px-3 py-2.5 text-white">
                  <option value="">Choisir un contact…</option>
                  {contacts.map((contact) => <option key={contact.whatsapp} value={contact.whatsapp}>{contact.name} · {formatWhatsAppNumber(contact.whatsapp)}</option>)}
                </select>
              </label>
              <label className="mt-4 block text-sm text-gray-300">
                Message
                <textarea value={message} onChange={(event) => setMessage(event.target.value)} required maxLength={4000} rows={6} placeholder="Écris ton message…" className="mt-1 block w-full resize-y rounded-lg border border-gray-600 bg-gray-900 px-3 py-2.5 text-white" />
              </label>
              {contacts.length === 0 && <p className="mt-3 text-sm text-amber-300">Ajoute d’abord un contact WhatsApp dans l’onglet Messagerie.</p>}
              <button type="submit" disabled={!connected || !selectedNumber || !message.trim() || Boolean(loading)} className="mt-5 min-h-[44px] rounded-lg bg-emerald-600 px-5 font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">
                {loading === 'send' ? 'Envoi…' : 'Envoyer sur WhatsApp'}
              </button>
            </form>
          </div>
        )}

        {view === 'conversations' && (
          <div>
            <BackButton onClick={() => setView('menu')} />
            <div className="space-y-3">
              {conversations.length === 0 ? (
                <p className="rounded-xl border border-gray-700 bg-gray-800/70 p-5 text-gray-400">Aucune conversation WhatsApp enregistrée.</p>
              ) : conversations.map((conversation) => (
                <div key={conversation.number} className="rounded-xl border border-gray-700 bg-gray-800/70 p-2">
                  <div className="flex items-center gap-2">
                    <button type="button" onClick={() => openConversation(conversation)} className="flex min-w-0 flex-1 items-center justify-between gap-4 rounded-lg p-2 text-left hover:bg-gray-800">
                      <span className="min-w-0">
                        <strong className="block text-white">{conversation.name === conversation.number ? formatWhatsAppNumber(conversation.number) : conversation.name}</strong>
                        <span className="mt-1 block truncate text-sm text-gray-400">{conversation.last_message || 'Aucun message'}</span>
                      </span>
                      <span className="shrink-0 text-xs text-gray-500">{loading === conversation.number ? 'Chargement…' : formatMessageDate(conversation.updated_at)}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteCandidate(conversation.number)}
                      aria-label={`Supprimer la conversation avec ${conversation.name}`}
                      title="Supprimer la conversation"
                      className="shrink-0 rounded-lg p-2 text-red-400 hover:bg-red-950/50 hover:text-red-300"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 fill-none stroke-current" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 7h16m-10 4v6m4-6v6M9 7V4h6v3m-9 0 1 14h10l1-14" />
                      </svg>
                    </button>
                  </div>
                  {deleteCandidate === conversation.number && (
                    <div className="mt-2 flex flex-wrap items-center justify-end gap-2 border-t border-gray-700 pt-2">
                      <span className="mr-auto text-sm text-red-300">Supprimer cet historique ?</span>
                      <button type="button" onClick={() => setDeleteCandidate('')} className="rounded-lg border border-gray-600 px-3 py-2 text-sm text-gray-300 hover:bg-gray-700">Annuler</button>
                      <button type="button" disabled={loading === `delete:${conversation.number}`} onClick={() => deleteConversation(conversation.number)} className="rounded-lg bg-red-700 px-3 py-2 text-sm font-semibold text-white hover:bg-red-600 disabled:opacity-50">
                        {loading === `delete:${conversation.number}` ? 'Suppression…' : 'Supprimer'}
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {view === 'conversation' && (
          <div className="flex min-h-0 flex-1 flex-col">
            <BackButton onClick={() => setView('conversations')} />
            <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-gray-700 bg-gray-800/70 p-5">
              <h3 className="font-normal text-white">
                Conversation avec{' '}
                {selectedContact && <strong className="font-semibold">{selectedContact.name}</strong>}
                {selectedContact && <span> · </span>}
                <span>{formatWhatsAppNumber(selectedNumber)}</span>
              </h3>
              <div aria-label="Messages WhatsApp" className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto pr-2">
                {messages.map((item) => (
                  <div key={item.id} className={`flex ${item.role === 'user' ? 'justify-start' : 'justify-end'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${item.role === 'user' ? 'bg-gray-700 text-gray-100' : 'bg-emerald-700 text-white'}`}>
                      <p className="whitespace-pre-wrap">{item.content}</p>
                      {item.image && (
                        <div className="mt-2">
                          <img
                            src={item.image.url}
                            alt={`Image reçue de ${selectedContact?.name || 'ce contact'}`}
                            onLoad={() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })}
                            className="max-h-96 max-w-full rounded-xl object-contain"
                          />
                          <a
                            href={`${item.image.url}?download=true`}
                            download={item.image.file_name}
                            className="mt-2 inline-flex rounded-lg bg-black/20 px-3 py-2 text-xs font-semibold text-white hover:bg-black/30"
                          >
                            Télécharger l’image
                          </a>
                        </div>
                      )}
                      {item.document && (
                        <a
                          href={`${item.document.url}?download=true`}
                          download={item.document.file_name}
                          className="mt-2 flex items-center gap-2 rounded-xl bg-black/20 px-3 py-3 font-medium text-white hover:bg-black/30"
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 shrink-0 fill-none stroke-current" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8m-6-6v6h6M8 13h8m-8 4h5" />
                          </svg>
                          <span className="truncate">{item.document.file_name}</span>
                        </a>
                      )}
                      {item.audio && (
                        <div className="mt-2">
                          <audio controls preload="metadata" src={item.audio.url} className="max-w-full">
                            Ton navigateur ne peut pas lire ce fichier audio.
                          </audio>
                          <a href={`${item.audio.url}?download=true`} download={item.audio.file_name} className="mt-2 inline-flex text-xs font-semibold text-white underline decoration-white/40 underline-offset-2">
                            Télécharger l’audio
                          </a>
                        </div>
                      )}
                      <p className="mt-1 flex justify-end gap-2 text-right text-[10px]">
                        <span className="opacity-60">{formatMessageDate(item.created_at)}</span>
                        {item.role !== 'user' && <DeliveryStatus status={item.delivery_status} />}
                      </p>
                    </div>
                  </div>
                ))}
                {messages.length === 0 && <p className="text-sm text-gray-400">Aucun message enregistré.</p>}
                <div ref={messagesEndRef} aria-hidden="true" />
              </div>
              <form onSubmit={sendMessage} className="mt-4 shrink-0 border-t border-gray-700 pt-4">
                {attachment && (
                  <div className="mb-2 flex items-center gap-2 rounded-lg bg-gray-700 px-3 py-2 text-sm text-gray-200">
                    <span className="rounded bg-gray-600 px-2 py-0.5 text-xs">{attachment.kind}</span>
                    <span className="min-w-0 flex-1 truncate">{attachment.file.name}</span>
                    <button type="button" onClick={() => { setAttachment(null); if (documentInputRef.current) documentInputRef.current.value = '' }} aria-label="Retirer le fichier" className="rounded px-2 py-1 text-gray-400 hover:bg-gray-600 hover:text-white">×</button>
                  </div>
                )}
                <div className="flex items-end gap-2">
                  <input
                    ref={documentInputRef}
                    type="file"
                    className="sr-only"
                    onChange={(event) => {
                      const file = event.target.files?.[0] || null
                      if (file && file.size > 10 * 1024 * 1024) {
                        setAttachment(null)
                        setError('Le fichier ne doit pas dépasser 10 Mo.')
                        event.target.value = ''
                        return
                      }
                      setError('')
                      if (file) {
                        const kind = file.type.startsWith('image/') ? 'Image' : file.type.startsWith('audio/') ? 'Audio' : 'Document'
                        setAttachment({ file, kind })
                      }
                    }}
                  />
                  <div className="relative">
                    {attachmentMenuOpen && (
                      <div className="absolute bottom-14 left-0 z-10 w-44 overflow-hidden rounded-xl border border-gray-600 bg-gray-800 p-1 shadow-xl">
                        {[
                          ['Image', 'image/jpeg,image/png,image/webp,image/gif'],
                          ['Document', '*/*'],
                          ['Audio', 'audio/*'],
                        ].map(([label, accept]) => (
                          <button
                            key={label}
                            type="button"
                            onClick={() => {
                              if (documentInputRef.current) {
                                documentInputRef.current.accept = accept
                                documentInputRef.current.click()
                              }
                              setAttachmentMenuOpen(false)
                            }}
                            className="block w-full rounded-lg px-3 py-2 text-left text-sm text-gray-200 hover:bg-gray-700"
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    )}
                    <button type="button" onClick={() => setAttachmentMenuOpen((open) => !open)} disabled={!connected || Boolean(loading)} aria-label="Joindre un fichier" title="Joindre une image, un document ou un audio" className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-gray-600 text-gray-300 hover:bg-gray-700 disabled:opacity-50">
                      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 fill-none stroke-current" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m21.4 11.6-8.9 8.9a6 6 0 0 1-8.5-8.5l9.6-9.6a4 4 0 0 1 5.7 5.7l-9.6 9.6a2 2 0 0 1-2.8-2.8l8.9-8.9" />
                      </svg>
                    </button>
                  </div>
                  <textarea
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    onPaste={handleMessagePaste}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault()
                        event.currentTarget.form?.requestSubmit()
                      }
                    }}
                    maxLength={4000}
                    rows={1}
                    placeholder="Écrire un message"
                    aria-label="Message WhatsApp"
                    className="max-h-32 min-h-[44px] flex-1 resize-y rounded-2xl border border-gray-600 bg-gray-900 px-4 py-2.5 text-white placeholder:text-gray-500"
                  />
                  <button type="submit" disabled={!connected || (!message.trim() && !attachment) || Boolean(loading)} aria-label="Envoyer le message" className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50">
                    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 fill-none stroke-current" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="m22 2-7 20-4-9-9-4 20-7ZM11 13l4-4" />
                    </svg>
                  </button>
                </div>
                <p className="mt-1 px-14 text-xs text-gray-500">Entrée : envoyer · Maj+Entrée : nouvelle ligne · Ctrl+V : texte ou image · 10 Mo max.</p>
              </form>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
