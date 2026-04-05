package com.gighala.app.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gighala.app.data.repository.AuthRepository
import com.gighala.app.data.repository.AuthState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
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

    fun completeSocialLogin(host: String, rawCookies: String) {
        viewModelScope.launch { authRepository.completeSocialLogin(host, rawCookies) }
    }
}
