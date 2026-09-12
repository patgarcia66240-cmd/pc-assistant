export const PLUGIN_NAVIGATE_EVENT = 'aria-plugin-navigate'

let pendingNavigationPayload = null

export function navigateToPlugin(pluginId, payload = null) {
  if (payload) {
    pendingNavigationPayload = { pluginId, ...payload }
  }
  window.dispatchEvent(
    new CustomEvent(PLUGIN_NAVIGATE_EVENT, { detail: { pluginId, payload } })
  )
}

export function getPendingNavigationPayload(pluginId) {
  if (pendingNavigationPayload && pendingNavigationPayload.pluginId === pluginId) {
    const payload = pendingNavigationPayload
    pendingNavigationPayload = null
    return payload
  }
  return null
}

