package com.aria.phonebridge.gateway

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.aria.phonebridge.MainActivity
import com.aria.phonebridge.R

/**
 * Service de premier plan : sans lui, Android suspend/tue le socket de GatewayServer dès que
 * l'app quitte le premier plan (comportement standard depuis Android 8+, encore plus strict
 * sur les versions récentes). La notification persistante est le prix normal de ce
 * fonctionnement — impossible de faire du réseau en tâche de fond sans elle.
 */
class GatewayForegroundService : Service() {

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val port = intent?.getIntExtra(EXTRA_PORT, PairingManager.DEFAULT_PORT) ?: PairingManager.DEFAULT_PORT
        startForeground(NOTIFICATION_ID, buildNotification(port))
        GatewayServer.start(this, port)
        return START_STICKY
    }

    override fun onDestroy() {
        GatewayServer.stop()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun buildNotification(port: Int): Notification {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, getString(R.string.notification_channel_name), NotificationManager.IMPORTANCE_LOW)
            )
        }

        val openApp = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val ip = LocalNetworkInfo.currentIpAddress(this) ?: "?"

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(getString(R.string.notification_running, ip, port))
            .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
            .setContentIntent(openApp)
            .setOngoing(true)
            .build()
    }

    companion object {
        private const val CHANNEL_ID = "aria_gateway"
        private const val NOTIFICATION_ID = 1
        private const val EXTRA_PORT = "port"

        fun start(context: Context, port: Int) {
            val intent = Intent(context, GatewayForegroundService::class.java).putExtra(EXTRA_PORT, port)
            context.startForegroundService(intent)
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, GatewayForegroundService::class.java))
        }
    }
}
