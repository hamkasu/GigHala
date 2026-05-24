package com.gighala.app.ui.settings

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Contrast
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material.icons.filled.LightMode
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.SettingsBrightness
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.gighala.app.ui.theme.ThemeMode
import com.gighala.app.ui.theme.ThemeViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    themeViewModel: ThemeViewModel,
    onBack: () -> Unit
) {
    val themeMode by themeViewModel.themeMode.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
        ) {
            Text(
                "App Theme",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(Modifier.height(12.dp))

            ThemeOption(
                icon        = Icons.Filled.LightMode,
                title       = "Light",
                description = "Always use light theme",
                selected    = themeMode == ThemeMode.LIGHT,
                onClick     = { themeViewModel.setThemeMode(ThemeMode.LIGHT) }
            )
            ThemeOption(
                icon        = Icons.Filled.DarkMode,
                title       = "Dark",
                description = "Always use dark theme",
                selected    = themeMode == ThemeMode.DARK,
                onClick     = { themeViewModel.setThemeMode(ThemeMode.DARK) }
            )
            ThemeOption(
                icon        = Icons.Filled.SettingsBrightness,
                title       = "System Default",
                description = "Follow your device theme setting",
                selected    = themeMode == ThemeMode.SYSTEM,
                onClick     = { themeViewModel.setThemeMode(ThemeMode.SYSTEM) }
            )
            ThemeOption(
                icon        = Icons.Filled.PhoneAndroid,
                title       = "AMOLED",
                description = "Pure-black dark theme — saves battery on OLED screens",
                selected    = themeMode == ThemeMode.AMOLED,
                onClick     = { themeViewModel.setThemeMode(ThemeMode.AMOLED) }
            )
            ThemeOption(
                icon        = Icons.Filled.Eco,
                title       = "Nature",
                description = "Warm earthy-green palette",
                selected    = themeMode == ThemeMode.NATURE,
                onClick     = { themeViewModel.setThemeMode(ThemeMode.NATURE) }
            )
            ThemeOption(
                icon        = Icons.Filled.Contrast,
                title       = "High Contrast",
                description = "Maximum contrast for improved accessibility",
                selected    = themeMode == ThemeMode.HIGH_CONTRAST,
                onClick     = { themeViewModel.setThemeMode(ThemeMode.HIGH_CONTRAST) }
            )
        }
    }
}

@Composable
private fun ThemeOption(
    icon: ImageVector,
    title: String,
    description: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (selected) MaterialTheme.colorScheme.primaryContainer
                             else MaterialTheme.colorScheme.surface
        ),
        border = if (selected) BorderStroke(2.dp, MaterialTheme.colorScheme.primary) else null
    ) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Icon(
                icon,
                contentDescription = null,
                tint = if (selected) MaterialTheme.colorScheme.primary
                       else MaterialTheme.colorScheme.onSurfaceVariant
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.bodyLarge)
                Text(
                    description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            RadioButton(selected = selected, onClick = onClick)
        }
    }
}
