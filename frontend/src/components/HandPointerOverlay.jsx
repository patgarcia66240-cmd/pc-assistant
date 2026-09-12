import { useCallback, useEffect, useRef, useState } from 'react'
import {
  POINTER_CALIBRATION_CHANGED_EVENT,
  POINTER_CALIBRATION_POINT_EVENT,
  POINTER_CALIBRATION_START_EVENT,
  POINTER_CALIBRATION_STOP_EVENT,
  POINTER_SETTINGS_CHANGED_EVENT,
  applyPointerCalibration,
  readPointerCalibration,
  readPointerSettings,
} from '../pointerCalibration'

// Mode pointeur : suit l'index de la main GAUCHE pour déplacer un curseur à l'écran, et déclenche
// un clic lorsque le pouce se rapproche du doigt choisi dans les options. Composant monté une
// seule fois, tout en haut de
// App.jsx (pas dans un onglet) : le curseur doit pouvoir cliquer n'importe où dans l'app, pas
// seulement dans l'onglet Assistant vocal — donc sa propre caméra/son propre modèle MediaPipe,
// indépendants du suivi visage/main de VoiceAssistant.jsx (les deux peuvent tourner en même temps
// si les deux sont activés, chacun avec son propre flux caméra — pas recommandé mais pas cassé).
//
// Gauche/droite : MediaPipe classe la main détectée "Left"/"Right" à partir de l'image caméra
// brute (non retournée) — l'étiquette peut être inversée par rapport à l'intuition selon la
// caméra/le navigateur, et je n'ai pas pu le vérifier avec une vraie caméra en sandbox. D'où la
// règle ci-dessous (voir pickHand) : une seule main visible est utilisée quelle que soit son
// étiquette — le cas normal en pratique — et l'étiquette "Left" ne sert qu'à choisir entre les deux
// si les deux mains sont dans le champ. Si jamais le curseur suit la main droite avec les deux
// mains levées, un seul mot à changer ci-dessous (LEFT_HAND_LABEL) pour corriger.
const LEFT_HAND_LABEL = 'Left'

// Choisit quelle main utiliser parmi celles détectées cette frame : la main gauche si les deux
// sont visibles (ou si une seule est visible et étiquetée main droite — pas de main gauche
// possible dans ce cas), sinon la seule main présente, quelle que soit son étiquette. Renvoie
// `null` si aucune main n'est détectée.
function pickHand(result) {
  const handednesses = result.handedness || []
  if (handednesses.length === 0) return null
  if (handednesses.length === 1) return result.landmarks[0] ?? null
  const leftIndex = handednesses.findIndex((entries) => entries?.[0]?.categoryName === LEFT_HAND_LABEL)
  return result.landmarks[leftIndex !== -1 ? leftIndex : 0] ?? null
}

const CURSOR_SIZE = 26
const POSITION_HISTORY_LENGTH = 3
const CAMERA_ACTIVE_AREA = Object.freeze({ left: 0.12, right: 0.88, top: 0.1, bottom: 0.9 })
const MAGNET_DISTANCE = 72
const POINTER_TARGET_SELECTOR =
  'button:not(:disabled):not([data-hand-pointer-ignore]), [role="button"]:not([aria-disabled="true"]):not([data-hand-pointer-ignore])'
const MAX_HORIZONTAL_CURSOR_SPEED = 1100
const MAX_VERTICAL_CURSOR_SPEED = 520
const HAND_LOSS_GRACE_MS = 1500
const DWELL_CLICK_DELAY_MS = 1000
const CLICK_FINGER_TIPS = Object.freeze({ index: 8, middle: 12, ring: 16, pinky: 20 })

function median(values) {
  const sorted = [...values].sort((a, b) => a - b)
  return sorted[Math.floor(sorted.length / 2)]
}

function mapCameraPointToScreen(point) {
  return {
    x: Math.max(
      0,
      Math.min(1, (point.x - CAMERA_ACTIVE_AREA.left) / (CAMERA_ACTIVE_AREA.right - CAMERA_ACTIVE_AREA.left)),
    ),
    y: Math.max(
      0,
      Math.min(1, (point.y - CAMERA_ACTIVE_AREA.top) / (CAMERA_ACTIVE_AREA.bottom - CAMERA_ACTIVE_AREA.top)),
    ),
  }
}

function stabilizedPoint(history, point) {
  history.push(point)
  if (history.length > POSITION_HISTORY_LENGTH) history.shift()
  return {
    x: median(history.map((entry) => entry.x)),
    y: median(history.map((entry) => entry.y)),
  }
}

function magneticTarget(position) {
  let nearest = null
  let nearestDistance = Number.POSITIVE_INFINITY

  document.querySelectorAll(POINTER_TARGET_SELECTOR).forEach((element) => {
    const rect = element.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0 || getComputedStyle(element).visibility === 'hidden') return
    const dx = Math.max(rect.left - position.x, 0, position.x - rect.right)
    const dy = Math.max(rect.top - position.y, 0, position.y - rect.bottom)
    const distance = Math.hypot(dx, dy)
    if (distance < nearestDistance) {
      nearest = { element, rect }
      nearestDistance = distance
    }
  })

  if (!nearest || nearestDistance > MAGNET_DISTANCE) {
    return { position, element: null }
  }

  const center = {
    x: nearest.rect.left + nearest.rect.width / 2,
    y: nearest.rect.top + nearest.rect.height / 2,
  }
  const proximity = 1 - nearestDistance / MAGNET_DISTANCE
  const attraction = nearestDistance === 0 ? 0.72 : 0.45 + proximity * 0.27
  return {
    position: {
      x: position.x + (center.x - position.x) * attraction,
      y: position.y + (center.y - position.y) * attraction,
    },
    element: nearest.element,
  }
}

export default function HandPointerOverlay({ enabled, onError }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const recognizerRef = useRef(null)
  const rafRef = useRef(null)
  const renderRafRef = useRef(null)
  // Dernière position stable du curseur, en pixels écran. Elle n'est pas mise à jour pendant le
  // pincement afin que le clic parte de l'endroit visé.
  const targetRef = useRef(null)
  const smoothedRef = useRef(null)
  const pinchingRef = useRef(false)
  const cursorElRef = useRef(null)
  const hoveredTargetRef = useRef(null)
  const dwellTargetRef = useRef(null)
  const dwellStartedAtRef = useRef(0)
  const dwellTriggeredRef = useRef(false)
  const pointHistoryRef = useRef([])
  const cameraPointRef = useRef(null)
  const lastHandSeenRef = useRef(0)
  const calibrationRef = useRef(readPointerCalibration())
  const settingsRef = useRef(readPointerSettings())
  const calibrationActiveRef = useRef(false)
  // Jeton de génération : incrémenté à chaque stop() pour invalider tout appel start() encore en
  // cours. Nécessaire en développement, où <React.StrictMode> démonte puis remonte immédiatement
  // le composant (monte → nettoie → remonte) : sans ce garde-fou, le deuxième start() réassigne
  // video.srcObject pendant que le premier attend encore video.play(), ce qui interrompt cette
  // promesse avec un AbortError ("The play() request was interrupted by a new load request.")
  // remonté à tort comme une vraie panne caméra. Avec le jeton, l'appel périmé se referme
  // silencieusement (coupe le flux qu'il a ouvert) au lieu de signaler une erreur.
  const startTokenRef = useRef(0)

  const [visible, setVisible] = useState(false)
  const [clicking, setClicking] = useState(false)
  const [settingsVersion, setSettingsVersion] = useState(0)

  const resetDwell = useCallback(() => {
    dwellTargetRef.current?.classList.remove('hand-pointer-dwell')
    dwellTargetRef.current = null
    dwellStartedAtRef.current = 0
    dwellTriggeredRef.current = false
  }, [])

  const stop = useCallback(() => {
    startTokenRef.current += 1
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    targetRef.current = null
    smoothedRef.current = null
    pointHistoryRef.current = []
    cameraPointRef.current = null
    lastHandSeenRef.current = 0
    pinchingRef.current = false
    hoveredTargetRef.current?.classList.remove('hand-pointer-hover')
    hoveredTargetRef.current = null
    resetDwell()
    setVisible(false)
    setClicking(false)
  }, [resetDwell])

  useEffect(() => {
    const startCalibration = () => {
      calibrationActiveRef.current = true
      hoveredTargetRef.current?.classList.remove('hand-pointer-hover')
      hoveredTargetRef.current = null
      resetDwell()
    }
    const stopCalibration = () => {
      calibrationActiveRef.current = false
    }
    const updateCalibration = (event) => {
      calibrationRef.current = event.detail
    }
    const updateSettings = (event) => {
      settingsRef.current = event.detail
      recognizerRef.current?.close()
      recognizerRef.current = null
      setSettingsVersion((version) => version + 1)
    }
    window.addEventListener(POINTER_CALIBRATION_START_EVENT, startCalibration)
    window.addEventListener(POINTER_CALIBRATION_STOP_EVENT, stopCalibration)
    window.addEventListener(POINTER_CALIBRATION_CHANGED_EVENT, updateCalibration)
    window.addEventListener(POINTER_SETTINGS_CHANGED_EVENT, updateSettings)
    return () => {
      window.removeEventListener(POINTER_CALIBRATION_START_EVENT, startCalibration)
      window.removeEventListener(POINTER_CALIBRATION_STOP_EVENT, stopCalibration)
      window.removeEventListener(POINTER_CALIBRATION_CHANGED_EVENT, updateCalibration)
      window.removeEventListener(POINTER_SETTINGS_CHANGED_EVENT, updateSettings)
    }
  }, [resetDwell])

  const triggerClick = useCallback((position) => {
    if (!position) return
    const target = hoveredTargetRef.current || document.elementFromPoint(position.x, position.y)
    // elementFromPoint peut renvoyer le curseur lui-même ou un enfant sans le savoir si jamais le
    // pointer-events:none ci-dessous était retiré par erreur — garde-fou simple, sans incidence
    // dans le cas normal.
    if (target && typeof target.click === 'function' && target !== cursorElRef.current) {
      target.click()
    }
  }, [])

  const start = useCallback(async () => {
    // Capturé au tout début : si stop() est appelé pendant qu'on attend (StrictMode qui nettoie
    // avant de remonter, ou désactivation rapide du mode pointeur), startTokenRef.current avance
    // et ce `token` devient périmé — isStale() le détecte après chaque attente ci-dessous.
    const token = ++startTokenRef.current
    const isStale = () => token !== startTokenRef.current
    let stream = null
    try {
      const settings = settingsRef.current
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: settings.cameraWidth, min: 640 },
          height: { ideal: settings.cameraHeight, min: 480 },
          frameRate: { ideal: 30, max: 30 },
          facingMode: 'user',
        },
      })
      if (isStale()) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      streamRef.current = stream
      if (!videoRef.current) {
        const video = document.createElement('video')
        video.muted = true
        video.playsInline = true
        videoRef.current = video
      }
      const video = videoRef.current
      video.srcObject = stream
      await video.play()
      if (isStale()) {
        stream.getTracks().forEach((track) => track.stop())
        if (streamRef.current === stream) streamRef.current = null
        return
      }

      if (!recognizerRef.current) {
        const visionCdnUrl = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/vision_bundle.mjs'
        const visionModule = await import(/* @vite-ignore */ visionCdnUrl)
        const filesetResolver = await visionModule.FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm',
        )
        // numHands: 2 (et pas 1) : elle peut avoir sa main droite dans le champ de la caméra sans
        // que ça gêne — on cherche explicitement la main gauche parmi celles détectées ci-dessous,
        // plutôt que de forcer une seule main et risquer de suivre la mauvaise.
        recognizerRef.current = await visionModule.GestureRecognizer.createFromOptions(filesetResolver, {
          baseOptions: {
            modelAssetPath:
              'https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task',
          },
          runningMode: 'VIDEO',
          numHands: 2,
          minHandDetectionConfidence: settings.detectionConfidence,
          minHandPresenceConfidence: settings.presenceConfidence,
          minTrackingConfidence: settings.trackingConfidence,
        })
        console.info('[ARIA] Paramètres du pointeur appliqués :', {
          resolution: `${settings.cameraWidth}x${settings.cameraHeight}`,
          detection: settings.detectionConfidence,
          presence: settings.presenceConfidence,
          tracking: settings.trackingConfidence,
          verticalOffsetCm: settings.verticalOffsetCm,
          clickFinger: settings.clickFinger,
          pinchThreshold: settings.pinchThreshold,
        })
      }
      if (isStale()) {
        stream.getTracks().forEach((track) => track.stop())
        if (streamRef.current === stream) streamRef.current = null
        return
      }

      let lastVideoTime = -1
      let framesSeen = 0
      let lastDiagLog = 0
      const loop = () => {
        // Périmé : un démarrage plus récent a pris le relais (ou le mode a été désactivé) — cette
        // boucle s'arrête d'elle-même au lieu de continuer à tourner en double avec la nouvelle.
        if (isStale()) return
        try {
          const currentVideo = videoRef.current
          const recognizer = recognizerRef.current
          if (currentVideo && recognizer && currentVideo.videoWidth && currentVideo.currentTime !== lastVideoTime) {
            lastVideoTime = currentVideo.currentTime
            framesSeen += 1
            const result = recognizer.recognizeForVideo(currentVideo, performance.now())
            const landmarks = pickHand(result)

            // Un log par seconde environ (pas à chaque frame) : utile pour diagnostiquer à distance
            // si jamais ça ne marche toujours pas — dit si la caméra tourne bien (framesSeen avance)
            // et combien de mains sont vues, sans étiquettes personnelles ni image, juste des
            // compteurs.
            const now = performance.now()
            if (now - lastDiagLog > 10000) {
              lastDiagLog = now
              console.debug('[ARIA] Pointeur main — diagnostic :', {
                framesSeen,
                videoSize: `${currentVideo.videoWidth}x${currentVideo.videoHeight}`,
                mainsDetectees: (result.handedness || []).length,
                etiquettes: (result.handedness || []).map((entries) => entries?.[0]?.categoryName),
                mainChoisie: landmarks ? 'oui' : 'non',
              })
            }

            if (landmarks) {
              lastHandSeenRef.current = now
              const tip = landmarks[8]
              const thumbTip = landmarks[4]
              const clickFingerTip = landmarks[CLICK_FINGER_TIPS[settings.clickFinger]]
              const palmWidth = Math.max(
                Math.hypot(landmarks[5].x - landmarks[17].x, landmarks[5].y - landmarks[17].y),
                0.01,
              )
              const pinchDistance =
                Math.hypot(thumbTip.x - clickFingerTip.x, thumbTip.y - clickFingerTip.y) / palmWidth
              const releaseThreshold = settings.pinchThreshold * 1.45
              const isPinching = pinchingRef.current
                ? pinchDistance < releaseThreshold
                : pinchDistance < settings.pinchThreshold
              if (!isPinching) {
                // Même correction miroir que le regard/les yeux ailleurs dans l'app (voir
                // VoiceAssistant.jsx) : bouger l'index vers sa propre droite déplace le curseur
                // vers la droite de l'écran, pas l'inverse.
                // Le mouvement vient uniquement du bout de l'index (landmark 8). L'ancienne
                // projection depuis l'articulation 6 faisait aussi réagir le curseur à
                // l'orientation de la main et donnait l'impression qu'il suivait la paume.
                const trackedTip = stabilizedPoint(pointHistoryRef.current, {
                  x: Math.max(0, Math.min(1, tip.x)),
                  y: Math.max(0, Math.min(1, tip.y)),
                })
                const cameraPoint = { x: 1 - trackedTip.x, y: trackedTip.y }
                cameraPointRef.current = cameraPoint
                const screenPoint =
                  applyPointerCalibration(cameraPoint, calibrationRef.current) ??
                  mapCameraPointToScreen(cameraPoint)
                const verticalOffset = (settings.verticalOffsetCm * 96) / 2.54
                const absolutePosition = {
                  x: screenPoint.x * window.innerWidth,
                  y: Math.max(
                    0,
                    Math.min(
                      window.innerHeight,
                      screenPoint.y * (window.innerHeight + verticalOffset) - verticalOffset,
                    ),
                  ),
                }
                const magnetic = calibrationActiveRef.current
                  ? { position: absolutePosition, element: null }
                  : magneticTarget(absolutePosition)
                if (hoveredTargetRef.current !== magnetic.element) {
                  hoveredTargetRef.current?.classList.remove('hand-pointer-hover')
                  magnetic.element?.classList.add('hand-pointer-hover')
                  hoveredTargetRef.current = magnetic.element
                }
                if (dwellTargetRef.current !== magnetic.element) {
                  resetDwell()
                  if (magnetic.element) {
                    dwellTargetRef.current = magnetic.element
                    dwellStartedAtRef.current = now
                    magnetic.element.classList.add('hand-pointer-dwell')
                  }
                } else if (
                  magnetic.element &&
                  !dwellTriggeredRef.current &&
                  now - dwellStartedAtRef.current >= DWELL_CLICK_DELAY_MS
                ) {
                  dwellTriggeredRef.current = true
                  magnetic.element.classList.remove('hand-pointer-dwell')
                  triggerClick(magnetic.position)
                }
                targetRef.current = magnetic.position
              }
              if (isPinching && !pinchingRef.current) {
                if (calibrationActiveRef.current && cameraPointRef.current) {
                  window.dispatchEvent(
                    new CustomEvent(POINTER_CALIBRATION_POINT_EVENT, {
                      detail: { ...cameraPointRef.current },
                    }),
                  )
                } else {
                  triggerClick(targetRef.current)
                  dwellTriggeredRef.current = true
                  dwellTargetRef.current?.classList.remove('hand-pointer-dwell')
                }
                setClicking(true)
              } else if (!isPinching && pinchingRef.current) {
                setClicking(false)
              }
              pinchingRef.current = isPinching
              setVisible(true)
            } else {
              pointHistoryRef.current = []
              resetDwell()
              setClicking(false)
              pinchingRef.current = false
              if (now - lastHandSeenRef.current > HAND_LOSS_GRACE_MS) {
                hoveredTargetRef.current?.classList.remove('hand-pointer-hover')
                hoveredTargetRef.current = null
                setVisible(false)
              }
            }
          }
        } catch (frameErr) {
          console.error('[ARIA] Erreur de détection du pointeur main sur une frame (suivi continue) :', frameErr)
        }
        rafRef.current = requestAnimationFrame(loop)
      }
      loop()
    } catch (err) {
      if (isStale()) {
        // Démarrage périmé (typiquement le double-rendu de <React.StrictMode> en développement,
        // qui démonte puis remonte le composant aussitôt) : l'erreur — souvent un AbortError parce
        // que video.play() a été interrompu par la réassignation de srcObject du démarrage
        // suivant — ne concerne plus l'appel actif. On referme juste ce qu'on a ouvert, sans rien
        // signaler à Sarah : le démarrage suivant prend le relais normalement.
        if (stream) stream.getTracks().forEach((track) => track.stop())
        if (streamRef.current === stream) streamRef.current = null
        return
      }
      console.error('[ARIA] Échec du démarrage du pointeur main :', err)
      onError?.(err)
      stop()
    }
  }, [onError, resetDwell, stop, triggerClick])

  useEffect(() => {
    if (enabled) {
      start()
    } else {
      stop()
    }
    return stop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, settingsVersion])

  useEffect(() => {
    document.documentElement.classList.toggle('hand-pointer-active', enabled && visible)
    return () => document.documentElement.classList.remove('hand-pointer-active')
  }, [enabled, visible])

  // Boucle d'affichage séparée de la boucle de détection ci-dessus : anime le curseur vers
  // targetRef à chaque frame d'écran (lissage), indépendamment du rythme des détections MediaPipe.
  useEffect(() => {
    if (!enabled) return undefined
    let previousTimestamp = performance.now()
    const render = (timestamp) => {
      if (targetRef.current && cursorElRef.current) {
        if (!smoothedRef.current) smoothedRef.current = { ...targetRef.current }
        const dx = targetRef.current.x - smoothedRef.current.x
        const dy = targetRef.current.y - smoothedRef.current.y
        const distance = Math.hypot(dx, dy)
        const smoothing = distance > 120 ? 0.42 : distance > 40 ? 0.36 : distance > 8 ? 0.3 : 1
        const elapsedSeconds = Math.min((timestamp - previousTimestamp) / 1000, 0.033)
        const horizontalStep = MAX_HORIZONTAL_CURSOR_SPEED * elapsedSeconds
        const verticalStep = MAX_VERTICAL_CURSOR_SPEED * elapsedSeconds
        const verticalSmoothing = distance > 8 ? smoothing * 0.2 : 1
        smoothedRef.current.x += Math.sign(dx) * Math.min(Math.abs(dx) * smoothing, horizontalStep)
        smoothedRef.current.y += Math.sign(dy) * Math.min(Math.abs(dy) * verticalSmoothing, verticalStep)
        cursorElRef.current.style.transform =
          `translate(${smoothedRef.current.x - CURSOR_SIZE / 2}px, ${smoothedRef.current.y - CURSOR_SIZE / 2}px)`
      }
      previousTimestamp = timestamp
      renderRafRef.current = requestAnimationFrame(render)
    }
    renderRafRef.current = requestAnimationFrame(render)
    return () => cancelAnimationFrame(renderRafRef.current)
  }, [enabled])

  if (!enabled) return null

  return (
    <>
      <div
        ref={cursorElRef}
        hidden={!visible}
        aria-hidden="true"
        className={`pointer-events-none fixed left-0 top-0 z-[9999] rounded-full border-2 shadow-lg transition-colors duration-100 ${
          clicking ? 'border-emerald-400 bg-emerald-400/40' : 'border-blue-400 bg-blue-400/25'
        }`}
        style={{ width: CURSOR_SIZE, height: CURSOR_SIZE }}
      />
      {/* Indication tant qu'aucune main n'est vue : distingue "caméra active mais rien détecté"
          (ce badge reste affiché) de "ça marche" (il disparaît dès qu'une main est trouvée, le
          curseur devient alors le seul retour visuel). Disparaît aussi en cas d'erreur caméra
          (voir onError dans App.jsx, qui désactive le mode et affiche son propre message). */}
      {!visible && (
        <p className="pointer-events-none fixed left-1/2 top-16 z-[9999] -translate-x-1/2 rounded-full bg-gray-900/90 px-3 py-1 text-xs text-gray-300 shadow">
          Pointeur actif — recherche de votre main…
        </p>
      )}
    </>
  )
}
