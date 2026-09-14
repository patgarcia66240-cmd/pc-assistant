package com.aria.phonebridge.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * Écran unique de l'app : statut de la passerelle, IP/port/jeton à recopier côté ARIA
 * (backend/plugins/android_bridge/, onglet "Téléphone" du frontend), et l'état de chaque
 * capacité (accordée ou non) avec un bouton pour ouvrir la demande de permission correspondante.
 */
@Composable
fun GatewayScreen(
    state: GatewayUiState,
    onToggleServer: () -> Unit,
    onRegenerateToken: () -> Unit,
    onRequestPermission: (List<String>) -> Unit,
) {
    Scaffold(topBar = { TopAppBar(title = { Text("ARIA Phone Bridge") }) }) { padding ->
        Column(modifier = Modifier.padding(padding).padding(16.dp)) {
            StatusCard(state, onToggleServer)
            Spacer(Modifier.height(16.dp))
            if (state.running) PairingCard(state, onRegenerateToken)
            Spacer(Modifier.height(16.dp))
            Text("Capacités", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(state.capabilities) { capability ->
                    CapabilityRow(capability, onRequestPermission)
                }
            }
        }
    }
}

@Composable
private fun StatusCard(state: GatewayUiState, onToggleServer: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(if (state.running) "Passerelle active" else "Passerelle arrêtée", style = MaterialTheme.typography.titleMedium)
                Button(onClick = onToggleServer) { Text(if (state.running) "Arrêter" else "Démarrer") }
            }
            if (state.running) {
                Spacer(Modifier.height(8.dp))
                Text("Clients connectés : ${state.connectedClients}", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun PairingCard(state: GatewayUiState, onRegenerateToken: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Informations d'appairage", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            LabelValue("Adresse IP", state.ipAddress ?: "Indisponible (connecte-toi au Wi-Fi)")
            LabelValue("Port", state.port.toString())
            LabelValue("Jeton", state.token)
            Spacer(Modifier.height(8.dp))
            OutlinedButton(onClick = onRegenerateToken) { Text("Régénérer le jeton") }
            Spacer(Modifier.height(4.dp))
            Text(
                "Ne partage ce jeton qu'avec ton propre PC ARIA. Le régénérer déconnecte tout PC déjà appairé.",
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun LabelValue(label: String, value: String) {
    Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
        Text(label, style = MaterialTheme.typography.bodyMedium)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun CapabilityRow(capability: CapabilityUiState, onRequestPermission: (List<String>) -> Unit) {
    Surface(tonalElevation = 1.dp, modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(capability.label)
            if (capability.granted) {
                Text("Autorisé", color = MaterialTheme.colorScheme.primary)
            } else {
                OutlinedButton(onClick = { onRequestPermission(capability.permissions) }) {
                    Text("Autoriser")
                }
            }
        }
    }
}
