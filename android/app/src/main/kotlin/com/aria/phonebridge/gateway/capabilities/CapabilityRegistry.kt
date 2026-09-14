package com.aria.phonebridge.gateway.capabilities

import android.content.Context
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/**
 * Point d'extension unique de la passerelle : toutes les capacités exposées aux requêtes du PC
 * (voir GatewayServer.kt) sont listées ici. Pour en ajouter une nouvelle (SMS, localisation,
 * notifications...), implémente PhoneCapability dans un nouveau fichier et ajoute-la à la
 * liste ci-dessous — le routage de l'action "get_<id>" et l'entrée dans get_capabilities
 * suivent automatiquement.
 */
object CapabilityRegistry {
    private val all: List<PhoneCapability> = listOf(
        ContactsCapability(),
        DeviceInfoCapability(),
    )

    private val byAction: Map<String, PhoneCapability> = all.associateBy { "get_${it.id}" }

    fun find(action: String): PhoneCapability? = byAction[action]

    fun listCapabilities(context: Context) = buildJsonArray {
        for (capability in all) {
            add(buildJsonObject {
                put("id", capability.id)
                put("label", capability.label)
                put("granted", capability.hasPermission(context))
                put("permissions", JsonArray(capability.requiredPermissions.map { JsonPrimitive(it) }))
            })
        }
    }
}
