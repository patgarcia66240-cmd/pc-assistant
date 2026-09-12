// Pont local entre ARIA et WhatsApp — service Node.js séparé du backend Python, parce que
// Baileys (bibliothèque WhatsApp non officielle, voir README.md) n'existe qu'en JS/TS. Se
// connecte à WhatsApp Web via websocket (pas de navigateur), en scannant un QR code une seule
// fois avec le téléphone dédié à ARIA — voir README.md pour la procédure complète.
//
// Ce que fait ce service, et rien de plus :
//   - reçoit les messages WhatsApp entrants (1-to-1 seulement, les groupes sont ignorés) et les
//     transmet au backend ARIA (POST /api/whatsapp/incoming) ;
//   - expose trois routes locales pour le backend : GET /status (diagnostic, inclut le QR code
//     à scanner tant que la session n'est pas liée), POST /send (poster une réponse sur
//     WhatsApp) et GET /contacts (contacts synchronisés depuis le téléphone lié — ajouté le
//     12/09/2026 pour permettre de les importer dans le carnet d'ARIA sans les retaper à la
//     main, voir backend/plugins/messaging/ "Carnet de contacts").
// Toute la logique "qui a le droit de parler à ARIA" et "que répondre" vit côté backend
// (backend/plugins/whatsapp/router.py) — ce fichier ne fait que relayer.
import 'dotenv/config'
import http from 'node:http'
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  makeWASocket,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  DisconnectReason,
  downloadMediaMessage,
  normalizeMessageContent,
} from '@whiskeysockets/baileys'
import pino from 'pino'
import QRCode from 'qrcode'
import qrcodeTerminal from 'qrcode-terminal'

const PORT = Number(process.env.PORT || 3001)
const BACKEND_URL = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const BRIDGE_SECRET = process.env.WHATSAPP_BRIDGE_SECRET || ''
const AUTH_DIR = process.env.AUTH_DIR || './auth'
const PROCESSED_MESSAGES_PATH = resolve(AUTH_DIR, 'processed-messages.json')
const LID_MAPPINGS_PATH = resolve(AUTH_DIR, 'lid-mappings.json')
const MAX_IMAGE_BYTES = 10 * 1024 * 1024
const MAX_DOCUMENT_BYTES = 10 * 1024 * 1024

if (!BRIDGE_SECRET) {
  console.error('[pont WhatsApp] WHATSAPP_BRIDGE_SECRET manquant dans whatsapp-bridge/.env — obligatoire (doit être identique à backend/.env). Arrêt.')
  process.exit(1)
}

let sock = null
let isConnected = false
// data:image/png;base64,... — lu par GET /status et affiché dans une fenêtre modale côté app
// (voir Messaging.jsx, ajouté le 12/09/2026 à la demande de Sarah, qui préfère ça au QR ASCII
// affiché dans ce terminal — gardé quand même ci-dessous en secours si l'app n'est pas ouverte).
let latestQrDataUrl = null
// jid ("33612345678@s.whatsapp.net") -> { number, name } — rempli au fil des évènements
// contacts.upsert/contacts.update émis par Baileys (synchronisation depuis le téléphone lié,
// pas instantanée ni forcément exhaustive). Lu par GET /contacts. Ajouté le 12/09/2026.
const contactsMap = new Map()
const lidToPhoneJid = loadLidMappings()
const processedMessageIds = loadProcessedMessageIds()
const pendingAriaMessages = []
const trackedDeliveryStatuses = new Map()

function deliveryStatus(status) {
  return {
    0: 'failed',
    1: 'pending',
    2: 'sent',
    3: 'delivered',
    4: 'read',
    5: 'read',
  }[Number(status)] || 'pending'
}

async function forwardDeliveryStatus(messageId, status) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/whatsapp/delivery`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Bridge-Secret': BRIDGE_SECRET },
      body: JSON.stringify({ message_id: messageId, status }),
    })
    if (!response.ok) {
      console.error(`[pont WhatsApp] Statut ${status} refusé par le backend pour ${messageId}`)
    }
  } catch (error) {
    console.error('[pont WhatsApp] Échec du relais d’un statut de livraison :', error)
  }
}

function messageRecipientNumber(jid) {
  const resolvedJid = lidToPhoneJid.get(jid) || jid || ''
  return resolvedJid.split('@')[0]
}

function markAriaMessagePending(jid, text, hasMedia = false) {
  pendingAriaMessages.push({
    number: messageRecipientNumber(jid),
    text,
    hasMedia,
    expiresAt: Date.now() + 30_000,
  })
}

function removePendingAriaMessage(jid, text, hasMedia = false) {
  const number = messageRecipientNumber(jid)
  const index = pendingAriaMessages.findIndex(
    (item) => item.number === number && item.text === text && item.hasMedia === hasMedia,
  )
  if (index !== -1) pendingAriaMessages.splice(index, 1)
}

function consumePendingAriaMessage(jid, alternativeJid, text, hasMedia = false) {
  const now = Date.now()
  for (let index = pendingAriaMessages.length - 1; index >= 0; index -= 1) {
    if (pendingAriaMessages[index].expiresAt <= now) pendingAriaMessages.splice(index, 1)
  }
  const numbers = new Set([
    messageRecipientNumber(jid),
    messageRecipientNumber(alternativeJid),
  ])
  const index = pendingAriaMessages.findIndex(
    (item) => numbers.has(item.number) && item.text === text && item.hasMedia === hasMedia,
  )
  if (index === -1) return false
  pendingAriaMessages.splice(index, 1)
  return true
}

function loadLidMappings() {
  try {
    return new Map(Object.entries(JSON.parse(readFileSync(LID_MAPPINGS_PATH, 'utf8'))))
  } catch (error) {
    if (error?.code !== 'ENOENT') {
      console.error('[pont WhatsApp] Associations LID illisibles :', error)
    }
    return new Map()
  }
}

function loadProcessedMessageIds() {
  try {
    return new Set(JSON.parse(readFileSync(PROCESSED_MESSAGES_PATH, 'utf8')))
  } catch (error) {
    if (error?.code !== 'ENOENT') {
      console.error('[pont WhatsApp] Historique des identifiants de messages illisible :', error)
    }
    return new Set()
  }
}

function clearWhatsAppCredentials() {
  mkdirSync(AUTH_DIR, { recursive: true })
  const preservedFiles = new Set(['processed-messages.json', 'lid-mappings.json'])
  for (const entry of readdirSync(AUTH_DIR, { withFileTypes: true })) {
    if (preservedFiles.has(entry.name)) continue
    rmSync(resolve(AUTH_DIR, entry.name), { recursive: entry.isDirectory(), force: true })
  }
}

function markMessageProcessed(messageId) {
  if (!messageId) return
  processedMessageIds.add(messageId)
  const recentIds = [...processedMessageIds].slice(-2000)
  processedMessageIds.clear()
  for (const id of recentIds) processedMessageIds.add(id)
  writeFileSync(PROCESSED_MESSAGES_PATH, JSON.stringify(recentIds))
}

function rememberLidMapping(phoneJid, lidJid) {
  if (typeof phoneJid !== 'string' || typeof lidJid !== 'string') return
  const normalizedPhoneJid = phoneJid.includes('@') ? phoneJid : `${phoneJid}@s.whatsapp.net`
  const normalizedLidJid = lidJid.includes('@') ? lidJid : `${lidJid}@lid`
  if (!normalizedPhoneJid.endsWith('@s.whatsapp.net') || !normalizedLidJid.endsWith('@lid')) return
  lidToPhoneJid.set(normalizedLidJid, normalizedPhoneJid)
  writeFileSync(LID_MAPPINGS_PATH, JSON.stringify(Object.fromEntries(lidToPhoneJid)))
  console.log(`[pont WhatsApp] Association LID mémorisée pour ${normalizedPhoneJid}`)
}

function upsertContact(contact) {
  const jid = contact?.jid || contact?.id
  const lid = contact?.lid || (contact?.id?.endsWith('@lid') ? contact.id : null)
  rememberLidMapping(jid, lid)
  if (!jid || !jid.endsWith('@s.whatsapp.net')) return
  const name = contact.name || contact.notify || contact.verifiedName
  if (!name) return // un numéro sans nom n'apporte rien de plus que le taper à la main dans le carnet
  const number = jid.split('@')[0]
  if (!/^\d+$/.test(number)) return // JID non numérique (ex. @lid) — pas exploitable côté carnet
  contactsMap.set(jid, { number, name })
}

async function processIncomingMessage(msg, replyEnabled, logger, imagesOnly = false) {
  if (!msg.message) return
  const content = normalizeMessageContent(msg.message)
  const documentMessage = content?.documentMessage
  const imageMessage = content?.imageMessage
  const audioMessage = content?.audioMessage
  const mediaMessage = imageMessage || documentMessage || audioMessage
  const mediaKind = imageMessage ? 'image' : documentMessage ? 'document' : audioMessage ? 'audio' : null
  if (msg.key.id && processedMessageIds.has(msg.key.id)) return
  if (msg.key.remoteJid?.endsWith('@g.us')) return
  if (imagesOnly && !mediaMessage) return
  const text = content?.conversation
    || content?.extendedTextMessage?.text
    || mediaMessage?.caption
    || content?.videoMessage?.caption
  if (
    msg.key.fromMe
    && consumePendingAriaMessage(
      msg.key.remoteJid,
      msg.key.remoteJidAlt,
      text || '',
      Boolean(mediaMessage),
    )
  ) {
    markMessageProcessed(msg.key.id)
    console.log('[pont WhatsApp] Message envoyé par ARIA déjà enregistré par le backend')
    return
  }
  if (!text && !mediaMessage) {
    console.warn(`[pont WhatsApp] Message entrant sans texte exploitable : ${Object.keys(content || {}).join(', ')}`)
    return
  }

  let media = null
  if (mediaMessage) {
    const maxBytes = mediaKind === 'image' ? MAX_IMAGE_BYTES : MAX_DOCUMENT_BYTES
    const declaredSize = Number(mediaMessage.fileLength || 0)
    if (declaredSize > maxBytes) {
      console.warn(`[pont WhatsApp] Fichier ignoré car il dépasse ${maxBytes} octets`)
      return
    }
    const buffer = await downloadMediaMessage(
      msg,
      'buffer',
      {},
      { logger, reuploadRequest: sock.updateMediaMessage },
    )
    if (buffer.length > maxBytes) {
      console.warn(`[pont WhatsApp] Fichier ignoré car il dépasse ${maxBytes} octets`)
      return
    }
    const mimeType = mediaMessage.mimetype || 'application/octet-stream'
    const extension = mimeType === 'image/jpeg'
      ? 'jpg'
      : mimeType.split('/')[1]?.split(';')[0]?.replace(/[^a-z0-9]/gi, '') || 'bin'
    media = {
      base64: buffer.toString('base64'),
      mimeType,
      fileName: mediaMessage.fileName || `${mediaKind}-whatsapp-${msg.key.id || Date.now()}.${extension}`,
      kind: mediaKind,
    }
  }

  const receivedJid = msg.key.remoteJid
  const senderJid = msg.key.remoteJidAlt || lidToPhoneJid.get(receivedJid) || receivedJid
  if (receivedJid?.endsWith('@lid') && senderJid === receivedJid) {
    console.warn(`[pont WhatsApp] Message entrant reçu avec un identifiant LID non résolu : ${receivedJid}`)
  }
  const result = await forwardToBackend(
    senderJid,
    text || '',
    media || msg.key.fromMe ? false : replyEnabled,
    media,
    Boolean(msg.key.fromMe),
    msg.key.id || null,
    msg.key.fromMe ? deliveryStatus(msg.status) : null,
  )
  if (result.status !== 'ignored') {
    markMessageProcessed(msg.key.id)
    console.log(`[pont WhatsApp] Message entrant relayé au backend : ${senderJid}`)
  } else {
    console.warn(`[pont WhatsApp] Message refusé par le backend : ${result.reason || 'raison inconnue'}`)
  }
}

async function startSock() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR)
  const { version } = await fetchLatestBaileysVersion()
  const logger = pino({ level: 'silent' })

  sock = makeWASocket({
    version,
    auth: state,
    logger,
    // Pas d'option "printQRInTerminal" (dépréciée côté Baileys) : le QR est géré manuellement
    // ci-dessous via l'évènement connection.update, plus fiable dans la durée.
  })

  sock.ev.on('creds.update', saveCreds)

  sock.ev.on('contacts.upsert', (contacts) => {
    for (const contact of contacts) upsertContact(contact)
  })
  sock.ev.on('contacts.update', (updates) => {
    for (const update of updates) upsertContact(update)
  })

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update

    if (qr) {
      console.log('\n[pont WhatsApp] Scanne ce QR code avec le téléphone dédié à ARIA (WhatsApp > Appareils liés > Lier un appareil) :\n')
      qrcodeTerminal.generate(qr, { small: true })
      QRCode.toDataURL(qr)
        .then((dataUrl) => { latestQrDataUrl = dataUrl })
        .catch((error) => console.error('[pont WhatsApp] Échec de génération du QR code image :', error))
    }

    if (connection === 'open') {
      isConnected = true
      latestQrDataUrl = null // la session est liée, plus rien à scanner
      console.log('[pont WhatsApp] Connecté à WhatsApp.')
    }

    if (connection === 'close') {
      isConnected = false
      const statusCode = lastDisconnect?.error?.output?.statusCode
      const loggedOut = statusCode === DisconnectReason.loggedOut
      if (loggedOut) {
        console.log('[pont WhatsApp] Déconnecté (session invalidée côté WhatsApp) — supprime le dossier auth/ et relance pour scanner un nouveau QR code.')
      } else {
        console.log(`[pont WhatsApp] Connexion fermée (code ${statusCode ?? 'inconnu'}), reconnexion...`)
        startSock()
      }
    }
  })

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    console.log(`[pont WhatsApp] Évènement messages.upsert : type=${type}, nombre=${messages.length}`)
    if (type !== 'notify' && type !== 'append') return

    for (const msg of messages) {
      try {
        await processIncomingMessage(msg, type === 'notify', logger)
      } catch (error) {
        console.error('[pont WhatsApp] Échec du relais vers le backend :', error)
      }
    }
  })

  sock.ev.on('messages.update', async (updates) => {
    for (const { key, update } of updates) {
      const messageId = key?.id
      if (!messageId || update?.status === undefined) continue
      const status = deliveryStatus(update.status)
      trackedDeliveryStatuses.set(messageId, status)
      console.log(`[pont WhatsApp] Statut du message ${messageId} : ${status}`)
      await forwardDeliveryStatus(messageId, status)
    }
  })

}

async function forwardToBackend(
  fromJid,
  text,
  replyEnabled,
  media = null,
  fromMe = false,
  whatsappMessageId = null,
  currentDeliveryStatus = null,
) {
  const response = await fetch(`${BACKEND_URL}/api/whatsapp/incoming`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Bridge-Secret': BRIDGE_SECRET },
    body: JSON.stringify({
      from_number: fromJid,
      message: text,
      reply_enabled: replyEnabled,
      image_base64: media?.kind === 'image' ? media.base64 : null,
      image_mime_type: media?.kind === 'image' ? media.mimeType : null,
      image_file_name: media?.kind === 'image' ? media.fileName : null,
      document_base64: media?.kind === 'document' ? media.base64 : null,
      document_mime_type: media?.kind === 'document' ? media.mimeType : null,
      document_file_name: media?.kind === 'document' ? media.fileName : null,
      audio_base64: media?.kind === 'audio' ? media.base64 : null,
      audio_mime_type: media?.kind === 'audio' ? media.mimeType : null,
      audio_file_name: media?.kind === 'audio' ? media.fileName : null,
      whatsapp_message_id: fromMe ? whatsappMessageId : null,
      delivery_status: fromMe ? currentDeliveryStatus : null,
      from_me: fromMe,
    }),
  })
  if (!response.ok) {
    throw new Error(`le backend a répondu ${response.status} pour un message de ${fromJid}`)
  }
  return response.json()
}

// Petit serveur HTTP local (module http natif, pas besoin d'Express pour deux routes) : le
// backend ARIA l'appelle pour poster une réponse sur WhatsApp et vérifier l'état de connexion.
const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/status') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    // qr : null une fois connecté (rien à scanner), sinon la dernière image générée (peut être
    // null aussi tout au début, le temps que Baileys émette son premier QR).
    res.end(JSON.stringify({ connected: isConnected, qr: isConnected ? null : latestQrDataUrl }))
    return
  }

  if (req.method === 'GET' && req.url === '/contacts') {
    if (req.headers['x-bridge-secret'] !== BRIDGE_SECRET) {
      res.writeHead(403, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ error: 'invalid secret' }))
      return
    }
    const contacts = [...contactsMap.values()].sort((a, b) => a.name.localeCompare(b.name))
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ contacts }))
    return
  }

  if (req.method === 'POST' && req.url === '/logout') {
    if (req.headers['x-bridge-secret'] !== BRIDGE_SECRET) {
      res.writeHead(403, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ error: 'invalid secret' }))
      return
    }
    ;(async () => {
      try {
        if (sock && isConnected) await sock.logout()
        sock = null
        isConnected = false
        latestQrDataUrl = null
        clearWhatsAppCredentials()
        res.writeHead(200, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ status: 'disconnected' }))
        setTimeout(() => {
          startSock().catch((error) => console.error('[pont WhatsApp] Échec de préparation du nouveau QR code :', error))
        }, 500)
      } catch (error) {
        res.writeHead(500, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ error: String(error?.message || error) }))
      }
    })()
    return
  }

  if (req.method === 'POST' && req.url === '/send') {
    if (req.headers['x-bridge-secret'] !== BRIDGE_SECRET) {
      res.writeHead(403, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ error: 'invalid secret' }))
      return
    }
    let body = ''
    req.on('data', (chunk) => { body += chunk })
    req.on('end', async () => {
      try {
        const { to, message } = JSON.parse(body)
        if (!to || !message) throw new Error('paramètres "to"/"message" manquants')
        if (!sock || !isConnected) throw new Error('pas connecté à WhatsApp')
        const jid = to.includes('@') ? to : `${to}@s.whatsapp.net`
        const [recipient] = await sock.onWhatsApp(jid)
        if (!recipient?.exists) throw new Error('ce numéro n’utilise pas WhatsApp')
        rememberLidMapping(recipient.jid, recipient.lid)
        const recipientJid = recipient.jid || jid
        markAriaMessagePending(recipientJid, message)
        try {
          const sentMessage = await sock.sendMessage(recipientJid, { text: message })
          if (!sentMessage?.key?.id) throw new Error('WhatsApp n’a pas retourné d’identifiant de message')
          const currentStatus = trackedDeliveryStatuses.get(sentMessage.key.id)
            || deliveryStatus(sentMessage.status)
          trackedDeliveryStatuses.set(sentMessage.key.id, currentStatus)
          res.writeHead(200, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({
            status: 'sent',
            messageId: sentMessage.key.id,
            deliveryStatus: currentStatus,
          }))
        } catch (error) {
          removePendingAriaMessage(recipientJid, message)
          throw error
        }
      } catch (error) {
        res.writeHead(400, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ error: String(error?.message || error) }))
      }
    })
    return
  }

  if (req.method === 'POST' && (req.url === '/send-document' || req.url === '/send-media')) {
    if (req.headers['x-bridge-secret'] !== BRIDGE_SECRET) {
      res.writeHead(403, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ error: 'invalid secret' }))
      return
    }
    let body = ''
    let tooLarge = false
    req.on('data', (chunk) => {
      if (tooLarge) return
      body += chunk
      if (Buffer.byteLength(body) > MAX_DOCUMENT_BYTES * 1.5) {
        tooLarge = true
        body = ''
      }
    })
    req.on('end', async () => {
      try {
        if (tooLarge) throw new Error('document supérieur à 10 Mo')
        const { to, caption = '', fileName, mimeType, mediaKind = 'document', base64 } = JSON.parse(body)
        if (!to || !fileName || !mimeType || !base64) {
          throw new Error('paramètres de fichier manquants')
        }
        if (!['image', 'document', 'audio'].includes(mediaKind)) throw new Error('type de fichier invalide')
        if (!sock || !isConnected) throw new Error('pas connecté à WhatsApp')
        const data = Buffer.from(base64, 'base64')
        if (!data.length || data.length > MAX_DOCUMENT_BYTES) {
          throw new Error('fichier vide ou supérieur à 10 Mo')
        }
        const jid = to.includes('@') ? to : `${to}@s.whatsapp.net`
        const [recipient] = await sock.onWhatsApp(jid)
        if (!recipient?.exists) throw new Error('ce numéro n’utilise pas WhatsApp')
        rememberLidMapping(recipient.jid, recipient.lid)
        const recipientJid = recipient.jid || jid
        const mediaCaption = mediaKind === 'audio' ? '' : caption
        markAriaMessagePending(recipientJid, mediaCaption, true)
        if (mediaKind === 'audio' && caption) markAriaMessagePending(recipientJid, caption, false)
        try {
          const content = mediaKind === 'image'
            ? { image: data, mimetype: mimeType, caption: caption || undefined }
            : mediaKind === 'audio'
              ? { audio: data, mimetype: mimeType, ptt: false }
              : { document: data, mimetype: mimeType, fileName, caption: caption || undefined }
          const sentMedia = await sock.sendMessage(recipientJid, content)
          if (!sentMedia?.key?.id) throw new Error('WhatsApp n’a pas retourné d’identifiant de fichier')
          const mediaDeliveryStatus = trackedDeliveryStatuses.get(sentMedia.key.id)
            || deliveryStatus(sentMedia.status)
          trackedDeliveryStatuses.set(sentMedia.key.id, mediaDeliveryStatus)
          let sentCaption = null
          if (mediaKind === 'audio' && caption) {
            sentCaption = await sock.sendMessage(recipientJid, { text: caption })
            if (!sentCaption?.key?.id) throw new Error('WhatsApp n’a pas retourné d’identifiant de légende')
            const captionStatus = trackedDeliveryStatuses.get(sentCaption.key.id)
              || deliveryStatus(sentCaption.status)
            trackedDeliveryStatuses.set(sentCaption.key.id, captionStatus)
          }
          res.writeHead(200, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({
            status: 'sent',
            messageId: sentMedia.key.id,
            captionMessageId: sentCaption?.key?.id || null,
            deliveryStatus: mediaDeliveryStatus,
            captionDeliveryStatus: sentCaption
              ? trackedDeliveryStatuses.get(sentCaption.key.id)
              : null,
          }))
        } catch (error) {
          removePendingAriaMessage(recipientJid, mediaCaption, true)
          if (mediaKind === 'audio' && caption) removePendingAriaMessage(recipientJid, caption, false)
          throw error
        }
      } catch (error) {
        res.writeHead(400, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({ error: String(error?.message || error) }))
      }
    })
    return
  }

  res.writeHead(404, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({ error: 'not found' }))
})

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[pont WhatsApp] API locale sur http://127.0.0.1:${PORT}`)
})

startSock()
