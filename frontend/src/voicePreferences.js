export const VOICE_SETTINGS_EVENT = 'aria-voice-settings-changed'

const NATURAL_VOICE_PATTERN = /natural|neural|enhanced|premium|online/i
const FRENCH_FEMALE_VOICE_PATTERN = /female|femme|amélie|audrey|céline|denise|éloïse|hortense|julie|léa|marie|vivienne/i

export function getFrenchVoices(voices) {
  return voices
    .filter((voice) => voice.lang?.toLowerCase().startsWith('fr'))
    .sort((a, b) => {
      const score = (voice) =>
        (NATURAL_VOICE_PATTERN.test(voice.name) ? 100 : 0) +
        (voice.lang?.toLowerCase() === 'fr-fr' ? 20 : 0) +
        (FRENCH_FEMALE_VOICE_PATTERN.test(voice.name) ? 10 : 0)
      return score(b) - score(a) || a.name.localeCompare(b.name, 'fr')
    })
}

export function pickFrenchVoice(voices, preferredVoiceURI) {
  return voices.find((voice) => voice.voiceURI === preferredVoiceURI) || voices[0] || null
}

export function readVoicePreferences() {
  try {
    const storedRate = Number(localStorage.getItem('aria-voice-rate'))
    const storedEngine = localStorage.getItem('aria-tts-engine')
    return {
      engine: ['kokoro', 'piper', 'browser'].includes(storedEngine) ? storedEngine : 'kokoro',
      voiceURI: localStorage.getItem('aria-voice-uri') || '',
      rate: storedRate >= 0.75 && storedRate <= 1.1 ? storedRate : 0.92,
      streaming: localStorage.getItem('aria-tts-streaming') !== '0',
    }
  } catch {
    return { engine: 'kokoro', voiceURI: '', rate: 0.92, streaming: true }
  }
}

export function writeVoicePreferences(preferences) {
  try {
    localStorage.setItem('aria-tts-engine', preferences.engine)
    localStorage.setItem('aria-voice-uri', preferences.voiceURI)
    localStorage.setItem('aria-voice-rate', String(preferences.rate))
    localStorage.setItem('aria-tts-streaming', preferences.streaming ? '1' : '0')
  } catch {
    // Les préférences restent utilisables pour la session via l'événement ci-dessous.
  }
  window.dispatchEvent(new CustomEvent(VOICE_SETTINGS_EVENT, { detail: preferences }))
}
