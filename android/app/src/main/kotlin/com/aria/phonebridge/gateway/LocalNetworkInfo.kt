package com.aria.phonebridge.gateway

import android.content.Context
import android.net.ConnectivityManager
import android.net.LinkAddress
import android.net.LinkProperties
import java.net.Inet4Address

/** Trouve l'IPv4 locale de l'interface réseau active (Wi-Fi normalement) — c'est cette adresse
 * que l'utilisatrice recopie côté ARIA pour l'appairage (voir GatewayScreen.kt). */
object LocalNetworkInfo {
    fun currentIpAddress(context: Context): String? {
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return null
        val network = connectivityManager.activeNetwork ?: return null
        val linkProperties: LinkProperties = connectivityManager.getLinkProperties(network) ?: return null
        return linkProperties.linkAddresses
            .mapNotNull(LinkAddress::getAddress)
            .filterIsInstance<Inet4Address>()
            .firstOrNull { !it.isLoopbackAddress }
            ?.hostAddress
    }
}
