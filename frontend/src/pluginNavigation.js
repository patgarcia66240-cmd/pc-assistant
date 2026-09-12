export const PLUGIN_NAVIGATE_EVENT = 'aria-plugin-navigate'

export function navigateToPlugin(pluginId) {
  window.dispatchEvent(new CustomEvent(PLUGIN_NAVIGATE_EVENT, { detail: { pluginId } }))
}
