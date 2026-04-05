package com.gighala.app.ui.auth

import android.annotation.SuppressLint
import android.webkit.CookieManager
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.hilt.navigation.compose.hiltViewModel
import com.gighala.app.BuildConfig

/**
 * Full-screen WebView that handles OAuth flows for Google, X, and Facebook.
 * When the backend redirects to /dashboard after a successful login, we extract
 * the session cookie from the WebView and inject it into OkHttp's cookie jar,
 * then call onSuccess so the app transitions to the main screens.
 */
@SuppressLint("SetJavaScriptEnabled")
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SocialLoginScreen(
    provider: String,          // "google" | "x" | "facebook"
    onSuccess: () -> Unit,
    onBack: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel()
) {
    val authState by viewModel.authState.collectAsState()

    // Navigate away as soon as auth state flips to Authenticated
    LaunchedEffect(authState) {
        if (authState is com.gighala.app.data.repository.AuthState.Authenticated) onSuccess()
    }

    val oauthUrl = "${BuildConfig.BASE_URL}/api/auth/$provider"
    val baseHost  = BuildConfig.BASE_URL
        .removePrefix("https://")
        .removePrefix("http://")
        .substringBefore(":")   // strip port for cookie lookup

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    val label = when (provider) {
                        "google"   -> "Continue with Google"
                        "x"        -> "Continue with X"
                        "facebook" -> "Continue with Facebook"
                        else       -> "Social Login"
                    }
                    Text(label)
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        AndroidView(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            factory = { context ->
                WebView(context).apply {
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled  = true

                    // Sync WebView cookies with OkHttp after each page load
                    webViewClient = object : WebViewClient() {
                        override fun shouldOverrideUrlLoading(
                            view: WebView,
                            request: WebResourceRequest
                        ): Boolean {
                            val url = request.url.toString()
                            if (url.contains("/dashboard")) {
                                // OAuth succeeded — grab cookies and hand off to OkHttp
                                val rawCookies = CookieManager.getInstance()
                                    .getCookie(url) ?: ""
                                viewModel.completeSocialLogin(baseHost, rawCookies)
                                return true
                            }
                            return false // let WebView handle it
                        }

                        override fun onPageFinished(view: WebView, url: String) {
                            super.onPageFinished(view, url)
                            if (url.contains("/dashboard")) {
                                val rawCookies = CookieManager.getInstance()
                                    .getCookie(url) ?: ""
                                viewModel.completeSocialLogin(baseHost, rawCookies)
                            }
                        }
                    }

                    loadUrl(oauthUrl)
                }
            }
        )
    }
}
