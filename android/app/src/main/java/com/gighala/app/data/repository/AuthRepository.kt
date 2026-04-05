package com.gighala.app.data.repository

import com.gighala.app.data.api.ApiService
import com.gighala.app.data.api.models.*
import com.gighala.app.util.PersistentCookieJar
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONObject
import retrofit2.Response
import javax.inject.Inject
import javax.inject.Singleton

sealed class AuthState {
    object Loading : AuthState()
    data class Authenticated(val user: UserDto) : AuthState()
    object Unauthenticated : AuthState()
    data class Requires2FA(val message: String) : AuthState()
}

@Singleton
class AuthRepository @Inject constructor(
    private val api: ApiService,
    private val cookieJar: PersistentCookieJar
) {
    private val _authState = MutableStateFlow<AuthState>(AuthState.Unauthenticated)
    val authState: StateFlow<AuthState> = _authState

    suspend fun login(email: String, password: String): Result<AuthResponse> = runCatching {
        val response = api.login(LoginRequest(email, password))
        val body = response.bodyOrError("Login failed")
        when {
            body.requires2fa -> _authState.value = AuthState.Requires2FA(body.message ?: "2FA required")
            body.success && body.user != null -> _authState.value = AuthState.Authenticated(body.user)
            else -> error(body.error ?: body.message ?: "Login failed")
        }
        body
    }

    suspend fun register(
        username: String,
        email: String,
        password: String,
        fullName: String,
        userType: String,
        privacyConsent: Boolean = true,
        socsoConsent: Boolean = true
    ): Result<AuthResponse> = runCatching {
        val response = api.register(RegisterRequest(username, email, password, fullName, userType, privacyConsent, socsoConsent))
        val body = response.bodyOrError("Registration failed")
        if (body.success && body.user != null) _authState.value = AuthState.Authenticated(body.user)
        else error(body.error ?: body.message ?: "Registration failed")
        body
    }

    suspend fun verify2fa(code: String): Result<AuthResponse> = runCatching {
        val response = api.verify2fa(Verify2faRequest(code))
        val body = response.bodyOrError("2FA verification failed")
        if (body.success && body.user != null) _authState.value = AuthState.Authenticated(body.user)
        else error(body.error ?: body.message ?: "2FA verification failed")
        body
    }

    /** Reads body() on success, or parses errorBody() JSON for the error/message field. */
    private fun Response<AuthResponse>.bodyOrError(fallback: String): AuthResponse {
        if (isSuccessful) return body() ?: AuthResponse()
        val errJson = errorBody()?.string() ?: return AuthResponse(error = fallback)
        return try {
            val obj = JSONObject(errJson)
            AuthResponse(error = obj.optString("error").ifEmpty { obj.optString("message", fallback) })
        } catch (_: Exception) {
            AuthResponse(error = fallback)
        }
    }

    suspend fun logout() {
        runCatching { api.logout() }
        cookieJar.clearAll()
        _authState.value = AuthState.Unauthenticated
    }

    suspend fun refreshCurrentUser() {
        if (!cookieJar.hasSession()) {
            _authState.value = AuthState.Unauthenticated
            return
        }
        runCatching {
            val response = api.getCurrentUser()
            if (response.isSuccessful && response.body() != null) {
                _authState.value = AuthState.Authenticated(response.body()!!)
            } else {
                _authState.value = AuthState.Unauthenticated
            }
        }.onFailure {
            _authState.value = AuthState.Unauthenticated
        }
    }

    fun currentUser(): UserDto? = (_authState.value as? AuthState.Authenticated)?.user

    /** Called after social OAuth in WebView — inject cookies then refresh user. */
    suspend fun completeSocialLogin(host: String, rawCookies: String) {
        cookieJar.injectRawCookies(host, rawCookies)
        refreshCurrentUser()
    }
}
