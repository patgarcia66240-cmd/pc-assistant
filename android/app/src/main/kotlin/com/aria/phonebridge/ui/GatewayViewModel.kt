package com.aria.phonebridge.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.aria.phonebridge.gateway.GatewayForegroundService
import com.aria.phonebridge.gateway.GatewayServer
import com.aria.phonebridge.gateway.LocalNetworkInfo
import com.aria.phonebridge.gateway.PairingManager
import com.aria.phonebridge.gateway.capabilities.CapabilityRegistry
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.content
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

data class CapabilityUiState(
    val id: String,
    val label: String,
    val granted: Boolean,
    val permissions: List<String>,
)

data class GatewayUiState(
    val running: Boolean = false,
    val ipAddress: String? = null,
    val port: Int = PairingManager.DEFAULT_PORT,
    val token: String = "",
    val connectedClients: Int = 0,
    val capabilities: List<CapabilityUiState> = emptyList(),
)

class GatewayViewModel(application: Application) : AndroidViewModel(application) {
    private val pairingManager = PairingManager(application)
    private val _state = MutableStateFlow(GatewayUiState())
    val state = _state.asStateFlow()

    init {
        refreshStaticInfo()
        GatewayServer.connectedClients
            .onEach { count -> _state.value = _state.value.copy(connectedClients = count) }
            .launchIn(viewModelScope)
        // Le statut "accordée/refusée" d'une permission peut changer pendant que l'écran est
        // ouvert (retour depuis les paramètres système) : revérifié à intervalle régulier plutôt
        // qu'une seule fois au lancement.
        viewModelScope.launch {
            while (true) {
                refreshCapabilities()
                delay(2_000)
            }
        }
    }

    fun toggleServer() {
        val application = getApplication<Application>()
        val startingUp = !_state.value.running
        if (startingUp) {
            GatewayForegroundService.start(application, _state.value.port)
        } else {
            GatewayForegroundService.stop(application)
        }
        // État optimiste : GatewayServer.isRunning ne devient vrai/faux qu'une fois le service
        // (démarré de façon asynchrone par le système) arrivé à onStartCommand/onDestroy, donc
        // le relire tout de suite via refreshStaticInfo() ferait clignoter l'UI en arrière.
        _state.value = _state.value.copy(running = startingUp, ipAddress = LocalNetworkInfo.currentIpAddress(application))
    }

    fun regenerateToken() {
        _state.value = _state.value.copy(token = pairingManager.regenerateToken())
    }

    fun onPermissionResult() {
        refreshCapabilities()
    }

    private fun refreshStaticInfo() {
        val application = getApplication<Application>()
        _state.value = _state.value.copy(
            running = GatewayServer.isRunning,
            ipAddress = LocalNetworkInfo.currentIpAddress(application),
            port = pairingManager.port,
            token = pairingManager.currentToken(),
        )
        refreshCapabilities()
    }

    private fun refreshCapabilities() {
        val application = getApplication<Application>()
        val capabilities = CapabilityRegistry.listCapabilities(application) as JsonArray
        _state.value = _state.value.copy(
            capabilities = capabilities.map {
                val obj: JsonObject = it.jsonObject
                CapabilityUiState(
                    id = obj["id"]!!.jsonPrimitive.content,
                    label = obj["label"]!!.jsonPrimitive.content,
                    granted = obj["granted"]!!.jsonPrimitive.boolean,
                    permissions = obj["permissions"]!!.jsonArray.map { it.jsonPrimitive.content },
                )
            },
        )
    }
}
