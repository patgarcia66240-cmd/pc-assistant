package com.aria.phonebridge.gateway.capabilities

import android.Manifest
import android.content.Context
import android.provider.ContactsContract
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/**
 * Première capacité de la passerelle (celle demandée en priorité) : la liste des contacts,
 * nom + numéros de téléphone. Un contact peut avoir plusieurs numéros (mobile, fixe...), donc
 * regroupés sous une seule entrée par CONTACT_ID plutôt qu'une ligne par numéro comme le
 * renvoie le ContentProvider brut.
 */
class ContactsCapability : PhoneCapability {
    override val id = "contacts"
    override val label = "Contacts"
    override val requiredPermissions = listOf(Manifest.permission.READ_CONTACTS)

    override suspend fun fetch(context: Context): JsonElement = withContext(Dispatchers.IO) {
        if (!hasPermission(context)) {
            error("Permission READ_CONTACTS non accordée sur le téléphone.")
        }

        // contactId -> (nom, numéros) : agrégation manuelle car ContactsContract.CommonDataKinds
        // .Phone renvoie une ligne par numéro, plusieurs lignes peuvent partager le même
        // CONTACT_ID pour un contact ayant plusieurs numéros.
        val numbersByContact = LinkedHashMap<String, Pair<String, MutableList<String>>>()

        val projection = arrayOf(
            ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
            ContactsContract.CommonDataKinds.Phone.NUMBER,
        )
        context.contentResolver.query(
            ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
            projection,
            null,
            null,
            "${ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME} ASC",
        )?.use { cursor ->
            val idIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.CONTACT_ID)
            val nameIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
            val numberIndex = cursor.getColumnIndexOrThrow(ContactsContract.CommonDataKinds.Phone.NUMBER)
            while (cursor.moveToNext()) {
                val contactId = cursor.getString(idIndex) ?: continue
                val name = cursor.getString(nameIndex) ?: ""
                val number = cursor.getString(numberIndex)?.trim().orEmpty()
                val entry = numbersByContact.getOrPut(contactId) { name to mutableListOf() }
                if (number.isNotEmpty() && number !in entry.second) entry.second.add(number)
            }
        }

        buildJsonArray {
            for ((contactId, entry) in numbersByContact) {
                val (name, numbers) = entry
                add(buildJsonObject {
                    put("id", contactId)
                    put("name", JsonPrimitive(name))
                    put("numbers", JsonArray(numbers.map { JsonPrimitive(it) }))
                })
            }
        }
    }
}
