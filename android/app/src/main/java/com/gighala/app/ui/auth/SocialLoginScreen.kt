package com.gighala.app.ui.auth

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.net.http.SslError
import android.webkit.*
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.BuildConfig

@SuppressLint("SetJavaScriptEnabled")
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SocialLoginScreen(
    provider: String,
    onSuccess: () -> Unit,
    onBack: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel()
) {
    val authState by viewModel.authState.collectAsState()
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(authState) {
        if (authState is com.gighala.app.data.repository.AuthState.Authenticated) onSuccess()
    }

    val oauthUrl = "${BuildConfig.BASE_URL}/api/auth/$provider"
    val baseHost = BuildConfig.BASE_URL
        .removePrefix("https://")
        .removePrefix("http://")
        .substringBefore(":")

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
                .padding(padding)
        ) {
            val error = errorMessage
            if (error != null) {
                // Error state
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Icon(
                        Icons.Filled.ErrorOutline,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.error
                    )
                    Spacer(Modifier.height(16.dp))
                    Text(
                        "$providerLabel login is not available",
                        style = MaterialTheme.typography.titleMedium,
                        textAlign = TextAlign.Center
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "Social login requires the GigHala production server. " +
                        "Please use email/password login for local development.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                    Spacer(Modifier.height(24.dp))
                    Button(onClick = onBack) { Text("Go Back") }
                }
            } else {
                AndroidView(
                    modifier = Modifier.fillMaxSize(),
                    factory = { context ->
                        WebView(context).apply {
                            settings.javaScriptEnabled = true
                            settings.domStorageEnabled  = true

                            webViewClient = object : WebViewClient() {
                                override fun onPageStarted(view: WebView, url: String, favicon: Bitmap?) {
                                    isLoading = true
                                }

                                override fun onPageFinished(view: WebView, url: String) {
                                    isLoading = false
                                    if (url.contains("/dashboard")) {
                                        val rawCookies = CookieManager.getInstance().getCookie(url) ?: ""
                                        viewModel.completeSocialLogin(baseHost, rawCookies)
                                    }
                                }

                                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                                    val url = request.url.toString()
                                    if (url.contains("/dashboard")) {
                                        val rawCookies = CookieManager.getInstance().getCookie(url) ?: ""
                                        viewModel.completeSocialLogin(baseHost, rawCookies)
                                        return true
                                    }
                                    return false
                                }

                                override fun onReceivedError(
                                    view: WebView,
                                    request: WebResourceRequest,
                                    error: WebResourceError
                                ) {
                                    if (request.isForMainFrame) {
                                        isLoading = false
                                        errorMessage = error.description.toString()
                                    }
                                }

                                override fun onReceivedHttpError(
                                    view: WebView,
                                    request: WebResourceRequest,
                                    errorResponse: WebResourceResponse
                                ) {
                                    if (request.isForMainFrame && errorResponse.statusCode >= 500) {
                                        isLoading = false
                                        errorMessage = "Server error (${errorResponse.statusCode})"
                                    }
                                }

                                @SuppressLint("WebViewClientOnReceivedSslError")
                                override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
                                    // Reject SSL errors — don't proceed
                                    handler.cancel()
                                    isLoading = false
                                    errorMessage = "SSL error"
                                }
                            }

                            loadUrl(oauthUrl)
                        }
                    }
                )

                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
            }
        }
    }
}
