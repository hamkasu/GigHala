package com.gighala.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.ViewModel
import com.gighala.app.data.api.models.PaymentResult
import com.gighala.app.ui.auth.AuthViewModel
import com.gighala.app.ui.navigation.AppNavigation
import com.gighala.app.ui.theme.GigHalaTheme
import com.gighala.app.ui.theme.ThemeMode
import com.gighala.app.ui.theme.ThemeViewModel
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Holds the last payment deep-link result so EscrowScreen can react to it. */
class PaymentStateViewModel : ViewModel() {
    private val _result = MutableStateFlow<PaymentResult?>(null)
    val result: StateFlow<PaymentResult?> = _result.asStateFlow()

    fun set(status: String, gigId: Int?) { _result.value = PaymentResult(status, gigId) }
    fun clear() { _result.value = null }
}

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private val authViewModel: AuthViewModel by viewModels()
    private val paymentViewModel: PaymentStateViewModel by viewModels()
    private val themeViewModel: ThemeViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        handleDeepLink(intent)
        setContent {
            val themeMode by themeViewModel.themeMode.collectAsState()
            val systemDark = isSystemInDarkTheme()
            val isDark = when (themeMode) {
                ThemeMode.LIGHT -> false
                ThemeMode.DARK -> true
                ThemeMode.SYSTEM -> systemDark
            }
            GigHalaTheme(darkTheme = isDark) {
                AppNavigation(
                    authViewModel = authViewModel,
                    paymentViewModel = paymentViewModel,
                    themeViewModel = themeViewModel
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleDeepLink(intent)
    }

    private fun handleDeepLink(intent: Intent) {
        val data = intent.data ?: return

        // Reject anything that isn't our custom scheme — belt-and-suspenders guard
        // against third-party apps sending spoofed intents.
        if (data.scheme != "gighala") return

        when (data.host) {
            "oauth" -> {
                val token = data.getQueryParameter("token") ?: return
                // Validate token format: alphanumeric + URL-safe chars, 10–500 chars.
                // Rejects empty strings, injected characters, and suspiciously long values.
                if (!TOKEN_REGEX.matches(token)) return
                authViewModel.exchangeMobileToken(token)
            }
            "payment" -> {
                val rawStatus = data.getQueryParameter("status") ?: "error"
                // Only accept known status values — default to "error" for anything else.
                val status = if (rawStatus in VALID_PAYMENT_STATUSES) rawStatus else "error"
                // gig_id must be a positive integer that fits in Int range.
                val gigId = data.getQueryParameter("gig_id")
                    ?.toLongOrNull()
                    ?.takeIf { it in 1..Int.MAX_VALUE }
                    ?.toInt()
                paymentViewModel.set(status, gigId)
            }
            // Unknown host — silently ignore to avoid processing unexpected deep links.
        }
    }

    companion object {
        /** Alphanumeric + URL-safe characters (-, _, .), 10–500 chars. */
        private val TOKEN_REGEX = Regex("[A-Za-z0-9_.\\-]{10,500}")
        private val VALID_PAYMENT_STATUSES = setOf("success", "cancel", "error")
    }
}
