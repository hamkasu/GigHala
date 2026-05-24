package com.gighala.app.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.repository.AuthRepository
import com.gighala.app.data.repository.AuthState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    val authState: StateFlow<AuthState> = authRepository.authState

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    private var pollingJob: Job? = null

    init {
        viewModelScope.launch { authRepository.refreshCurrentUser() }
    }

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            authRepository.login(email.trim(), password)
                .onFailure { _uiState.value = AuthUiState(error = it.message) }
                .onSuccess { _uiState.value = AuthUiState() }
        }
    }

    fun register(
        username: String, email: String, password: String,
        fullName: String, userType: String,
        privacyConsent: Boolean = true, socsoConsent: Boolean = true
    ) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            authRepository.register(username.trim(), email.trim(), password, fullName.trim(), userType, privacyConsent, socsoConsent)
                .onFailure { _uiState.value = AuthUiState(error = it.message) }
                .onSuccess { _uiState.value = AuthUiState() }
        }
    }

    fun verify2fa(code: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            authRepository.verify2fa(code.trim())
                .onFailure { _uiState.value = AuthUiState(error = it.message) }
                .onSuccess { _uiState.value = AuthUiState() }
        }
    }

    fun logout() {
        viewModelScope.launch { authRepository.logout() }
    }

    fun clearError() { _uiState.value = _uiState.value.copy(error = null) }

    fun exchangeMobileToken(token: String) {
        viewModelScope.launch {
            _uiState.value = AuthUiState(isLoading = true)
            authRepository.exchangeMobileToken(token)
                .onFailure { _uiState.value = AuthUiState(error = it.message) }
                .onSuccess { _uiState.value = AuthUiState() }
        }
    }

    /**
     * Start polling the server every 2 s for OAuth completion identified by
     * [requestId].  When the server returns the bridge token, exchanges it
     * automatically — no deep link required.
     *
     * Stops automatically once auth state becomes Authenticated, or when
     * [stopMobilePolling] is called (e.g. on screen cancel / dispose).
     */
    fun startMobilePolling(requestId: String) {
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            // Phase 1: poll every 2 s until a bridge token arrives or job is cancelled.
            // Store the token in a local variable so Phase 2 can use it AFTER the loop
            // exits — this avoids the self-cancellation bug where calling
            // pollingJob?.cancel() inside the loop set the cancellation flag before the
            // subsequent suspend call (exchangeMobileToken) could complete, causing
            // runCatching to surface a CancellationException as a user-visible error.
            var bridgeToken: String? = null
            while (isActive && authRepository.authState.value !is AuthState.Authenticated) {
                delay(2_000)
                try {
                    val token = authRepository.pollMobileAuth(requestId)
                    if (token != null) {
                        bridgeToken = token
                        break
                    }
                } catch (e: CancellationException) {
                    throw e  // Never swallow coroutine cancellation
                } catch (_: Exception) {
                    // Network hiccup — swallow and retry on next tick
                }
            }

            // Phase 2: exchange the token (runs in the same coroutine, which is
            // still active because we broke cleanly — no self-cancellation).
            val token = bridgeToken ?: return@launch
            if (!isActive) return@launch
            _uiState.value = AuthUiState(isLoading = true)
            authRepository.exchangeMobileToken(token)
                .onFailure { _uiState.value = AuthUiState(error = it.message) }
                .onSuccess { _uiState.value = AuthUiState() }
        }
    }

    fun stopMobilePolling() {
        pollingJob?.cancel()
        pollingJob = null
    }
}
