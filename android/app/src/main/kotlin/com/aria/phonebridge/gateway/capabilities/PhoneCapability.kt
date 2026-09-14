package com.aria.phonebridge.gateway.capabilities

import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import kotlinx.serialization.json.JsonElement

/**
 * Une capacité = une catégorie de données du téléphone exposée à la passerelle (contacts,
 * infos appareil, et demain SMS/notifications/localisation...). Chaque capacité déclare son
 * propre id d'action WebSocket ("get_contacts", ...) et sait dire si l'utilisatrice lui a déjà
 * accordé la permission Android nécessaire — voir CapabilityRegistry pour la liste complète et
 * GatewayServer.kt pour comment un "request" entrant y est routé.
 *
 * Ajouter une nouvelle capacité = un nouveau fichier qui implémente cette interface +
 * une ligne dans CapabilityRegistry.ALL, rien d'autre à toucher côté serveur.
 */
interface PhoneCapability {
    /** Identifiant utilisé à la fois comme action WebSocket ("get_<id>") et comme clé dans la
     * réponse de get_capabilities. */
    val id: String

    /** Libellé affiché dans l'UI Compose (GatewayScreen.kt). */
    val label: String

    /** Permissions runtime Android requises (vide si aucune, ex. infos appareil). */
    val requiredPermissions: List<String>

    fun hasPermission(context: Context): Boolean =
        requiredPermissions.all {
            ContextCompat.checkSelfPermission(context, it) == PackageManager.PERMISSION_GRANTED
        }

    /** Lève une exception avec un message déjà présentable si la permission manque ou si la
     * lecture échoue — GatewayServer.kt la convertit telle quelle en réponse "ok: false". */
    suspend fun fetch(context: Context): JsonElement
}
