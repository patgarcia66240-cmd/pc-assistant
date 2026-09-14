package com.aria.phonebridge.gateway

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.security.SecureRandom

/**
 * Génère et conserve le jeton d'appairage (le secret que le PC doit fournir pour se connecter
 * à la passerelle, voir GatewayServer.kt) dans des SharedPreferences chiffrées — ce jeton est
 * l'unique barrière entre "n'importe qui sur le Wi-Fi" et l'accès aux contacts/infos de
 * l'appareil, donc pas stocké en clair.
 *
 * Le port d'écoute par défaut (8765) est aussi mémorisé ici pour rester le même entre deux
 * lancements de l'app (plus simple à ressaisir côté ARIA, voir backend/plugins/android_bridge/
 * store.py qui persiste le dernier host/port/token utilisés avec succès).
 */
class PairingManager(context: Context) {
    private val prefs = EncryptedSharedPreferences.create(
        context,
        "aria_pairing",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    var port: Int
        get() = prefs.getInt(KEY_PORT, DEFAULT_PORT)
        set(value) = prefs.edit().putInt(KEY_PORT, value).apply()

    fun currentToken(): String =
        prefs.getString(KEY_TOKEN, null) ?: regenerateToken()

    fun regenerateToken(): String {
        val token = generateToken()
        prefs.edit().putString(KEY_TOKEN, token).apply()
        return token
    }

    /** Comparaison en temps constant : évite qu'une attaque par mesure de latence sur le
     * réseau local devine le jeton octet par octet. */
    fun verifyToken(candidate: String): Boolean {
        val expected = currentToken()
        if (candidate.length != expected.length) return false
        var diff = 0
        for (i in expected.indices) diff = diff or (expected[i].code xor candidate[i].code)
        return diff == 0
    }

    private fun generateToken(): String {
        val bytes = ByteArray(16)
        SecureRandom().nextBytes(bytes)
        return bytes.joinToString("") { "%02x".format(it) }
    }

    companion object {
        private const val KEY_TOKEN = "pairing_token"
        private const val KEY_PORT = "gateway_port"
        const val DEFAULT_PORT = 8765
    }
}
