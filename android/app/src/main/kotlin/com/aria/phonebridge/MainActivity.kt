package com.aria.phonebridge

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.aria.phonebridge.ui.GatewayScreen
import com.aria.phonebridge.ui.GatewayViewModel

class MainActivity : ComponentActivity() {
    private val viewModel: GatewayViewModel by viewModels()

    private val requestPermissions = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        viewModel.onPermissionResult()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Android 13+ : la notification du service de premier plan (GatewayForegroundService)
        // n'apparaît pas sans cette permission — demandée une fois au lancement, indépendamment
        // des capacités (contacts, etc.) demandées à la volée depuis GatewayScreen.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissions.launch(arrayOf(Manifest.permission.POST_NOTIFICATIONS))
        }

        setContent {
            MaterialTheme {
                val state by viewModel.state.collectAsState()
                GatewayScreen(
                    state = state,
                    onToggleServer = viewModel::toggleServer,
                    onRegenerateToken = viewModel::regenerateToken,
                    onRequestPermission = { permissions -> requestPermissions.launch(permissions.toTypedArray()) },
                )
            }
        }
    }
}
