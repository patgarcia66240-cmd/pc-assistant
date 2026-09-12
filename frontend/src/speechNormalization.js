export function normalizeSpeechUnits(text) {
  return text
    .replace(/\s*°\s*C\b/gi, ' degrés Celsius')
    .replace(/\bkm\s*\/\s*h\b/gi, 'kilomètres par heure')
}
