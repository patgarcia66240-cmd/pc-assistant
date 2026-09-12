import { useEffect, useState } from 'react'
import {
  POINTER_CALIBRATION_POINT_EVENT,
  POINTER_CALIBRATION_START_EVENT,
  POINTER_CALIBRATION_STOP_EVENT,
  POINTER_MODE_EVENT,
  POINTER_MODE_REQUEST_EVENT,
  DEFAULT_POINTER_SETTINGS,
  clearPointerCalibration,
  readPointerCalibration,
  readPointerSettings,
  writePointerCalibration,
  writePointerSettings,
} from '../pointerCalibration'

const TARGETS = [
  { label: 'coin supérieur gauche', x: 0.1, y: 0.14 },
  { label: 'coin supérieur droit', x: 0.9, y: 0.14 },
  { label: 'coin inférieur droit', x: 0.9, y: 0.9 },
  { label: 'coin inférieur gauche', x: 0.1, y: 0.9 },
]

function buildCalibration(samples) {
  return {
    version: 1,
    sourceLeft: (samples[0].x + samples[3].x) / 2,
    sourceRight: (samples[1].x + samples[2].x) / 2,
    sourceTop: (samples[0].y + samples[1].y) / 2,
    sourceBottom: (samples[2].y + samples[3].y) / 2,
    targetLeft: TARGETS[0].x,
    targetRight: TARGETS[1].x,
    targetTop: TARGETS[0].y,
    targetBottom: TARGETS[2].y,
  }
}

export default function PointerCalibration({ isActive = true }) {
  const [calibration, setCalibration] = useState(readPointerCalibration)
  const [pointerEnabled, setPointerEnabled] = useState(
    () => localStorage.getItem('aria-pointer-mode') === '1',
  )
  const [calibrating, setCalibrating] = useState(false)
  const [samples, setSamples] = useState([])
  const [pointerSettings, setPointerSettings] = useState(readPointerSettings)
  const [settingsApplied, setSettingsApplied] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const updatePointerMode = (event) => setPointerEnabled(Boolean(event.detail?.enabled))
    window.addEventListener(POINTER_MODE_EVENT, updatePointerMode)
    return () => window.removeEventListener(POINTER_MODE_EVENT, updatePointerMode)
  }, [])

  useEffect(() => {
    const capturePoint = (event) => {
      const point = event.detail
      if (!point || !calibrating || samples.length >= TARGETS.length) return
      const nextSamples = [...samples, point]
      if (nextSamples.length === TARGETS.length) {
        const nextCalibration = buildCalibration(nextSamples)
        if (
          Math.abs(nextCalibration.sourceRight - nextCalibration.sourceLeft) < 0.05 ||
          Math.abs(nextCalibration.sourceBottom - nextCalibration.sourceTop) < 0.05
        ) {
          setError('Zone de calibrage trop petite. Recommencez en visant précisément les quatre points.')
          setSamples([])
          setCalibrating(false)
          window.dispatchEvent(new Event(POINTER_CALIBRATION_STOP_EVENT))
          return
        }
        writePointerCalibration(nextCalibration)
        setCalibration(nextCalibration)
        setSamples([])
        setCalibrating(false)
        setError('')
        window.dispatchEvent(new Event(POINTER_CALIBRATION_STOP_EVENT))
        return
      }
      setSamples(nextSamples)
    }
    window.addEventListener(POINTER_CALIBRATION_POINT_EVENT, capturePoint)
    return () => window.removeEventListener(POINTER_CALIBRATION_POINT_EVENT, capturePoint)
  }, [calibrating, samples])

  function startCalibration() {
    if (!pointerEnabled) {
      setError("Activez d'abord le bouton Pointeur dans l'en-tête.")
      return
    }
    setError('')
    setSamples([])
    setCalibrating(true)
    window.dispatchEvent(new Event(POINTER_CALIBRATION_START_EVENT))
  }

  function cancelCalibration() {
    setSamples([])
    setCalibrating(false)
    window.dispatchEvent(new Event(POINTER_CALIBRATION_STOP_EVENT))
  }

  function resetCalibration() {
    clearPointerCalibration()
    setCalibration(null)
    setError('')
  }

  function updateSetting(name, value) {
    setSettingsApplied(false)
    setPointerSettings((current) => ({ ...current, [name]: Number(value) }))
  }

  function applySettings() {
    writePointerSettings(pointerSettings)
    if (!pointerEnabled) {
      window.dispatchEvent(new CustomEvent(POINTER_MODE_REQUEST_EVENT, { detail: { enabled: true } }))
    }
    setSettingsApplied(true)
    setError('')
  }

  function resetSettings() {
    const defaults = { ...DEFAULT_POINTER_SETTINGS }
    setPointerSettings(defaults)
    writePointerSettings(defaults)
    if (!pointerEnabled) {
      window.dispatchEvent(new CustomEvent(POINTER_MODE_REQUEST_EVENT, { detail: { enabled: true } }))
    }
    setSettingsApplied(true)
  }

  const targetIndex = calibrating ? samples.length : -1
  const target = targetIndex >= 0 ? TARGETS[targetIndex] : null

  useEffect(() => {
    if (calibrating && (!isActive || !pointerEnabled)) {
      setSamples([])
      setCalibrating(false)
      window.dispatchEvent(new Event(POINTER_CALIBRATION_STOP_EVENT))
    }
  }, [calibrating, isActive, pointerEnabled])

  useEffect(
    () => () => window.dispatchEvent(new Event(POINTER_CALIBRATION_STOP_EVENT)),
    [],
  )

  return (
    <section className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl rounded-2xl border border-gray-700 bg-gray-800/80 p-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-blue-400">Pointeur main</p>
        <h2 className="mt-1 text-2xl font-semibold text-white">Calibration en quatre points</h2>
        <p className="mt-3 text-sm leading-6 text-gray-300">
          Activez le pointeur, lancez la calibration, puis visez chaque cible avec l&apos;index.
          Faites le geste de pincement choisi pour enregistrer le point et passer au suivant.
        </p>

        <div className="mt-5 rounded-xl border border-gray-700 bg-gray-900/60 p-4 text-sm">
          <p className={pointerEnabled ? 'text-emerald-300' : 'text-amber-300'}>
            Pointeur : {pointerEnabled ? 'activé' : 'désactivé'}
          </p>
          <p className={calibration ? 'mt-1 text-emerald-300' : 'mt-1 text-gray-400'}>
            Calibration : {calibration ? 'enregistrée' : 'non effectuée'}
          </p>
        </div>

        {error && <p className="mt-4 rounded-lg border border-red-800/70 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}

        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={startCalibration}
            disabled={calibrating}
            className="min-h-[42px] rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
          >
            {calibrating ? `Point ${targetIndex + 1} sur ${TARGETS.length}` : 'Démarrer la calibration'}
          </button>
          {calibrating && (
            <button type="button" onClick={cancelCalibration} className="min-h-[42px] rounded-lg border border-gray-600 px-4 text-sm text-gray-300 hover:bg-gray-700">
              Annuler
            </button>
          )}
          {calibration && !calibrating && (
            <button type="button" onClick={resetCalibration} className="min-h-[42px] rounded-lg border border-gray-600 px-4 text-sm text-gray-300 hover:bg-gray-700">
              Réinitialiser
            </button>
          )}
        </div>
      </div>

      <div className="mx-auto mt-5 max-w-3xl rounded-2xl border border-gray-700 bg-gray-800/80 p-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-cyan-400">Essais caméra</p>
        <h3 className="mt-1 text-xl font-semibold text-white">Qualité de détection</h3>
        <p className="mt-2 text-sm text-gray-400">
          Des seuils plus bas détectent plus facilement une main proche ou partiellement visible,
          mais peuvent rendre le pointeur moins stable.
        </p>

        <label className="mt-5 block text-sm text-gray-300">
          Résolution
          <select
            value={`${pointerSettings.cameraWidth}x${pointerSettings.cameraHeight}`}
            onChange={(event) => {
              const [cameraWidth, cameraHeight] = event.target.value.split('x').map(Number)
              setSettingsApplied(false)
              setPointerSettings((current) => ({ ...current, cameraWidth, cameraHeight }))
            }}
            className="mt-1 block w-full rounded-lg border border-gray-600 bg-gray-900 px-3 py-2 text-white"
          >
            <option value="640x480">640 × 480 — rapide</option>
            <option value="1280x720">1280 × 720 — recommandé</option>
            <option value="1920x1080">1920 × 1080 — haute précision</option>
          </select>
        </label>

        {[
          ['detectionConfidence', 'Détection de la main'],
          ['presenceConfidence', 'Présence de la main'],
          ['trackingConfidence', 'Suivi des mouvements'],
        ].map(([name, label]) => (
          <label key={name} className="mt-4 block text-sm text-gray-300">
            <span className="flex justify-between">
              <span>{label}</span>
              <span className="font-mono text-cyan-300">{pointerSettings[name].toFixed(2)}</span>
            </span>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={pointerSettings[name]}
              onChange={(event) => updateSetting(name, event.target.value)}
              className="mt-2 w-full accent-cyan-500"
            />
          </label>
        ))}

        <label className="mt-4 block text-sm text-gray-300">
          <span className="flex justify-between">
            <span>Hauteur du pointeur au-dessus du doigt</span>
            <span className="font-mono text-cyan-300">{pointerSettings.verticalOffsetCm.toFixed(1)} cm</span>
          </span>
          <input
            type="range"
            min="0"
            max="15"
            step="0.5"
            value={pointerSettings.verticalOffsetCm}
            onChange={(event) => updateSetting('verticalOffsetCm', event.target.value)}
            className="mt-2 w-full accent-cyan-500"
          />
        </label>

        <label className="mt-4 block text-sm text-gray-300">
          Doigt à rapprocher du pouce pour valider
          <select
            value={pointerSettings.clickFinger}
            onChange={(event) => {
              setSettingsApplied(false)
              setPointerSettings((current) => ({ ...current, clickFinger: event.target.value }))
            }}
            className="mt-1 block w-full rounded-lg border border-gray-600 bg-gray-900 px-3 py-2 text-white"
          >
            <option value="index">Index — recommandé</option>
            <option value="middle">Majeur</option>
            <option value="ring">Annulaire</option>
            <option value="pinky">Auriculaire</option>
          </select>
        </label>

        <label className="mt-4 block text-sm text-gray-300">
          <span className="flex justify-between">
            <span>Sensibilité du pincement</span>
            <span className="font-mono text-cyan-300">{pointerSettings.pinchThreshold.toFixed(2)}</span>
          </span>
          <input
            type="range"
            min="0.2"
            max="0.8"
            step="0.05"
            value={pointerSettings.pinchThreshold}
            onChange={(event) => updateSetting('pinchThreshold', event.target.value)}
            className="mt-2 w-full accent-cyan-500"
          />
          <span className="mt-1 block text-xs text-gray-500">
            Une valeur élevée déclenche le clic avec les doigts moins rapprochés.
          </span>
        </label>

        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={applySettings}
            data-hand-pointer-ignore
            className="min-h-[42px] rounded-lg bg-cyan-600 px-4 text-sm font-semibold text-white hover:bg-cyan-500"
          >
            Appliquer et redémarrer la caméra
          </button>
          <button
            type="button"
            onClick={resetSettings}
            data-hand-pointer-ignore
            className="min-h-[42px] rounded-lg border border-gray-600 px-4 text-sm text-gray-300 hover:bg-gray-700"
          >
            Valeurs recommandées
          </button>
        </div>
        {settingsApplied && (
          <p className="mt-3 text-sm text-emerald-300">
            Paramètres appliqués. La caméra du pointeur a été redémarrée.
          </p>
        )}
      </div>

      {target && (
        <div className="pointer-events-none fixed inset-0 z-[10000] bg-gray-950/35">
          <div
            className="absolute h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-cyan-300 bg-blue-500/30 shadow-[0_0_30px_rgba(34,211,238,0.8)]"
            style={{ left: `${target.x * 100}%`, top: `${target.y * 100}%` }}
          >
            <span className="absolute inset-2 rounded-full border-2 border-white" />
          </div>
          <p className="absolute left-1/2 top-1/2 -translate-x-1/2 rounded-xl bg-gray-950/90 px-5 py-3 text-center text-sm text-white shadow-xl">
            Visez le {target.label}, puis faites le geste de pincement
          </p>
        </div>
      )}
    </section>
  )
}
