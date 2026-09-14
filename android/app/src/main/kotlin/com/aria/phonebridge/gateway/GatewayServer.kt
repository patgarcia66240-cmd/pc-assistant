package com.aria.phonebridge.gateway

import android.content.Context
import android.util.Log
import com.aria.phonebridge.gateway.capabilities.CapabilityRegistry
import com.aria.phonebridge.gateway.capabilities.DeviceInfoCapability
import io.ktor.server.application.Application
import io.ktor.server.application.install
import io.ktor.server.cio.CIO
import io.ktor.server.engine.ApplicationEngine
import io.ktor.server.engine.embeddedServer
import io.ktor.server.routing.routing
import io.ktor.server.websocket.DefaultWebSocketServerSession
import io.ktor.server.websocket.WebSockets
import io.ktor.server.websocket.webSocket
import io.ktor.websocket.CloseReason
import io.ktor.websocket.Frame
import io.ktor.websocket.close
import io.ktor.websocket.readText
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withTimeout
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import java.time.Duration

private const val TAG = "AriaGatewayServer"
private const val AUTH_TIMEOUT_MS = 8_000L

/**
 * Le cœur de la passerelle : un serveur WebSocket (Ktor/CIO) qui écoute sur le réseau local et
 * répond aux requêtes du plugin android_bridge côté ARIA (backend/plugins/android_bridge/
 * client.py). Un seul objet pour toute l'app — démarré/arrêté par GatewayForegroundService,
 * dont le cycle de vie garde le socket ouvert même quand l'app n'est pas au premier plan.
 *
 * Protocole détaillé dans client.py (côté PC) : auth par jeton puis requêtes
 * {"type":"request","id":...,"action":"get_<capability id>"} routées vers CapabilityRegistry.
 */
object GatewayServer {
    private var engine: ApplicationEngine? = null
    private lateinit var pairingManager: PairingManager

    private val _connectedClients = MutableStateFlow(0)
    val connectedClients = _connectedClients.asStateFlow()

    val isRunning: Boolean
        get() = engine != null

    fun start(context: Context, port: Int) {
        if (isRunning) return
        pairingManager = PairingManager(context)
        val appContext = context.applicationContext

        engine = embeddedServer(CIO, port = port, host = "0.0.0.0") {
            module(appContext)
        }.also { it.start(wait = false) }
        Log.i(TAG, "Passerelle démarrée sur le port $port")
    }

    fun stop() {
        engine?.stop(gracePeriodMillis = 200, timeoutMillis = 1_000)
        engine = null
        _connectedClients.value = 0
        Log.i(TAG, "Passerelle arrêtée")
    }

    private fun Application.module(context: Context) {
        install(WebSockets) {
            pingPeriod = Duration.ofSeconds(20)
            timeout = Duration.ofSeconds(30)
        }

        routing {
            webSocket("/ws") {
                _connectedClients.value += 1
                try {
                    if (!authenticate(this, context)) return@webSocket
                    for (frame in incoming) {
                        if (frame !is Frame.Text) continue
                        handleRequestFrame(this, frame.readText(), context)
                    }
                } catch (error: Exception) {
                    Log.w(TAG, "Session WebSocket interrompue : ${error.message}")
                } finally {
                    _connectedClients.value = (_connectedClients.value - 1).coerceAtLeast(0)
                }
            }
        }
    }

    /** Le PREMIER message d'une connexion doit être {"type":"auth","token":...}, reçu sous
     * AUTH_TIMEOUT_MS sans quoi la connexion est fermée — évite qu'un client laisse une socket
     * ouverte indéfiniment sans jamais s'authentifier. */
    private suspend fun authenticate(session: DefaultWebSocketServerSession, context: Context): Boolean {
        val frame = try {
            withTimeout(AUTH_TIMEOUT_MS) { session.incoming.receive() }
        } catch (timeout: TimeoutCancellationException) {
            session.close(CloseReason(CloseReason.Codes.VIOLATED_POLICY, "auth timeout"))
            return false
        }

        val json = (frame as? Frame.Text)?.readText()
            ?.let { runCatching { Json.parseToJsonElement(it).jsonObject }.getOrNull() }
        val token = json?.get("token")?.jsonPrimitive?.contentOrNull
        val ok = json?.get("type")?.jsonPrimitive?.contentOrNull == "auth" &&
            token != null && pairingManager.verifyToken(token)

        val response = buildJsonObject {
            put("type", "auth_result")
            put("ok", ok)
            if (ok) put("device", DeviceInfoCapability.snapshot(context))
            else put("error", JsonPrimitive("Jeton d'appairage incorrect."))
        }
        session.send(Frame.Text(Json.encodeToString(JsonElement.serializer(), response)))

        if (!ok) session.close(CloseReason(CloseReason.Codes.VIOLATED_POLICY, "bad token"))
        return ok
    }

    private suspend fun handleRequestFrame(session: DefaultWebSocketServerSession, text: String, context: Context) {
        val json = runCatching { Json.parseToJsonElement(text).jsonObject }.getOrNull() ?: return
        if (json["type"]?.jsonPrimitive?.contentOrNull != "request") return
        val requestId = json["id"]?.jsonPrimitive?.contentOrNull ?: return
        val action = json["action"]?.jsonPrimitive?.contentOrNull ?: return

        // Résolu AVANT buildJsonObject { ... } : son lambda n'est pas suspend, il ne peut donc
        // pas appeler directement capability.fetch() (qui l'est, pour les capacités qui lisent
        // un ContentProvider sur Dispatchers.IO — voir ContactsCapability).
        var data: JsonElement? = null
        var error: String? = null

        if (action == "get_capabilities") {
            data = CapabilityRegistry.listCapabilities(context)
        } else {
            val capability = CapabilityRegistry.find(action)
            when {
                capability == null -> error = "Action inconnue : $action"
                !capability.hasPermission(context) ->
                    error = "Permission requise non accordée sur le téléphone (${capability.label})."
                else -> try {
                    data = capability.fetch(context)
                } catch (fetchError: Exception) {
                    error = fetchError.message ?: "Erreur inconnue"
                }
            }
        }

        val response = buildJsonObject {
            put("type", "response")
            put("id", requestId)
            put("ok", data != null)
            if (data != null) put("data", data) else put("error", error ?: "Erreur inconnue")
        }
        session.send(Frame.Text(Json.encodeToString(JsonElement.serializer(), response)))
    }
}
