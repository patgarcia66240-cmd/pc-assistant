package com.aria.phonebridge.gateway.capabilities

import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.os.StatFs
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/**
 * Infos appareil "sans permission" : modèle, version Android, batterie, RAM, stockage — tout
 * ce qu'Android expose déjà sans demander l'accord de l'utilisatrice. Utilisée aussi bien
 * comme capacité explicite (get_device_info) que pour le snapshot renvoyé juste après un
 * appairage réussi (voir GatewayServer.kt, message auth_result).
 */
class DeviceInfoCapability : PhoneCapability {
    override val id = "device_info"
    override val label = "Informations appareil"
    override val requiredPermissions = emptyList<String>()

    override suspend fun fetch(context: Context): JsonElement = snapshot(context)

    companion object {
        fun snapshot(context: Context): JsonElement {
            val batteryStatus = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            val level = batteryStatus?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
            val scale = batteryStatus?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
            val batteryPercent = if (level >= 0 && scale > 0) (level * 100 / scale) else null
            val status = batteryStatus?.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
            val isCharging = status == BatteryManager.BATTERY_STATUS_CHARGING || status == BatteryManager.BATTERY_STATUS_FULL

            val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
            val memoryInfo = ActivityManager.MemoryInfo()
            activityManager.getMemoryInfo(memoryInfo)

            val stat = StatFs(Environment.getDataDirectory().path)
            val totalStorage = stat.blockCountLong * stat.blockSizeLong
            val freeStorage = stat.availableBlocksLong * stat.blockSizeLong

            return buildJsonObject {
                put("manufacturer", Build.MANUFACTURER)
                put("model", Build.MODEL)
                put("android_version", Build.VERSION.RELEASE)
                put("sdk_int", Build.VERSION.SDK_INT)
                put("battery_percent", batteryPercent)
                put("is_charging", isCharging)
                put("total_ram_bytes", memoryInfo.totalMem)
                put("available_ram_bytes", memoryInfo.availMem)
                put("total_storage_bytes", totalStorage)
                put("free_storage_bytes", freeStorage)
            }
        }
    }
}
