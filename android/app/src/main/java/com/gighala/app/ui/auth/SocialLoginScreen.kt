package com.gighala.app.ui.auth

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import androidx.browser.customtabs.CustomTabColorSchemeParams
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.BuildConfig
import com.gighala.app.data.repository.AuthState
import kotlinx.coroutines.delay

/** GigHala brand green — matches the launcher icon background. */
private val GigHalaGreen = Color(0xFF2E7D32)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SocialLoginScreen(
    provider: String,
    onSuccess: () -> Unit,
    onBack: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    val authState by viewModel.authState.collectAsState()
    val uiState by viewModel.uiState.collectAsState()

    // Show a "didn't redirect?" helper after 12 s in case Chrome didn't fire
    // the deep link automatically (rare, but seen on some emulators).
    var showManualHelp by remember { mutableStateOf(false) }

    LaunchedEffect(authState) {
        if (authState is AuthState.Authenticated) onSuccess()
    }

    // Open OAuth in a Chrome Custom Tab.
    //
    // Custom Tabs (≠ WebView) send the full Chrome user-agent, so Google's
    // "disallowed_useragent" check does NOT block them.  They also handle
    // deep-link redirects (gighala://...) more reliably than an external
    // browser: when Chrome Custom Tab gets a custom-scheme redirect it fires
    // the intent directly to the owning app and closes the tab automatically.
    LaunchedEffect(Unit) {
        openOAuthCustomTab(context, provider)
        delay(12_000)
        showManualHelp = true
    }

    val providerLabel = when (provider) {
        "google"   -> "Google"
        "x"        -> "X"
        "facebook" -> "Facebook"
        else       -> provider.replaceFirstChar { it.uppercase() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Continue with $providerLabel") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp),
                modifier = Modifier.padding(32.dp)
            ) {
                when {
                    uiState.isLoading -> {
                        CircularProgressIndicator()
                        Text(
                            "Completing sign-in…",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    uiState.error != null -> {
                        Text("Sign-in failed", style = MaterialTheme.typography.titleMedium)
                        Text(
                            uiState.error!!,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error,
                            textAlign = TextAlign.Center
                        )
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = {
                            viewModel.clearError()
                            openOAuthCustomTab(context, provider)
                        }) { Text("Try Again") }
                        TextButton(onClick = onBack) { Text("Go Back") }
                    }

                    else -> {
                        CircularProgressIndicator()
                        Text(
                            "Waiting for $providerLabel sign-in…",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            textAlign = TextAlign.Center
                        )

                        if (showManualHelp) {
                            Spacer(Modifier.height(4.dp))
                            Card(
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                                )
                            ) {
                                Column(
                                    modifier = Modifier.padding(16.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Text(
                                        "Didn't redirect back automatically?",
                                        style = MaterialTheme.typography.labelMedium
                                    )
                                    Text(
                                        "If you completed sign-in in the browser but are stuck here, " +
                                            "tap the link on the browser page that says " +
                                            "\"Tap here if the app doesn't open\".",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        textAlign = TextAlign.Center
                                    )
                                    OutlinedButton(onClick = {
                                        openOAuthCustomTab(context, provider)
                                    }) { Text("Open Browser Again") }
                                }
                            }
                        }

                        Spacer(Modifier.height(4.dp))
                        TextButton(onClick = onBack) { Text("Cancel") }
                    }
                }
            }
        }
    }
}

/**
 * Opens the OAuth flow in a Chrome Custom Tab.
 *
 * Falls back to a plain ACTION_VIEW intent if Chrome / Custom Tabs is
 * unavailable (e.g. on an emulator without Chrome installed).
 */
private fun openOAuthCustomTab(context: android.content.Context, provider: String) {
    val path = when (provider) {
        "google" -> "/api/auth/google?source=android"
        else     -> "/api/auth/google?source=android"
    }
    val url = Uri.parse("${BuildConfig.BASE_URL}$path")

    val colorSchemeParams = CustomTabColorSchemeParams.Builder()
        .setToolbarColor(GigHalaGreen.toArgb())
        .build()

    val customTabsIntent = CustomTabsIntent.Builder()
        .setDefaultColorSchemeParams(colorSchemeParams)
        .setShowTitle(true)
        .setUrlBarHidingEnabled(false)
        .build()

    try {
        customTabsIntent.launchUrl(context, url)
    } catch (_: ActivityNotFoundException) {
        // Chrome / Custom Tabs not available — fall back to system browser
        val fallback = Intent(Intent.ACTION_VIEW, url).apply {
            addCategory(Intent.CATEGORY_BROWSABLE)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(fallback)
    }
}
