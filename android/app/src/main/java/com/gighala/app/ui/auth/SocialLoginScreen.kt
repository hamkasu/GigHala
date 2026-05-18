package com.gighala.app.ui.auth

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.BuildConfig
import com.gighala.app.data.repository.AuthState

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

    LaunchedEffect(authState) {
        if (authState is AuthState.Authenticated) onSuccess()
    }

    // Open OAuth in the real default browser (not Custom Tabs, which can fall back to
    // an in-process WebView and trigger Google's disallowed_useragent block).
    LaunchedEffect(Unit) {
        val oauthUrl = "${BuildConfig.BASE_URL}/google_login?source=android"
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(oauthUrl)).apply {
            addCategory(Intent.CATEGORY_BROWSABLE)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
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
                if (uiState.isLoading) {
                    CircularProgressIndicator()
                    Text(
                        "Completing sign-in…",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else if (uiState.error != null) {
                    Text(
                        "Sign-in failed",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text(
                        uiState.error!!,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                        textAlign = TextAlign.Center
                    )
                    Spacer(Modifier.height(8.dp))
                    Button(onClick = onBack) { Text("Go Back") }
                } else {
                    CircularProgressIndicator()
                    Text(
                        "Waiting for $providerLabel sign-in…",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                    Spacer(Modifier.height(8.dp))
                    TextButton(onClick = onBack) { Text("Cancel") }
                }
            }
        }
    }
}
