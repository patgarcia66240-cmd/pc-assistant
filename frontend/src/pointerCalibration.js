export const POINTER_CALIBRATION_START_EVENT = 'aria-pointer-calibration-start'
export const POINTER_CALIBRATION_STOP_EVENT = 'aria-pointer-calibration-stop'
export const POINTER_CALIBRATION_POINT_EVENT = 'aria-pointer-calibration-point'
export const POINTER_CALIBRATION_CHANGED_EVENT = 'aria-pointer-calibration-changed'
export const POINTER_MODE_EVENT = 'aria-pointer-mode-changed'
export const POINTER_MODE_REQUEST_EVENT = 'aria-pointer-mode-request'
export const POINTER_SETTINGS_CHANGED_EVENT = 'aria-pointer-settings-changed'

const STORAGE_KEY = 'aria-pointer-calibration'
const SETTINGS_STORAGE_KEY = 'aria-pointer-settings'

export const DEFAULT_POINTER_SETTINGS = Object.freeze({
  cameraWidth: 1280,
  cameraHeight: 720,
  detectionConfidence: 0.35,
  presenceConfidence: 0.35,
  trackingConfidence: 0.35,
  verticalOffsetCm: 10,
  clickFinger: 'index',
  pinchThreshold: 0.4,
})

function boundedConfidence(value, fallback) {
  const number = Number(value)
  return Number.isFinite(number) ? Math.max(0.1, Math.min(0.9, number)) : fallback
}

export function readPointerSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY))
    const supportedResolution =
      (saved?.cameraWidth === 640 && saved?.cameraHeight === 480) ||
      (saved?.cameraWidth === 1280 && saved?.cameraHeight === 720) ||
      (saved?.cameraWidth === 1920 && saved?.cameraHeight === 1080)
    return {
      cameraWidth: supportedResolution ? saved.cameraWidth : DEFAULT_POINTER_SETTINGS.cameraWidth,
      cameraHeight: supportedResolution ? saved.cameraHeight : DEFAULT_POINTER_SETTINGS.cameraHeight,
      detectionConfidence: boundedConfidence(
        saved?.detectionConfidence,
        DEFAULT_POINTER_SETTINGS.detectionConfidence,
      ),
      presenceConfidence: boundedConfidence(
        saved?.presenceConfidence,
        DEFAULT_POINTER_SETTINGS.presenceConfidence,
      ),
      trackingConfidence: boundedConfidence(
        saved?.trackingConfidence,
        DEFAULT_POINTER_SETTINGS.trackingConfidence,
      ),
      verticalOffsetCm: Number.isFinite(Number(saved?.verticalOffsetCm))
        ? Math.max(0, Math.min(15, Number(saved.verticalOffsetCm)))
        : DEFAULT_POINTER_SETTINGS.verticalOffsetCm,
      clickFinger: ['index', 'middle', 'ring', 'pinky'].includes(saved?.clickFinger)
        ? saved.clickFinger
        : DEFAULT_POINTER_SETTINGS.clickFinger,
      pinchThreshold: Number.isFinite(Number(saved?.pinchThreshold))
        ? Math.max(0.2, Math.min(0.8, Number(saved.pinchThreshold)))
        : DEFAULT_POINTER_SETTINGS.pinchThreshold,
    }
  } catch {
    return { ...DEFAULT_POINTER_SETTINGS }
  }
}

export function writePointerSettings(settings) {
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
  window.dispatchEvent(new CustomEvent(POINTER_SETTINGS_CHANGED_EVENT, { detail: settings }))
}

export function readPointerCalibration() {
  try {
    const calibration = JSON.parse(localStorage.getItem(STORAGE_KEY))
    const values = [
      calibration?.sourceLeft,
      calibration?.sourceRight,
      calibration?.sourceTop,
      calibration?.sourceBottom,
      calibration?.targetLeft,
      calibration?.targetRight,
      calibration?.targetTop,
      calibration?.targetBottom,
    ]
    if (
      calibration?.version !== 1 ||
      values.some((value) => !Number.isFinite(value)) ||
      Math.abs(calibration.sourceRight - calibration.sourceLeft) < 0.05 ||
      Math.abs(calibration.sourceBottom - calibration.sourceTop) < 0.05
    ) {
      return null
    }
    return calibration
  } catch {
    return null
  }
}

export function writePointerCalibration(calibration) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(calibration))
  window.dispatchEvent(new CustomEvent(POINTER_CALIBRATION_CHANGED_EVENT, { detail: calibration }))
}

export function clearPointerCalibration() {
  localStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new CustomEvent(POINTER_CALIBRATION_CHANGED_EVENT, { detail: null }))
}

export function applyPointerCalibration(point, calibration) {
  if (!calibration) return null
  const xRatio = (point.x - calibration.sourceLeft) / (calibration.sourceRight - calibration.sourceLeft)
  const yRatio = (point.y - calibration.sourceTop) / (calibration.sourceBottom - calibration.sourceTop)
  return {
    x: Math.max(0, Math.min(1, calibration.targetLeft + xRatio * (calibration.targetRight - calibration.targetLeft))),
    y: Math.max(0, Math.min(1, calibration.targetTop + yRatio * (calibration.targetBottom - calibration.targetTop))),
  }
}
