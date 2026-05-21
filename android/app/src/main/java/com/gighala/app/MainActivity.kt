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
        when (data.scheme) {
            "gighala" -> when (data.host) {
                "oauth" -> {
                    val token = data.getQueryParameter("token") ?: return
                    authViewModel.exchangeMobileToken(token)
                }
                "payment" -> {
                    val status = data.getQueryParameter("status") ?: "error"
                    val gigId  = data.getQueryParameter("gig_id")?.toIntOrNull()
                    paymentViewModel.set(status, gigId)
                }
            }
        }
    }
}
